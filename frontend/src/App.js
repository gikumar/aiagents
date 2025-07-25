// src/App.js
import React from 'react';
import ChatWindow from './components/ChatWindow';
import './App.css'; // This line correctly imports the CSS file

function App() {
  return (
    <div className="App">
      <ChatWindow />
    </div>
  );
}

export default App;
