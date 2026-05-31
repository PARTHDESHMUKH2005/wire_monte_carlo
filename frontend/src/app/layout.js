"use client";

import { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import "./globals.css";

export default function RootLayout({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState("");
  const [isAuth, setIsAuth] = useState(false);

  useEffect(() => {
    const u = localStorage.getItem("liverisk_user");
    const t = localStorage.getItem("liverisk_token");
    if (u && t) {
      setUser(u);
      setIsAuth(true);
    }
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("liverisk_token");
    localStorage.removeItem("liverisk_user");
    localStorage.removeItem("liverisk_replay");
    setIsAuth(false);
    setUser("");
    router.push("/");
  };

  const showNav = pathname === "/dashboard" || pathname === "/history";

  return (
    <html lang="en" className="h-full">
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="application-name" content="LiveRisk" />
      </head>
      <body className="min-h-full" role="application">
        {showNav && isAuth && (
          <nav className="border-b border-zinc-800 bg-zinc-900/50">
            <div className="max-w-6xl mx-auto px-4 md:px-8 py-3 flex items-center justify-between">
              <div className="flex items-center gap-6">
                <a
                  href="/dashboard"
                  className={`text-sm font-medium transition-colors ${
                    pathname === "/dashboard" ? "text-green-400" : "text-zinc-400 hover:text-white"
                  }`}
                >
                  Dashboard
                </a>
                <a
                  href="/history"
                  className={`text-sm font-medium transition-colors ${
                    pathname === "/history" ? "text-green-400" : "text-zinc-400 hover:text-white"
                  }`}
                >
                  History
                </a>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-500">
                  Signed in as <span className="text-zinc-300 font-medium">{user}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-400 px-3 py-1.5 rounded-md transition-colors"
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
