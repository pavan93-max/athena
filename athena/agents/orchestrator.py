from athena.ingestion.pdf_ingest import extract_pdf_text
from athena.rag.vector_store import ChromaStore
from athena.agents.debate_engine import run_three_way_debate, call_llm
from athena.agents.fact_checker import check_wikipedia_claim, pubmed_lookup
from athena.synth.report_synthesizer import synthesize_report
import uuid
import os
import re
import nltk

nltk.download("punkt", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)


def preprocess_claim_for_search(claim: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", claim)
    words = cleaned.split()
    return " ".join(words[:6])  


def extract_keywords(text: str) -> str:
    tokens = nltk.word_tokenize(text)
    tagged = nltk.pos_tag(tokens)
    keywords = [w for (w, t) in tagged if t.startswith("NN") or t.startswith("JJ")]
    return " ".join(keywords[:6])


class Orchestrator:
    def __init__(self, chroma_dir="./chroma_db"):
        self.store = ChromaStore(persist_directory=chroma_dir)

    def ingest_pdf(self, path: str):
        pages = extract_pdf_text(path)
        docs = []
        for p in pages:
            docid = str(uuid.uuid4())
            docs.append({
                "id": docid,
                "text": p["text"],
                "meta": {"page": p["page"], "source": os.path.basename(path)}
            })
        self.store.add_documents(docs)
        return {"ingested_pages": len(docs)}

    def query_and_synthesize(self, query: str):
        results = self.store.query(query, n_results=5)
        context = "\n\n".join([doc for (_id, doc, meta) in results])


        claim_prompt = f"Read the following context and propose up to 3 concise research claims/findings. Context:\n{context}"
        claims_output = call_llm(claim_prompt)
        claims = [c.strip() for c in claims_output.split("\n") if c.strip()][:3]

        debates = {}
        for claim in claims:
            debates[claim] = run_three_way_debate(claim, context=context, rounds=2)

            short_claim = claim[:280]
            wiki = check_wikipedia_claim(short_claim)
            if not wiki:
                wiki = check_wikipedia_claim(extract_keywords(claim))

            pubmed_query = preprocess_claim_for_search(claim)
            pubmed = pubmed_lookup(pubmed_query)
            if not pubmed:
                pubmed = pubmed_lookup(extract_keywords(claim))

            debates[claim]["wiki"] = wiki
            debates[claim]["pubmed"] = pubmed

        report = synthesize_report(query, results, debates)
        return {"report": report, "claims": claims}
