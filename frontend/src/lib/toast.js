"use client";

import { useState, useCallback } from "react";

let toastId = 0;

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "success", duration = 3000) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);

  const ToastContainer = () => {
    if (toasts.length === 0) return null;
    return (
      <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, display: "flex", flexDirection: "column", gap: 8 }}>
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              padding: "12px 20px",
              borderRadius: 12,
              fontSize: 13,
              fontWeight: 500,
              background: t.type === "success" ? "rgba(0,230,118,0.12)" : t.type === "error" ? "rgba(255,82,82,0.12)" : "rgba(68,138,255,0.12)",
              border: t.type === "success" ? "1px solid rgba(0,230,118,0.25)" : t.type === "error" ? "1px solid rgba(255,82,82,0.25)" : "1px solid rgba(68,138,255,0.25)",
              color: t.type === "success" ? "#00e676" : t.type === "error" ? "#ff5252" : "#448aff",
              backdropFilter: "blur(20px)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
              animation: "slideUp 0.3s ease",
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    );
  };

  return { toasts, addToast, ToastContainer };
}
