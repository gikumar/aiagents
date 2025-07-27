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
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Bar, Line, Pie } from "react-chartjs-2";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "../App.css";

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

const TokenIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5.5c.58 0 1.12.23 1.52.63l3.58 3.58c.4.4.63.94.63 1.52V21c0 1.1-.9 2-2 2H7c-1.1 0-2-.9-2-2V5c0-1.1.9-2 2-2zm0 14h10V9H7v12z" />
    </svg>
);

const GraphIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
);

const FileLoadingIndicator = () => (
    <div className="file-loading-indicator">
        <div className="loading-dot dot-1"></div>
        <div className="loading-dot dot-2"></div>
        <div className="loading-dot dot-3"></div>
    </div>
);

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
    const [defaultGraphType, setDefaultGraphType] = useState("bar");

    const chatEndRef = useRef(null);
    const sidebarRef = useRef(null);
    const appContainerRef = useRef(null);
    const [isResizing, setIsResizing] = useState(false);
    const startX = useRef(0);
    const startWidth = useRef(0);
    const fileInputRef = useRef(null);

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
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: graphData.title || 'Deals Analysis'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false
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

                <div className="settings-section file-upload-section">
                    <label className="settings-label">Upload a file for context</label>
                    <div className="drag-drop-area">
                        <input
                            type="file"
                            className="file-input"
                            ref={fileInputRef}
                            onChange={handleFileUpload}
                            accept=".txt,.md,.csv,.json,.log"
                        />
                        <p>Drag and drop file here</p>
                        <p>Limit 200MB per file</p>
                        <button className="browse-files-button">Browse files</button>
                    </div>
                    {uploadedFile && (
                        <div className="uploaded-file-info">
                            <span className="file-name">{uploadedFile.name}</span>
                            {uploadedFile.isLoading && <FileLoadingIndicator />}
                            {uploadedFile.error && (
                                <span className="file-error-text">({uploadedFile.error})</span>
                            )}
                            <button
                                onClick={handleClearFile}
                                className="clear-file-button"
                                title="Clear uploaded file"
                            >
                                <XCircleIcon />
                            </button>
                        </div>
                    )}
                </div>

                <div className="settings-section">
                    <label className="settings-label">Agent Behavior</label>
                    <select
                        className="agent-behavior-select"
                        value={agentBehavior}
                        onChange={(e) => setAgentBehavior(e.target.value)}
                    >
                        <option value="Balanced">Balanced</option>
                        <option value="Short">Short</option>
                        <option value="Detailed">Detailed</option>
                        <option value="Structured">Structured</option>
                    </select>
                </div>

                <div className="settings-section">
                    <label className="settings-label">Message Layout</label>
                    <select
                        className="agent-behavior-select"
                        value={messageLayout}
                        onChange={(e) => setMessageLayout(e.target.value)}
                    >
                        <option value="alternating">Alternating</option>
                        <option value="same-side">Same Side</option>
                    </select>
                </div>

                <div className="settings-section">
                    <label className="settings-label">Default Graph Type</label>
                    <select
                        className="agent-behavior-select"
                        value={defaultGraphType}
                        onChange={(e) => setDefaultGraphType(e.target.value)}
                    >
                        <option value="bar">Bar Chart</option>
                        <option value="line">Line Chart</option>
                        <option value="pie">Pie Chart</option>
                    </select>
                </div>

                <div className="settings-section token-usage-section">
                    <div className="token-usage-header">
                        <TokenIcon />
                        <h3>Token Usage (Last Request)</h3>
                    </div>
                    <div className="token-info">
                        <p>Input Tokens: <span>{inputTokens}</span></p>
                        <p>Output Tokens: <span>{outputTokens}</span></p>
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
                        {uploadedFile && uploadedFile.name && (
                            <div className="file-context-display">
                                <span className="file-name-tag">
                                    <span className="file-icon">📄</span> {uploadedFile.name}
                                </span>
                                {uploadedFile.isLoading && <FileLoadingIndicator />}
                                {uploadedFile.error && (
                                    <span className="file-error-text">({uploadedFile.error})</span>
                                )}
                            </div>
                        )}
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
                        <div className="input-buttons">
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