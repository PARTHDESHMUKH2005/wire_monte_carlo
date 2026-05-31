"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/lib/api";

const API = getApiBaseUrl();

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userName, setUserName] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("liverisk_token");
    const u = localStorage.getItem("liverisk_user");
    if (!token) {
      router.push("/");
      return;
    }
    setUserName(u);
    fetchHistory();
  }, [router]);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("liverisk_token");
      const res = await fetch(`${API}/history`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (res.status === 401) {
        localStorage.removeItem("liverisk_token");
        router.push("/");
        return;
      }
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setHistory(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalysis = (item) => {
    const data = { tickers: item.tickers.join(", "), weights: item.weights.join(", ") };
    localStorage.setItem("liverisk_replay", JSON.stringify(data));
    router.push("/dashboard");
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return d.toLocaleDateString("en-US", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="p-4 md:p-8 max-w-6xl mx-auto">
        <div className="card text-center py-12">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="loader-ring" />
            <p className="text-zinc-300 text-sm font-medium">Loading history</p>
          </div>
          <p className="text-zinc-500 text-xs">Fetching your past analyses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto">
      <header className="border-b border-zinc-800 pb-4 mb-6">
        <h1 className="text-3xl font-bold text-white tracking-tight">
          Analysis History
        </h1>
        <p className="text-zinc-500 text-sm mt-1">
          {userName ? `${userName}'s past portfolio risk analyses` : "Your past portfolio risk analyses"}
        </p>
      </header>

      {error && (
        <div className="card border-red-800 bg-red-950/30 mb-8">
          <p className="text-red-400 text-sm mb-3">{error}</p>
          <button onClick={fetchHistory} className="text-xs bg-zinc-700 px-3 py-1.5 rounded">
            RETRY
          </button>
        </div>
      )}

      {history.length === 0 ? (
        <div className="card text-center py-16">
          <div className="text-5xl mb-4 text-zinc-700">&#128202;</div>
          <p className="text-zinc-400 text-sm mb-1">No analyses yet</p>
          <p className="text-zinc-600 text-xs mb-4">Run your first risk analysis on the dashboard.</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="px-6 py-2"
          >
            GO TO DASHBOARD
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((item) => {
            const r = item.result;
            const varColor = r?.var > 50000 ? "text-red-400" : "text-green-400";
            return (
              <div
                key={item.id}
                className="card hover:border-zinc-600 transition-all cursor-pointer relative overflow-hidden"
                onClick={() => loadAnalysis(item)}
              >
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-green-500/20 to-transparent" />
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {item.tickers.map((t) => (
                        <span key={t} className="text-xs bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded font-mono border border-zinc-700/50">
                          {t}
                        </span>
                      ))}
                    </div>
                    <div className="text-xs text-zinc-500">
                      Weights: {item.weights.map((w, i) => `${item.tickers[i]}: ${(w * 100).toFixed(0)}%`).join("  |  ")}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    <div className={`text-lg font-bold ${varColor}`}>
                      ${r?.var?.toLocaleString() || "N/A"}
                    </div>
                    <div className="text-xs text-zinc-600">95% VaR</div>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs pt-2 border-t border-zinc-800/50">
                  <div className="flex gap-4 text-zinc-500">
                    <span>CVaR: <span className="text-zinc-300 font-medium">${r?.cvar?.toLocaleString() || "N/A"}</span></span>
                    <span>Sentiment: <span className={r?.sentiment_score > 0.3 ? "text-green-400 font-medium" : r?.sentiment_score < -0.3 ? "text-red-400 font-medium" : "text-yellow-400 font-medium"}>{r?.sentiment_score?.toFixed(3) || "N/A"}</span></span>
                    <span>Loss Prob: <span className="text-zinc-300 font-medium">{(r?.prob_loss * 100).toFixed(0)}%</span></span>
                  </div>
                  <span className="text-zinc-600" title={new Date(item.created_at).toLocaleString()}>{formatDate(item.created_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
