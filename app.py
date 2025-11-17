import streamlit as st
import os
import time
from pathlib import Path
import shutil
import traceback
import tempfile
from dotenv import load_dotenv

# Do not construct Orchestrator at import time (avoid loading models / DB on startup)
orchestrator = None
Orchestrator = None

def ensure_orchestrator(chroma_dir: str = "./chroma_db"):
    global orchestrator, Orchestrator
    if orchestrator is None:
        try:
            mod = __import__("athena.agents.orchestrator", fromlist=["Orchestrator"])
            Orchestrator = getattr(mod, "Orchestrator")
            orchestrator = Orchestrator(chroma_dir=chroma_dir)
        except Exception as e:
            st.sidebar.error("Failed to initialize Orchestrator: " + str(e))
            st.sidebar.text("Full traceback in logs")
            st.sidebar.text(traceback.format_exc())
            orchestrator = None
    return orchestrator

load_dotenv(".env")

if not hasattr(st, "experimental_rerun"):
    st.experimental_rerun = st.rerun

st.set_page_config(page_title="Athena Research Assistant", layout="wide")

st.title("Athena — Agentic Research Assistant (Prototype)")

# Always prompt for session-only OpenAI API key in sidebar
try:
    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = ""
    api_key = st.sidebar.text_input(
        "OpenAI API key (session only)",
        value=st.session_state["openai_api_key"],
        type="password",
        help="Enter your OpenAI API key here. The key is kept in session only and not written to disk.",
        key="openai_api_key_input",
    )
    if api_key:
        st.session_state["openai_api_key"] = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    else:
        os.environ.pop("OPENAI_API_KEY", None)
except Exception:
    pass

# Semantic Scholar API key
try:
    if "semantic_scholar_api_key" not in st.session_state:
        st.session_state["semantic_scholar_api_key"] = "vBOi9Ku9PS6YOkIeyMyo93f9LmlKeHvB8C1MfBfa"
    semantic_key = st.sidebar.text_input(
        "Semantic Scholar API key",
        value=st.session_state["semantic_scholar_api_key"],
        type="password",
        help="Enter your Semantic Scholar API key here.",
        key="semantic_scholar_api_key_input",
    )
    if semantic_key:
        st.session_state["semantic_scholar_api_key"] = semantic_key
except Exception:
    pass

chroma_dir = os.environ.get("CHROMA_DIR", "./chroma_db")
persist_path = Path(chroma_dir)

# ensure last uploaded path exists in session
if "last_uploaded_path" not in st.session_state:
    st.session_state["last_uploaded_path"] = ""

# Sidebar: ingest & reset DB
with st.sidebar:
    st.header("Ingest")
    uploaded_files = st.file_uploader(
        "Upload one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploader",
    )
    if uploaded_files:
        st.session_state["uploaded_files"] = uploaded_files

    if st.button("Ingest PDF", key="ingest_pdf_btn"):
        ensure_orchestrator(chroma_dir=chroma_dir)
        if orchestrator is None:
            st.warning("Cannot ingest: Orchestrator failed to initialize. See sidebar for details.")
        else:
            files_to_process = st.session_state.get("uploaded_files", [])
            if not files_to_process:
                st.warning("Please upload at least one PDF.")
            else:
                os.makedirs("./uploads", exist_ok=True)
                total = len(files_to_process)
                successes = 0
                for idx, uploaded_file in enumerate(files_to_process, 1):
                    path = f"./uploads/{uploaded_file.name}"
                    with open(path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    try:
                        res = orchestrator.ingest_pdf(path)
                        pages = res.get("ingested_pages", "unknown")
                        st.success(f"[{idx}/{total}] Ingested {uploaded_file.name} ({pages} pages).")
                        st.session_state["last_uploaded_path"] = path
                        successes += 1
                    except Exception as ex:
                        st.error(f"[{idx}/{total}] Failed to ingest {uploaded_file.name}: {ex}")

                if successes and successes == total:
                    st.info(f"Finished ingesting {total} PDF(s).")
                elif successes:
                    st.info(f"Ingested {successes} of {total} PDF(s).")

    # Reset local Chroma DB button
    st.markdown("---")
    if persist_path.exists():
        if st.button("Reset local Chroma DB (delete data)", key="reset_db_btn"):
            try:
                orchestrator = None
                shutil.rmtree(persist_path)
                st.success(f"Deleted {persist_path}. Restarting app...")
                st.experimental_rerun()
            except Exception as ex:
                st.error(f"Failed to delete {persist_path}: {ex}")
    else:
        st.info(f"No local Chroma DB found at {persist_path}.")

# ---------------- Query & Synthesize ----------------
st.header("Query & Synthesize")
query = "Run Synthesis"

if st.button("Run Synthesis", key="run_synthesis_btn"):
    ensure_orchestrator(chroma_dir=chroma_dir)
    if orchestrator is None:
        st.warning("Cannot run synthesis: Orchestrator failed to initialize. See sidebar for details.")
    else:
        if not query:
            st.warning("Enter query first.")
        else:
            with st.spinner("Running retrieval + debates..."):
                out = orchestrator.query_and_synthesize(query)
            st.success("Synthesis complete.")
            st.write("Claims found:")
            for c in out.get("claims", []):
                st.markdown(f"- {c}")

            # Normalize report payload
            report_obj = out.get("report")
            report_bytes = None
            report_name = "report.tex"

            if isinstance(report_obj, dict):
                candidate = report_obj.get("report")
                if isinstance(candidate, str) and os.path.exists(candidate):
                    with open(candidate, "rb") as fh:
                        report_bytes = fh.read()
                    report_name = os.path.basename(candidate)
                elif isinstance(candidate, str):
                    report_bytes = candidate.encode("utf-8")
                elif isinstance(candidate, (bytes, bytearray)):
                    report_bytes = bytes(candidate)
            elif isinstance(report_obj, str) and os.path.exists(report_obj):
                with open(report_obj, "rb") as fh:
                    report_bytes = fh.read()
                report_name = os.path.basename(report_obj)
            elif isinstance(report_obj, str):
                report_bytes = report_obj.encode("utf-8")
            elif isinstance(report_obj, (bytes, bytearray)):
                report_bytes = bytes(report_obj)

            if report_bytes is None:
                st.warning("No report file produced or report could not be read.")
            else:
                st.session_state["last_report_bytes"] = report_bytes
                st.session_state["last_report_name"] = report_name

                st.write("Report (LaTeX file):")
                try:
                    st.code(report_bytes.decode("utf-8"), language="latex")
                except Exception:
                    st.write("Report (binary content)")

                tmp_dir = Path(tempfile.gettempdir()) / "athena_reports"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time() * 1000)
                tmp_path = tmp_dir / f"{timestamp}_{report_name}"
                with open(tmp_path, "wb") as outf:
                    outf.write(report_bytes)

                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "Download LaTeX",
                        data=f.read(),
                        file_name=report_name,
                    )

# ---------------- Ask uploaded document ----------------
st.header("Ask uploaded document")
doc_question = st.text_input("Ask a question about the most recently uploaded document", key="doc_question_input")
if st.button("Ask Document", key="ask_document_btn"):
    ensure_orchestrator(chroma_dir=chroma_dir)
    if orchestrator is None:
        st.warning("Cannot answer: Orchestrator failed to initialize. See sidebar for details.")
    else:
        doc_path = st.session_state.get("last_uploaded_path", "")
        if not doc_path or not os.path.exists(doc_path):
            st.warning("No uploaded document found. Upload a PDF in the Ingest sidebar first.")
        elif not doc_question:
            st.warning("Enter a question about the uploaded document.")
        else:
            with st.spinner("Running document QA..."):
                answer = None
                try:
                    mod = __import__("athena.rag.langchain", fromlist=["retrieve_from_document"])
                    retrieve_fn = getattr(mod, "retrieve_from_document", None)
                    if callable(retrieve_fn):
                        answer = retrieve_fn(doc_path, doc_question)
                except Exception as e:
                    st.sidebar.info(f"LangChain QA helper not used: {e}")

                if answer is None:
                    qa_fn = getattr(orchestrator, "answer_from_document", None) or getattr(orchestrator, "qa_document", None) or getattr(orchestrator, "answer_document", None)
                    try:
                        if qa_fn is not None:
                            answer = qa_fn(doc_path, doc_question)
                        else:
                            fallback_prompt = (
                                f"Use only the contents of the uploaded PDF at path: {doc_path}\n\n"
                                f"Question: {doc_question}\n\nProvide a concise answer and cite pages if possible."
                            )
                            out = orchestrator.query_and_synthesize(fallback_prompt)
                            answer = out.get("answer") if isinstance(out, dict) else out
                    except Exception as ex:
                        st.error(f"Document QA failed: {ex}")
                        answer = None

                if answer is None:
                    st.warning("No answer produced.")
                else:
                    if isinstance(answer, dict):
                        st.json(answer)
                    else:
                        st.markdown(answer)

# ---------------- Layman Summarizer ---------------- 
st.header("Layman Summarizer")

if st.button("Summarize in Layman's Terms", key="layman_summarize_btn"):
    doc_path = st.session_state.get("last_uploaded_path", "")
    if not doc_path or not os.path.exists(doc_path):
        st.warning("No uploaded document found. Upload a PDF in the Ingest sidebar first.")
    else:
        with st.spinner("Generating easy-to-understand summary..."):
            try:
                mod = __import__("athena.agents.layman_agent", fromlist=["summarize_layman_from_pdf"])
                layman_fn = getattr(mod, "summarize_layman_from_pdf")
                layman_summary = layman_fn(doc_path)
                st.markdown(f"### Summary for Everyone:\n{layman_summary}")
            except Exception as ex:
                st.error(f"Layman summarizer failed: {ex}")

# ---------------- Related Papers (Semantic Scholar) ---------------- 
st.header("Related Papers (Semantic Scholar)")

if st.button("Find Related Papers", key="find_related_papers_btn"):
    doc_path = st.session_state.get("last_uploaded_path", "")
    if not doc_path or not os.path.exists(doc_path):
        st.warning("No uploaded document found. Upload a PDF in the Ingest sidebar first.")
    else:
        semantic_key = st.session_state.get("semantic_scholar_api_key", "")
        if not semantic_key:
            st.warning("Please enter your Semantic Scholar API key in the sidebar.")
        else:
            with st.spinner("Extracting paper metadata and finding related papers..."):
                try:
                    from athena.external.semantic_scholar import SemanticScholarClient, extract_paper_metadata_from_pdf
                    
                    # Extract metadata from PDF
                    metadata = extract_paper_metadata_from_pdf(doc_path)
                    title = metadata.get("title", "")
                    authors = metadata.get("authors", [])
                    
                    if not title:
                        st.warning("Could not extract paper title from PDF. You can manually search for papers using the search feature below.")
                    else:
                        st.info(f"**Found paper:** {title}")
                        if authors:
                            st.info(f"**Authors:** {', '.join(authors[:3])}")
                        
                        # Initialize Semantic Scholar client
                        client = SemanticScholarClient(semantic_key)
                        
                        # Find paper and related papers
                        result = client.find_paper_and_related(title, authors, limit=10)
                        
                        found_paper = result.get("paper")
                        related_papers = result.get("related", [])
                        citations = result.get("citations", [])
                        references = result.get("references", [])
                        
                        if found_paper:
                            st.success("✅ Paper found in Semantic Scholar!")
                            with st.expander("View Paper Details", expanded=False):
                                st.markdown(f"**Title:** {found_paper.get('title', 'N/A')}")
                                if found_paper.get('authors'):
                                    author_names = [a.get('name', '') for a in found_paper['authors']]
                                    st.markdown(f"**Authors:** {', '.join(author_names[:5])}")
                                if found_paper.get('year'):
                                    st.markdown(f"**Year:** {found_paper.get('year')}")
                                if found_paper.get('venue'):
                                    st.markdown(f"**Venue:** {found_paper.get('venue')}")
                                if found_paper.get('citationCount') is not None:
                                    st.markdown(f"**Citations:** {found_paper.get('citationCount')}")
                                if found_paper.get('abstract'):
                                    st.markdown(f"**Abstract:** {found_paper.get('abstract')[:500]}...")
                                if found_paper.get('url'):
                                    st.markdown(f"[View on Semantic Scholar]({found_paper.get('url')})")
                        else:
                            st.warning("Paper not found in Semantic Scholar database.")
                        
                        # Display related papers
                        if related_papers:
                            st.subheader(f"Related Papers ({len(related_papers)})")
                            for i, paper in enumerate(related_papers, 1):
                                with st.expander(f"{i}. {paper.get('title', 'Untitled')}", expanded=False):
                                    if paper.get('authors'):
                                        author_names = [a.get('name', '') for a in paper['authors']]
                                        st.markdown(f"**Authors:** {', '.join(author_names[:5])}")
                                    if paper.get('year'):
                                        st.markdown(f"**Year:** {paper.get('year')}")
                                    if paper.get('venue'):
                                        st.markdown(f"**Venue:** {paper.get('venue')}")
                                    if paper.get('citationCount') is not None:
                                        st.markdown(f"**Citations:** {paper.get('citationCount')}")
                                    if paper.get('abstract'):
                                        st.markdown(f"**Abstract:** {paper.get('abstract')[:300]}...")
                                    if paper.get('url'):
                                        st.markdown(f"[View on Semantic Scholar]({paper.get('url')})")
                        
                        # Display citations
                        if citations:
                            st.subheader(f"Papers Citing This Work ({len(citations)})")
                            for i, paper in enumerate(citations[:5], 1):
                                with st.expander(f"{i}. {paper.get('title', 'Untitled')}", expanded=False):
                                    if paper.get('authors'):
                                        author_names = [a.get('name', '') for a in paper['authors']]
                                        st.markdown(f"**Authors:** {', '.join(author_names[:5])}")
                                    if paper.get('year'):
                                        st.markdown(f"**Year:** {paper.get('year')}")
                                    if paper.get('url'):
                                        st.markdown(f"[View on Semantic Scholar]({paper.get('url')})")
                        
                        # Display references
                        if references:
                            st.subheader(f"Papers Referenced ({len(references)})")
                            for i, paper in enumerate(references[:5], 1):
                                with st.expander(f"{i}. {paper.get('title', 'Untitled')}", expanded=False):
                                    if paper.get('authors'):
                                        author_names = [a.get('name', '') for a in paper['authors']]
                                        st.markdown(f"**Authors:** {', '.join(author_names[:5])}")
                                    if paper.get('year'):
                                        st.markdown(f"**Year:** {paper.get('year')}")
                                    if paper.get('url'):
                                        st.markdown(f"[View on Semantic Scholar]({paper.get('url')})")
                        
                except Exception as ex:
                    st.error(f"Failed to find related papers: {ex}")
                    st.exception(ex)

# Manual search option
st.subheader("Manual Search")
search_query = st.text_input("Search for papers by title or keywords", key="paper_search_input")
if st.button("Search Papers", key="search_papers_btn"):
    semantic_key = st.session_state.get("semantic_scholar_api_key", "")
    if not semantic_key:
        st.warning("Please enter your Semantic Scholar API key in the sidebar.")
    elif not search_query:
        st.warning("Please enter a search query.")
    else:
        with st.spinner("Searching Semantic Scholar..."):
            try:
                from athena.external.semantic_scholar import SemanticScholarClient
                client = SemanticScholarClient(semantic_key)
                results = client.search_paper(search_query, limit=10)
                
                if results:
                    st.success(f"Found {len(results)} papers")
                    for i, paper in enumerate(results, 1):
                        with st.expander(f"{i}. {paper.get('title', 'Untitled')}", expanded=False):
                            if paper.get('authors'):
                                author_names = [a.get('name', '') for a in paper['authors']]
                                st.markdown(f"**Authors:** {', '.join(author_names[:5])}")
                            if paper.get('year'):
                                st.markdown(f"**Year:** {paper.get('year')}")
                            if paper.get('venue'):
                                st.markdown(f"**Venue:** {paper.get('venue')}")
                            if paper.get('citationCount') is not None:
                                st.markdown(f"**Citations:** {paper.get('citationCount')}")
                            if paper.get('abstract'):
                                st.markdown(f"**Abstract:** {paper.get('abstract')[:300]}...")
                            if paper.get('url'):
                                st.markdown(f"[View on Semantic Scholar]({paper.get('url')})")
                else:
                    st.warning("No papers found.")
            except Exception as ex:
                st.error(f"Search failed: {ex}")
                st.exception(ex)
