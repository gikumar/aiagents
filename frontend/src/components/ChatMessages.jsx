// src/components/ChatWindow.jsx
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

// Configure console logging with timestamps
const log = {
    info: (...args) =>
        console.log(`[${new Date().toISOString()}] INFO:`, ...args),
    warn: (...args) =>
        console.warn(`[${new Date().toISOString()}] WARN:`, ...args),
    error: (...args) =>
        console.error(`[${new Date().toISOString()}] ERROR:`, ...args),
    debug: (...args) =>
        console.debug(`[${new Date().toISOString()}] DEBUG:`, ...args),
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
        <svg
            xmlns="http://www.w3.org/2000/svg"
            className="icon"
            viewBox="0 0 24 24"
            fill="currentColor"
        >
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
        </svg>
    </div>
);

const AgentAvatar = () => (
    <div className="avatar agent-avatar">
        <svg
            xmlns="http://www.w3.org/2000/svg"
            className="icon"
            viewBox="0 0 24 24"
            fill="currentColor"
        >
            <path d="M12 1.5c-3.87 0-7 3.13-7 7v6c0 1.1.9 2 2 2h3v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h3c1.1 0 2-.9 2-2V8.5c0-3.87-3.13-7-7-7zm0 14c-1.66 0-3-1.34-3-3V9h6v3c0 1.66-1.34 3-3 3z" />
        </svg>
    </div>
);

const ChatMessages = React.memo(function ChatMessages({
    messages,
    loading,
    messageLayout,
    theme,
}) {
    const [sidebarWidth, setSidebarWidth] = useState(350);

    const chatEndRef = useRef(null);
    const appContainerRef = useRef(null);
    const [isResizing, setIsResizing] = useState(false);
    const startX = useRef(0);
    const startWidth = useRef(0);

    // Enhanced ChartComponent with validation
    const ChartComponent = ({ chartData }) => {
        if (!chartData?.data) {
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
                    {chartData.type === "bar" && (
                        <Bar
                            data={chartData.data}
                            options={chartData.options}
                        />
                    )}
                    {chartData.type === "line" && (
                        <Line
                            data={chartData.data}
                            options={chartData.options}
                        />
                    )}
                    {chartData.type === "pie" && (
                        <Pie
                            data={chartData.data}
                            options={chartData.options}
                        />
                    )}
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

        const requiredFields = ["type", "labels", "values"];
        for (const field of requiredFields) {
            if (!(field in data)) {
                log.debug(`Missing required field: ${field}`);
                return false;
            }
        }

        if (!["bar", "line", "pie"].includes(data.type)) {
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
        if (
            !graphData.values ||
            graphData.values.length === 0 ||
            graphData.values.some(
                (v) => v === null || v === undefined || isNaN(v)
            )
        ) {
            log.warn(
                "Graph data has invalid values - falling back to table view"
            );
            return (
                <div className="data-fallback">
                    <h4>{graphData.title || "Data Table"}</h4>
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
                                        {graphData.values[index] !==
                                            undefined &&
                                        graphData.values[index] !== null &&
                                        !isNaN(graphData.values[index])
                                            ? graphData.values[index]
                                            : "N/A"}
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
            type: graphData.type || "bar",
            data: {
                labels: graphData.labels || [],
                datasets: [
                    {
                        label: graphData.dataset_label || "Deals Data",
                        data: graphData.values || [],
                        backgroundColor:
                            theme === "dark"
                                ? "rgba(100, 181, 246, 0.7)" // light blue
                                : "rgba(25, 118, 210, 0.7)", // corporate blue
                        borderColor:
                            theme === "dark"
                                ? "rgba(100, 181, 246, 1)"
                                : "rgba(25, 118, 210, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: graphData.title || "Deals Analysis",
                        color: theme === "dark" ? "#E0E0E0" : "#212529",
                    },
                    legend: {
                        labels: {
                            color: theme === "dark" ? "#E0E0E0" : "#212529",
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            color: theme === "dark" ? "#E0E0E0" : "#212529",
                        },
                        grid: {
                            color:
                                theme === "dark"
                                    ? "rgba(255, 255, 255, 0.1)"
                                    : "rgba(0, 0, 0, 0.1)",
                        },
                    },
                    x: {
                        ticks: {
                            color: theme === "dark" ? "#E0E0E0" : "#212529",
                        },
                        grid: {
                            color:
                                theme === "dark"
                                    ? "rgba(255, 255, 255, 0.1)"
                                    : "rgba(0, 0, 0, 0.1)",
                        },
                    },
                },
            },
        };

        return (
            <div
                className="chart-container"
                style={{
                    height: "400px",
                    width: "100%",
                }}
            >
                <ChartComponent chartData={chartData} />
            </div>
        );
    };

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        log.debug("Messages updated, scrolling to bottom");
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Auto-scroll to bottom when loading starts
    useEffect(() => {
        if (loading) {
            log.debug("Loading started, scrolling to bottom");
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [loading]);

    // Update sidebar width CSS variable
    useEffect(() => {
        if (appContainerRef.current) {
            log.debug(`Updating sidebar width to ${sidebarWidth}px`);
            appContainerRef.current.style.setProperty(
                "--sidebar-width",
                `${sidebarWidth}px`
            );
        }
    }, [sidebarWidth]);

    // Sidebar resize handlers

    const onMouseMove = useCallback(
        (e) => {
            if (!isResizing) return;
            const newWidth = startWidth.current + (e.clientX - startX.current);
            const clampedWidth = Math.max(250, Math.min(500, newWidth));
            log.debug(`Resizing sidebar to ${clampedWidth}px`);
            setSidebarWidth(clampedWidth);
        },
        [isResizing]
    );

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

    return (
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
                            msg.sender === "user" &&
                            messageLayout === "alternating"
                                ? "user-message-wrapper"
                                : ""
                        }`}
                    >
                        {msg.sender === "user" ? (
                            <UserAvatar />
                        ) : (
                            <AgentAvatar />
                        )}
                        <div
                            className={`message-bubble ${
                                msg.sender
                            }-message-bubble ${
                                msg.isError ? "error-message-bubble" : ""
                            }`}
                        >
                            {msg.type === "graph" ? (
                                renderGraph(msg.data)
                            ) : (
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {typeof msg.text === "string"
                                        ? msg.text
                                        : JSON.stringify(msg.text)}
                                </ReactMarkdown>
                            )}
                            {msg.tokens && (
                                <div className="token-info-small">
                                    <span>
                                        Tokens: {msg.tokens.input} in /{" "}
                                        {msg.tokens.output} out
                                    </span>
                                </div>
                            )}
                            {msg.details && (
                                <div className="debug-details">
                                    <details>
                                        <summary>Error Details</summary>
                                        <pre>
                                            {JSON.stringify(
                                                msg.details,
                                                null,
                                                2
                                            )}
                                        </pre>
                                    </details>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ))}

            {loading && (
                <div
                    className={`chat-message-row ${
                        messageLayout === "alternating"
                            ? "agent-message-row"
                            : ""
                    }`}
                >
                    <div
                        className={`message-content-wrapper ${
                            messageLayout === "alternating"
                                ? "agent-message-wrapper"
                                : ""
                        }`}
                    >
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
    );
});

ChatMessages.propTypes = {
    messages: PropTypes.arrayOf(
        PropTypes.shape({
            sender: PropTypes.string.isRequired,
            text: PropTypes.string,
            type: PropTypes.string,
            data: PropTypes.object,
            tokens: PropTypes.object,
            isError: PropTypes.bool,
            details: PropTypes.any,
        })
    ).isRequired,
    loading: PropTypes.bool.isRequired,
    messageLayout: PropTypes.string.isRequired,
    theme: PropTypes.string.isRequired,
};

export default ChatMessages;
