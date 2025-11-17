"""
Test script for Semantic Scholar integration.
"""
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from athena.external.semantic_scholar import SemanticScholarClient, extract_paper_metadata_from_pdf

def test_api_client():
    """Test basic API client functionality."""
    print("=" * 60)
    print("Testing Semantic Scholar API Client")
    print("=" * 60)
    
    api_key = "vBOi9Ku9PS6YOkIeyMyo93f9LmlKeHvB8C1MfBfa"
    client = SemanticScholarClient(api_key)
    
    # Test 1: Search for a well-known paper
    print("\n1. Testing paper search...")
    print("   Searching for: 'Attention is All You Need'")
    results = client.search_paper("Attention is All You Need", limit=3)
    
    if results:
        print(f"   ✅ Found {len(results)} papers")
        for i, paper in enumerate(results[:2], 1):
            print(f"   Paper {i}:")
            print(f"      Title: {paper.get('title', 'N/A')}")
            if paper.get('authors'):
                authors = [a.get('name', '') for a in paper['authors'][:3]]
                print(f"      Authors: {', '.join(authors)}")
            if paper.get('year'):
                print(f"      Year: {paper.get('year')}")
            print()
    else:
        print("   ❌ No results found")
        return False
    
    # Test 2: Get paper details by ID (if we found one)
    if results and results[0].get('paperId'):
        print("2. Testing get paper by ID...")
        paper_id = results[0]['paperId']
        print(f"   Getting paper ID: {paper_id}")
        paper = client.get_paper_by_id(paper_id)
        
        if paper:
            print(f"   ✅ Retrieved paper: {paper.get('title', 'N/A')}")
            print(f"      Citation count: {paper.get('citationCount', 'N/A')}")
        else:
            print("   ❌ Failed to retrieve paper")
            return False
    
    # Test 3: Get related papers
    if results and results[0].get('paperId'):
        print("\n3. Testing get related papers...")
        paper_id = results[0]['paperId']
        print(f"   Getting related papers for: {paper_id}")
        related = client.get_related_papers(paper_id, limit=3)
        
        if related:
            print(f"   ✅ Found {len(related)} related papers")
            for i, paper in enumerate(related[:2], 1):
                print(f"   Related {i}: {paper.get('title', 'N/A')[:60]}...")
        else:
            print("   ⚠️  No related papers found (this might be normal)")
    
    return True

def test_pdf_metadata_extraction():
    """Test PDF metadata extraction."""
    print("\n" + "=" * 60)
    print("Testing PDF Metadata Extraction")
    print("=" * 60)
    
    # Test with available PDFs
    test_pdfs = [
        "./uploads/sample.pdf",
        "./examles/sample.pdf"
    ]
    
    for pdf_path in test_pdfs:
        if os.path.exists(pdf_path):
            print(f"\nTesting: {pdf_path}")
            try:
                metadata = extract_paper_metadata_from_pdf(pdf_path)
                title = metadata.get("title", "")
                authors = metadata.get("authors", [])
                
                print(f"   Title: {title if title else 'Not extracted'}")
                print(f"   Authors: {', '.join(authors) if authors else 'Not extracted'}")
                
                if title or authors:
                    print("   ✅ Metadata extraction successful")
                else:
                    print("   ⚠️  Could not extract metadata (PDF might not be a research paper)")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                return False
    
    return True

def test_find_paper_and_related():
    """Test the complete workflow: find paper and get related papers."""
    print("\n" + "=" * 60)
    print("Testing Complete Workflow: Find Paper and Related Papers")
    print("=" * 60)
    
    api_key = "vBOi9Ku9PS6YOkIeyMyo93f9LmlKeHvB8C1MfBfa"
    client = SemanticScholarClient(api_key)
    
    # Test with a well-known paper title
    test_title = "Attention is All You Need"
    test_authors = ["Vaswani", "Shazeer"]
    
    print(f"\nSearching for: '{test_title}'")
    print(f"Authors: {', '.join(test_authors)}")
    
    result = client.find_paper_and_related(test_title, test_authors, limit=5)
    
    found_paper = result.get("paper")
    related_papers = result.get("related", [])
    citations = result.get("citations", [])
    references = result.get("references", [])
    
    if found_paper:
        print(f"\n✅ Paper found!")
        print(f"   Title: {found_paper.get('title', 'N/A')}")
        if found_paper.get('authors'):
            author_names = [a.get('name', '') for a in found_paper['authors'][:3]]
            print(f"   Authors: {', '.join(author_names)}")
        print(f"   Year: {found_paper.get('year', 'N/A')}")
        print(f"   Citations: {found_paper.get('citationCount', 'N/A')}")
    else:
        print("\n❌ Paper not found")
        return False
    
    print(f"\n   Related papers: {len(related_papers)}")
    print(f"   Citations: {len(citations)}")
    print(f"   References: {len(references)}")
    
    if related_papers:
        print("\n   Sample related papers:")
        for i, paper in enumerate(related_papers[:3], 1):
            print(f"   {i}. {paper.get('title', 'N/A')[:60]}...")
    
    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SEMANTIC SCHOLAR INTEGRATION TEST")
    print("=" * 60)
    
    results = []
    
    # Test 1: API Client
    try:
        results.append(("API Client", test_api_client()))
    except Exception as e:
        print(f"\n❌ API Client test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("API Client", False))
    
    # Test 2: PDF Metadata Extraction
    try:
        results.append(("PDF Metadata Extraction", test_pdf_metadata_extraction()))
    except Exception as e:
        print(f"\n❌ PDF Metadata Extraction test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("PDF Metadata Extraction", False))
    
    # Test 3: Complete Workflow
    try:
        results.append(("Complete Workflow", test_find_paper_and_related()))
    except Exception as e:
        print(f"\n❌ Complete Workflow test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Complete Workflow", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


