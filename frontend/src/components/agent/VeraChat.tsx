"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import SafeMarkdown from "@/lib/markdown";
import MarketIntelCards from "./MarketIntelCards";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";

const QUICK_ACTIONS = [
  "Morning Brief",
  "60-Day Outlook",
  "Rebalance Options",
  "Stress Test",
];

function HealthBadge({ score }) {
  let color, label;
  if (score >= 75) { color = "#00e676"; label = "Good"; }
  else if (score >= 50) { color = "#f59e0b"; label = "Fair"; }
  else { color = "#ef4444"; label = "Risk"; }
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px", borderRadius: 20, background: `${color}15`, border: `1px solid ${color}30`, fontSize: 12, fontWeight: 600, color }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: color }} />
      {score}/100 · {label}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 4, padding: "8px 0", alignItems: "center" }}>
      {[0, 0.2, 0.4].map((d, i) => (
        <span key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "#00e676", animation: "veraPulse 1.2s ease-in-out infinite", animationDelay: `${d}s` }} />
      ))}
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
    <div style={{ fontSize: 11, color: "#00e676", fontWeight: 500, padding: "2px 8px", borderRadius: 4, background: "#22c55e10", display: "inline-block", marginBottom: 4 }}>
      {labels[node] || "Processing..."}
    </div>
  );
}

function MetricCard({ label, value, sub, color }) {
  return (
    <div style={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 10, padding: 14, position: "relative", overflow: "hidden" }}>
      <div style={{ fontSize: 10, color: "#71717a", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color, letterSpacing: "-0.03em", lineHeight: 1.2 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: "#52525b", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function ScenarioCard({ label, color, data }) {
  if (!data || !data.probability) return null;
  return (
    <div style={{ background: "#14141a", border: `1px solid ${color}30`, borderRadius: 10, padding: 12 }}>
      <div style={{ color, fontSize: 11, fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: "#e4e4e7" }}>{data.probability}%</div>
      {data.return_pct !== undefined && (
        <div style={{ fontSize: 13, color: "#a1a1aa", marginTop: 2 }}>
          {data.return_pct > 0 ? "+" : ""}{data.return_pct}%
        </div>
      )}
      {data.trigger && (
        <div style={{ fontSize: 10, color: "#71717a", marginTop: 4, lineHeight: 1.3 }}>{data.trigger}</div>
      )}
    </div>
  );
}

function StressTestTable({ scenarios }) {
  if (!scenarios || scenarios.length === 0) return null;
  return (
    <div style={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 10, padding: 14, marginTop: 8 }}>
      <div style={{ fontSize: 10, color: "#f59e0b", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>
        Armor Test — Stress Scenarios
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #27272a" }}>
              <th style={{ textAlign: "left", padding: "6px 8px", color: "#71717a", fontWeight: 400 }}>Scenario</th>
              <th style={{ textAlign: "right", padding: "6px 8px", color: "#71717a", fontWeight: 400 }}>Shock</th>
              <th style={{ textAlign: "right", padding: "6px 8px", color: "#71717a", fontWeight: 400 }}>VaR 95%</th>
              <th style={{ textAlign: "right", padding: "6px 8px", color: "#71717a", fontWeight: 400 }}>CVaR 95%</th>
              <th style={{ textAlign: "right", padding: "6px 8px", color: "#71717a", fontWeight: 400 }}>Floor</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((s, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #18181b" }}>
                <td style={{ padding: "6px 8px", color: "#d4d4d8" }}>{s.scenario}</td>
                <td style={{ textAlign: "right", padding: "6px 8px", color: "#a1a1aa" }}>{(s.shock * 100).toFixed(0)}%</td>
                <td style={{ textAlign: "right", padding: "6px 8px", color: "#a1a1aa" }}>${s.var_95?.toLocaleString()}</td>
                <td style={{ textAlign: "right", padding: "6px 8px", color: "#a1a1aa" }}>${s.cvar_95?.toLocaleString()}</td>
                <td style={{ textAlign: "right", padding: "6px 8px" }}>
                  <span style={{ color: s.breach ? "#ef4444" : "#00e676", fontWeight: 600 }}>
                    {s.breach ? "BREACH" : "OK"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ForecastChart({ forecast }) {
  if (!forecast || forecast.length < 2) return null;
  return (
    <div style={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 10, padding: 14, marginTop: 8 }}>
      <div style={{ fontSize: 10, color: "#3b82f6", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>
        60-Day Horizon Scan
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={forecast.map((v, i) => ({ day: i, value: v }))}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis dataKey="day" stroke="#52525b" tick={{ fontSize: 10 }} />
          <YAxis stroke="#52525b" tick={{ fontSize: 10 }} domain={["auto", "auto"]} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
          <Tooltip contentStyle={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 8, fontSize: 11 }} formatter={(v) => [`$${v.toLocaleString()}`, "Value"]} />
          <Line type="monotone" dataKey="value" stroke="#00e676" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function loadChatHistory(userId) {
  try {
    const key = `liverisk_chat_${userId}`;
    const saved = localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {}
  return null;
}

function saveChatHistory(userId, messages) {
  try {
    const key = `liverisk_chat_${userId}`;
    const toSave = messages.slice(-50);
    localStorage.setItem(key, JSON.stringify(toSave));
  } catch {}
}

export default function VeraChat() {
  const [userId] = useState(() => localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0");
  const [messages, setMessages] = useState(() => {
    const history = loadChatHistory(localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0");
    if (history) return history;
    const saved = localStorage.getItem("liverisk_last_analysis");
    if (saved) {
      try {
        const data = JSON.parse(saved);
        const tickerStr = data.tickers?.join(", ");
        const healthStr = data.health_score;
        if (data.tickers && data.health_score) {
          return [{
            role: "assistant",
            content: `I'm **Vera**, your senior portfolio risk analyst. I can see your last analysis for **${tickerStr}** (Health: **${healthStr}/100**). Ask me anything — risk metrics, forecasts, stress tests, market news, or run a new portfolio analysis.`,
          }];
        }
      } catch {}
    }
    return [{
      role: "assistant",
      content: `I'm **Vera**, your senior portfolio risk analyst. I can analyze your portfolio's risk, run scenario forecasts, check sentiment, or generate institutional reports. What would you like to explore?`,
    }];
  });
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [currentNode, setCurrentNode] = useState("");
  const [healthScore, setHealthScore] = useState(null);
  const [savedTickers, setSavedTickers] = useState(() => {
    try {
      const data = JSON.parse(localStorage.getItem("liverisk_last_analysis") || "{}");
      return data.tickers || null;
    } catch { return null; }
  });
  const [savedWeights, setSavedWeights] = useState(() => {
    try {
      const data = JSON.parse(localStorage.getItem("liverisk_last_analysis") || "{}");
      return data.weights || null;
    } catch { return null; }
  });
  const [latestForecast, setLatestForecast] = useState(null);
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [latestMarketIntel, setLatestMarketIntel] = useState(null);
  const [latestStress, setLatestStress] = useState(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (userId !== "0" && messages.length > 0) {
      saveChatHistory(userId, messages);
    }
  }, [messages, userId]);

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
      const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";

      const response = await fetch(`${baseUrl}/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          user_id: user,
          tickers: savedTickers,
          weights: savedWeights,
        }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error("Response body is null");

      setLatestForecast(null);
      setLatestMetrics(null);
      setLatestMarketIntel(null);
      setLatestStress(null);

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
                updated[updated.length - 1] = { ...last, content: last.content + data.token };
              }
              return updated;
            });
          }

          if (data.node) setCurrentNode(data.node);

          if (data.done) {
            setStreaming(false);
            setCurrentNode("");
            if (data.health_score) setHealthScore(data.health_score);
            if (data.forecast) setLatestForecast(data.forecast);
            if (data.metrics) {
              setLatestMetrics(data.metrics);
              if (data.metrics.stress_results) setLatestStress(data.metrics.stress_results);
            }
            if (data.market_intel) setLatestMarketIntel(data.market_intel);
            if (data.action_items?.length > 0) {
              const items = data.action_items.join("\n- ");
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, content: last.content + `\n\n**Action Items:**\n- ${items}` };
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
      const msg = error.name === "AbortError"
        ? "The analysis is taking longer than expected. The backend may be processing complex computations. Please try again in a moment."
        : "I encountered an error processing your request. Please try again.";
      console.error("Vera chat error:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: msg }]);
      setStreaming(false);
      setCurrentNode("");
    }
  };

  const handleQuickAction = (action) => {
    let prompt = "";
    switch (action) {
      case "Morning Brief":
        prompt = "Generate my morning brief with current risk metrics and outlook";
        break;
      case "60-Day Outlook":
        prompt = "What is my 60-day forecast outlook with bull, base, and bear scenarios?";
        break;
      case "Rebalance Options":
        prompt = "Should I rebalance my portfolio? What are my options?";
        break;
      case "Stress Test":
        prompt = "Run stress tests on my current portfolio";
        break;
      default:
        prompt = action;
    }
    sendMessage(prompt);
  };

  const handleDownloadPdf = async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const token = localStorage.getItem("liverisk_token");
      const reportRes = await fetch(`${baseUrl}/agent/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ user_id: userId, tickers: savedTickers, weights: savedWeights }),
      });
      if (reportRes.ok) {
        const reportData = await reportRes.json();
        const md = reportData.report_markdown || "";
        if (md) {
          const blob = new Blob([md], { type: "text/markdown" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `LiveRisk_Report_${new Date().toISOString().slice(0, 10)}.md`;
          a.click();
          URL.revokeObjectURL(url);
          return;
        }
      }
      const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
      if (lastAssistant?.content) {
        const clean = lastAssistant.content.replace(/<[^>]*>/g, "").replace(/\*\*/g, "");
        const blob = new Blob([`# LiveRisk Portfolio Analysis\n\n${clean}`], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `LiveRisk_Analysis_${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error("Download error:", error);
    }
  };

  const formatCurrency = (v) => {
    if (v == null) return "$0";
    if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
    if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
    return `$${v.toFixed(0)}`;
  };

  const isMarketIntent = () => {
    const lastMsg = messages[messages.length - 1];
    return lastMsg?.role === "assistant" && latestMarketIntel && !latestMetrics;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative" }}>
      <div ref={chatContainerRef} style={{ flex: 1, overflowY: "auto", padding: "16px 24px 8px" }}>
        {messages.length === 1 && !streaming && (
          <div style={{ textAlign: "center", padding: "40px 20px 20px", opacity: 0.8 }}>
            <div style={{ width: 48, height: 48, borderRadius: 14, background: "linear-gradient(135deg, #22c55e, #16a34a)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700, color: "#000", margin: "0 auto 12px" }}>V</div>
            <div style={{ fontSize: 13, color: "#71717a", maxWidth: 420, margin: "0 auto", lineHeight: 1.5 }}>
              Ask me about your portfolio, market news, IPOs, global events, or type <strong style={{ color: "#00e676" }}>&quot;analyse my portfolio with NVDA 0.7, AMZN 0.3&quot;</strong> for a full risk analysis.
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", marginBottom: 12 }}>
            <div style={{
              maxWidth: "72%",
              padding: msg.role === "user" ? "8px 16px" : "12px 18px",
              borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
              background: msg.role === "user" ? "#00e676" : "#14141a",
              color: msg.role === "user" ? "#000" : "#e4e4e7",
              border: msg.role === "user" ? "none" : "1px solid #27272a",
              fontSize: msg.role === "user" ? 14 : (isMarketIntent() && i === messages.length - 1 ? 15 : 14),
              lineHeight: 1.7,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}>
              {i === messages.length - 1 && streaming && !msg.content && <TypingIndicator />}
              {msg.content && <SafeMarkdown content={msg.content} />}
            </div>
          </div>
        ))}

        {streaming && currentNode && (
          <div style={{ paddingLeft: 8, marginBottom: 8 }}>
            <NodePill node={currentNode} />
          </div>
        )}

        {!streaming && latestMetrics && (
          <div style={{ margin: "4px 0 12px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, marginBottom: 8 }}>
              <MetricCard label="95% VaR" value={formatCurrency(latestMetrics.var_95)} sub="Max loss in 95% of scenarios" color={latestMetrics.var_95 > 50000 ? "#ef4444" : "#00e676"} />
              <MetricCard label="95% CVaR" value={formatCurrency(latestMetrics.cvar)} sub="Avg loss in worst 5%" color={latestMetrics.cvar > 50000 ? "#ef4444" : "#00e676"} />
              <MetricCard label="Sentiment" value={latestMetrics.sentiment_score?.toFixed(3)} sub="FinBERT news sentiment" color={latestMetrics.sentiment_score > 0.3 ? "#00e676" : latestMetrics.sentiment_score < -0.3 ? "#ef4444" : "#f59e0b"} />
              <MetricCard label="Loss Prob" value={`${(latestMetrics.prob_loss * 100).toFixed(0)}%`} sub="Chance of negative return" color={latestMetrics.prob_loss > 0.5 ? "#ef4444" : "#00e676"} />
              {latestMetrics.health_score != null && (
                <MetricCard label="Health" value={`${latestMetrics.health_score}/100`} sub="Portfolio health score" color={latestMetrics.health_score >= 75 ? "#00e676" : latestMetrics.health_score >= 50 ? "#f59e0b" : "#ef4444"} />
              )}
            </div>

            {latestForecast && latestForecast.bull && latestForecast.base && latestForecast.bear && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 8 }}>
                <ScenarioCard label="Bull" color="#00e676" data={latestForecast.bull} />
                <ScenarioCard label="Base" color="#f59e0b" data={latestForecast.base} />
                <ScenarioCard label="Bear" color="#ef4444" data={latestForecast.bear} />
              </div>
            )}

            {latestForecast && latestForecast["60_day_outlook"] && (
              <div style={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 10, padding: 12, marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: "#3b82f6", fontWeight: 600, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.5px" }}>60-Day Outlook</div>
                <div style={{ fontSize: 13, color: "#a1a1aa", lineHeight: 1.5 }}>{latestForecast["60_day_outlook"]}</div>
              </div>
            )}

            <ForecastChart forecast={latestMetrics.forecast} />
            <StressTestTable scenarios={latestStress} />
          </div>
        )}

        {!streaming && latestMarketIntel && !latestMetrics && (
          <div style={{ margin: "4px 0 12px" }}>
            <MarketIntelCards marketIntel={latestMarketIntel} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div style={{ borderTop: "1px solid #27272a", padding: "8px 24px 16px", background: "#0a0a0f" }}>
        {!streaming && messages.length > 1 && (
          <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
            {QUICK_ACTIONS.map((action) => (
              <button key={action} onClick={() => handleQuickAction(action)} disabled={false}
                style={{ background: "transparent", color: "#00e676", border: "1px solid #22c55e30", padding: "4px 12px", fontSize: 11, fontWeight: 500, borderRadius: 16, cursor: "pointer", opacity: 1 }}>
                {action}
              </button>
            ))}
            <button onClick={handleDownloadPdf}
              style={{ background: "transparent", color: "#3b82f6", border: "1px solid #3b82f630", padding: "4px 12px", fontSize: 11, fontWeight: 500, borderRadius: 16, cursor: "pointer" }}>
              Download PDF
            </button>
          </div>
        )}

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <textarea value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
            placeholder={streaming ? "Vera is thinking..." : "Ask Vera about your portfolio..."}
            disabled={streaming} rows={1}
            style={{ flex: 1, background: "#1a1a24", border: "1px solid #27272a", color: "#e4e4e7", borderRadius: 10, padding: "12px 16px", fontSize: 14, outline: "none", resize: "none", fontFamily: "inherit", maxHeight: 120 }}
          />
          <button onClick={() => sendMessage(input)} disabled={streaming || !input.trim()}
            style={{ background: streaming ? "#52525b" : "#00e676", color: "#000", fontWeight: 600, padding: "12px 24px", borderRadius: 10, border: "none", cursor: (streaming || !input.trim()) ? "not-allowed" : "pointer", opacity: (streaming || !input.trim()) ? 0.5 : 1, fontSize: 14, whiteSpace: "nowrap", minWidth: 80 }}>
            {streaming ? "..." : "Send"}
          </button>
        </div>
      </div>


    </div>
  );
}
