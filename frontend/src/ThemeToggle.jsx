import React, { useState, useEffect } from 'react';
import '../App.css';

const ThemeToggle = () => {
  const [theme, setTheme] = useState(() => {
    // Initialize from localStorage or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return savedTheme || (systemPrefersDark ? 'dark' : 'light');
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <div className="theme-toggle">
      <button 
        onClick={() => setTheme('light')} 
        className={theme === 'light' ? 'active' : ''}
        aria-label="Light theme"
      >
        ☀️
      </button>
      <button 
        onClick={() => setTheme('dark')} 
        className={theme === 'dark' ? 'active' : ''}
        aria-label="Dark theme"
      >
        🌙
      </button>
    </div>
  );
};

export default ThemeToggle;