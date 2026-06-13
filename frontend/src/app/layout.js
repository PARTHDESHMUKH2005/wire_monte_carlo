"use client";

/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import "./globals.css";

function getAuth() {
  if (typeof window === "undefined") return { user: "", isAuth: false };
  const u = localStorage.getItem("liverisk_user");
  const t = localStorage.getItem("liverisk_token");
  return { user: u || "", isAuth: !!(u && t) };
}

export default function RootLayout({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState(() => getAuth().user);
  const [isAuth, setIsAuth] = useState(() => getAuth().isAuth);

  const syncAuth = useCallback(() => {
    const { user: u, isAuth: a } = getAuth();
    setUser(u);
    setIsAuth(a);
  }, []);

  useEffect(() => { syncAuth(); }, [pathname, syncAuth]);

  const handleLogout = () => {
    localStorage.removeItem("liverisk_token");
    localStorage.removeItem("liverisk_user");
    localStorage.removeItem("liverisk_user_id");
    localStorage.removeItem("liverisk_email");
    localStorage.removeItem("liverisk_replay");
    localStorage.removeItem("liverisk_last_analysis");
    setIsAuth(false);
    setUser("");
    router.push("/");
  };

  const showNav = pathname === "/vera";

  return (
    <html lang="en" className="h-full">
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="application-name" content="LiveRisk" />
        <title>LiveRisk — Financial Risk Intelligence</title>
      </head>
      <body className="min-h-full bg-[#050508]" role="application">
        {showNav && isAuth && (
          <nav className="border-b border-[rgba(255,255,255,0.04)] bg-[rgba(5,5,8,0.8)] backdrop-blur-2xl">
            <div className="max-w-7xl mx-auto px-6 md:px-10 py-4 flex items-center justify-between">
              <Link href="/vera" className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-black font-extrabold text-[10px]">LR</span>
                <span className="text-sm font-bold text-white tracking-tight">LiveRisk</span>
              </Link>
              <div className="flex items-center gap-4">
                <span className="text-xs text-[rgba(255,255,255,0.3)]">
                  Signed in as <span className="text-[rgba(255,255,255,0.6)] font-medium">{user}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.4)] px-4 py-2 rounded-lg transition-all"
                >
                  LOGOUT
                </button>
              </div>
            </div>
          </nav>
        )}
        {children}
      </body>
    </html>
  );
}
