// src/components/ChatWindow.jsx
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

// Configure console logging with timestamps
const log = {
  info: (...args) => console.log(`[${new Date().toISOString()}] INFO:`, ...args),
  warn: (...args) => console.warn(`[${new Date().toISOString()}] WARN:`, ...args),
  error: (...args) => console.error(`[${new Date().toISOString()}] ERROR:`, ...args),
  debug: (...args) => console.debug(`[${new Date().toISOString()}] DEBUG:`, ...args)
};

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

const LightThemeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.36 6.36l-.71-.71M6.34 6.34l-.71-.71m12.73 0l-.71.71M6.34 17.66l-.71.71M12 8a4 4 0 100 8 4 4 0 000-8z" />
  </svg>
);

const DarkThemeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
  </svg>
);

const ThemeToggle = ({ theme, toggleTheme }) => {
  return (
    <div className="theme-toggle">
      <button
        onClick={() => toggleTheme('light')}
        className={theme === 'light' ? 'active' : ''}
        aria-label="Light theme"
      >
        <LightThemeIcon />
      </button>
      <button
        onClick={() => toggleTheme('dark')}
        className={theme === 'dark' ? 'active' : ''}
        aria-label="Dark theme"
      >
        <DarkThemeIcon />
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
    log.info("Initializing theme:", initialTheme);
    setTheme(initialTheme);
    document.documentElement.setAttribute('data-theme', initialTheme);
  }, []);

  // Toggle theme function
  const toggleTheme = (newTheme) => {
    log.info("Changing theme to:", newTheme);
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  // Enhanced ChartComponent with validation
  const ChartComponent = ({ chartData }) => {
    if (!chartData || !chartData.data) {
      log.error("Invalid chart data format", chartData);
      return (
        <div className="error-message-bubble">
          Invalid chart data format
        </div>
      );
    }

    try {
      return (
        <>
          {chartData.type === "bar" && <Bar data={chartData.data} options={chartData.options} />}
          {chartData.type === "line" && <Line data={chartData.data} options={chartData.options} />}
          {chartData.type === "pie" && <Pie data={chartData.data} options={chartData.options} />}
        </>
      );
    } catch (error) {
      log.error("Chart rendering error:", error);
      return (
        <div className="error-message-bubble">
          Chart rendering failed: {error.message}
        </div>
      );
    }
  };

  ChartComponent.propTypes = {
    chartData: PropTypes.shape({
      type: PropTypes.string,
      data: PropTypes.object,
      options: PropTypes.object,
    }),
  };

  // Robust graph data validation
  const validateGraphData = (data) => {
    if (!data) {
      log.debug("Graph data is null/undefined");
      return false;
    }
    
    const requiredFields = ['type', 'labels', 'values'];
    for (const field of requiredFields) {
      if (!(field in data)) {
        log.debug(`Missing required field: ${field}`);
        return false;
      }
    }

    if (!['bar', 'line', 'pie'].includes(data.type)) {
      log.debug(`Invalid chart type: ${data.type}`);
      return false;
    }

    if (!Array.isArray(data.labels) || !Array.isArray(data.values)) {
      log.debug("Labels or values are not arrays");
      return false;
    }

    if (data.labels.length !== data.values.length) {
      log.debug("Labels and values length mismatch");
      return false;
    }

    if (data.labels.length === 0) {
      log.debug("Empty data arrays");
      return false;
    }

    return true;
  };

  // Enhanced graph data extraction with multiple fallbacks
  const extractGraphData = (response) => {
    log.debug("Attempting to extract graph data from response");
    
    // Case 1: Response is already a graph data object
    if (response && typeof response === 'object' && response.graph_data) {
      log.debug("Found graph_data in response object");
      return response.graph_data;
    }
    
    // Case 2: Response is a string that might contain JSON
    if (typeof response === 'string') {
      try {
        // Try parsing as pure JSON first
        try {
          const parsed = JSON.parse(response);
          if (parsed.graph_data) {
            log.debug("Found graph_data in parsed JSON");
            return parsed.graph_data;
          }
          if (parsed.graphData) { // Handle camelCase variation
            log.debug("Found graphData in parsed JSON");
            return parsed.graphData;
          }
        } catch (e) {
          log.debug("Response is not pure JSON, trying embedded JSON");
        }

        // Try extracting embedded JSON
        try {
          const jsonStart = response.indexOf('{');
          const jsonEnd = response.lastIndexOf('}') + 1;
          
          if (jsonStart >= 0 && jsonEnd > jsonStart) {
            const jsonStr = response.substring(jsonStart, jsonEnd);
            log.debug("Extracted potential JSON:", jsonStr.slice(0, 100) + (jsonStr.length > 100 ? "..." : ""));
            
            const parsedData = JSON.parse(jsonStr);
            if (parsedData.graph_data) {
              log.debug("Found graph_data in embedded JSON");
              return parsedData.graph_data;
            }
            if (parsedData.graphData) { // Handle camelCase variation
              log.debug("Found graphData in embedded JSON");
              return parsedData.graphData;
            }
          }
        } catch (e) {
          log.debug("Failed to parse embedded JSON:", e.message);
        }

        // Try to find graph data in markdown code blocks
        const codeBlockRegex = /```(?:json)?\s*({.*?})\s*```/s;
        const match = response.match(codeBlockRegex);
        if (match) {
          try {
            const parsed = JSON.parse(match[1]);
            if (parsed.graph_data || parsed.graphData) {
              log.debug("Found graph data in markdown code block");
              return parsed.graph_data || parsed.graphData;
            }
          } catch (e) {
            log.debug("Failed to parse code block JSON:", e.message);
          }
        }
      } catch (e) {
        log.debug("Error during string response processing:", e);
      }
    }

    log.debug("No valid graph data found in response");
    return null;
  };

  // Enhanced graph rendering with fallbacks
  const renderGraph = (graphData) => {
    log.debug("Rendering graph with data:", graphData);
    
    if (!validateGraphData(graphData)) {
      log.error("Invalid graph data structure:", graphData);
      return (
        <div className="error-message-bubble">
          Invalid graph data structure. Expected format: {"{"}
          type: 'bar'|'line'|'pie', labels: [], values: []
          {"}"}
          <div className="debug-info">
            <pre>{JSON.stringify(graphData, null, 2)}</pre>
          </div>
        </div>
      );
    }

    // Check if values are empty or invalid
    if (!graphData.values || graphData.values.length === 0 || 
        graphData.values.some(v => v === null || v === undefined || isNaN(v))) {
      log.warn("Graph data has invalid values - falling back to table view");
      return (
        <div className="data-fallback">
          <h4>{graphData.title || 'Data Table'}</h4>
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {graphData.labels.map((label, index) => (
                <tr key={index}>
                  <td>{label}</td>
                  <td>
                    {graphData.values[index] !== undefined && graphData.values[index] !== null && !isNaN(graphData.values[index]) 
                      ? graphData.values[index] 
                      : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Prepare chart data with theme-aware colors
    const chartData = {
      type: graphData.type || 'bar',
      data: {
        labels: graphData.labels || [],
        datasets: [{
          label: graphData.dataset_label || 'Deals Data',
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

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    log.debug("Messages updated, scrolling to bottom");
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Update sidebar width CSS variable
  useEffect(() => {
    if (appContainerRef.current) {
      log.debug(`Updating sidebar width to ${sidebarWidth}px`);
      appContainerRef.current.style.setProperty("--sidebar-width", `${sidebarWidth}px`);
    }
  }, [sidebarWidth]);

  // Sidebar resize handlers
  const onMouseDown = useCallback((e) => {
    if (!isSidebarHidden) {
      log.debug("Starting sidebar resize");
      setIsResizing(true);
      startX.current = e.clientX;
      startWidth.current = sidebarRef.current.offsetWidth;
    }
  }, [isSidebarHidden]);

  const onMouseMove = useCallback((e) => {
    if (!isResizing) return;
    const newWidth = startWidth.current + (e.clientX - startX.current);
    const clampedWidth = Math.max(250, Math.min(500, newWidth));
    log.debug(`Resizing sidebar to ${clampedWidth}px`);
    setSidebarWidth(clampedWidth);
  }, [isResizing]);

  const onMouseUp = useCallback(() => {
    if (isResizing) {
      log.debug("Finished sidebar resize");
      setIsResizing(false);
    }
  }, [isResizing]);

  // Add/remove resize event listeners
  useEffect(() => {
    if (isResizing) {
      log.debug("Adding resize event listeners");
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    } else {
      log.debug("Removing resize event listeners");
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [isResizing, onMouseMove, onMouseUp]);

  const toggleSidebar = () => {
    log.debug(`Toggling sidebar visibility. Current state: ${isSidebarHidden}`);
    setIsSidebarHidden((prev) => !prev);
  };

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!prompt.trim() && (!uploadedFile || !uploadedFile.content)) {
      log.warn("Submit attempted with empty prompt and no file");
      return;
    }

    log.info("Submitting new message to agent");
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

    log.debug("Sending payload to API:", {
      ...payload,
      file_content: payload.file_content ? `[${payload.file_content.length} chars]` : undefined
    });

    try {
      const res = await axios.post("http://localhost:8000/ask", payload);
      log.info("Received API response:", {
        status: res.data.status,
        thread_id: res.data.thread_id,
        has_graph_data: !!res.data.graph_data
      });

      let agentResponse = {
        sender: "agent",
        text: res.data.response,
        threadId: res.data.thread_id,
        tokens: {
          input: res.data.input_tokens,
          output: res.data.output_tokens
        }
      };

      if (res.data.status === "error") {
        log.error("API returned error:", res.data.message);
        agentResponse.text = `Error: ${res.data.message}`;
        if (res.data.details?.available_columns) {
          agentResponse.text += `\n\nAvailable columns: ${res.data.details.available_columns.join(', ')}`;
        }
        agentResponse.isError = true;
      }
      
      // Extract graph data from multiple possible locations
      let graphData = null;
      if (res.data.graph_data) {
        log.debug("Found graph_data in top-level response");
        graphData = res.data.graph_data;
      } else {
        graphData = extractGraphData(res.data.response);
        if (graphData) {
          log.debug("Extracted graph_data from response text");
        }
      }

      if (graphData) {
        log.debug("Adding graph data to response");
        agentResponse.type = "graph";
        agentResponse.data = graphData;
      }

      setMessages((prev) => [...prev, agentResponse]);
      setCurrentThreadId(res.data.thread_id);
      setInputTokens(res.data.input_tokens);
      setOutputTokens(res.data.output_tokens);

    } catch (error) {
      log.error("Error sending message:", error);
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "agent",
          text: "Error: Could not get a response from the agent. Please try again.",
          isError: true,
          details: error.response?.data || error.message
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
    if (!file) {
      log.debug("File selection cancelled");
      return;
    }

    const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200MB
    if (file.size > MAX_FILE_SIZE) {
      log.warn("File size exceeds limit:", file.size);
      alert("File size exceeds 200MB limit.");
      event.target.value = "";
      setUploadedFile(null);
      return;
    }

    log.info("Uploading file:", file.name);
    setUploadedFile({
      name: file.name,
      content: null,
      isLoading: true,
      error: null,
    });

    const reader = new FileReader();
    reader.onload = (e) => {
      log.debug("File read successfully");
      setUploadedFile((prev) => ({
        ...prev,
        content: e.target.result,
        isLoading: false,
      }));
    };
    reader.onerror = () => {
      log.error("File read error");
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
      log.warn("File read aborted");
      alert("File reading cancelled");
      setUploadedFile(null);
      event.target.value = "";
    };
    reader.readAsText(file);
  };

  const handleClearFile = () => {
    log.debug("Clearing uploaded file");
    setUploadedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileClick = () => {
    log.debug("Triggering file input click");
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
              onClick={() => {
                log.debug("Setting agent behavior to Balanced");
                setAgentBehavior("Balanced");
              }}
            >
              Balanced
            </button>
            <button
              className={`behavior-option ${agentBehavior === "Short" ? "active" : ""}`}
              onClick={() => {
                log.debug("Setting agent behavior to Short");
                setAgentBehavior("Short");
              }}
            >
              Short
            </button>
            <button
              className={`behavior-option ${agentBehavior === "Detailed" ? "active" : ""}`}
              onClick={() => {
                log.debug("Setting agent behavior to Detailed");
                setAgentBehavior("Detailed");
              }}
            >
              Detailed
            </button>
            <button
              className={`behavior-option ${agentBehavior === "Structured" ? "active" : ""}`}
              onClick={() => {
                log.debug("Setting agent behavior to Structured");
                setAgentBehavior("Structured");
              }}
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
              onClick={() => {
                log.debug("Setting message layout to alternating");
                setMessageLayout("alternating");
              }}
            >
              Alternating
            </button>
            <button
              className={`layout-option ${messageLayout === "same-side" ? "active" : ""}`}
              onClick={() => {
                log.debug("Setting message layout to same-side");
                setMessageLayout("same-side");
              }}
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
          <h3 className="welcome-title">E&C - Interactive Agent</h3>
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
                  {msg.details && (
                    <div className="debug-details">
                      <details>
                        <summary>Error Details</summary>
                        <pre>{JSON.stringify(msg.details, null, 2)}</pre>
                      </details>
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
              ref={fileInputRef}
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              accept=".txt,.csv,.json,.pdf,.doc,.docx"
            />
            
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
            {uploadedFile && (
              <div className="file-attachment-info">
                {uploadedFile.isLoading ? (
                  <FileLoadingIndicator />
                ) : (
                  <>
                    <span>{uploadedFile.name}</span>
                    <button
                      type="button"
                      className="clear-file-button"
                      onClick={handleClearFile}
                      title="Remove file"
                    >
                      <XCircleIcon />
                    </button>
                  </>
                )}
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;