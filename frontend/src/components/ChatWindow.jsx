//\src\Component\ChatWindow
import axios from "axios";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import PropTypes from "prop-types";
import React, { Component, useCallback, useEffect, useRef, useState } from "react";
import { Bar, Line, Pie } from "react-chartjs-2";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "../App.css";

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

// --- SVG Icons ---
const UserAvatar = () => (
  <div className="avatar user-avatar">
    <svg xmlns="http://www.w3.org/2000/svg" className="icon" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
  </div>
);

const AgentAvatar = () => (
  <div className="avatar agent-avatar">
    <svg xmlns="http://www.w3.org/2000/svg" className="icon" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 1.5c-3.87 0-7 3.13-7 7v6c0 1.1.9 2 2 2h3v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h3c1.1 0 2-.9 2-2V8.5c0-3.87-3.13-7-7-7zm0 14c-1.66 0-3-1.34-3-3V9h6v3c0 1.66-1.34 3-3 3z" />
    </svg>
  </div>
);

const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-small" viewBox="0 0 24 24" fill="currentColor">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
  </svg>
);

const SettingsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.82 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.82 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.82-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.82-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
);

const XCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-x-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ThemeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
);

const AttachmentIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
  </svg>
);

const FileLoadingIndicator = () => (
  <div className="file-loading-indicator">
    <div className="loading-dot dot-1"></div>
    <div className="loading-dot dot-2"></div>
    <div className="loading-dot dot-3"></div>
  </div>
);

const ThemeToggle = ({ theme, toggleTheme }) => {
  return (
    <div className="theme-toggle">
      <button 
        onClick={() => toggleTheme('light')} 
        className={theme === 'light' ? 'active' : ''}
        aria-label="Light theme"
      >
        ☀️
      </button>
      <button 
        onClick={() => toggleTheme('dark')} 
        className={theme === 'dark' ? 'active' : ''}
        aria-label="Dark theme"
      >
        🌙
      </button>
    </div>
  );
};

const ChatWindow = () => {
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentThreadId, setCurrentThreadId] = useState("");
  const [agentBehavior, setAgentBehavior] = useState("Balanced");
  const [messageLayout, setMessageLayout] = useState("alternating");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [inputTokens, setInputTokens] = useState(0);
  const [outputTokens, setOutputTokens] = useState(0);
  const [isSidebarHidden, setIsSidebarHidden] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(350);
  const [theme, setTheme] = useState('light');

  const chatEndRef = useRef(null);
  const sidebarRef = useRef(null);
  const appContainerRef = useRef(null);
  const [isResizing, setIsResizing] = useState(false);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const fileInputRef = useRef(null);

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    setTheme(initialTheme);
    document.documentElement.setAttribute('data-theme', initialTheme);
  }, []);

  // Toggle theme function
  const toggleTheme = (newTheme) => {
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const ChartComponent = ({ chartData }) => {
    if (!chartData || !chartData.data) {
      return (
        <div className="error-message-bubble">
          Invalid chart data format
        </div>
      );
    }

    return (
      <>
        {chartData.type === "bar" && <Bar data={chartData.data} options={chartData.options} />}
        {chartData.type === "line" && <Line data={chartData.data} options={chartData.options} />}
        {chartData.type === "pie" && <Pie data={chartData.data} options={chartData.options} />}
      </>
    );
  };

  ChartComponent.propTypes = {
    chartData: PropTypes.shape({
      type: PropTypes.string,
      data: PropTypes.object,
      options: PropTypes.object,
    }),
  };

  const extractGraphData = (responseText) => {
    try {
      const jsonStart = responseText.indexOf('{');
      const jsonEnd = responseText.lastIndexOf('}') + 1;
      
      if (jsonStart >= 0 && jsonEnd > jsonStart) {
        const jsonStr = responseText.substring(jsonStart, jsonEnd);
        const parsedData = JSON.parse(jsonStr);
        return parsedData.graph_data || null;
      }
    } catch (e) {
      console.error("Error parsing embedded JSON:", e);
    }
    return null;
  };

  const renderGraph = (graphData) => {
    if (!graphData) {
      return (
        <div className="error-message-bubble">
          No graph data received
        </div>
      );
    }

    const chartData = {
      type: graphData.type || 'bar',
      data: {
        labels: graphData.labels || [],
        datasets: [{
          label: graphData.title || 'Deals Data',
          data: graphData.values || [],
          backgroundColor: theme === 'dark' ? 'rgba(129, 199, 132, 0.7)' : 'rgba(54, 162, 235, 0.7)',
          borderColor: theme === 'dark' ? 'rgba(129, 199, 132, 1)' : 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: graphData.title || 'Deals Analysis',
            color: theme === 'dark' ? '#E0E0E0' : '#212529'
          },
          legend: {
            labels: {
              color: theme === 'dark' ? '#E0E0E0' : '#212529'
            }
          }
        },
        scales: {
          y: {
            beginAtZero: false,
            ticks: {
              color: theme === 'dark' ? '#E0E0E0' : '#212529'
            },
            grid: {
              color: theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
            }
          },
          x: {
            ticks: {
              color: theme === 'dark' ? '#E0E0E0' : '#212529'
            },
            grid: {
              color: theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
            }
          }
        }
      }
    };

    return (
      <div className="chart-container" style={{ height: '400px', width: '100%' }}>
        <ChartComponent chartData={chartData} />
      </div>
    );
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (appContainerRef.current) {
      appContainerRef.current.style.setProperty("--sidebar-width", `${sidebarWidth}px`);
    }
  }, [sidebarWidth]);

  const onMouseDown = useCallback((e) => {
    if (!isSidebarHidden) {
      setIsResizing(true);
      startX.current = e.clientX;
      startWidth.current = sidebarRef.current.offsetWidth;
    }
  }, [isSidebarHidden]);

  const onMouseMove = useCallback((e) => {
    if (!isResizing) return;
    const newWidth = startWidth.current + (e.clientX - startX.current);
    const clampedWidth = Math.max(250, Math.min(500, newWidth));
    setSidebarWidth(clampedWidth);
  }, [isResizing]);

  const onMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    } else {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [isResizing, onMouseMove, onMouseUp]);

  const toggleSidebar = () => {
    setIsSidebarHidden((prev) => !prev);
  };

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!prompt.trim() && (!uploadedFile || !uploadedFile.content)) {
      return;
    }

    const userMessage = {
      sender: "user",
      text: prompt.trim(),
      ...(uploadedFile && {
        file_name: uploadedFile.fileName,
        file_content: uploadedFile.content,
      }),
    };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setPrompt("");
    setLoading(true);

    const payload = {
      agentMode: agentBehavior,
      prompt: prompt.trim(),
      file_content: uploadedFile ? uploadedFile.content : undefined,
      chat_history: messages.map((msg) => ({
        role: msg.sender === "user" ? "user" : "agent",
        content: msg.text,
      })),
      thread_id: currentThreadId || undefined
    };

    try {
      const res = await axios.post("http://localhost:8000/ask", payload);
      console.log("API Response:", res.data);

      let agentResponse = {
        sender: "agent",
        text: res.data.response,
        threadId: res.data.thread_id,
        tokens: {
          input: res.data.input_tokens,
          output: res.data.output_tokens
        }
      };

      // First try root-level graph_data
      if (res.data.graph_data) {
        agentResponse.type = "graph";
        agentResponse.data = res.data.graph_data;
      } 
      // Then try extracting from response text
      else {
        const extractedGraphData = extractGraphData(res.data.response);
        if (extractedGraphData) {
          agentResponse.type = "graph";
          agentResponse.data = extractedGraphData;
        }
      }

      setMessages((prev) => [...prev, agentResponse]);
      setCurrentThreadId(res.data.thread_id);
      setInputTokens(res.data.input_tokens);
      setOutputTokens(res.data.output_tokens);

    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "agent",
          text: "Error: Could not get a response from the agent.",
          isError: true
        }
      ]);
    } finally {
      setLoading(false);
      setUploadedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, [prompt, messages, uploadedFile, currentThreadId, agentBehavior]);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const MAX_FILE_SIZE = 200 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE) {
      alert("File size exceeds 200MB limit.");
      event.target.value = "";
      setUploadedFile(null);
      return;
    }

    setUploadedFile({
      name: file.name,
      content: null,
      isLoading: true,
      error: null,
    });

    const reader = new FileReader();
    reader.onload = (e) => {
      setUploadedFile((prev) => ({
        ...prev,
        content: e.target.result,
        isLoading: false,
      }));
    };
    reader.onerror = () => {
      alert("Failed to read file");
      setUploadedFile({
        name: file.name,
        content: null,
        isLoading: false,
        error: "Read error",
      });
      event.target.value = "";
    };
    reader.onabort = () => {
      alert("File reading cancelled");
      setUploadedFile(null);
      event.target.value = "";
    };
    reader.readAsText(file);
  };

  const handleClearFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="app-container" ref={appContainerRef}>
      {/* Left Sidebar */}
      <div
        ref={sidebarRef}
        className={`sidebar ${isSidebarHidden ? "hidden" : ""}`}
        style={{ width: isSidebarHidden ? "0px" : `${sidebarWidth}px` }}
      >
        <div className="agent-settings-header">
          <SettingsIcon />
          <h2>Agent Settings</h2>
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>

        <div className="settings-section">
          <label className="settings-label">Current Thread ID:</label>
          <input
            type="text"
            className="thread-id-input"
            value={currentThreadId}
            readOnly
            title={currentThreadId}
          />
        </div>

        <div className="settings-section">
          <label className="settings-label">Agent Behavior</label>
          <div className="behavior-options">
            <button
              className={`behavior-option ${agentBehavior === "Balanced" ? "active" : ""}`}
              onClick={() => setAgentBehavior("Balanced")}
            >
              Balanced
            </button>
            <button
              className={`behavior-option ${agentBehavior === "Short" ? "active" : ""}`}
              onClick={() => setAgentBehavior("Short")}
            >
              Short
            </button>
            <button
              className={`behavior-option ${agentBehavior === "Detailed" ? "active" : ""}`}
              onClick={() => setAgentBehavior("Detailed")}
            >
              Detailed
            </button>
            <button
              className={`behavior-option ${agentBehavior === "Structured" ? "active" : ""}`}
              onClick={() => setAgentBehavior("Structured")}
            >
              Structured
            </button>
          </div>
        </div>

        <div className="settings-section">
          <label className="settings-label">Message Layout</label>
          <div className="layout-options">
            <button
              className={`layout-option ${messageLayout === "alternating" ? "active" : ""}`}
              onClick={() => setMessageLayout("alternating")}
            >
              Alternating
            </button>
            <button
              className={`layout-option ${messageLayout === "same-side" ? "active" : ""}`}
              onClick={() => setMessageLayout("same-side")}
            >
              Same Side
            </button>
          </div>
        </div>

        {!isSidebarHidden && (
          <div className="sidebar-resizer" onMouseDown={onMouseDown}></div>
        )}
      </div>

      {/* Sidebar Toggle Button */}
      <button
        className={`sidebar-toggle-button ${isSidebarHidden ? "rotated" : ""}`}
        onClick={toggleSidebar}
        title={isSidebarHidden ? "Show Sidebar" : "Hide Sidebar"}
        style={{ left: isSidebarHidden ? "0px" : `${sidebarWidth}px` }}
      >
        <ChevronLeftIcon />
      </button>

      {/* Main Chat Area */}
      <div className="main-chat-area">
        <div className="main-chat-header">
          <h3 className="welcome-title">E&C - Integrated AI Agents</h3>
          <p className="welcome-subtitle">AI-powered agent for front, middle and back offices</p>
        </div>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`chat-message-row ${
                msg.sender === "user" && messageLayout === "alternating"
                  ? "user-message-row"
                  : ""
              }`}
            >
              <div
                className={`message-content-wrapper ${
                  msg.sender === "user" && messageLayout === "alternating"
                    ? "user-message-wrapper"
                    : ""
                }`}
              >
                {msg.sender === "user" ? <UserAvatar /> : <AgentAvatar />}
                <div
                  className={`message-bubble ${msg.sender}-message-bubble ${
                    msg.isError ? "error-message-bubble" : ""
                  }`}
                >
                  {msg.type === "graph" ? (
                    renderGraph(msg.data)
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {typeof msg.text === "string" ? msg.text : JSON.stringify(msg.text)}
                    </ReactMarkdown>
                  )}
                  {msg.tokens && (
                    <div className="token-info-small">
                      <span>Tokens: {msg.tokens.input} in / {msg.tokens.output} out</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className={`chat-message-row ${messageLayout === "alternating" ? "agent-message-row" : ""}`}>
              <div className={`message-content-wrapper ${messageLayout === "alternating" ? "agent-message-wrapper" : ""}`}>
                <AgentAvatar />
                <div className="message-bubble agent-message-bubble">
                  <div className="loading-indicator">
                    <div className="loading-dot dot-1"></div>
                    <div className="loading-dot dot-2"></div>
                    <div className="loading-dot dot-3"></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="input-area">
          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="file"
              className="file-input"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".txt,.md,.csv,.json,.log"
              style={{ display: 'none' }}
            />
            {uploadedFile && (
              <div className="file-context-display">
                <span className="file-name-tag">
                  <span className="file-icon">📄</span> {uploadedFile.name}
                </span>
                {uploadedFile.isLoading && <FileLoadingIndicator />}
                {!uploadedFile.isLoading && (
                  <button
                    onClick={handleClearFile}
                    className="clear-file-button"
                    title="Clear uploaded file"
                  >
                    <XCircleIcon />
                  </button>
                )}
              </div>
            )}
            <div className="input-row">
              <button
                type="button"
                className="attach-button"
                onClick={handleFileClick}
                title="Attach file"
              >
                <AttachmentIcon />
              </button>
              <textarea
                className="input-textarea"
                rows={3}
                placeholder="Ask me anything..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    handleSubmit(e);
                  }
                }}
                disabled={loading || (uploadedFile && uploadedFile.isLoading)}
              ></textarea>
              <button
                type="submit"
                className={`send-button ${
                  (prompt.trim() || (uploadedFile && uploadedFile.content && !uploadedFile.isLoading && !uploadedFile.error)) && !loading
                    ? "send-button-active"
                    : "send-button-disabled"
                }`}
                disabled={
                  (!prompt.trim() && (!uploadedFile || !uploadedFile.content || uploadedFile.isLoading || uploadedFile.error)) ||
                  loading
                }
              >
                <SendIcon />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;