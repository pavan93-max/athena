import React, { useRef } from 'react';
import './Sidebar.css';
import { 
  Library, MessageSquare, Sparkles, Search, 
  Upload, Loader 
} from 'lucide-react';

const Sidebar = ({ activeView, onViewChange, onFileUpload, loading }) => {
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileUpload(files);
    }
  };

  const menuItems = [
    { id: 'library', label: 'Library', icon: Library },
    { id: 'qa', label: 'Ask Document', icon: MessageSquare },
    { id: 'synthesis', label: 'Synthesis', icon: Sparkles },
    { id: 'related', label: 'Related Papers', icon: Search },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-content">
        <div className="upload-section">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <button
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader className="icon spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="icon" />
                Upload PDFs
              </>
            )}
          </button>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-item ${activeView === item.id ? 'active' : ''}`}
                onClick={() => onViewChange(item.id)}
              >
                <Icon className="icon" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
};

export default Sidebar;

