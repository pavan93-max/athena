from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

from athena.agents.orchestrator import Orchestrator
from athena.agents.layman_agent import summarize_layman_from_pdf
from athena.external.semantic_scholar import (
    SemanticScholarClient,
    extract_paper_metadata_from_pdf,
)
from athena.rag.langchain import retrieve_from_document


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class QueryRequest(BaseModel):
    query: str


class AskDocumentRequest(BaseModel):
    path: str
    question: str


class LaymanSummaryRequest(BaseModel):
    path: str


class RelatedPapersRequest(BaseModel):
    path: str
    limit: Optional[int] = 10


class SemanticScholarSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


def ensure_orchestrator() -> Orchestrator:
    global _orchestrator
    if "_orchestrator" not in globals():
        _orchestrator = Orchestrator(chroma_dir=os.environ.get("CHROMA_DIR", "./chroma_db"))
    return _orchestrator


app = FastAPI(
    title="Athena Research Assistant API",
    version="1.0.0",
    description="Backend services for ingestion, document QA, synthesis, and related research helpers.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "time": int(time.time())}


@app.get("/outputs/{filename}")
def get_report_file(filename: str):
    """Serve generated report files for download."""
    from fastapi.responses import FileResponse
    
    report_path = Path("outputs") / filename
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found.")
    
    return FileResponse(
        path=str(report_path),
        filename=filename,
        media_type="application/x-tex"
    )


@app.get("/uploads")
def list_uploads():
    files = []
    for pdf in sorted(UPLOAD_DIR.glob("*.pdf")):
        stat = pdf.stat()
        files.append(
            {
                "name": pdf.name,
                "path": str(pdf),
                "size": stat.st_size,
                "updated": stat.st_mtime,
            }
        )
    return {"files": files}


@app.delete("/uploads/{filename}")
def delete_upload(filename: str):
    """Delete an uploaded PDF file and optionally remove from vector store."""
    from urllib.parse import unquote
    
    filename = unquote(filename)
    pdf_path = UPLOAD_DIR / filename
    
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    
    try:
        # Delete the file
        pdf_path.unlink()
        
        # Optionally remove from vector store (this would require additional logic)
        # For now, we just delete the file
        # In a full implementation, you might want to:
        # 1. Query the vector store for documents with this source
        # 2. Delete those documents from the vector store
        
        return {"message": "File deleted successfully", "filename": filename}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}") from exc


@app.post("/ingest")
async def ingest_documents(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    orchestrator = ensure_orchestrator()
    responses = []

    for upload in files:
        if not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{upload.filename} is not a PDF.")

        target_path = UPLOAD_DIR / upload.filename
        with target_path.open("wb") as outfile:
            shutil.copyfileobj(upload.file, outfile)

        try:
            result = orchestrator.ingest_pdf(str(target_path))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Failed to ingest {upload.filename}: {exc}") from exc

        responses.append(
            {
                "file": upload.filename,
                "path": str(target_path),
                "ingested_pages": result.get("ingested_pages"),
            }
        )

    return {"ingested": responses}


@app.post("/document/ask")
def ask_document(payload: AskDocumentRequest):
    pdf_path = Path(payload.path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found. Please ingest first.")

    try:
        response = retrieve_from_document(str(pdf_path), payload.question)
        return response
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/synthesis")
def run_synthesis(payload: QueryRequest):
    orchestrator = ensure_orchestrator()
    try:
        return orchestrator.query_and_synthesize(payload.query)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/layman")
def layman_summary(payload: LaymanSummaryRequest):
    pdf_path = Path(payload.path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        summary = summarize_layman_from_pdf(str(pdf_path))
        return {"summary": summary}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/related-papers")
def related_papers(payload: RelatedPapersRequest):
    pdf_path = Path(payload.path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")

    # Try to get API key from environment or use default demo key
    semantic_key = (
        os.getenv("SEMANTIC_SCHOLAR_API_KEY") 
        or os.getenv("SEMANTIC_SCHOLAR_KEY") 
        or "vBOi9Ku9PS6YOkIeyMyo93f9LmlKeHvB8C1MfBfa"  # Default demo key
    )
    if not semantic_key:
        raise HTTPException(status_code=400, detail="Semantic Scholar API key not configured.")

    try:
        metadata = extract_paper_metadata_from_pdf(str(pdf_path))
        client = SemanticScholarClient(semantic_key)
        result = client.find_paper_and_related(metadata.get("title", ""), metadata.get("authors", []), limit=payload.limit)
        return {"metadata": metadata, "result": result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/semantic-scholar/search")
def semantic_scholar_search(payload: SemanticScholarSearchRequest):
    # Try to get API key from environment or use default demo key
    semantic_key = (
        os.getenv("SEMANTIC_SCHOLAR_API_KEY") 
        or os.getenv("SEMANTIC_SCHOLAR_KEY") 
        or "vBOi9Ku9PS6YOkIeyMyo93f9LmlKeHvB8C1MfBfa"  # Default demo key
    )
    if not semantic_key:
        raise HTTPException(status_code=400, detail="Semantic Scholar API key not configured.")

    client = SemanticScholarClient(semantic_key)
    try:
        results = client.search_paper(payload.query, limit=payload.limit or 10)
        return {"results": results}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

