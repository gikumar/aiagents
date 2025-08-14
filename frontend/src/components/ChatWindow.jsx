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
import React, { memo, useCallback, useEffect, useRef, useState } from "react";
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

const CopyIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-x-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-2m-4-4l-4 4m0-4h.01M16 12l-4-4m4 4h.01M12 10a2 2 0 012 2v4a2 2 0 01-2 2h-4a2 2 0 01-2-2v-4a2 2 0 012-2h4z" />
  </svg>
);

const RetryIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="icon-x-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.999 8.999 0 0120.985 12a9 9 0 11-14.471-8.529M20 9v5h-.582m-15.356-2A8.999 8.999 0 013.015 12a9 9 0 1114.471 8.529" />
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

const MemoizedChartComponent = memo(({ chartData }) => {
  if (!chartData || !chartData.data) {
    log.error("Invalid chart data format", chartData);
    return (
      <div className="error-message-bubble">
        Invalid chart data format
      </div>
    );
  }

  try {
    const Component =
      chartData.type === "bar" ? Bar :
      chartData.type === "line" ? Line :
      chartData.type === "pie" ? Pie :
      null;

    if (!Component) {
      return <div className="error-message-bubble">Unsupported chart type: {chartData.type}</div>;
    }

    return (
      <div className="chart-container">
        <Component data={chartData.data} options={chartData.options} />
      </div>
    );
  } catch (error) {
    log.error("Chart rendering error:", error);
    return (
      <div className="error-message-bubble">
        Chart rendering failed: {error.message}
      </div>
    );
  }
});

MemoizedChartComponent.propTypes = {
  chartData: PropTypes.shape({
    type: PropTypes.string,
    data: PropTypes.object,
    options: PropTypes.object,
  }),
};

const ChatInput = memo(({ prompt, setPrompt, handleSubmit, loading, uploadedFile, handleClearFile, handleFileClick, fileInputRef, handleFileUpload }) => (
  <div className="input-area">
    <form onSubmit={handleSubmit} className="input-form">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        style={{ display: 'none' }}
        accept=".txt,.csv,.json"
        aria-label="Attach a text, CSV, or JSON file"
      />

      <div className="input-row">
        <button
          type="button"
          className="attach-button"
          onClick={handleFileClick}
          title="Attach file"
          aria-label="Attach file"
        >
          <AttachmentIcon />
        </button>
        <textarea
          className="input-textarea"
          rows={3}
          placeholder="Ask me anything..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          aria-label="Message input"
        ></textarea>
        <button
          type="submit"
          aria-label="Send message"
          className={`send-button ${
            (prompt.trim() || (uploadedFile && uploadedFile.content && !uploadedFile.isLoading && !uploadedFile.error)) && !loading
              ? "send-button-active"
              : "send-button-disabled"
          }`}
          disabled={
            (!prompt.trim() && (!uploadedFile || !uploadedFile.content || uploadedFile.isLoading || uploadedFile.error)) ||
            loading
          }
          title="Send"
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
                aria-label="Remove file"
              >
                <XCircleIcon />
              </button>
            </>
          )}
        </div>
      )}
    </form>
  </div>
));

ChatInput.propTypes = {
  prompt: PropTypes.string.isRequired,
  setPrompt: PropTypes.func.isRequired,
  handleSubmit: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  uploadedFile: PropTypes.object,
  handleClearFile: PropTypes.func.isRequired,
  handleFileClick: PropTypes.func.isRequired,
  fileInputRef: PropTypes.object.isRequired,
  handleFileUpload: PropTypes.func.isRequired,
};

const ChatMessage = memo(({ message, messageLayout, onCopy, onRetry }) => {
  const messageRef = useRef(null);

  const handleCopyClick = useCallback(() => {
    if (messageRef.current) {
      onCopy(messageRef.current.innerText);
    }
  }, [onCopy]);

  return (
    <div
      className={`chat-message-row ${
        message.sender === "user" && messageLayout === "alternating"
          ? "user-message-row"
          : ""
      }`}
    >
      <div
        className={`message-content-wrapper ${
          message.sender === "user" && messageLayout === "alternating"
            ? "user-message-wrapper"
            : ""
        }`}
      >
        {message.sender === "user" ? <UserAvatar /> : <AgentAvatar />}
        <div
          className={`message-bubble ${message.sender}-message-bubble ${
            message.isError ? "error-message-bubble" : ""
          }`}
        >
          {message.sender === "agent" && (
            <div className="message-actions">
              <button className="copy-button" onClick={handleCopyClick} title="Copy response" aria-label="Copy response">
                <CopyIcon />
              </button>
              {message.isError && (
                <button
                  className="retry-button"
                  onClick={() => onRetry(message.index)}
                  title="Retry"
                  aria-label="Retry"
                >
                  <RetryIcon />
                </button>
              )}
            </div>
          )}
          <div ref={messageRef}>
            {message.type === "graph" ? (
              <MemoizedChartComponent chartData={message.data} />
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {typeof message.text === "string" ? message.text : JSON.stringify(message.text)}
              </ReactMarkdown>
            )}
            {message.tokens && (
              <div className="token-info-small">
                <span>Tokens: {message.tokens.input} in / {message.tokens.output} out</span>
              </div>
            )}
            {message.details && (
              <div className="debug-details">
                <details>
                  <summary>Error Details</summary>
                  <pre>{JSON.stringify(message.details, null, 2)}</pre>
                </details>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

ChatMessage.propTypes = {
  message: PropTypes.object.isRequired,
  messageLayout: PropTypes.string.isRequired,
  onCopy: PropTypes.func.isRequired,
  onRetry: PropTypes.func.isRequired,
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
  const [showScrollButton, setShowScrollButton] = useState(false);

  const chatEndRef = useRef(null);
  const chatMessagesRef = useRef(null);
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

  const handleCopy = useCallback(async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      log.info("Text copied to clipboard successfully!");
    } catch (err) {
      log.error("Failed to copy text:", err);
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      log.warn("Text copied using fallback method");
    }
  }, []);

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

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    log.debug("Messages updated, scrolling to bottom");
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle scroll event for the "Scroll to Top" button
  useEffect(() => {
    const handleScroll = () => {
      if (chatMessagesRef.current) {
        const isScrolled = chatMessagesRef.current.scrollTop > 100;
        setShowScrollButton(isScrolled);
      }
    };

    const messagesContainer = chatMessagesRef.current;
    if (messagesContainer) {
      messagesContainer.addEventListener('scroll', handleScroll);
    }

    return () => {
      if (messagesContainer) {
        messagesContainer.removeEventListener('scroll', handleScroll);
      }
    };
  }, []);

  const scrollToTop = () => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  };

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
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [isResizing, onMouseMove, onMouseUp]);

  const toggleSidebar = () => {
    log.debug(`Toggling sidebar visibility. Current state: ${isSidebarHidden}`);
    setIsSidebarHidden((prev) => !prev);
  };

  const handleSend = useCallback(async (text, file, history) => {
    setLoading(true);

    const payload = {
      agentMode: agentBehavior,
      prompt: text.trim(),
      file_content: file ? file.content : undefined,
      chat_history: history,
      thread_id: currentThreadId || undefined
    };

    log.debug("Sending payload to API:", {
      ...payload,
      file_content: payload.file_content ? `[${payload.file_content.length} chars]` : undefined
    });

    // theme-aware palettes for charts
    const lightThemePalette = [
      'rgba(54, 162, 235, 0.7)', 'rgba(255, 99, 132, 0.7)', 'rgba(255, 206, 86, 0.7)',
      'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)',
      'rgba(192, 192, 192, 0.7)'
    ];
    const darkThemePalette = [
      'rgba(129, 199, 132, 0.7)', 'rgba(255, 159, 64, 0.7)', 'rgba(255, 205, 86, 0.7)',
      'rgba(54, 162, 235, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 99, 132, 0.7)',
      'rgba(192, 192, 192, 0.7)'
    ];

    const toChartJSConfig = (g) => {
      if (!g) return null;

      // already a full chart config?
      if (g.data && g.options) return g;

      // expected "simple" shape: { type, labels, values, title?, dataset_label? }
      const type = ['bar', 'line', 'pie'].includes(g.type) ? g.type : 'bar';
      const labels = Array.isArray(g.labels) ? g.labels : [];
      const values = Array.isArray(g.values) ? g.values : [];
      const datasetLabel = g.dataset_label || g.title || 'Data';

      const palette = (theme === 'dark' ? darkThemePalette : lightThemePalette);
      const bg =
        (type === 'pie' || type === 'bar')
          ? labels.map((_, i) => palette[i % palette.length])
          : palette[0];
      const border =
        Array.isArray(bg) ? bg.map(c => c.replace('0.7', '1')) : bg.replace('0.7', '1');

      const options = {
        responsive: true,
        plugins: {
          title: {
            display: !!g.title,
            text: g.title || datasetLabel,
            color: theme === 'dark' ? '#E0E0E0' : '#212529'
          },
          legend: {
            labels: { color: theme === 'dark' ? '#E0E0E0' : '#212529' }
          }
        },
        scales: (type === 'pie') ? undefined : {
          y: {
            beginAtZero: false,
            ticks: { color: theme === 'dark' ? '#E0E0E0' : '#212529' },
            grid: { color: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }
          },
          x: {
            ticks: { color: theme === 'dark' ? '#E0E0E0' : '#212529' },
            grid: { color: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }
          }
        }
      };

      const dataset = {
        label: datasetLabel,
        data: values,
        borderWidth: 1
      };

      if (type === 'line') {
        dataset.backgroundColor = bg;
        dataset.borderColor = border;
        dataset.fill = false;
      } else {
        dataset.backgroundColor = Array.isArray(bg) ? bg : [bg];
        dataset.borderColor = Array.isArray(border) ? border : [border];
      }

      const data = { labels, datasets: [dataset] };
      const chart = { type, data, options };
      if (type === 'pie') delete chart.options.scales;
      return chart;
    };

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

      // normalize any graph payload to Chart.js config
      let graphData = res.data.graph_data || extractGraphData(res.data.response);
      if (graphData) {
        const normalized = toChartJSConfig(graphData);
        if (normalized) {
          agentResponse.type = "graph";
          agentResponse.data = normalized;
        } else {
          log.warn("Graph data found but could not be normalized", graphData);
        }
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
  }, [messages, uploadedFile, currentThreadId, agentBehavior, theme]);

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
        file_name: uploadedFile.name,           // fixed: was fileName
        file_content: uploadedFile.content,
      }),
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setPrompt("");

    const chatHistory = newMessages.map((msg) => ({
      role: msg.sender === "user" ? "user" : "agent",
      content: msg.text,
    }));

    handleSend(userMessage.text, uploadedFile, chatHistory);

  }, [prompt, messages, uploadedFile, handleSend]);

  const handleRetry = useCallback((errorMsgIndex) => {
    log.info(`Retrying message at index: ${errorMsgIndex}`);
    if (errorMsgIndex > 0) {
      const lastUserMessage = messages[errorMsgIndex - 1];
      if (lastUserMessage && lastUserMessage.sender === 'user') {
        // Remove the error message from the chat history for a clean retry
        setMessages(prevMessages => prevMessages.slice(0, errorMsgIndex));
        handleSend(lastUserMessage.text, null, messages.slice(0, errorMsgIndex).map((msg) => ({
          role: msg.sender === "user" ? "user" : "agent",
          content: msg.text,
        })));
      }
    }
  }, [messages, handleSend]);

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
        aria-label={isSidebarHidden ? "Show sidebar" : "Hide sidebar"}
        aria-expanded={!isSidebarHidden}
        style={{ left: isSidebarHidden ? "0px" : `${sidebarWidth}px` }}
      >
        <ChevronLeftIcon />
      </button>

      {/* Main Chat Area */}
      <div className="main-chat-area">
        <div className="main-chat-header">
          <h3 className="welcome-title">E&amp;C - Interactive Agent</h3>
          <p className="welcome-subtitle">AI-powered agent for front, middle and back offices</p>
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>

        <div
          className="chat-messages"
          ref={chatMessagesRef}
          role="log"
          aria-live="polite"
          aria-relevant="additions"
        >
          {messages.map((msg, index) => (
            <ChatMessage
              key={index}
              message={{ ...msg, index }}
              messageLayout={messageLayout}
              onCopy={handleCopy}
              onRetry={handleRetry}
            />
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

        <button
          className={`scroll-to-top-button ${showScrollButton ? "show" : ""}`}
          onClick={scrollToTop}
          title="Scroll to top"
          aria-label="Scroll to top"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="icon-small" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>

        <ChatInput
          prompt={prompt}
          setPrompt={setPrompt}
          handleSubmit={handleSubmit}
          loading={loading}
          uploadedFile={uploadedFile}
          handleClearFile={handleClearFile}
          handleFileClick={handleFileClick}
          fileInputRef={fileInputRef}
          handleFileUpload={handleFileUpload}
        />
      </div>
    </div>
  );
};

export default ChatWindow;
