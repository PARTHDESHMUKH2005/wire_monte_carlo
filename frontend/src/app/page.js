"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Home() {
  const [tickers, setTickers] = useState("NVDA, AAPL");
  const [weights, setWeights] = useState("0.6, 0.4");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    const t = tickers.split(",").map((s) => s.trim().toUpperCase());
    const w = weights.split(",").map((s) => parseFloat(s.trim()));

    if (t.length !== w.length) {
      setError("Number of tickers must match number of weights");
      setLoading(false);
      return;
    }

    const sum = w.reduce((a, b) => a + b, 0);
    if (Math.abs(sum - 1) > 0.01) {
      setError("Weights must sum to 1.0");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickers: t, weights: w }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="min-h-screen p-4 md:p-8 max-w-6xl mx-auto">
      <header className="border-b border-zinc-800 pb-4 mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          LiveRisk <span className="text-zinc-500 font-normal text-lg">/ Financial Risk Intelligence</span>
        </h1>
        <p className="text-zinc-500 text-sm mt-1">
          Powered by Anakin Wire API — Yahoo Finance, Finviz, Reuters, Reddit
        </p>
      </header>

      <div className="flex flex-col md:flex-row gap-4 mb-8">
        <div className="flex-1">
          <label className="block text-xs text-zinc-500 mb-1 uppercase tracking-wider">Tickers</label>
          <input value={tickers} onChange={(e) => setTickers(e.target.value)} placeholder="NVDA, AAPL" />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-zinc-500 mb-1 uppercase tracking-wider">Weights</label>
          <input value={weights} onChange={(e) => setWeights(e.target.value)} placeholder="0.6, 0.4" />
        </div>
        <div className="flex items-end">
          <button onClick={runAnalysis} disabled={loading} className="px-8 py-[10px]">
            {loading ? "ANALYZING..." : "RUN ANALYSIS"}
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
          <p className="text-zinc-400 text-sm animate-pulse">Fetching market data via Wire API → simulating 10,000 paths → computing risk metrics...</p>
        </div>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="card">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">95% VaR</div>
              <div className={`card-value ${result.var > 50000 ? "var-negative" : "var-positive"}`}>
                ${result.var?.toLocaleString()}
              </div>
              <div className="text-xs text-zinc-600 mt-1">Value at Risk (95% confidence)</div>
            </div>
            <div className="card">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">95% CVaR</div>
              <div className={`card-value ${result.cvar > 50000 ? "var-negative" : "var-positive"}`}>
                ${result.cvar?.toLocaleString()}
              </div>
              <div className="text-xs text-zinc-600 mt-1">Conditional VaR (tail avg)</div>
            </div>
            <div className="card">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Sentiment</div>
              <div className={`card-value ${result.sentiment_score > 0.3 ? "var-positive" : result.sentiment_score < -0.3 ? "var-negative" : "var-neutral"}`}>
                {result.sentiment_score?.toFixed(3)}
              </div>
              <div className="text-xs text-zinc-600 mt-1">FinBERT news sentiment (-1 to +1)</div>
            </div>
            <div className="card">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Adj VaR</div>
              <div className={`card-value ${result.sentiment_adjusted_var > result.var ? "var-negative" : "var-positive"}`}>
                ${result.sentiment_adjusted_var?.toLocaleString()}
              </div>
              <div className="text-xs text-zinc-600 mt-1">Sentiment-adjusted VaR</div>
            </div>
          </div>

          {result.forecast_60d && result.forecast_60d.length > 1 && (
            <div className="card mb-8">
              <div className="text-sm text-zinc-400 uppercase tracking-wider mb-4">60-Day LSTM Forecast</div>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={result.forecast_60d.map((v, i) => ({ day: i, value: v }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="day" stroke="#52525b" tick={{ fontSize: 11 }} label={{ value: "Day", position: "insideBottom", offset: -5, fill: "#52525b", fontSize: 11 }} />
                  <YAxis stroke="#52525b" tick={{ fontSize: 11 }} domain={["auto", "auto"]} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    contentStyle={{ background: "#14141a", border: "1px solid #27272a", borderRadius: 8, fontSize: 12 }}
                    formatter={(v) => [`$${v.toLocaleString()}`, "Portfolio Value"]}
                    labelFormatter={(d) => `Day ${d}`}
                  />
                  <Line type="monotone" dataKey="value" stroke="#22c55e" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {result.stress_scenarios && result.stress_scenarios.length > 0 && (
            <div className="card mb-8">
              <div className="text-sm text-zinc-400 uppercase tracking-wider mb-4">Stress Scenarios</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left py-2 pr-4 text-zinc-500 font-normal">Scenario</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">Shock</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">Vol</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">Var 95%</th>
                      <th className="text-right py-2 px-2 text-zinc-500 font-normal">CVaR 95%</th>
                      <th className="text-right py-2 pl-2 text-zinc-500 font-normal">Breach</th>
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
                          <span className={s.breach ? "text-red-400 font-bold" : "text-green-500"}>
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <div className="card">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Reddit Hype</div>
              {result.reddit_hype ? (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-2 h-2 rounded-full ${result.reddit_hype.spike_detected ? "bg-red-500" : "bg-green-500"}`} />
                    <span className="text-sm text-zinc-300">
                      {result.reddit_hype.spike_detected ? "Hype spike detected" : "Normal activity"}
                    </span>
                  </div>
                  {result.reddit_hype.mentions && Object.entries(result.reddit_hype.mentions).map(([t, c]) => (
                    <div key={t} className="flex justify-between text-xs text-zinc-400 py-1">
                      <span>r/wallstreetbets mentions for {t}</span>
                      <span className="font-mono">{c}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-zinc-600">No Reddit data available</div>
              )}
            </div>
            <div className="card">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">News Summary</div>
              <p className="text-sm text-zinc-300 mb-3">{result.news_summary || "No news data"}</p>
              {result.headlines && result.headlines.length > 0 && (
                <div className="space-y-1">
                  {result.headlines.slice(0, 4).map((h, i) => (
                    <p key={i} className="text-xs text-zinc-500 truncate">• {h.title || h.snippet || ""}</p>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Configuration</div>
            <div className="flex flex-wrap gap-4 text-xs">
              <span className="text-zinc-400">Tickers: <span className="text-zinc-200 font-mono">{result.config?.tickers?.join(", ")}</span></span>
              <span className="text-zinc-400">Weights: <span className="text-zinc-200 font-mono">{result.config?.weights?.join(", ")}</span></span>
              <span className="text-zinc-400">Prob Loss: <span className="text-zinc-200 font-mono">{(result.prob_loss * 100).toFixed(1)}%</span></span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
