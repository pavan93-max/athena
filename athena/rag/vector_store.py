# athena/rag/vector_store.py
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import os

MODEL_NAME = "all-MiniLM-L6-v2"

class ChromaStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        os.makedirs(persist_directory, exist_ok=True)
        client = chromadb.PersistentClient(path="./chroma_db")        
        self.col = client.get_or_create_collection("athena_collection")
        self.encoder = SentenceTransformer(MODEL_NAME)

    def add_documents(self, docs: List[Dict]):
        # docs: list of {'id':..., 'text':..., 'meta': {...}}
        texts = [d["text"] for d in docs]
        ids = [d["id"] for d in docs]
        metadatas = [d.get("meta", {}) for d in docs]

        # Generate embeddings
        embeddings = self.encoder.encode(texts, show_progress_bar=False)
        embeddings = [e.tolist() for e in embeddings]

        # Add to Chroma with embeddings
        self.col.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

    def query(self, query_text: str, n_results: int = 5):
        query_emb = self.encoder.encode([query_text])[0].tolist()
        results = self.col.query(query_embeddings=[query_emb], n_results=n_results)

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        return list(zip(ids, docs, metas))

