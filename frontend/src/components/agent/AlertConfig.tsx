"use client";

import { useState, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";

const ALERTS = [
  { key: "var_95", label: "VaR 95% Threshold", min: 1, max: 30, unit: "%", default: 15 },
  { key: "health_score", label: "Min Health Score", min: 0, max: 100, unit: "", default: 50 },
  { key: "volatility", label: "Volatility Threshold", min: 0.5, max: 10, unit: "%", step: 0.5, default: 3 },
  { key: "cvar", label: "CVaR Threshold", min: 1, max: 40, unit: "%", default: 20 },
];

export default function AlertConfig() {
  const [values, setValues] = useState(() => {
    try {
      const config = JSON.parse(localStorage.getItem("liverisk_alert_config") || "{}");
      return config.values || {};
    } catch { return {}; }
  });
  const [enabled, setEnabled] = useState(() => {
    try {
      const config = JSON.parse(localStorage.getItem("liverisk_alert_config") || "{}");
      return config.enabled || {};
    } catch { return {}; }
  });
  const [testing, setTesting] = useState(false);
  const [saved, setSaved] = useState(false);
  const [notification, setNotification] = useState(null);

  const handleSlider = (key, val) => {
    setValues((prev) => ({ ...prev, [key]: parseFloat(val) }));
  };

  const handleToggle = (key) => {
    setEnabled((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setSaved(false);
    try {
      const baseUrl = getApiBaseUrl();
      const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
      const token = localStorage.getItem("liverisk_token");

      await Promise.all(
        ALERTS.filter((a) => enabled[a.key]).map((alert) =>
          fetch(`${baseUrl}/agent/alerts`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              user_id: user,
              metric: alert.key,
              threshold: values[alert.key] || alert.default,
            }),
          })
        )
      );

      localStorage.setItem(
        "liverisk_alert_config",
        JSON.stringify({ values, enabled })
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error("Failed to save alerts:", error);
    }
  };

  const handleTestAlert = async () => {
    setTesting(true);
    try {
      const baseUrl = getApiBaseUrl();
      const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
      const token = localStorage.getItem("liverisk_token");

      const res = await fetch(`${baseUrl}/agent/alerts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          user_id: user,
          metric: "health_score",
          threshold: 100,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setNotification("Test alert configured!");
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (error) {
      console.error("Test alert failed:", error);
    }
    setTesting(false);
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "0 16px" }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#e4e4e7" }}>
          Alert Configuration
        </h2>
        <p style={{ margin: 0, fontSize: 11, color: "#71717a" }}>
          Set thresholds for automatic risk alerts via WhatsApp and email
        </p>
      </div>

      {ALERTS.map((alert) => {
        const val = values[alert.key] !== undefined ? values[alert.key] : alert.default;
        const isEnabled = enabled[alert.key] || false;

        return (
          <div
            key={alert.key}
            style={{
              background: "#14141a",
              border: "1px solid #27272a",
              borderRadius: 12,
              padding: 16,
              marginBottom: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <div>
                <h3
                  style={{
                    margin: 0,
                    fontSize: 14,
                    fontWeight: 600,
                    color: "#e4e4e7",
                  }}
                >
                  {alert.label}
                </h3>
                <p style={{ margin: 0, fontSize: 11, color: "#71717a" }}>
                  Threshold: {val}{alert.unit}
                </p>
              </div>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  cursor: "pointer",
                  fontSize: 12,
                  color: "#a1a1aa",
                }}
              >
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={() => handleToggle(alert.key)}
                  style={{ accentColor: "#00e676", width: 14, height: 14 }}
                />
                Active
              </label>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 11, color: "#71717a", minWidth: 30 }}>
                {alert.min}{alert.unit}
              </span>
              <input
                type="range"
                min={alert.min}
                max={alert.max}
                step={alert.step || 1}
                value={val}
                onChange={(e) => handleSlider(alert.key, e.target.value)}
                disabled={!isEnabled}
                style={{
                  flex: 1,
                  height: 4,
                  appearance: "none",
                  background: isEnabled
                    ? "linear-gradient(90deg, #22c55e, #f59e0b, #ef4444)"
                    : "#27272a",
                  borderRadius: 2,
                  outline: "none",
                  cursor: isEnabled ? "pointer" : "not-allowed",
                }}
              />
              <span style={{ fontSize: 11, color: "#71717a", minWidth: 30 }}>
                {alert.max}{alert.unit}
              </span>
            </div>

            <div
              style={{
                marginTop: 8,
                display: "flex",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  padding: "2px 10px",
                  borderRadius: 12,
                  fontSize: 13,
                  fontWeight: 600,
                  color: isEnabled
                    ? val >= 75 && alert.key === "health_score"
                      ? "#00e676"
                      : val <= 10 && alert.key !== "health_score"
                      ? "#00e676"
                      : "#ef4444"
                    : "#71717a",
                  background: isEnabled ? "#22c55e10" : "transparent",
                }}
              >
                {val}{alert.unit}
              </div>
            </div>
          </div>
        );
      })}

      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <button
          onClick={handleSave}
          style={{
            flex: 1,
            background: "#00e676",
            color: "#000",
            fontWeight: 600,
            padding: "10px 20px",
            borderRadius: 8,
            border: "none",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {saved ? "Saved!" : "Save Alert Settings"}
        </button>
        <button
          onClick={handleTestAlert}
          disabled={testing}
          style={{
            background: "transparent",
            color: "#f59e0b",
            border: "1px solid #f59e0b30",
            padding: "10px 20px",
            borderRadius: 8,
            cursor: testing ? "not-allowed" : "pointer",
            fontSize: 13,
            opacity: testing ? 0.5 : 1,
          }}
        >
          {testing ? "Testing..." : "Test Alert"}
        </button>
      </div>

      {notification && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 9999,
          padding: "12px 20px", borderRadius: 12, fontSize: 13, fontWeight: 500,
          background: "rgba(0,230,118,0.12)",
          border: "1px solid rgba(0,230,118,0.25)",
          color: "#00e676",
          backdropFilter: "blur(20px)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
          animation: "slideUp 0.3s ease",
        }}>
          {notification}
        </div>
      )}
    </div>
  );
}
