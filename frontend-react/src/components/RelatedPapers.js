import React, { useState } from 'react';
import './RelatedPapers.css';
import { Search, Loader, ExternalLink, AlertCircle, FileText } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const RelatedPapers = ({ selectedFile }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState(null);
  const [relatedPapers, setRelatedPapers] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRelatedPapers = async () => {
    if (!selectedFile) {
      setError('Please select a document first');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch(`${API_BASE}/related-papers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, limit: 10 })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || errorData.detail || `Failed to find related papers: ${response.status}`);
      }

      const data = await response.json();
      setRelatedPapers(data);
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Network error: Could not connect to server. Please ensure the backend is running.');
      } else {
        setError(err.message || 'Failed to find related papers. Please check if Semantic Scholar API key is configured.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setRelatedPapers(null);

    try {
      const response = await fetch(`${API_BASE}/semantic-scholar/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim(), limit: 10 })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || errorData.detail || `Search failed: ${response.status}`);
      }

      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Network error: Could not connect to server. Please ensure the backend is running.');
      } else {
        setError(err.message || 'Search failed. Please check if Semantic Scholar API key is configured.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="related-papers">
      <div className="view-header">
        <h2>Related Papers</h2>
        <p>Discover related research papers using Semantic Scholar</p>
        <p className="info-note">
          <strong>Note:</strong> A default demo API key is included for testing. For production use, set <code>SEMANTIC_SCHOLAR_API_KEY</code> in your <code>.env</code> file or environment variables. Get your free key at <a href="https://www.semanticscholar.org/product/api" target="_blank" rel="noopener noreferrer">Semantic Scholar</a>.
        </p>
      </div>

      <div className="actions-section">
        {selectedFile && (
          <div className="action-card">
            <FileText className="icon" />
            <div>
              <h3>Find Related Papers</h3>
              <p>Extract metadata and find related papers for the selected document</p>
            </div>
            <button onClick={handleRelatedPapers} disabled={loading}>
              {loading ? (
                <>
                  <Loader className="icon spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="icon" />
                  Find Related
                </>
              )}
            </button>
          </div>
        )}

        <div className="action-card">
          <Search className="icon" />
          <div>
            <h3>Manual Search</h3>
            <p>Search Semantic Scholar by title or keywords</p>
          </div>
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter paper title or keywords..."
              disabled={loading}
            />
            <button type="submit" disabled={loading || !searchQuery.trim()}>
              {loading ? (
                <Loader className="icon spin" />
              ) : (
                <Search className="icon" />
              )}
            </button>
          </form>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <AlertCircle className="icon" />
          <span>{error}</span>
        </div>
      )}

      {relatedPapers && (
        <div className="results-section">
          {relatedPapers.metadata && (
            <div className="paper-metadata">
              <h3>Document Metadata</h3>
              <p><strong>Title:</strong> {relatedPapers.metadata.title || 'N/A'}</p>
              {relatedPapers.metadata.authors && relatedPapers.metadata.authors.length > 0 && (
                <p><strong>Authors:</strong> {relatedPapers.metadata.authors.join(', ')}</p>
              )}
            </div>
          )}

          {relatedPapers.result?.related && (
            <div className="papers-list">
              <h3>Related Papers ({relatedPapers.result.related.length})</h3>
              {relatedPapers.result.related.map((paper, idx) => (
                <PaperCard key={idx} paper={paper} />
              ))}
            </div>
          )}
        </div>
      )}

      {results && (
        <div className="results-section">
          <h3>Search Results ({results.length})</h3>
          <div className="papers-list">
            {results.map((paper, idx) => (
              <PaperCard key={idx} paper={paper} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const PaperCard = ({ paper }) => {
  return (
    <div className="paper-card">
      <h4>{paper.title || 'Untitled'}</h4>
      {paper.authors && paper.authors.length > 0 && (
        <p className="authors">
          {paper.authors.slice(0, 3).map(a => a.name || a).join(', ')}
          {paper.authors.length > 3 && ' et al.'}
        </p>
      )}
      {paper.year && <p className="year">Year: {paper.year}</p>}
      {paper.venue && <p className="venue">Venue: {paper.venue}</p>}
      {paper.citationCount !== undefined && (
        <p className="citations">Citations: {paper.citationCount}</p>
      )}
      {paper.abstract && (
        <p className="abstract">{paper.abstract.substring(0, 200)}...</p>
      )}
      {paper.url && (
        <a href={paper.url} target="_blank" rel="noopener noreferrer" className="paper-link">
          <ExternalLink className="icon" />
          View on Semantic Scholar
        </a>
      )}
    </div>
  );
};

export default RelatedPapers;

