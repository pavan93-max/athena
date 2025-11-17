import React, { useState } from 'react';
import './DocumentQA.css';
import { Send, Loader, FileText, AlertCircle } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const DocumentQA = ({ selectedFile, uploads }) => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fileToUse = selectedFile || (uploads.length > 0 ? uploads[0].path : null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || !fileToUse) return;

    setLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const response = await fetch(`${API_BASE}/document/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: fileToUse,
          question: question.trim()
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get answer');
      }

      const data = await response.json();
      setAnswer(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="document-qa">
      <div className="view-header">
        <h2>Ask Document</h2>
        <p>Ask questions about your uploaded documents</p>
      </div>

      {!fileToUse ? (
        <div className="empty-state">
          <AlertCircle className="empty-icon" />
          <h3>No document selected</h3>
          <p>Please select a document from the Library first</p>
        </div>
      ) : (
        <>
          <div className="selected-file-info">
            <FileText className="icon" />
            <span>{fileToUse.split(/[/\\]/).pop()}</span>
          </div>

          <form onSubmit={handleSubmit} className="qa-form">
            <div className="input-group">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about the document..."
                rows="4"
                disabled={loading}
              />
              <button type="submit" disabled={loading || !question.trim()}>
                {loading ? (
                  <>
                    <Loader className="icon spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Send className="icon" />
                    Ask
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

          {answer && (
            <div className="answer-section">
              <h3>Answer</h3>
              <div className="answer-content">
                <p>{answer.answer || 'No answer provided'}</p>
              </div>

              {answer.context && answer.context.length > 0 && (
                <div className="context-section">
                  <h4>Supporting Context ({answer.source_docs || answer.context.length} sources)</h4>
                  <div className="context-list">
                    {answer.context.slice(0, 3).map((ctx, idx) => (
                      <div key={idx} className="context-item">
                        <div className="context-meta">
                          {ctx.metadata?.page && (
                            <span className="page-badge">Page {ctx.metadata.page}</span>
                          )}
                        </div>
                        <p className="context-text">
                          {ctx.page_content?.substring(0, 300)}...
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default DocumentQA;

