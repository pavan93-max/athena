import React from 'react';
import './LibraryView.css';
import { FileText, Calendar, HardDrive, Trash2 } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const LibraryView = ({ uploads, onFileSelect, selectedFile, onFileDelete, onRefresh }) => {
  const formatDate = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString();
  };

  const formatSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const handleDelete = async (e, file, index) => {
    e.stopPropagation(); // Prevent card selection when clicking delete
    
    if (!window.confirm(`Are you sure you want to delete "${file.name}"? This will also remove it from the vector database.`)) {
      return;
    }

    try {
      // Extract just the filename (handle both full paths and just filenames)
      const filename = file.name || file.path?.split(/[/\\]/).pop() || '';
      
      if (!filename) {
        throw new Error('Could not determine filename');
      }

      console.log('Attempting to delete file:', filename);
      console.log('API_BASE:', API_BASE);
      const deleteUrl = `${API_BASE}/uploads/${encodeURIComponent(filename)}`;
      console.log('Delete URL:', deleteUrl);

      const response = await fetch(deleteUrl, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      console.log('Delete response status:', response.status, response.statusText);

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await response.json();
            errorMessage = errorData.error || errorData.detail || errorMessage;
          } else {
            const text = await response.text();
            errorMessage = text || errorMessage;
          }
        } catch (parseError) {
          console.error('Failed to parse error response:', parseError);
          errorMessage = `Failed to delete file (status ${response.status})`;
        }
        
        throw new Error(errorMessage);
      }

      const result = await response.json().catch(() => ({ message: 'File deleted successfully' }));
      console.log('Delete successful:', result);

      // Call the parent's delete handler if provided, or refresh
      if (onFileDelete) {
        onFileDelete(file, index);
      } else if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      console.error('Delete error:', err);
      if (err.name === 'TypeError' && (err.message.includes('fetch') || err.message.includes('Failed to fetch'))) {
        alert('Network error: Could not connect to server. Please ensure the backend is running on port 3001.');
      } else {
        alert(`Failed to delete file: ${err.message}`);
      }
    }
  };

  return (
    <div className="library-view">
      <div className="view-header">
        <h2>Document Library</h2>
        <p>Manage and select your uploaded research documents</p>
      </div>

      {uploads.length === 0 ? (
        <div className="empty-state">
          <FileText className="empty-icon" />
          <h3>No documents yet</h3>
          <p>Upload PDF files to get started with research analysis</p>
        </div>
      ) : (
        <div className="documents-grid">
          {uploads.map((file, index) => (
            <div
              key={index}
              className={`document-card ${selectedFile === file.path ? 'selected' : ''}`}
              onClick={() => onFileSelect(file.path)}
            >
              <div className="card-header">
                <FileText className="file-icon" />
                <h3>{file.name}</h3>
                <button
                  className="delete-btn"
                  onClick={(e) => handleDelete(e, file, index)}
                  title="Delete document"
                >
                  <Trash2 className="delete-icon" />
                </button>
              </div>
              <div className="card-details">
                <div className="detail-item">
                  <HardDrive className="detail-icon" />
                  <span>{formatSize(file.size)}</span>
                </div>
                <div className="detail-item">
                  <Calendar className="detail-icon" />
                  <span>{formatDate(file.updated)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LibraryView;

