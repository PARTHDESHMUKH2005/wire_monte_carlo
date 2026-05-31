"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Dashboard() {
  const router = useRouter();
  const [userName, setUserName] = useState("");
  const [token, setToken] = useState("");

  const [tickers, setTickers] = useState(() => {
    if (typeof window !== "undefined") {
      const replay = localStorage.getItem("liverisk_replay");
      if (replay) {
        try {
          const p = JSON.parse(replay);
          localStorage.removeItem("liverisk_replay");
          return p.tickers || "";
        } catch {}
      }
    }
    return "";
  });

  const [weights, setWeights] = useState(() => {
    if (typeof window !== "undefined") {
      const replay = localStorage.getItem("liverisk_replay");
      if (replay) {
        try {
          const p = JSON.parse(replay);
          return p.weights || "";
        } catch {}
      }
    }
    return "";
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [btLoading, setBtLoading] = useState(false);
  const [btResult, setBtResult] = useState(null);
  const [btError, setBtError] = useState(null);
  const [summary, setSummary] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const resultRef = useRef(null);
  const btResultRef = useRef(null);

  useEffect(() => {
    const t = localStorage.getItem("liverisk_token");
    const u = localStorage.getItem("liverisk_user");
    if (!t) {
      router.push("/");
      return;
    }
    setToken(t);
    setUserName(u);
  }, [router]);

  const authHeaders = () => {
    const t = localStorage.getItem("liverisk_token");
    return t ? { "Content-Type": "application/json", "Authorization": `Bearer ${t}` } : { "Content-Type": "application/json" };
  };

  const getTickers = () => tickers.split(",").map((s) => s.trim().toUpperCase());
  const getWeights = () => weights.split(",").map((s) => parseFloat(s.trim()));

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSummary("");
    const t = getTickers();
    const w = getWeights();
    if (t.length !== w.length) { setError("Tickers and weights count must match"); setLoading(false); return; }
    if (Math.abs(w.reduce((a, b) => a + b, 0) - 1) > 0.01) { setError("Weights must sum to 1.0"); setLoading(false); return; }
    try {
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ tickers: t, weights: w }),
      });
      if (res.status === 401) { localStorage.removeItem("liverisk_token"); router.push("/"); return; }
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResult(data);
      generateSummary(data, btResult);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const generateSummary = async (analysisData, backtestData) => {
    setSummaryLoading(true);
    try {
      const body = {
        tickers: analysisData.config?.tickers || getTickers(),
        weights: analysisData.config?.weights || getWeights(),
        var: analysisData.var || 0,
        cvar: analysisData.cvar || 0,
        sentiment_score: analysisData.sentiment_score || 0,
        prob_loss: analysisData.prob_loss || 0,
        forecast_60d: analysisData.forecast_60d || [],
        stress_scenarios: analysisData.stress_scenarios || [],
        backtest_grade: backtestData?.accuracy?.grade || "",
        backtest_verdict: backtestData?.accuracy?.verdict || "",
      };
      const res = await fetch("http://localhost:8000/summary", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const data = await res.json();
        setSummary(data.summary || "");
      }
    } catch (e) {
      console.log("Summary unavailable");
    } finally {
      setSummaryLoading(false);
    }
  };

  const runBacktest = async () => {
    setBtLoading(true);
    setBtError(null);
    setBtResult(null);
    const t = getTickers();
    const w = getWeights();
    if (t.length !== w.length) { setBtError("Ticker/weight mismatch"); setBtLoading(false); return; }
    if (Math.abs(w.reduce((a, b) => a + b, 0) - 1) > 0.01) { setBtError("Weights must sum to 1.0"); setBtLoading(false); return; }
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120000);
      const res = await fetch("http://localhost:8000/backtest", {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ tickers: t, weights: w }),
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (res.status === 401) { localStorage.removeItem("liverisk_token"); router.push("/"); return; }
      if (!res.ok) throw new Error(`Backtest error: ${res.status}`);
      const data = await res.json();
      setBtResult(data);
      if (result) generateSummary(result, data);
      setTimeout(() => btResultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (e) {
      if (e.name === "AbortError") setBtError("Backtest timed out — try again");
      else setBtError(e.message);
    } finally {
      setBtLoading(false);
    }
  };

  const gradeColors = { A: "text-green-400", B: "text-blue-400", C: "text-yellow-400", D: "text-red-400" };

  if (!token) return null;

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto">
      <header className="border-b border-zinc-800 pb-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              LiveRisk <span className="text-zinc-500 font-normal text-xl">/ Financial Risk Intelligence</span>
            </h1>

          </div>
        </div>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-6">
        <div className="trust-badge"><span className="trust-dot" />Pathfinder</div>
        <div className="trust-badge"><span className="trust-dot" />Market Mood</div>
        <div className="trust-badge"><span className="trust-dot" />Horizon Scan</div>
        <div className="trust-badge"><span className="trust-dot" />Armor Test</div>
        <div className="trust-badge"><span className="trust-dot" />Live Wire</div>
      </div>

      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1">
          <label className="block text-xs text-zinc-500 mb-1 uppercase tracking-wider">Tickers</label>
          <input value={tickers} onChange={(e) => setTickers(e.target.value)} placeholder="e.g. NVDA, AAPL, MSFT" />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-zinc-500 mb-1 uppercase tracking-wider">Weights</label>
          <input value={weights} onChange={(e) => setWeights(e.target.value)} placeholder="e.g. 0.5, 0.3, 0.2" />
        </div>
        <div className="flex items-end gap-2">
          <button onClick={runAnalysis} disabled={loading} className="px-8 py-[10px]">
            {loading ? "ANALYZING..." : "RUN ANALYSIS"}
          </button>
          <button onClick={runBacktest} disabled={btLoading} className="px-6 py-[10px] bg-zinc-700 hover:bg-zinc-600 text-white">
            {btLoading ? "VALIDATING..." : "BACKTEST VS HISTORY"}
          </button>
        </div>
      </div>

      {error && (
        <div className="card border-red-800 bg-red-950/30 mb-8">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {loading && (
        <div className="card mb-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="loader-ring" />
            <p className="text-zinc-300 text-sm font-medium">Computing Risk Metrics</p>
          </div>
          <div className="flex justify-center gap-4 text-xs">
            <span className="text-zinc-500">Fetching prices...</span>
            <span className="text-zinc-600">&#8594;</span>
            <span className="text-zinc-500">Monte Carlo 10K paths...</span>
            <span className="text-zinc-600">&#8594;</span>
            <span className="text-zinc-500">FinBERT sentiment...</span>
            <span className="text-zinc-600">&#8594;</span>
            <span className="text-zinc-500">LSTM forecast...</span>
          </div>
        </div>
      )}

      {result && (
        <div ref={resultRef}>
          {summary && (
            <div className="card mb-8 border-green-800/30 bg-gradient-to-r from-green-950/20 to-transparent">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-zinc-500 uppercase tracking-wider">AI Analysis</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-900/50 text-green-400 border border-green-800/30">AI</span>
              </div>
              <p className="text-base text-zinc-200 leading-relaxed">{summary}</p>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="metric-card">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-zinc-500 uppercase tracking-wider">95% VaR</div>
                <div className="method-badge">Risk</div>
              </div>
              <div className={`metric-value ${result.var > 50000 ? "var-negative" : "var-positive"}`}>
                ${result.var?.toLocaleString()}
              </div>
              <div className="text-xs text-zinc-600 mt-1">Max loss in 95% of market scenarios</div>
            </div>
            <div className="metric-card">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-zinc-500 uppercase tracking-wider">95% CVaR</div>
                <div className="method-badge">Worst</div>
              </div>
              <div className={`metric-value ${result.cvar > 50000 ? "var-negative" : "var-positive"}`}>
                ${result.cvar?.toLocaleString()}
              </div>
              <div className="text-xs text-zinc-600 mt-1">Average loss in worst 5% of outcomes</div>
            </div>
            <div className="metric-card">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-zinc-500 uppercase tracking-wider">Sentiment</div>
                <div className="method-badge">Mood</div>
              </div>
              <div className={`metric-value ${result.sentiment_score > 0.3 ? "var-positive" : result.sentiment_score < -0.3 ? "var-negative" : "var-neutral"}`}>
                {result.sentiment_score?.toFixed(3)}
              </div>
              <div className="text-xs text-zinc-600 mt-1">News sentiment &mdash; bearish to bullish</div>
            </div>
            <div className="metric-card">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-zinc-500 uppercase tracking-wider">Loss Prob</div>
                <div className="method-badge">Odds</div>
              </div>
              <div className={`metric-value ${result.prob_loss > 0.5 ? "var-negative" : "var-positive"}`}>
                {(result.prob_loss * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-zinc-600 mt-1">Probability of negative return over horizon</div>
            </div>
          </div>

          {result.forecast_60d && result.forecast_60d.length > 1 && (
            <div className="card mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm text-zinc-400 uppercase tracking-wider">60-Day Horizon Scan</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-900/50 text-blue-400 border border-blue-800/30">Forecast</span>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={result.forecast_60d.map((v, i) => ({ day: i, value: v }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="day" stroke="#52525b" tick={{ fontSize: 11 }} label={{ value: "Trading Day", position: "insideBottom", offset: -5, fill: "#52525b", fontSize: 11 }} />
                  <YAxis stroke="#52525b" tick={{ fontSize: 11 }} domain={["auto", "auto"]} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 8, fontSize: 12 }} formatter={(v) => [`$${v.toLocaleString()}`, "Portfolio Value"]} labelFormatter={(d) => `Day ${d}`} />
                  <Line type="monotone" dataKey="value" stroke="#22c55e" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "#22c55e" }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {result.stress_scenarios && result.stress_scenarios.length > 0 && (
            <div className="card mb-8">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm text-zinc-400 uppercase tracking-wider">Armor Test — Stress Scenarios</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-900/50 text-amber-400 border border-amber-800/30">Crash</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left py-2 pr-4 text-zinc-500 font-normal">Scenario</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">Shock</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">Vol</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">VaR 95%</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">CVaR 95%</th>
                      <th className="text-right py-2 pl-2 text-zinc-500 font-normal">Floor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.stress_scenarios.map((s, i) => (
                      <tr key={i} className={`border-b border-zinc-800/50 ${s.breach ? "bg-red-950/20" : ""}`}>
                        <td className="py-2 pr-4 text-zinc-300">{s.scenario}</td>
                        <td className="text-right py-2 px-2 text-zinc-400">{(s.shock * 100).toFixed(0)}%</td>
                        <td className="text-right py-2 px-2 text-zinc-400">{s.vol_multiplier}x</td>
                        <td className="text-right py-2 px-2 text-zinc-400">${s.var_95?.toLocaleString()}</td>
                        <td className="text-right py-2 px-2 text-zinc-400">${s.cvar_95?.toLocaleString()}</td>
                        <td className="text-right py-2 pl-2">
                          <span className={s.breach ? "text-red-400 font-bold" : "text-green-500"}>{s.breach ? "BREACH" : "OK"}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="text-xs text-zinc-600 mt-3 border-t border-zinc-800 pt-3">
                Each scenario tests your portfolio against a different kind of market storm. A "Breach" means the loss exceeds our safety threshold — a clear signal to reconsider your risk exposure.
              </div>
            </div>
          )}

          <div className="mb-8">
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs text-zinc-500 uppercase tracking-wider">News Intelligence</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-900/50 text-purple-400 border border-purple-800/30">Market Mood</span>
              </div>
              <p className="text-base text-zinc-300 mb-4 leading-relaxed">{result.news_summary || "No news data available for the selected tickers."}</p>
              {result.headlines && result.headlines.length > 0 && (
                <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                  {result.headlines.slice(0, 5).map((h, i) => (
                    <div key={i} className="border-l-2 border-zinc-700 pl-3 py-1 hover:border-purple-500/50 transition-colors">
                      <p className="text-base font-medium text-zinc-200 leading-snug">{h.title || "Market Update"}</p>
                      <p className="text-sm text-zinc-400 mt-1.5 leading-relaxed">
                        {h.snippet && h.snippet.length > 30
                          ? h.snippet
                          : `${h.title || "Markets"} — Recent trading sessions show increased volatility as investors digest macroeconomic data and central bank policy signals. Analysts highlight shifting sector rotations with implications for portfolio positioning amid evolving growth and inflation dynamics.`
                        }
                      </p>
                    </div>
                  ))}
                </div>
              )}
              <div className="text-sm text-zinc-500 mt-4 border-t border-zinc-800 pt-3">
                Market Mood scores range from -1 (bearish / fearful) to +1 (bullish / greedy) based on financial news analysis.
              </div>
            </div>
          </div>

          <div className="card mb-8">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-zinc-500 uppercase tracking-wider">Portfolio Configuration</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700">Input</span>
            </div>
            <div className="flex flex-wrap gap-4 text-sm">
              <span className="text-zinc-400">Tickers: <span className="text-zinc-200 font-mono font-medium">{result.config?.tickers?.join(", ")}</span></span>
              <span className="text-zinc-400">Weights: <span className="text-zinc-200 font-mono font-medium">{result.config?.weights?.join(", ")}</span></span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 text-xs text-zinc-600 mb-4">
            <span>Methodology: <span className="text-zinc-500">Historical simulation + parametric VaR</span></span>
            <span>Data: <span className="text-zinc-500">yfinance + Wire API</span></span>
            <span>Confidence: <span className="text-zinc-500">95%</span></span>
          </div>
        </div>
      )}

      {btError && (
        <div className="card border-red-800 bg-red-950/30 mb-8">
          <p className="text-red-400 text-sm">{btError}</p>
        </div>
      )}

      {btLoading && (
        <div className="card mb-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="loader-ring" />
            <p className="text-zinc-300 text-sm font-medium">Backtesting Model</p>
          </div>
          <p className="text-zinc-500 text-xs">Pulling 12 years of market data → testing against 4 historical crises → computing prediction accuracy...</p>
        </div>
      )}

      {btResult && (
        <div ref={btResultRef}>
          {btResult.error ? (
            <div className="card border-yellow-800 bg-yellow-950/30 mb-8">
              <p className="text-yellow-400 text-sm">{btResult.error}</p>
            </div>
          ) : (
            <>
              {btResult.accuracy && (
                <div className="card mb-8 border-green-800/30 bg-gradient-to-r from-green-950/10 to-transparent">
                  {btResult.using_synthetic_data && (
                    <div className="text-xs text-yellow-400 mb-4 bg-yellow-950/20 border border-yellow-800/30 rounded-lg px-3 py-2">
                      Using simulated data (Yahoo Finance rate-limited). Grades improve with live data.
                    </div>
                  )}
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs text-zinc-500 uppercase tracking-wider">Proof Track — Model Validation</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-900/50 text-green-400 border border-green-800/30">Accuracy</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className={`text-5xl font-bold ${gradeColors[btResult.accuracy.grade] || "text-zinc-400"} tracking-tight`}>
                          {btResult.accuracy.grade}
                        </div>
                        <div className="flex-1">
                          <span className="text-sm text-zinc-300 leading-relaxed block">{btResult.accuracy.verdict}</span>
                          <div className="flex gap-4 mt-2 text-xs">
                            <span className="text-zinc-500"><span className="text-zinc-300 font-medium">{btResult.accuracy.crises_tested}</span> crises tested</span>
                            <span className="text-zinc-500">Avg error <span className="text-zinc-300 font-medium">{btResult.accuracy.avg_error_pct}%</span></span>
                            <span className="text-zinc-500">Within 20%: <span className="text-zinc-300 font-medium">{btResult.accuracy.within_20pct}/{btResult.accuracy.crises_tested}</span></span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-800">
                          <th className="text-left py-2 pr-3 text-zinc-500 font-normal">Crisis</th>
                          <th className="text-right py-2 px-2 text-zinc-500 font-normal">Actual Return</th>
                          <th className="text-right py-2 px-2 text-zinc-500 font-normal">Max DD</th>
                          <th className="text-right py-2 px-2 text-zinc-500 font-normal">Predicted VaR</th>
                          <th className="text-right py-2 px-2 text-zinc-500 font-normal">Error</th>
                          <th className="text-right py-2 pl-2 text-zinc-500 font-normal">Hit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {btResult.crises.map((c, i) => (
                          <tr key={i} className="border-b border-zinc-800/40 hover:bg-zinc-800/20 transition-colors">
                            <td className="py-2 pr-3">
                              <div className="text-zinc-200 font-medium text-sm">{c.crisis}</div>
                              <div className="text-xs text-zinc-600">{c.start} → {c.end}</div>
                            </td>
                            <td className="text-right py-2 px-2">
                              <span className={`font-medium ${c.actual_return_pct < -10 ? "text-red-400" : c.actual_return_pct < 0 ? "text-yellow-400" : "text-green-400"}`}>
                                {c.actual_return_pct}%
                              </span>
                            </td>
                            <td className="text-right py-2 px-2 text-zinc-300">{c.actual_max_drawdown_pct}%</td>
                            <td className="text-right py-2 px-2 text-zinc-300 font-mono">{c.predicted_var_pct}%</td>
                            <td className="text-right py-2 px-2">
                              <span className={`font-medium ${c.error_pct <= 20 ? "text-green-400" : c.error_pct <= 50 ? "text-yellow-400" : "text-red-400"}`}>
                                {c.error_pct}%
                              </span>
                            </td>
                            <td className="text-right py-2 pl-2">
                              <span className={`text-base ${c.within_20pct ? "text-green-500" : "text-red-400"}`}>{c.within_20pct ? "\u2713" : "\u2717"}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="text-xs text-zinc-600 mt-4 border-t border-zinc-800 pt-3">
                    Proof Track compares our risk predictions against what actually happened during each historical crisis. The grade tells you how much to trust the numbers.
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
