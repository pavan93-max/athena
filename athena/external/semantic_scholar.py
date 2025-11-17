"""
Semantic Scholar API integration for finding related papers.
"""
import requests
import time
from typing import List, Dict, Optional
import re


class SemanticScholarClient:
    """Client for interacting with Semantic Scholar API."""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self, api_key: str):
        """
        Initialize the Semantic Scholar client.
        
        Args:
            api_key: Semantic Scholar API key
        """
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    def search_paper(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for papers by query string.
        
        Args:
            query: Search query (title, keywords, etc.)
            limit: Maximum number of results to return
            
        Returns:
            List of paper dictionaries
        """
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": min(limit, 100),  # API limit is 100
            "fields": "paperId,title,authors,year,abstract,citationCount,referenceCount,url,venue"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Error searching papers: {e}")
            return []
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Dict]:
        """
        Get paper details by Semantic Scholar paper ID.
        
        Args:
            paper_id: Semantic Scholar paper ID
            
        Returns:
            Paper dictionary or None if not found
        """
        url = f"{self.BASE_URL}/paper/{paper_id}"
        params = {
            "fields": "paperId,title,authors,year,abstract,citationCount,referenceCount,url,venue,references,references.paperId,references.title,references.authors,references.year,references.url"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting paper by ID: {e}")
            return None
    
    def get_related_papers(self, paper_id: str, limit: int = 10) -> List[Dict]:
        """
        Get papers related to a given paper ID.
        
        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of related papers to return
            
        Returns:
            List of related paper dictionaries
        """
        url = f"{self.BASE_URL}/paper/{paper_id}/recommendations"
        params = {
            "limit": min(limit, 100),
            "fields": "paperId,title,authors,year,abstract,citationCount,referenceCount,url,venue"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("recommendedPapers", [])
        except Exception as e:
            print(f"Error getting related papers: {e}")
            return []
    
    def get_citations(self, paper_id: str, limit: int = 10) -> List[Dict]:
        """
        Get papers that cite the given paper.
        
        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of citations to return
            
        Returns:
            List of citing paper dictionaries
        """
        url = f"{self.BASE_URL}/paper/{paper_id}/citations"
        params = {
            "limit": min(limit, 100),
            "fields": "paperId,title,authors,year,abstract,citationCount,referenceCount,url,venue"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Extract paper data from citations
            citations = []
            for item in data.get("data", []):
                if "citingPaper" in item:
                    citations.append(item["citingPaper"])
            return citations
        except Exception as e:
            print(f"Error getting citations: {e}")
            return []
    
    def get_references(self, paper_id: str, limit: int = 10) -> List[Dict]:
        """
        Get papers referenced by the given paper.
        
        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of references to return
            
        Returns:
            List of referenced paper dictionaries
        """
        url = f"{self.BASE_URL}/paper/{paper_id}/references"
        params = {
            "limit": min(limit, 100),
            "fields": "paperId,title,authors,year,abstract,citationCount,referenceCount,url,venue"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Extract paper data from references
            references = []
            for item in data.get("data", []):
                if "citedPaper" in item:
                    references.append(item["citedPaper"])
            return references
        except Exception as e:
            print(f"Error getting references: {e}")
            return []
    
    def find_paper_and_related(self, title: str, authors: Optional[List[str]] = None, limit: int = 10) -> Dict:
        """
        Find a paper by title (and optionally authors) and get related papers.
        
        Args:
            title: Paper title
            authors: Optional list of author names
            limit: Maximum number of related papers to return
            
        Returns:
            Dictionary with 'paper' (found paper) and 'related' (related papers list)
        """
        # Search for the paper
        query = title
        if authors:
            query += " " + " ".join(authors[:2])  # Add first 2 authors to query
        
        search_results = self.search_paper(query, limit=5)
        
        if not search_results:
            return {"paper": None, "related": []}
        
        # Try to find the best match
        found_paper = search_results[0]
        paper_id = found_paper.get("paperId")
        
        if not paper_id:
            return {"paper": found_paper, "related": []}
        
        # Get related papers
        related = self.get_related_papers(paper_id, limit=limit)
        
        return {
            "paper": found_paper,
            "related": related,
            "citations": self.get_citations(paper_id, limit=5),
            "references": self.get_references(paper_id, limit=5)
        }


def extract_paper_metadata_from_pdf(pdf_path: str) -> Dict[str, any]:
    """
    Extract paper metadata (title, authors) from PDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with 'title' and 'authors' keys
    """
    try:
        import pymupdf  # PyMuPDF (fitz)
        
        doc = pymupdf.open(pdf_path)
        
        # Get first page text
        first_page = doc[0]
        text = first_page.get_text()
        
        # Try to extract title (usually first few lines)
        lines = [line.strip() for line in text.split('\n') if line.strip()][:20]
        
        title = ""
        authors = []
        
        # Simple heuristics to find title and authors
        # Title is usually one of the first few long lines
        for i, line in enumerate(lines[:10]):
            if len(line) > 20 and len(line) < 200 and not title:
                # Check if it looks like a title (not all caps, has some structure)
                if not line.isupper() and not line.startswith(('Abstract', 'Introduction', 'Keywords')):
                    title = line
                    break
        
        # Authors usually come after title, before abstract
        author_start = None
        for i, line in enumerate(lines):
            if title and line == title:
                author_start = i + 1
                break
        
        if author_start:
            for line in lines[author_start:author_start+10]:
                # Skip empty lines and common section headers
                if line and len(line) > 3 and not line.startswith(('Abstract', 'Introduction', 'Keywords', '1.', 'I.')):
                    # Check if line might contain authors (has commas or "and")
                    if ',' in line or ' and ' in line.lower():
                        # Split by comma or "and"
                        if ',' in line:
                            potential_authors = [a.strip() for a in line.split(',')]
                        else:
                            potential_authors = [a.strip() for a in line.split(' and ')]
                        authors.extend([a for a in potential_authors if len(a) > 2])
                        if len(authors) >= 3:  # Usually enough authors
                            break
        
        doc.close()
        
        return {
            "title": title,
            "authors": authors[:5]  # Limit to first 5 authors
        }
    except Exception as e:
        print(f"Error extracting metadata from PDF: {e}")
        return {"title": "", "authors": []}

