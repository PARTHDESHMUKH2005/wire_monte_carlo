"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), password }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Login failed");
      }
      const data = await res.json();
      localStorage.setItem("liverisk_token", data.token);
      localStorage.setItem("liverisk_user", data.name);
      router.push("/dashboard");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <Link href="/" className="inline-block hover:opacity-80 transition-opacity">
            <h1 className="text-3xl font-bold text-white tracking-tight">
              LiveRisk
            </h1>
          </Link>
          <p className="text-zinc-500 text-sm mt-1">
            Sign in to your risk dashboard
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 mb-6">
          <span className="trust-badge"><span className="trust-dot" />Monte Carlo 10K</span>
          <span className="trust-badge"><span className="trust-dot" />FinBERT</span>
          <span className="trust-badge"><span className="trust-dot" />LSTM</span>
        </div>

        <div className="card mb-6 border-amber-700/40 bg-gradient-to-r from-amber-950/15 to-transparent relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/40 to-transparent" />
          <div className="text-xs text-amber-400 uppercase tracking-wider mb-2 font-semibold flex items-center gap-2">
            <span>Shared Access Password</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-900/50 text-amber-400 border border-amber-800/30">Public</span>
          </div>
          <div className="bg-zinc-900/80 rounded-lg px-4 py-3 border border-amber-700/30">
            <code className="text-lg font-bold text-amber-300 tracking-wider select-all">
              riskmaster2024
            </code>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            This password is shared by all users. Enter it below along with your name to access the platform.
          </p>
        </div>

        <form onSubmit={handleLogin} className="card space-y-4 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-green-500/30 to-transparent" />
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              Your Name
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. John Doe"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter shared password"
                required
                className="pr-24"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-zinc-500 hover:text-zinc-300 bg-transparent px-2 py-1"
              >
                {showPassword ? "HIDE" : "SHOW"}
              </button>
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !name.trim() || !password}
            className="w-full py-3 text-base"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="loader-ring" />
                AUTHENTICATING...
              </span>
            ) : (
              "ACCESS DASHBOARD"
            )}
          </button>
        </form>

        <div className="text-center mt-6">
          <Link href="/" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
            &larr; Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
