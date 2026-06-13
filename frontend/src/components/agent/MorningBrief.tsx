"use client";

/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import SafeMarkdown from "@/lib/markdown";

export default function MorningBrief() {
  const [briefs, setBriefs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [accountability, setAccountability] = useState("");
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState(null);

  const loadLatestBrief = useCallback(async () => { // eslint-disable-line react-hooks/exhaustive-deps
    setLoading(true);
    try {
      const baseUrl = getApiBaseUrl();
      const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
      const token = localStorage.getItem("liverisk_token");

      const res = await fetch(`${baseUrl}/agent/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ user_id: user }),
      });
      const data = await res.json();
      if (data.report_markdown) {
        setBriefs((prev) => {
          const latest = {
            date: new Date().toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
            }),
            content: data.report_markdown.slice(0, 500) + "...",
            health: data.health_score,
          };
          if (prev.length > 0 && prev[0].date === latest.date) {
            return [latest, ...prev.slice(1)];
          }
          return [latest, ...prev.slice(0, 6)];
        });
      }
    } catch (error) {
      console.error("Failed to load brief:", error);
    }
    setLoading(false);
  });

  const loadAccountability = useCallback(async () => { // eslint-disable-line react-hooks/exhaustive-deps
    try {
      const baseUrl = getApiBaseUrl();
      const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
      const token = localStorage.getItem("liverisk_token");

      const res = await fetch(`${baseUrl}/agent/accountability/${user}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setAccountability(data.accountability || "");
    } catch (error) {
      console.error("Failed to load accountability:", error);
    }
  });

  const loadSubscription = useCallback(async () => { // eslint-disable-line react-hooks/exhaustive-deps
    try {
      const stored = localStorage.getItem("liverisk_brief_config");
      if (stored) {
        const config = JSON.parse(stored);
        setEnabled(config.enabled || false);
        setPhone(config.phone || "");
        setEmail(config.email || "");
      }
    } catch {
      // ignore
    }
  });

  useEffect(() => {
    loadLatestBrief();
    loadAccountability();
    loadSubscription();
  }, [loadLatestBrief, loadAccountability, loadSubscription]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const baseUrl = getApiBaseUrl();
      const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
      const token = localStorage.getItem("liverisk_token");

      const res = await fetch(`${baseUrl}/agent/subscribe`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          user_id: user,
          email,
          phone,
          tier: "pro",
        }),
      });
      const data = await res.json();
      if (data.success) {
        localStorage.setItem(
          "liverisk_brief_config",
          JSON.stringify({ enabled, phone, email })
        );
        setNotification("Brief preferences saved! You'll receive morning briefs at 6:30 AM.");
        setTimeout(() => setNotification(null), 4000);
      }
    } catch (error) {
      console.error("Failed to save subscription:", error);
    }
    setSaving(false);
  };

  const handleToggle = async () => {
    const baseUrl = getApiBaseUrl();
    const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
    const token = localStorage.getItem("liverisk_token");

    if (enabled) {
      await fetch(`${baseUrl}/agent/unsubscribe/${user}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    }
    setEnabled(!enabled);
  };

  const handleTestAlert = async () => {
    const baseUrl = getApiBaseUrl();
    const user = localStorage.getItem("liverisk_user_id") || localStorage.getItem("liverisk_user") || "0";
    const token = localStorage.getItem("liverisk_token");

    await fetch(`${baseUrl}/agent/alerts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        user_id: user,
        metric: "health_score",
        threshold: 50,
      }),
    });
    setNotification("Test alert configured for health_score < 50");
    setTimeout(() => setNotification(null), 3000);
  };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "0 16px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#e4e4e7" }}>
            Morning Briefs
          </h2>
          <p style={{ margin: 0, fontSize: 11, color: "#71717a" }}>
            Daily portfolio intelligence at 6:30 AM
          </p>
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            cursor: "pointer",
            fontSize: 13,
            color: "#a1a1aa",
          }}
        >
          <input
            type="checkbox"
            checked={enabled}
            onChange={handleToggle}
            style={{ accentColor: "#00e676", width: 16, height: 16 }}
          />
          {enabled ? "Active" : "Paused"}
        </label>
      </div>

      {/* Subscription Configuration */}
      {enabled && (
        <div
          style={{
            background: "#14141a",
            border: "1px solid #27272a",
            borderRadius: 12,
            padding: 16,
            marginBottom: 20,
          }}
        >
          <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#00e676" }}>
            Delivery Settings
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <input
              type="email"
              placeholder="Email for briefs"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ fontSize: 13, padding: "8px 12px" }}
            />
            <input
              type="tel"
              placeholder="WhatsApp number (with country code, e.g. +919876543210)"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              style={{ fontSize: 13, padding: "8px 12px" }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  flex: 1,
                  background: "#00e676",
                  color: "#000",
                  fontWeight: 600,
                  padding: "8px 16px",
                  borderRadius: 8,
                  border: "none",
                  cursor: saving ? "not-allowed" : "pointer",
                  opacity: saving ? 0.5 : 1,
                  fontSize: 12,
                }}
              >
                {saving ? "Saving..." : "Save Preferences"}
              </button>
              <button
                onClick={handleTestAlert}
                style={{
                  background: "transparent",
                  color: "#f59e0b",
                  border: "1px solid #f59e0b30",
                  padding: "8px 16px",
                  borderRadius: 8,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                Set Test Alert
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Latest Brief */}
      <div
        style={{
          background: "#14141a",
          border: "1px solid #27272a",
          borderRadius: 12,
          padding: 16,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 8,
          }}
        >
          <h3 style={{ margin: 0, fontSize: 14, color: "#e4e4e7" }}>
            Latest Brief
          </h3>
          <button
            onClick={loadLatestBrief}
            disabled={loading}
            style={{
              background: "transparent",
              color: "#00e676",
              border: "1px solid #00e67630",
              padding: "4px 12px",
              borderRadius: 6,
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: 11,
              opacity: loading ? 0.5 : 1,
            }}
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
        {briefs.length > 0 ? (
          <div>
            <div
              style={{
                fontSize: 11,
                color: "#71717a",
                marginBottom: 8,
              }}
            >
              {briefs[0].date} · Health:{" "}
              <span style={{ color: briefs[0].health >= 75 ? "#00e676" : "#f59e0b" }}>
                {briefs[0].health}/100
              </span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.6, color: "#a1a1aa" }}>
              <SafeMarkdown content={briefs[0].content} />
            </div>
          </div>
        ) : (
          <p style={{ color: "#71717a", fontSize: 13, margin: 0 }}>
            No briefs generated yet. Enable morning briefs above to get daily updates.
          </p>
        )}
      </div>

      {/* Accountability */}
      {accountability && (
        <div
          style={{
            background: "#14141a",
            border: "1px solid #27272a",
            borderRadius: 12,
            padding: 16,
            marginBottom: 20,
          }}
        >
          <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#3b82f6" }}>
            Accountability
          </h3>
          <div style={{ fontSize: 13, lineHeight: 1.6, color: "#a1a1aa" }}>
            <SafeMarkdown content={accountability} />
          </div>
        </div>
      )}

      {/* Brief Timeline */}
      {briefs.length > 1 && (
        <div
          style={{
            background: "#14141a",
            border: "1px solid #27272a",
            borderRadius: 12,
            padding: 16,
          }}
        >
          <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#e4e4e7" }}>
            Past Briefs
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {briefs.slice(1).map((brief, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "8px 0",
                  borderBottom: "1px solid #27272a",
                  fontSize: 13,
                }}
              >
                <span style={{ color: "#a1a1aa" }}>{brief.date}</span>
                <span
                  style={{
                    color: brief.health >= 75 ? "#00e676" : "#f59e0b",
                    fontWeight: 500,
                  }}
                >
                  {brief.health}/100
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

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
