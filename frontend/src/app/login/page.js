"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getApiBaseUrl } from "@/lib/api";

const API = getApiBaseUrl();

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (isRegister && password !== confirmPassword) {
      setError("Passwords do not match");
      setLoading(false);
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      setLoading(false);
      return;
    }

    const endpoint = isRegister ? "/register" : "/login";

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...(isRegister ? { name: name.trim() } : {}),
          email: email.trim().toLowerCase(),
          password,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || (isRegister ? "Registration failed" : "Login failed"));
      }

      const data = await res.json();
      localStorage.setItem("liverisk_token", data.token);
      localStorage.setItem("liverisk_user", data.name);
      localStorage.setItem("liverisk_user_id", String(data.user_id));
      localStorage.setItem("liverisk_email", data.email);
      router.push("/vera");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsRegister(!isRegister);
    setError(null);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#050508]">
      <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[rgba(0,230,118,0.03)] rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-[rgba(0,230,118,0.02)] rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 hover:opacity-80 transition-opacity">
            <span className="w-9 h-9 rounded-xl bg-[#00e676] flex items-center justify-center text-black font-extrabold text-sm">LR</span>
            <h1 className="text-3xl font-bold text-white tracking-tight">LiveRisk</h1>
          </Link>
          <p className="text-[rgba(255,255,255,0.3)] text-sm mt-2">
            {isRegister ? "Create your account to get started" : "Sign in to your risk dashboard"}
          </p>
        </div>

        <div className="glass-card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {isRegister && (
              <div>
                <label className="block text-xs text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-2 font-medium">
                  Full Name
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                  required
                  autoFocus
                />
              </div>
            )}

            <div>
              <label className="block text-xs text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-2 font-medium">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-xs text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-2 font-medium">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={isRegister ? "Create a password (min 6 chars)" : "Enter your password"}
                  required
                  className="pr-24"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[rgba(255,255,255,0.3)] hover:text-white bg-transparent px-2 py-1"
                >
                  {showPassword ? "HIDE" : "SHOW"}
                </button>
              </div>
            </div>

            {isRegister && (
              <div>
                <label className="block text-xs text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-2 font-medium">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  required
                />
              </div>
            )}

            {error && (
              <div className="text-[#ff5252] text-sm bg-[rgba(255,82,82,0.08)] border border-[rgba(255,82,82,0.2)] rounded-xl px-4 py-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email.trim() || !password || (isRegister && !name.trim())}
              className="w-full inline-flex items-center justify-center py-4 text-base rounded-2xl font-semibold text-black bg-[#00e676] hover:bg-[#00c853] transition-all duration-200 hover:shadow-lg hover:shadow-[rgba(0,230,118,0.2)] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="loader-ring" />
                  {isRegister ? "CREATING ACCOUNT..." : "SIGNING IN..."}
                </span>
              ) : (
                isRegister ? "CREATE ACCOUNT" : "SIGN IN"
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={toggleMode}
              className="text-sm text-[rgba(255,255,255,0.3)] hover:text-[#00e676] bg-transparent transition-colors"
            >
              {isRegister ? "Already have an account? Sign In" : "Don't have an account? Create One"}
            </button>
          </div>
        </div>

        <div className="text-center mt-6">
          <Link href="/" className="text-xs text-[rgba(255,255,255,0.2)] hover:text-[rgba(255,255,255,0.4)] transition-colors">
            &larr; Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
