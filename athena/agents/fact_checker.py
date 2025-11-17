import os
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List
from urllib.parse import quote

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
ARXIV_API = "http://export.arxiv.org/api/query"

REQUEST_TIMEOUT = float(os.getenv("ATHENA_EXTERNAL_TIMEOUT", "5"))
HTTP_USER_AGENT = os.getenv(
    "ATHENA_HTTP_USER_AGENT",
    "AthenaResearchAssistant/1.0 (+https://github.com/)",
)
HTTP_HEADERS = {"User-Agent": HTTP_USER_AGENT}


def check_wikipedia_claim(claim: str, top_n: int = 3) -> List[Dict]:
    """Search Wikipedia for a claim and return short summaries."""
    if not claim:
        return []

    try:
        params = {
            "action": "opensearch",
            "search": claim,
            "limit": top_n,
            "namespace": 0,
            "format": "json",
        }
        resp = requests.get(
            WIKIPEDIA_API, params=params, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        titles = data[1]
        descriptions = data[2]

        results = []
        for title, desc in zip(titles, descriptions):
            summary = desc or ""
            if not summary:
                try:
                    summary_resp = requests.get(
                        WIKIPEDIA_SUMMARY_API.format(title=quote(title)),
                        headers=HTTP_HEADERS,
                        timeout=REQUEST_TIMEOUT,
                    )
                    if summary_resp.ok:
                        summary = summary_resp.json().get("extract", "")
                except Exception:
                    summary = ""
            results.append({"title": title, "summary": summary})
        return results
    except Exception as e:
        return [{"error": f"Wikipedia lookup failed: {e}"}]


def pubmed_lookup(query: str, max_results: int = 5) -> List[Dict]:
    """Search PubMed and return abstracts for matching papers."""
    if not query:
        return []

    try:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "xml",
        }
        resp = requests.get(
            PUBMED_ESEARCH, params=params, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ids = [elem.text for elem in root.findall(".//IdList/Id")]
        if not ids:
            return []

        summary_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        }
        summary_resp = requests.get(
            PUBMED_ESUMMARY,
            params=summary_params,
            headers=HTTP_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        summary_resp.raise_for_status()
        summary_data = summary_resp.json().get("result", {})

        out = []
        for pid in ids:
            meta = summary_data.get(pid)
            if not meta:
                continue
            out.append(
                {
                    "id": pid,
                    "title": meta.get("title"),
                    "authors": [a.get("name") for a in meta.get("authors", [])],
                    "pubdate": meta.get("pubdate"),
                    "source": meta.get("source"),
                    "summary": meta.get("elocationid") or meta.get("sortfirstauthor"),
                }
            )
        return out
    except Exception as e:
        return [{"error": f"PubMed lookup failed: {e}"}]


def arxiv_lookup(query: str, max_results: int = 5) -> List[Dict]:
    """Search arXiv for scientific papers matching the query."""
    if not query:
        return []

    try:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
        }
        resp = requests.get(
            ARXIV_API, params=params, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        results = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", default="", namespaces=ns).strip()
            summary = entry.findtext("atom:summary", default="", namespaces=ns).strip()
            published = entry.findtext("atom:published", default="", namespaces=ns)
            link = ""
            for link_el in entry.findall("atom:link", ns):
                if link_el.get("type") == "application/pdf":
                    link = link_el.get("href", "")
                    break
            authors = [
                author.findtext("atom:name", default="", namespaces=ns)
                for author in entry.findall("atom:author", ns)
            ]
            results.append(
                {
                    "title": title,
                    "authors": [a for a in authors if a],
                    "summary": summary,
                    "published": published,
                    "pdf_url": link,
                }
            )
        return results
    except Exception as e:
        return [{"error": f"arXiv lookup failed: {e}"}]
