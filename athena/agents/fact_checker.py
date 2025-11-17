import wikipedia
from Bio import Entrez
import requests
import arxiv
from typing import Dict, List

# Configure Entrez (required for PubMed)
Entrez.email = "praut4830@gmail.com"  

def check_wikipedia_claim(claim: str, top_n: int = 3) -> List[Dict]:
    """Search Wikipedia for a claim and return short summaries."""
    try:
        hits = wikipedia.search(claim, results=top_n)
        results = []
        for h in hits:
            summary = wikipedia.summary(h, sentences=2)
            results.append({"title": h, "summary": summary})
        return results
    except Exception as e:
        return [{"error": str(e)}]

def pubmed_lookup(query: str, max_results: int = 5) -> List[Dict]:
    """Search PubMed and return abstracts for matching papers."""
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        ids = record.get("IdList", [])
        out = []
        if not ids:
            return out
        fetch = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="abstract", retmode="text")
        abstracts = fetch.read()
        out.append({"ids": ids, "abstracts": abstracts})
        return out
    except Exception as e:
        return [{"error": str(e)}]

def arxiv_lookup(query: str, max_results: int = 5) -> List[Dict]:
    """Search arXiv for scientific papers matching the query."""
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        results = []
        for result in search.results():
            results.append({
                "title": result.title,
                "authors": [a.name for a in result.authors],
                "summary": result.summary.strip(),
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


