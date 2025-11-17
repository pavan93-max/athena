import json
import os
from typing import Dict, List

import requests
import streamlit as st


st.set_page_config(
    page_title="Athena Research Studio",
    page_icon="🧠",
    layout="wide",
)

API_BASE = os.getenv("ATHENA_API_URL", "http://localhost:8000")


def call_api(method: str, path: str, **kwargs):
    url = f"{API_BASE.rstrip('/')}{path}"
    try:
        response = requests.request(method, url, timeout=120, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}
    except requests.HTTPError as http_err:
        try:
            detail = response.json()
        except Exception:  # noqa: BLE001
            detail = response.text
        st.error(f"API error {response.status_code}: {detail}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Request failed: {exc}")
    return None


@st.cache_data(show_spinner=False)
def fetch_library() -> List[Dict]:
    result = call_api("GET", "/uploads")
    return result.get("files", []) if result else []


def reset_library_cache():
    fetch_library.clear()


st.sidebar.header("Connection")
api_base_input = st.sidebar.text_input("API URL", value=API_BASE)
if api_base_input and api_base_input != API_BASE:
    API_BASE = api_base_input
    reset_library_cache()

st.sidebar.caption("Ensure you have uvicorn running: `uvicorn server.api:app --reload`")

st.title("Athena Research Studio")
st.write("Modern interface for ingesting PDFs, running document QA, and synthesizing findings.")

tab_ingest, tab_ask, tab_synthesis, tab_related = st.tabs(
    ["📚 Library & Ingest", "❓ Ask Documents", "🧪 Synthesis", "🔗 Summaries & Related"]
)

with tab_ingest:
    st.subheader("Upload & Ingest PDFs")
    uploads = st.file_uploader(
        "Drop multiple PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Ingest Selected Files", type="primary", disabled=not uploads):
        with st.spinner("Uploading and ingesting..."):
            files_payload = [("files", (f.name, f.getvalue(), "application/pdf")) for f in uploads]
            resp = call_api("POST", "/ingest", files=files_payload)
        if resp:
            st.success(f"Ingested {len(resp.get('ingested', []))} file(s).")
            reset_library_cache()

    st.markdown("### Library")
    library = fetch_library()
    if library:
        for file_entry in library:
            with st.expander(f"{file_entry['name']} — {file_entry['size']/1024:.1f} KB", expanded=False):
                st.code(json.dumps(file_entry, indent=2))
    else:
        st.info("No PDFs ingested yet.")

with tab_ask:
    st.subheader("Ask Questions about a Document")
    library = fetch_library()
    doc_options = {item["name"]: item for item in library}
    selected_doc = st.selectbox("Choose a document", list(doc_options.keys()) or ["No documents found"])
    question = st.text_area("Your question", placeholder="What problem does this paper address?")

    if st.button("Ask Document", disabled=not library or not question.strip()):
        with st.spinner("Querying document..."):
            payload = {"path": doc_options[selected_doc]["path"], "question": question}
            resp = call_api("POST", "/document/ask", json=payload)
        if resp:
            st.markdown("#### Answer")
            st.write(resp.get("answer") or "No answer returned.")
            st.markdown("#### Supporting Context")
            for idx, ctx in enumerate(resp.get("context", []), 1):
                meta = ctx.get("metadata", {})
                label = meta.get("page_label") or meta.get("page", "?")
                st.caption(f"Chunk {idx} — Page {label}")
                st.write(ctx.get("page_content", "")[:1000])

with tab_synthesis:
    st.subheader("Run Retrieval + Debate + Report")
    query = st.text_input("Enter research question", value="", placeholder="How effective are transformers for translation?")
    if st.button("Run Synthesis", type="primary", disabled=not query.strip()):
        with st.spinner("Running orchestrator..."):
            resp = call_api("POST", "/synthesis", json={"query": query})
        if resp:
            st.success("Synthesis complete.")
            claims = resp.get("claims", [])
            if claims:
                st.markdown("#### Claims")
                for claim in claims:
                    st.markdown(f"- {claim}")
            report = resp.get("report")
            if report and os.path.exists(report):
                with open(report, "r", encoding="utf-8") as fh:
                    st.download_button("Download LaTeX Report", fh.read(), file_name=os.path.basename(report))
            elif isinstance(report, str):
                st.code(report, language="latex")

with tab_related:
    st.subheader("Layman Summary & Related Papers")
    library = fetch_library()
    doc_options = {item["name"]: item for item in library}
    selected_doc = st.selectbox("Document for helpers", list(doc_options.keys()) or ["No documents"], key="helpers_doc")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Layman Summary")
        if st.button("Summarize Document", disabled=not library):
            with st.spinner("Summarizing..."):
                payload = {"path": doc_options[selected_doc]["path"]}
                resp = call_api("POST", "/layman", json=payload)
            if resp:
                st.write(resp.get("summary") or "No summary returned.")

    with col2:
        st.markdown("##### Related Papers")
        limit = st.slider("How many related papers?", 3, 15, 8)
        if st.button("Find Related Papers", disabled=not library):
            with st.spinner("Querying Semantic Scholar..."):
                payload = {"path": doc_options[selected_doc]["path"], "limit": limit}
                resp = call_api("POST", "/related-papers", json=payload)
            if resp:
                metadata = resp.get("metadata", {})
                if metadata:
                    st.caption(f"Detected title: {metadata.get('title')}")
                related = (resp.get("result") or {}).get("related", [])
                if related:
                    for paper in related:
                        title = paper.get("title", "Untitled")
                        st.write(f"**{title}** ({paper.get('year', '')})")
                        if paper.get("abstract"):
                            st.caption(paper["abstract"][:300] + "...")
                        if paper.get("url"):
                            st.markdown(f"[Link]({paper['url']})")
                else:
                    st.info("No related papers returned.")

st.markdown("---")
st.caption("Backend API lives at `/server/api.py`. Make sure both backend and this Streamlit client are running.")

