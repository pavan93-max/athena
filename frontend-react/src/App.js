import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LibraryView from './components/LibraryView';
import DocumentQA from './components/DocumentQA';
import SynthesisView from './components/SynthesisView';
import RelatedPapers from './components/RelatedPapers';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

function App() {
  const [activeView, setActiveView] = useState('library');
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('athena-theme') === 'dark';
    }
    return false;
  });

  useEffect(() => {
    const theme = isDarkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('athena-theme', theme);
  }, [isDarkMode]);

  useEffect(() => {
    fetchUploads();
  }, []);

  const fetchUploads = async () => {
    try {
      const response = await fetch(`${API_BASE}/uploads`);
      const data = await response.json();
      setUploads(data.files || []);
    } catch (error) {
      console.error('Failed to fetch uploads:', error);
    }
  };

  const handleFileDelete = async (deletedFile) => {
    // Remove from local state
    setUploads(prev => prev.filter(f => f.path !== deletedFile.path));
    // If deleted file was selected, clear selection
    if (selectedFile === deletedFile.path) {
      setSelectedFile(null);
    }
    // Refresh from server
    await fetchUploads();
  };

  const handleFileUpload = async (files) => {
    setLoading(true);
    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (data.ingested) {
        await fetchUploads();
        if (data.ingested.length > 0) {
          setSelectedFile(data.ingested[0].path);
        }
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const renderActiveView = () => {
    switch (activeView) {
      case 'library':
        return <LibraryView uploads={uploads} onFileSelect={setSelectedFile} selectedFile={selectedFile} onFileDelete={handleFileDelete} onRefresh={fetchUploads} />;
      case 'qa':
        return <DocumentQA selectedFile={selectedFile} uploads={uploads} />;
      case 'synthesis':
        return <SynthesisView />;
      case 'related':
        return <RelatedPapers selectedFile={selectedFile} />;
      default:
        return <LibraryView uploads={uploads} onFileSelect={setSelectedFile} selectedFile={selectedFile} />;
    }
  };

  const toggleTheme = () => setIsDarkMode((prev) => !prev);

  return (
    <div className="app">
      <Header isDarkMode={isDarkMode} onToggleTheme={toggleTheme} />
      <div className="app-container">
        <Sidebar 
          activeView={activeView} 
          onViewChange={setActiveView}
          onFileUpload={handleFileUpload}
          loading={loading}
        />
        <main className="main-content">
          {renderActiveView()}
        </main>
      </div>
    </div>
  );
}

export default App;

