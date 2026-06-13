"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import SafeMarkdown from "@/lib/markdown";

const QUICK_ACTIONS = [
  "What is my portfolio risk?",
  "60-Day Outlook",
  "Morning Brief",
  "Stress Test",
];

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 4, padding: "4px 0", alignItems: "center" }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#00e676", animation: "vp 1.2s ease-in-out infinite" }} />
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#00e676", animation: "vp 1.2s ease-in-out infinite", animationDelay: "0.2s" }} />
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#00e676", animation: "vp 1.2s ease-in-out infinite", animationDelay: "0.4s" }} />
    </div>
  );
}

function NodePill({ node }) {
  const labels = {
    intent_classifier: "Analyzing your question...",
    portfolio_loader: "Loading your portfolio...",
    quant_node: "Running Monte Carlo & VaR...",
    sentiment_node: "Analyzing market sentiment...",
    forecast_node: "Generating 60-day forecast...",
    risk_interpreter: "Interpreting risk metrics...",
    report_assembler: "Assembling report...",
    response_writer: "Writing response...",
  };
  return (
    <div style={{ fontSize: 10, color: "#00e676", fontWeight: 500, padding: "2px 8px", borderRadius: 4, background: "#22c55e10", display: "inline-block", marginBottom: 4 }}>
      {labels[node] || "Processing..."}
    </div>
  );
}

export default function VeraLandingChat() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "I'm **Vera**, your senior portfolio risk analyst. Ask me about market risk, portfolio analysis, or try one of the quick actions below.",
    },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [currentNode, setCurrentNode] = useState("");
  const [savedTickers, setSavedTickers] = useState(() => {
    try {
      const saved = localStorage.getItem("liverisk_last_analysis");
      if (saved) {
        const data = JSON.parse(saved);
        return data.tickers || null;
      }
    } catch {}
    return null;
  });
  const [savedWeights, setSavedWeights] = useState(() => {
    try {
      const saved = localStorage.getItem("liverisk_last_analysis");
      if (saved) {
        const data = JSON.parse(saved);
        return data.weights || null;
      }
    } catch {}
    return null;
  });
  const messagesEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = async (text) => {
    if (!text.trim() || streaming) return;

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setCurrentNode("intent_classifier");

    const assistantMsg = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    try {
      const baseUrl = getApiBaseUrl();
      const token = localStorage.getItem("liverisk_token");

      const response = await fetch(`${baseUrl}/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          user_id: localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0",
          tickers: savedTickers,
          weights: savedWeights,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let data;
          try {
            data = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (data.token !== undefined) {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + data.token,
                };
              }
              return updated;
            });
          }

          if (data.node) {
            setCurrentNode(data.node);
          }

          if (data.done) {
            setStreaming(false);
            setCurrentNode("");
            if (data.action_items?.length > 0) {
              const items = data.action_items.join("\n- ");
              const actionText = `\n\n**Action Items:**\n- ${items}`;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + actionText,
                  };
                }
                return updated;
              });
            }
          }
        }
      }
      clearTimeout(timeout);
    } catch (error) {
      clearTimeout(timeout);
      const msg =
        error.name === "AbortError"
          ? "The analysis is taking longer than expected. The backend may be processing complex computations. Please try again in a moment."
          : "I encountered an error. Please make sure the backend is running and try again.";
      console.error("Vera chat error:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: msg }]);
      setStreaming(false);
      setCurrentNode("");
    }
  };

  const handleQuickAction = (action) => {
    let prompt = "";
    const hasPortfolio = savedTickers && savedTickers.length > 0;
    const demoPortfolio = "Analyze the risk of a portfolio with SPY 40%, QQQ 30%, AGG 20%, GLD 10%";
    const demoForecast = "What is my 60-day forecast with bull, base, and bear scenarios for SPY, QQQ, AGG, GLD?";
    const demoStress = "Run stress tests on SPY 40%, QQQ 30%, AGG 20%, GLD 10%";
    switch (action) {
      case "What is my portfolio risk?":
        prompt = hasPortfolio ? "Analyze the risk of my current portfolio" : demoPortfolio;
        break;
      case "60-Day Outlook":
        prompt = hasPortfolio ? "What is my 60-day forecast outlook with bull, base, and bear scenarios?" : demoForecast;
        break;
      case "Morning Brief":
        prompt = "Generate a morning brief with current risk metrics and outlook";
        break;
      case "Stress Test":
        prompt = hasPortfolio ? "Run stress tests on my current portfolio" : demoStress;
        break;
      default:
        prompt = action;
    }
    sendMessage(prompt);
  };

  return (
    <div style={{ width: "100%" }}>
      <div
        style={{
          background: "#111",
          border: "1px solid #27272a",
          borderRadius: 16,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "14px 18px",
            borderBottom: "1px solid #27272a",
            background: "#0a0a0a",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, #22c55e, #16a34a)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                color: "#000",
              }}
            >
              V
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#e4e4e7", lineHeight: 1.2 }}>
                Vera AI
              </div>
              <div style={{ fontSize: 10, color: "#71717a" }}>
                Senior Portfolio Risk Analyst
              </div>
            </div>
          </div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: "3px 10px",
              borderRadius: 20,
              background: "#22c55e15",
              border: "1px solid #22c55e30",
              fontSize: 11,
              fontWeight: 600,
              color: "#00e676",
            }}
          >
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#00e676" }} />
            Online
          </div>
        </div>

        <div
          style={{
            height: 320,
            overflowY: "auto",
            padding: "12px 18px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <div
                style={{
                  maxWidth: "82%",
                  padding: "8px 14px",
                  borderRadius: 12,
                  background: msg.role === "user" ? "#00e676" : "#1a1a24",
                  color: msg.role === "user" ? "#000" : "#e4e4e7",
                  border: msg.role === "user" ? "none" : "1px solid #27272a",
                  fontSize: 13,
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {i === messages.length - 1 && streaming && !msg.content && (
                  <TypingIndicator />
                )}
                {msg.content && <SafeMarkdown content={msg.content} />}
              </div>
            </div>
          ))}

          {streaming && currentNode && (
            <div style={{ paddingLeft: 4 }}>
              <NodePill node={currentNode} />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div
          style={{
            display: "flex",
            gap: 6,
            padding: "6px 18px",
            flexWrap: "wrap",
            borderTop: "1px solid #18181b",
          }}
        >
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action}
              onClick={() => handleQuickAction(action)}
              disabled={streaming}
              style={{
                background: "transparent",
                color: "#00e676",
                border: "1px solid #22c55e30",
                padding: "4px 12px",
                fontSize: 11,
                fontWeight: 500,
                borderRadius: 16,
                cursor: streaming ? "not-allowed" : "pointer",
                opacity: streaming ? 0.5 : 1,
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => { if (!streaming) e.target.style.background = "#22c55e10"; }}
              onMouseLeave={(e) => { e.target.style.background = "transparent"; }}
            >
              {action}
            </button>
          ))}
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            padding: "10px 18px 16px",
            borderTop: "1px solid #18181b",
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            placeholder="Ask Vera about your portfolio..."
            disabled={streaming}
            rows={1}
            style={{
              flex: 1,
              background: "#1a1a24",
              border: "1px solid #27272a",
              color: "#e4e4e7",
              borderRadius: 8,
              padding: "9px 14px",
              fontSize: 13,
              outline: "none",
              resize: "none",
              fontFamily: "inherit",
            }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={streaming || !input.trim()}
            style={{
              background: "#00e676",
              color: "#000",
              fontWeight: 600,
              padding: "9px 20px",
              borderRadius: 8,
              border: "none",
              cursor: (streaming || !input.trim()) ? "not-allowed" : "pointer",
              opacity: (streaming || !input.trim()) ? 0.5 : 1,
              fontSize: 13,
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => { if (!streaming && input.trim()) e.target.style.background = "#16a34a"; }}
            onMouseLeave={(e) => { e.target.style.background = "#00e676"; }}
          >
            Send
          </button>
        </div>
      </div>


    </div>
  );
}
