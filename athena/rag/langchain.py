import os
from typing import Dict, List, Optional

# LangChain imports (best-effort; guard missing libs by raising clear errors)
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore[import-not-found]
except Exception:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore[import-not-found]
    except Exception as e:  # noqa: BLE001
        raise ImportError("Install langchain-text-splitters to enable document chunking.") from e

try:
    from langchain.document_loaders import PyPDFLoader  # type: ignore[import-not-found]
except Exception:
    try:
        from langchain_community.document_loaders import PyPDFLoader  # type: ignore[import-not-found]
    except Exception as e:  # noqa: BLE001
        raise ImportError("Install langchain-community to enable PDF loading.") from e

try:
    from langchain_core.prompts import ChatPromptTemplate
except Exception as e:  # noqa: BLE001
    raise ImportError("Install langchain-core to enable prompt templates.") from e

def _get_llm():
    """
    Use OpenAI Chat model via OPENAI_API_KEY. Fail fast with a clear error if it's not set
    or if the OpenAI chat model client isn't available.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY not set. Export it (or set it in the environment) to use OpenAI.")

    last_err = None

    # Preferred: langchain_openai package (actively maintained)
    try:
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

        return ChatOpenAI(
            temperature=0.1,
            model_name="gpt-4o-mini",
            openai_api_key=openai_key,
            max_tokens=1000,
        )
    except Exception as e:  # noqa: BLE001
        last_err = e

    # Legacy import paths kept for backwards compatibility
    try:
        from langchain.chat_models import ChatOpenAI  # type: ignore[import-not-found]
        return ChatOpenAI(temperature=0.1, model_name="gpt-4o-mini", openai_api_key=openai_key, max_tokens=1000)
    except Exception as e:
        last_err = e

    try:
        # Alternate import path
        from langchain.chat_models.openai import ChatOpenAI  # type: ignore[import-not-found]
        return ChatOpenAI(temperature=0.1, model_name="gpt-4o-mini", openai_api_key=openai_key, max_tokens=1000)
    except Exception as e:
        last_err = e

    # Absolute fallback: call OpenAI directly without LangChain wrappers
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)

        class _DirectChat:
            def __init__(self, client):
                self._client = client

            def invoke(self, params: Dict[str, str]):
                messages = [
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": params["input"]},
                ]
                resp = self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                )
                return resp.choices[0].message

            def __ror__(self, other):
                # Allow prompt_template | llm usage
                prompt = other

                class _Chained:
                    def __init__(self, prompt, llm):
                        self.prompt = prompt
                        self.llm = llm

                    def invoke(self, inputs):
                        rendered = self.prompt.format(**inputs)
                        return self.llm.invoke({"input": rendered})

                return _Chained(prompt, self)

        return _DirectChat(client)
    except Exception as e:  # noqa: BLE001
        last_err = e

    raise RuntimeError(
        "OpenAI Chat model client not available. Install langchain-openai or ensure the OpenAI SDK is installed. "
        f"Underlying error: {last_err}"
    )

def _get_embeddings():
    """
    Use OpenAI embeddings (OpenAIEmbeddings). Uses OPENAI_API_KEY from env.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY not set. Export it (or set it in the environment) to use OpenAI embeddings.")

    # Try a couple of import paths used by different LangChain versions
    try:
        # langchain-openai package or new names
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(openai_api_key=openai_key)
    except Exception:
        pass

    try:
        from langchain.embeddings import OpenAIEmbeddings
        return OpenAIEmbeddings(openai_api_key=openai_key)
    except Exception as e:
        raise RuntimeError("OpenAIEmbeddings not available. Install langchain_openai or an up-to-date langchain. "
                           f"Underlying error: {e}")

def retrieve_from_document(pdf_path: str, question: str, chunk_size: int = 1000, chunk_overlap: int = 200, max_docs: int = 10) -> Dict:
    """
    Load the given PDF, build vector embeddings (in-memory FAISS), run a retrieval chain, and return answer + context.

    Returns:
      {
        "answer": "<text answer>",
        "context": [{"page_content": "...", "metadata": {...}}, ...],
        "source_docs": n
      }
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # 1) Load PDF
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    if not docs:
        return {"answer": "", "context": [], "source_docs": 0}

    # 2) Chunk documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs)
    # keep a reasonably large pool but avoid insane sizes; keep at least all chunks if few
    chunks = chunks[: max(50, len(chunks))]

    # 3) Create embeddings
    embeddings = _get_embeddings()

    # 4) Build vectorstore (FAISS preferred to avoid persistent Chroma issues)
    try:
        from langchain_community.vectorstores import FAISS as CommunityFAISS  # type: ignore[import-not-found]
        vect = CommunityFAISS.from_documents(chunks, embeddings)
    except Exception:
        try:
            from langchain.vectorstores import FAISS  # type: ignore[import-not-found]
            vect = FAISS.from_documents(chunks, embeddings)
        except Exception as e:
            raise RuntimeError(f"Failed to build vectorstore: {e}")

    retriever = vect.as_retriever(search_kwargs={"k": max_docs})

    # 5) Retrieve supporting documents
    retrieval_error = None
    ctx_docs: List = []

    def _normalize_docs(result):
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            if "documents" in result:
                return result["documents"]
            if "context" in result:
                return result["context"]
        return []

    try:
        if hasattr(retriever, "get_relevant_documents"):
            ctx_docs = retriever.get_relevant_documents(question)
        elif hasattr(retriever, "invoke"):
            ctx_docs = _normalize_docs(retriever.invoke(question))
        elif callable(getattr(retriever, "__call__", None)):
            ctx_docs = _normalize_docs(retriever(question))
        else:
            retrieval_error = "Retriever does not expose a compatible interface."
    except Exception as exc:
        retrieval_error = str(exc)
        ctx_docs = []

    if not ctx_docs:
        # Fall back to a lightweight keyword heuristic before giving up entirely.
        lowered_terms = [t for t in question.lower().split() if len(t) > 2]
        scored_chunks = []
        for doc in chunks:
            text = getattr(doc, "page_content", "").lower()
            score = sum(text.count(term) for term in lowered_terms)
            scored_chunks.append((score, doc))

        scored_chunks.sort(key=lambda item: item[0], reverse=True)
        ctx_docs = [doc for score, doc in scored_chunks if score > 0][:max_docs]

        # If keyword matching still yields nothing, return the first few chunks
        if not ctx_docs:
            ctx_docs = chunks[:max_docs]

    context_text = "\n\n".join(
        f"[Page {doc.metadata.get('page', '?')}] {doc.page_content}"
        for doc in ctx_docs
    )
    if not context_text:
        context_text = "No additional context was retrieved."

    # 6) Build LLM prompt and generate answer
    llm = _get_llm()
    prompt_template = ChatPromptTemplate.from_template(
        (
            "You are a helpful research assistant. Answer the question strictly "
            "using the provided context. If the context is insufficient, say so.\n"
            "<context>\n{context}\n</context>\nQuestion: {input}"
        )
    )
    chain = prompt_template | llm

    result = chain.invoke({"context": context_text, "input": question})
    if hasattr(result, "content"):
        answer = result.content.strip()
    elif isinstance(result, dict) and "content" in result:
        answer = result["content"].strip()
    else:
        answer = str(result).strip()

    ctx_items = []
    for doc in ctx_docs:
        meta = dict(getattr(doc, "metadata", {}) or {})
        if retrieval_error and "retrieval_warning" not in meta:
            meta["retrieval_warning"] = retrieval_error
        ctx_items.append(
            {
                "page_content": getattr(doc, "page_content", ""),
                "metadata": meta,
            }
        )

    return {"answer": answer, "context": ctx_items, "source_docs": len(ctx_items)}
