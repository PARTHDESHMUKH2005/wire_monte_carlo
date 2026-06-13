"use client";

/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/lib/api";
import SafeMarkdown from "@/lib/markdown";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";

const API = getApiBaseUrl();
const isBrowser = () => typeof window !== "undefined";

const QUICK_ACTIONS = [
  "Morning Brief",
  "60-Day Outlook",
  "Stress Test",
  "What is my portfolio risk?",
];

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-2">
      {[0, 0.2, 0.4].map((d, i) => (
        <span key={i} className="w-1.5 h-1.5 rounded-full bg-accent" style={{ animation: `veraPulse 1.2s ease-in-out infinite`, animationDelay: `${d}s` }} />
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
    forecast_node: "Generating LSTM 60-day forecast...",
    risk_interpreter: "Interpreting risk metrics...",
    report_assembler: "Assembling report...",
    response_writer: "Writing response...",
  };
  return (
    <div className="node-pill">
      {labels[node] || "Processing..."}
    </div>
  );
}

function MetricCard({ label, value, sub, color }) {
  return (
    <div className="glass-card-compact">
      <div className="text-[10px] text-tertiary uppercase tracking-wider mb-1">{label}</div>
      <div className="text-[22px] font-bold tracking-tight leading-tight" style={{ color }}>{value}</div>
      {sub && <div className="text-[10px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

function ScenarioCard({ label, color, data }) {
  if (!data || !data.probability) return null;
  return (
    <div className="card-dark" style={{ borderColor: `${color}30` }}>
      <div className="text-[11px] font-semibold mb-1" style={{ color }}>{label}</div>
      <div className="text-[22px] font-bold text-text-primary tracking-tight">{data.probability}%</div>
      {data.return_pct !== undefined && (
        <div className="text-[13px] text-secondary mt-0.5">
          {data.return_pct > 0 ? "+" : ""}{data.return_pct}%
        </div>
      )}
      {data.trigger && (
        <div className="text-[10px] text-tertiary mt-1 leading-relaxed">{data.trigger}</div>
      )}
    </div>
  );
}

export default function VeraPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  // Lazy state initialization from localStorage (client only)
  const [token, setToken] = useState("");
  const [userName, setUserName] = useState("");
  const [userId, setUserId] = useState("0");
  const [userEmail, setUserEmail] = useState("");

  // Portfolio input
  const [tickers, setTickers] = useState("");
  const [weights, setWeights] = useState("");

  // Chat state
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [currentNode, setCurrentNode] = useState("");
  const [healthScore, setHealthScore] = useState(null);
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [latestForecast, setLatestForecast] = useState(null);
  const [latestStress, setLatestStress] = useState(null);
  const messagesEndRef = useRef(null);
  const chatRef = useRef(null);

  // Alert config
  const [alertValues, setAlertValues] = useState({ var_95: 15, health_score: 50, volatility: 3, cvar: 20 });
  const [alertEnabled, setAlertEnabled] = useState({});

  // Email state
  const [emailSending, setEmailSending] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [notification, setNotification] = useState(null);

  // Tabs
  const [activeTab, setActiveTab] = useState("chat");

  // Sidebar history
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const authHeaders = useCallback(() => {
    const t = localStorage.getItem("liverisk_token");
    return t ? { "Content-Type": "application/json", Authorization: `Bearer ${t}` } : { "Content-Type": "application/json" };
  }, []);

  const fetchHistory = useCallback(async (uid, tok) => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${API}/agent/history/${uid}`, {
        headers: tok ? { Authorization: `Bearer ${tok}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        if (data.history && data.history.length > 0) {
          setHistoryList(data.history);
        }
      }
    } catch (e) {
      console.error("Failed to load history:", e);
    }
    setLoadingHistory(false);
  }, []);

  // Read auth from localStorage after mount (fixes SSR hydration mismatch)
  useEffect(() => {
    setToken(localStorage.getItem("liverisk_token") || "");
    setUserName(localStorage.getItem("liverisk_user") || "");
    setUserId(localStorage.getItem("liverisk_user_id") || "0");
    setUserEmail(localStorage.getItem("liverisk_email") || "");
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    if (!token) { router.push("/"); return; }
    fetchHistory(userId, token);

    const replay = localStorage.getItem("liverisk_replay");
    if (replay) {
      try {
        const p = JSON.parse(replay);
        if (p.tickers) setTickers(p.tickers);
        if (p.weights) setWeights(p.weights);
        localStorage.removeItem("liverisk_replay");
      } catch {}
    }

    const saved = localStorage.getItem("liverisk_last_analysis");
    if (saved) {
      try {
        const d = JSON.parse(saved);
        if (d.tickers && !tickers) setTickers(d.tickers.join(", "));
        if (d.weights && !weights) setWeights(d.weights.join(", "));
      } catch {}
    }

    const alertCfg = localStorage.getItem("liverisk_alert_config");
    if (alertCfg) {
      try {
        const cfg = JSON.parse(alertCfg);
        if (cfg.values) setAlertValues(cfg.values);
        if (cfg.enabled) setAlertEnabled(cfg.enabled);
      } catch {}
    }

    setMessages([{
      role: "assistant",
      content: `Welcome back, **${userName}**. I'm **Vera**, your senior portfolio risk analyst. I can run full risk analysis, LSTM forecasts, stress tests, and send reports to your email. What would you like to explore?`,
    }]);
  }, [mounted, token, userName, userId, router, fetchHistory, tickers, weights]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const getTickers = () => tickers.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
  const getWeights = () => weights.split(",").map((s) => parseFloat(s.trim())).filter((n) => !isNaN(n));

  const runAnalysis = async () => {
    const t = getTickers();
    const w = getWeights();
    if (t.length === 0) {
      sendMessage("Analyze the risk of a portfolio with SPY 40%, QQQ 30%, AGG 20%, GLD 10%");
      return;
    }
    if (w.length > 0 && t.length !== w.length) {
      sendMessage(`Analyze the risk of my portfolio with ${tickers}`);
      return;
    }
    sendMessage(`Analyze the risk of my portfolio with ${tickers}${weights ? ` with weights ${weights}` : ""}`);
  };

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
      setLatestMetrics(null);
      setLatestForecast(null);
      setLatestStress(null);

      const response = await fetch(`${API}/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          user_id: userId,
          tickers: getTickers(),
          weights: getWeights(),
        }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error("Response body is null");

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
          try { data = JSON.parse(line.slice(6)); } catch { continue; }

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
      fetchHistory(userId, token);
    } catch (error) {
      clearTimeout(timeout);
      const msg = error.name === "AbortError"
        ? "Analysis timed out. Complex computations may still be running. Please try again."
        : "I encountered an error. Please make sure the backend is running and try again.";
      setMessages((prev) => [...prev, { role: "assistant", content: msg }]);
      setStreaming(false);
      setCurrentNode("");
    }
  };

  const handleQuickAction = (action) => {
    let prompt = "";
    const t = getTickers();
    switch (action) {
      case "Morning Brief":
        prompt = "Generate my morning brief with current risk metrics and outlook";
        break;
      case "60-Day Outlook":
        prompt = t.length > 0
          ? "What is my 60-day forecast outlook with bull, base, and bear scenarios?"
          : "What is the 60-day forecast outlook for SPY 40%, QQQ 30%, AGG 20%, GLD 10%?";
        break;
      case "Stress Test":
        prompt = t.length > 0 ? "Run stress tests on my current portfolio" : "Run stress tests on SPY 40%, QQQ 30%, AGG 20%, GLD 10%";
        break;
      case "What is my portfolio risk?":
        prompt = t.length > 0 ? "Analyze the risk of my current portfolio" : "Analyze the risk of a portfolio with SPY 40%, QQQ 30%, AGG 20%, GLD 10%";
        break;
      default:
        prompt = action;
    }
    sendMessage(prompt);
  };

  const handleSendEmail = async () => {
    setEmailSending(true);
    setEmailSent(false);
    try {
      const baseUrl = getApiBaseUrl();
      const token = localStorage.getItem("liverisk_token");

      const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
      const reportContent = lastAssistant?.content || "No analysis data available.";

      const res = await fetch(`${baseUrl}/agent/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ user_id: userId }),
      });

      let reportMd = "";
      if (res.ok) {
        const data = await res.json();
        reportMd = data.report_markdown || "";
      }

      const emailRes = await fetch(`${baseUrl}/send-report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          user_id: userId,
          email: userEmail,
          report_markdown: reportMd || reportContent,
          health_score: healthScore || latestMetrics?.health_score || 50,
        }),
      });

      if (emailRes.ok) {
        setEmailSent(true);
        setTimeout(() => setEmailSent(false), 4000);
      } else {
        setNotification({ type: "error", message: "Failed to send email. Make sure your email is configured." });
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (e) {
      console.error("Email send error:", e);
      setNotification({ type: "error", message: "Failed to send email. Check the backend email configuration." });
      setTimeout(() => setNotification(null), 4000);
    }
    setEmailSending(false);
  };

  const handleSaveAlerts = async () => {
    const ALERTS = [
      { key: "var_95", label: "VaR 95%", default: 15 },
      { key: "health_score", label: "Min Health Score", default: 50 },
      { key: "volatility", label: "Volatility", default: 3 },
      { key: "cvar", label: "CVaR", default: 20 },
    ];
    const promises = ALERTS.filter((a) => alertEnabled[a.key]).map((alert) =>
      fetch(`${API}/agent/alerts`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          user_id: userId,
          metric: alert.key,
          threshold: alertValues[alert.key] || alert.default,
        }),
      }).catch((e) => console.error("Alert save failed:", e))
    );
    await Promise.all(promises);
    localStorage.setItem("liverisk_alert_config", JSON.stringify({ values: alertValues, enabled: alertEnabled }));
    setNotification({ type: "success", message: "Alert thresholds saved!" });
    setTimeout(() => setNotification(null), 3000);
  };

  const formatCurrency = (v) => {
    if (v == null) return "$0";
    if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
    if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
    return `$${v.toFixed(0)}`;
  };

  const loadHistoryItem = (tickersList, weightsList) => {
    if (tickersList) setTickers(tickersList.join(", "));
    if (weightsList) setWeights(weightsList.join(", "));
    setActiveTab("chat");
  };

  return (
    <div style={{ display: "flex", height: "calc(100vh - 53px)", background: "#050508" }}>
      {/* Sidebar */}
      <div style={{ width: 260, borderRight: "1px solid rgba(255,255,255,0.04)", display: "flex", flexDirection: "column", flexShrink: 0, background: "rgba(10,10,20,0.5)" }}>
        <div style={{ padding: 16, borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 12 }}>
            {["chat", "config", "history"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  flex: 1,
                  background: "transparent",
                  color: activeTab === tab ? "#00e676" : "rgba(255,255,255,0.25)",
                  border: "none",
                  borderBottom: activeTab === tab ? "2px solid #00e676" : "2px solid transparent",
                  padding: "8px 4px",
                  fontSize: 11,
                  fontWeight: activeTab === tab ? 600 : 400,
                  cursor: "pointer",
                  borderRadius: 0,
                  transition: "all 0.2s",
                }}
              >
                {tab === "chat" ? "Chat" : tab === "config" ? "Alerts" : "History"}
              </button>
            ))}
          </div>
          <button onClick={runAnalysis} disabled={streaming} style={{ width: "100%", background: "linear-gradient(135deg, #00e676, #00c853)", color: "#000", fontWeight: 600, padding: "12px 16px", borderRadius: 12, border: "none", cursor: streaming ? "not-allowed" : "pointer", opacity: streaming ? 0.5 : 1, fontSize: 13, transition: "all 0.2s" }}>
            {streaming ? "ANALYZING..." : "RUN ANALYSIS"}
          </button>
        </div>

        {activeTab === "chat" && (
          <div style={{ padding: 12, flex: 1, overflowY: "auto" }}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 6, display: "block" }}>Tickers</label>
              <input value={tickers} onChange={(e) => setTickers(e.target.value)} placeholder="NVDA, AAPL, MSFT" style={{ fontSize: 12, padding: "8px 12px", borderRadius: 8, marginBottom: 8 }} />
              <label style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 6, display: "block" }}>Weights</label>
              <input value={weights} onChange={(e) => setWeights(e.target.value)} placeholder="0.5, 0.3, 0.2" style={{ fontSize: 12, padding: "8px 12px", borderRadius: 8 }} />
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {QUICK_ACTIONS.map((action) => (
                <button key={action} onClick={() => handleQuickAction(action)} disabled={streaming}
                  style={{ background: "rgba(0,230,118,0.06)", color: "#00e676", border: "1px solid rgba(0,230,118,0.15)", padding: "4px 10px", fontSize: 10, fontWeight: 500, borderRadius: 8, cursor: streaming ? "not-allowed" : "pointer", opacity: streaming ? 0.4 : 1 }}>
                  {action}
                </button>
              ))}
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 4 }}>
              <button onClick={handleSendEmail} disabled={emailSending || streaming}
                style={{ flex: 1, background: emailSent ? "rgba(0,230,118,0.1)" : "rgba(68,138,255,0.1)", color: emailSent ? "#00e676" : "#448aff", border: `1px solid ${emailSent ? "rgba(0,230,118,0.2)" : "rgba(68,138,255,0.2)"}`, padding: "8px 10px", fontSize: 10, fontWeight: 500, borderRadius: 8, cursor: "pointer" }}>
                {emailSending ? "SENDING..." : emailSent ? "EMAIL SENT!" : "EMAIL REPORT"}
              </button>
            </div>
          </div>
        )}

        {activeTab === "config" && (
          <div style={{ padding: 12, flex: 1, overflowY: "auto" }}>
            <p style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", marginBottom: 12 }}>Set thresholds for automatic risk alerts. Vera will notify you when your portfolio crosses these limits.</p>
            {[
              { key: "var_95", label: "VaR 95%", min: 1, max: 30, unit: "%" },
              { key: "health_score", label: "Min Health", min: 0, max: 100, unit: "" },
              { key: "volatility", label: "Volatility", min: 0.5, max: 10, unit: "%", step: 0.5 },
              { key: "cvar", label: "CVaR", min: 1, max: 40, unit: "%" },
            ].map((a) => (
              <div key={a.key} style={{ marginBottom: 12, background: "rgba(20,20,30,0.4)", borderRadius: 10, padding: 12, border: "1px solid rgba(255,255,255,0.04)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>{a.label}</span>
                  <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "rgba(255,255,255,0.3)", cursor: "pointer" }}>
                    <input type="checkbox" checked={alertEnabled[a.key] || false} onChange={() => setAlertEnabled((prev) => ({ ...prev, [a.key]: !prev[a.key] }))} style={{ accentColor: "#00e676", width: 12, height: 12 }} />
                    Active
                  </label>
                </div>
                <input type="range" min={a.min} max={a.max} step={a.step || 1} value={alertValues[a.key] !== undefined ? alertValues[a.key] : a.default} onChange={(e) => setAlertValues((prev) => ({ ...prev, [a.key]: parseFloat(e.target.value) }))} disabled={!alertEnabled[a.key]} style={{ width: "100%", height: 3, appearance: "none", background: alertEnabled[a.key] ? "linear-gradient(90deg, #00e676, #ffd740, #ff5252)" : "rgba(255,255,255,0.06)", borderRadius: 2, outline: "none", cursor: alertEnabled[a.key] ? "pointer" : "not-allowed" }} />
                <div style={{ textAlign: "center", fontSize: 14, fontWeight: 600, color: alertEnabled[a.key] ? "#00e676" : "rgba(255,255,255,0.15)", marginTop: 4 }}>{alertValues[a.key] !== undefined ? alertValues[a.key] : a.default}{a.unit}</div>
              </div>
            ))}
            <button onClick={handleSaveAlerts} style={{ width: "100%", background: "rgba(0,230,118,0.1)", color: "#00e676", border: "1px solid rgba(0,230,118,0.2)", padding: "10px", borderRadius: 10, fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
              SAVE ALERT SETTINGS
            </button>
          </div>
        )}

        {activeTab === "history" && (
          <div style={{ padding: 12, flex: 1, overflowY: "auto" }}>
            {loadingHistory ? (
              <div style={{ textAlign: "center", padding: 20, color: "rgba(255,255,255,0.2)", fontSize: 12 }}>Loading history...</div>
            ) : historyList.length === 0 ? (
              <div style={{ textAlign: "center", padding: 20, color: "rgba(255,255,255,0.2)", fontSize: 12 }}>No conversation history yet. Start chatting with Vera.</div>
            ) : (
              historyList.map((item, i) => (
                <div key={i} style={{ marginBottom: 6, padding: "8px 10px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }} onClick={() => loadHistoryItem(item.tickers, item.weights)}>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 2, textTransform: "capitalize" }}>{item.role}</div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.6)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.content?.substring(0, 60)}...</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div ref={chatRef} style={{ flex: 1, overflowY: "auto", padding: "16px 24px 8px" }}>
          {messages.map((msg, i) => (
            <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", marginBottom: 12, animation: "fadeIn 0.3s ease" }}>
              <div style={{
                maxWidth: "72%",
                padding: msg.role === "user" ? "10px 18px" : "14px 20px",
                borderRadius: msg.role === "user" ? "18px 18px 6px 18px" : "18px 18px 18px 6px",
                background: msg.role === "user" ? "#00e676" : "rgba(20,20,30,0.6)",
                color: msg.role === "user" ? "#000" : "#f0f0f5",
                border: msg.role === "user" ? "none" : "1px solid rgba(255,255,255,0.06)",
                fontSize: 14,
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                backdropFilter: msg.role === "user" ? "none" : "blur(16px)",
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
            <div style={{ margin: "4px 0 16px", animation: "fadeIn 0.5s ease" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, marginBottom: 8 }}>
                <MetricCard label="95% VaR" value={formatCurrency(latestMetrics.var_95)} sub="Max loss in 95% of scenarios" color={latestMetrics.var_95 > 50000 ? "#ff5252" : "#00e676"} />
                <MetricCard label="95% CVaR" value={formatCurrency(latestMetrics.cvar)} sub="Avg loss in worst 5%" color={latestMetrics.cvar > 50000 ? "#ff5252" : "#00e676"} />
                <MetricCard label="Sentiment" value={latestMetrics.sentiment_score?.toFixed(3)} sub="FinBERT news sentiment" color={latestMetrics.sentiment_score > 0.3 ? "#00e676" : latestMetrics.sentiment_score < -0.3 ? "#ff5252" : "#ffd740"} />
                <MetricCard label="Loss Prob" value={`${(latestMetrics.prob_loss * 100).toFixed(0)}%`} sub="Chance of negative return" color={latestMetrics.prob_loss > 0.5 ? "#ff5252" : "#00e676"} />
                {latestMetrics.health_score != null && (
                  <MetricCard label="Health" value={`${latestMetrics.health_score}/100`} sub="Portfolio health score" color={latestMetrics.health_score >= 75 ? "#00e676" : latestMetrics.health_score >= 50 ? "#ffd740" : "#ff5252"} />
                )}
                {latestMetrics.garch_vol != null && (
                  <MetricCard label="GARCH Vol" value={(latestMetrics.garch_vol * 100).toFixed(2) + "%"} sub="Estimated volatility" color="#448aff" />
                )}
              </div>

              {/* LSTM Forecast Chart */}
              {latestMetrics.forecast_60d && latestMetrics.forecast_60d.length > 1 && (
                <div className="glass-card" style={{ padding: 16, marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "#448aff", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    LSTM 60-Day Horizon Scan
                  </div>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={latestMetrics.forecast_60d.map((v, i) => ({ day: i, value: v }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="day" stroke="rgba(255,255,255,0.15)" tick={{ fontSize: 10 }} />
                      <YAxis stroke="rgba(255,255,255,0.15)" tick={{ fontSize: 10 }} domain={["auto", "auto"]} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <Tooltip contentStyle={{ background: "rgba(20,20,30,0.95)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, fontSize: 11 }} formatter={(v) => [`$${v.toLocaleString()}`, "Value"]} />
                      <Line type="monotone" dataKey="value" stroke="#00e676" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "#00e676" }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {latestForecast && latestForecast.bull && latestForecast.base && latestForecast.bear && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 8 }}>
                  <ScenarioCard label="Bull" color="#00e676" data={latestForecast.bull} />
                  <ScenarioCard label="Base" color="#ffd740" data={latestForecast.base} />
                  <ScenarioCard label="Bear" color="#ff5252" data={latestForecast.bear} />
                </div>
              )}

              {latestForecast && latestForecast["60_day_outlook"] && (
                <div className="glass-card" style={{ padding: 12, marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "#448aff", fontWeight: 600, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.5px" }}>60-Day Outlook</div>
                  <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", lineHeight: 1.5 }}>{latestForecast["60_day_outlook"]}</div>
                </div>
              )}

              {latestStress && latestStress.length > 0 && (
                <div className="glass-card" style={{ padding: 16, marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "#ffd740", fontWeight: 600, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    Armor Test — Stress Scenarios
                  </div>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                          <th style={{ textAlign: "left", padding: "6px 8px", color: "rgba(255,255,255,0.3)", fontWeight: 400 }}>Scenario</th>
                          <th style={{ textAlign: "right", padding: "6px 8px", color: "rgba(255,255,255,0.3)", fontWeight: 400 }}>Shock</th>
                          <th style={{ textAlign: "right", padding: "6px 8px", color: "rgba(255,255,255,0.3)", fontWeight: 400 }}>VaR 95%</th>
                          <th style={{ textAlign: "right", padding: "6px 8px", color: "rgba(255,255,255,0.3)", fontWeight: 400 }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {latestStress.map((s, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                            <td style={{ padding: "6px 8px", color: "rgba(255,255,255,0.6)" }}>{s.scenario}</td>
                            <td style={{ textAlign: "right", padding: "6px 8px", color: "rgba(255,255,255,0.4)" }}>{(s.shock * 100).toFixed(0)}%</td>
                            <td style={{ textAlign: "right", padding: "6px 8px", color: "rgba(255,255,255,0.4)" }}>${s.var_95?.toLocaleString()}</td>
                            <td style={{ textAlign: "right", padding: "6px 8px" }}>
                              <span style={{ color: s.breach ? "#ff5252" : "#00e676", fontWeight: 600 }}>
                                {s.breach ? "BREACH" : "OK"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.04)", padding: "12px 24px 20px", background: "rgba(5,5,8,0.8)" }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <textarea value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              placeholder={streaming ? "Vera is thinking..." : "Ask Vera about your portfolio..."}
              disabled={streaming} rows={1}
              style={{
                flex: 1,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.06)",
                color: "#f0f0f5",
                borderRadius: 14,
                padding: "14px 18px",
                fontSize: 14,
                outline: "none",
                resize: "none",
                fontFamily: "inherit",
                maxHeight: 120,
              }}
            />
            <button onClick={() => sendMessage(input)} disabled={streaming || !input.trim()}
              style={{
                background: streaming ? "rgba(255,255,255,0.1)" : "#00e676",
                color: "#000",
                fontWeight: 600,
                padding: "14px 28px",
                borderRadius: 14,
                border: "none",
                cursor: (streaming || !input.trim()) ? "not-allowed" : "pointer",
                opacity: (streaming || !input.trim()) ? 0.4 : 1,
                fontSize: 14,
                whiteSpace: "nowrap",
                minWidth: 90,
                transition: "all 0.2s",
              }}>
              {streaming ? "..." : "Send"}
            </button>
          </div>
        </div>
      </div>

      {notification && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 9999,
          padding: "12px 20px", borderRadius: 12, fontSize: 13, fontWeight: 500,
          background: notification.type === "success" ? "rgba(0,230,118,0.12)" : "rgba(255,82,82,0.12)",
          border: notification.type === "success" ? "1px solid rgba(0,230,118,0.25)" : "1px solid rgba(255,82,82,0.25)",
          color: notification.type === "success" ? "#00e676" : "#ff5252",
          backdropFilter: "blur(20px)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
          animation: "slideUp 0.3s ease",
        }}>
          {notification.message}
        </div>
      )}
    </div>
  );
}
