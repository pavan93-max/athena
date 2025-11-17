import React, { useState } from 'react';
import './SynthesisView.css';
import { Sparkles, Loader, Download, AlertCircle } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const SynthesisView = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE}/synthesis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || errorData.detail || `Synthesis failed: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Network error: Could not connect to server. Please ensure the backend is running.');
      } else if (err.message.includes('OPENAI_API_KEY') || err.message.includes('OpenAI')) {
        setError('OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file or environment variables.');
      } else {
        setError(err.message || 'Synthesis failed. Make sure documents are ingested and OpenAI API key is configured.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (result?.report) {
      try {
        // Extract filename from report path
        let fileName = 'athena_report.tex';
        if (result.report.includes('/')) {
          fileName = result.report.split('/').pop();
        } else if (result.report.includes('\\')) {
          fileName = result.report.split('\\').pop();
        } else if (result.report.endsWith('.tex')) {
          fileName = result.report;
        }
        
        // Try to fetch from Python API (port 8000) or Node backend (port 3001)
        const pythonApiUrl = process.env.REACT_APP_PYTHON_API_URL || 'http://localhost:8000';
        const nodeApiUrl = API_BASE.replace('/api', '');
        
        // Try Python API first, then Node backend
        let response = await fetch(`${pythonApiUrl}/outputs/${fileName}`).catch(() => null);
        if (!response || !response.ok) {
          response = await fetch(`${nodeApiUrl}/outputs/${fileName}`).catch(() => null);
        }
        
        if (response && response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = fileName;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
        } else {
          // Fallback: inform user where to find the file
          alert(`Report saved to: ${result.report}\n\nYou can find it in the outputs/ directory on the server.`);
        }
      } catch (err) {
        console.error('Download failed:', err);
        alert(`Report saved to: ${result.report}\n\nYou can find it in the outputs/ directory on the server.`);
      }
    }
  };

  return (
    <div className="synthesis-view">
      <div className="view-header">
        <h2>Research Synthesis</h2>
        <p>Generate comprehensive research reports with AI-powered analysis</p>
        <div className="requirements-note">
          <strong>Requirements:</strong>
          <ul>
            <li>📄 <strong>Documents ingested:</strong> Upload and ingest PDFs in the Library first</li>
            <li>🔑 <strong>OpenAI API key:</strong> Required for AI analysis (set in <code>.env</code> as <code>OPENAI_API_KEY</code>)</li>
            <li>❓ <strong>Research query:</strong> Enter your research question or topic below</li>
          </ul>
          <p className="info-text">
            The synthesis process will: retrieve relevant documents, generate research claims, run AI debates, 
            validate with Wikipedia/PubMed, and produce a LaTeX report.
          </p>
        </div>
        
        <div className="sample-queries">
          <strong>Sample Research Queries:</strong>
          <div className="query-examples">
            <button 
              type="button" 
              className="sample-query-btn"
              onClick={() => setQuery("What are the main findings and contributions of transformer architectures in natural language processing?")}
            >
              Transformer architectures in NLP
            </button>
            <button 
              type="button" 
              className="sample-query-btn"
              onClick={() => setQuery("Summarize the key methodologies and experimental results discussed in the documents.")}
            >
              Key methodologies and results
            </button>
            <button 
              type="button" 
              className="sample-query-btn"
              onClick={() => setQuery("What are the limitations and future research directions mentioned in the papers?")}
            >
              Limitations and future work
            </button>
            <button 
              type="button" 
              className="sample-query-btn"
              onClick={() => setQuery("Compare and contrast the different approaches presented in the research documents.")}
            >
              Compare different approaches
            </button>
            <button 
              type="button" 
              className="sample-query-btn"
              onClick={() => setQuery("What are the main conclusions and their implications for the field?")}
            >
              Main conclusions and implications
            </button>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="synthesis-form">
        <div className="input-group">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your research query or topic..."
            rows="5"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? (
              <>
                <Loader className="icon spin" />
                Synthesizing...
              </>
            ) : (
              <>
                <Sparkles className="icon" />
                Run Synthesis
              </>
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="error-message">
          <AlertCircle className="icon" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="result-section">
          {result.claims && result.claims.length > 0 && (
            <div className="claims-section">
              <h3>Key Claims</h3>
              <ul className="claims-list">
                {result.claims.map((claim, idx) => (
                  <li key={idx}>{claim}</li>
                ))}
              </ul>
            </div>
          )}

          {result.report && (
            <div className="report-section">
              <div className="report-header">
                <h3>Generated Report</h3>
                <button onClick={handleDownload} className="download-btn">
                  <Download className="icon" />
                  Download LaTeX
                </button>
              </div>
              <div className="report-info">
                <p>Report generated successfully. Download the LaTeX file to compile.</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SynthesisView;

