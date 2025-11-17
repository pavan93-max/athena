import os
from typing import Dict, List, Optional

# LangChain imports (best-effort; guard missing libs by raising clear errors)
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.document_loaders import PyPDFLoader
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains import create_retrieval_chain
except Exception as e:
    raise ImportError(f"Install required langchain packages: {e}")

def _get_llm():
    """
    Use OpenAI Chat model via OPENAI_API_KEY. Fail fast with a clear error if it's not set
    or if the OpenAI chat model client isn't available.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY not set. Export it (or set it in the environment) to use OpenAI.")

    # Try common LangChain OpenAI Chat client import locations
    last_err = None
    try:
        # Newer langchain versions:
        from langchain.chat_models import ChatOpenAI
        return ChatOpenAI(temperature=0.1, model_name="gpt-4o-mini", openai_api_key=openai_key, max_tokens=1000)
    except Exception as e:
        last_err = e

    try:
        # Alternate import path
        from langchain.chat_models.openai import ChatOpenAI
        return ChatOpenAI(temperature=0.1, model_name="gpt-4o-mini", openai_api_key=openai_key, max_tokens=1000)
    except Exception as e:
        last_err = e

    raise RuntimeError(
        "OpenAI Chat model client not available. Install a compatible LangChain OpenAI client. "
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
        from langchain_community.vectorstores import FAISS as CommunityFAISS
        vect = CommunityFAISS.from_documents(chunks, embeddings)
    except Exception:
        try:
            from langchain.vectorstores import FAISS
            vect = FAISS.from_documents(chunks, embeddings)
        except Exception as e:
            raise RuntimeError(f"Failed to build vectorstore: {e}")

    retriever = vect.as_retriever(search_kwargs={"k": max_docs})

    # 5) Build LLM + prompt chain
    llm = _get_llm()
    prompt_template = ChatPromptTemplate.from_template(
        """
        Answer the question based on the context below. If you don't know the answer, say you don't know.
        <context>
        {context}
        </context>
        Question: {input}
        """
    )
    doc_chain = create_stuff_documents_chain(llm, prompt_template)
    retrieval_chain = create_retrieval_chain(retriever, doc_chain)

    # 6) Run retrieval chain
    result = retrieval_chain.invoke({"input": question})

    # Normalize result
    answer = ""
    if isinstance(result, dict):
        answer = result.get("answer") or result.get("output") or result.get("text") or str(result)
    else:
        answer = str(result)

    # Gather context: try to pull context from the result, otherwise fetch relevant docs from retriever
    context = result.get("context") if isinstance(result, dict) and "context" in result else None
    try:
        if context:
            ctx_docs = context
        else:
            # many retrievers expose get_relevant_documents; fall back gracefully
            ctx_docs = retriever.get_relevant_documents(question) if hasattr(retriever, "get_relevant_documents") else []
        ctx_items = [{"page_content": d.page_content, "metadata": getattr(d, "metadata", {})} for d in ctx_docs]
    except Exception:
        # Last-resort: empty context
        ctx_items = []

    return {"answer": answer, "context": ctx_items, "source_docs": len(ctx_items)}
