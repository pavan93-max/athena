import React from 'react';
import './Header.css';
import { BookOpen, Moon, Sun } from 'lucide-react';

const Header = ({ isDarkMode, onToggleTheme }) => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo">
          <BookOpen className="logo-icon" />
          <div>
            <h1>Athena Research Assistant</h1>
            <p className="header-subtitle">AI-Powered Research & Document Analysis</p>
          </div>
        </div>
        <button className="theme-toggle" onClick={onToggleTheme}>
          {isDarkMode ? <Sun className="theme-icon" /> : <Moon className="theme-icon" />}
          <span>{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
        </button>
      </div>
    </header>
  );
};

export default Header;

