"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const features = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
      </svg>
    ),
    title: "Pathfinder",
    desc: "Explores thousands of possible market paths your portfolio could take — mapping out every twist and turn so you see the risks that others miss.",
    tag: "10K paths",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
      </svg>
    ),
    title: "Market Mood",
    desc: "Scans thousands of financial headlines in seconds to read the market's emotional temperature — telling you whether fear or greed is driving the room.",
    tag: "Live",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
      </svg>
    ),
    title: "Horizon Scan",
    desc: "Looks ahead 60 trading days by learning the rhythm of your portfolio's own history — no crystal ball, just pattern recognition at scale.",
    tag: "60-day",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
    title: "Armor Test",
    desc: "Drops your portfolio into real historical market storms — 2008 crash, COVID panic, rate hike routs — to show you exactly how much punishment it can take.",
    tag: "Stress",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
      </svg>
    ),
    title: "Proof Track",
    desc: "Checks our risk predictions against 12 years of real market chaos — from COVID to the banking crisis — and grades us on how well we would have protected you.",
    tag: "12yr",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
      </svg>
    ),
    title: "Live Wire",
    desc: "Pulls real-time pricing and breaking news directly from institutional-grade financial feeds — so your risk analysis is always working with what's happening right now.",
    tag: "Real-time",
  },
];

const stats = [
  { value: "10,000", label: "Market Paths Explored" },
  { value: "60", label: "Day Forecast Horizon" },
  { value: "4", label: "Real Crises Tested" },
  { value: "12", label: "Years of Data Analyzed" },
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "bg-zinc-900/90 backdrop-blur-lg border-b border-zinc-800" : "bg-transparent"}`}>
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-4 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-white tracking-tight">
            LiveRisk
          </Link>
          <div className="flex items-center gap-6">
            <a href="#features" className="text-sm text-zinc-400 hover:text-white transition-colors">Features</a>
            <a href="#why" className="text-sm text-zinc-400 hover:text-white transition-colors">Why LiveRisk</a>
            <Link href="/login" className="text-sm font-semibold text-white bg-green-500 hover:bg-green-400 px-5 py-2 rounded-lg transition-all hover:shadow-lg hover:shadow-green-500/20">
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-green-950/20 via-transparent to-zinc-900" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-green-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl" />
        <div className="absolute inset-0">
          <div className="absolute top-20 left-10 w-px h-40 bg-gradient-to-b from-green-500/20 to-transparent" />
          <div className="absolute bottom-20 right-10 w-px h-60 bg-gradient-to-t from-green-500/20 to-transparent" />
        </div>
        <div className="relative z-10 text-center px-4 max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-green-900/50 bg-green-950/30 text-green-400 text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Institutional-Grade Risk Intelligence
          </div>
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white tracking-tight leading-tight mb-6">
            See Risk Before<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-300">
              It Moves
            </span>
          </h1>
          <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-6 leading-relaxed">
            LiveRisk turns hidden portfolio risks into a clear dashboard — mapping thousands of possible market outcomes,
            reading financial news sentiment, forecasting trends, and stress-testing against real crashes. All in one place.
          </p>
          <div className="flex items-center justify-center gap-4 mb-8">
            <span className="inline-flex items-center gap-1.5 text-xs text-zinc-600 bg-zinc-800/50 px-3 py-1.5 rounded-full border border-zinc-700/50">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Powered by Wire <span className="text-zinc-500">(Anakin)</span>
            </span>
          </div>
          <div className="flex items-center justify-center gap-4">
            <Link href="/login" className="text-base font-semibold text-black bg-green-500 hover:bg-green-400 px-8 py-3.5 rounded-lg transition-all hover:shadow-xl hover:shadow-green-500/25">
              Start Free Analysis
            </Link>
            <a href="#features" className="text-base font-medium text-zinc-300 border border-zinc-700 hover:border-zinc-500 px-8 py-3.5 rounded-lg transition-all">
              Explore Features
            </a>
          </div>
          <div className="flex items-center justify-center gap-6 mt-10 text-xs text-zinc-600">
            <span className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-green-500" />No credit card</span>
            <span className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-green-500" />JWT secured</span>
            <span className="flex items-center gap-1.5"><span className="w-1 h-1 rounded-full bg-green-500" />Instant results</span>
          </div>
        </div>
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <svg className="w-5 h-5 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 border-y border-zinc-800/50">
        <div className="max-w-6xl mx-auto px-4 md:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-1">{s.value}</div>
                <div className="text-sm text-zinc-500">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-4 md:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-green-900/50 bg-green-950/30 text-green-400 text-xs font-medium mb-4">
              Everything You Need
            </div>
              <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-4">
              Six Powers. One Dashboard.
            </h2>
            <p className="text-zinc-400 max-w-xl mx-auto">
              Every risk tool you need to know what your portfolio is really exposed to — no complex models to understand, just clear answers.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div key={f.title} className="group relative p-6 rounded-xl border border-zinc-800 hover:border-zinc-700 bg-zinc-900/50 transition-all hover:bg-zinc-900/80">
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-green-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex items-start justify-between mb-3">
                  <div className="text-green-400">{f.icon}</div>
                  <span className="text-[10px] font-semibold text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">{f.tag}</span>
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why LiveRisk */}
      <section id="why" className="py-20 md:py-28 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-green-950/10 via-transparent to-transparent" />
        <div className="max-w-6xl mx-auto px-4 md:px-8 relative z-10">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-green-900/50 bg-green-950/30 text-green-400 text-xs font-medium mb-4">
                Our Mission
              </div>
              <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-6">
                Your Portfolio Has a Blind Spot. We Illuminate It.
              </h2>
              <div className="space-y-4 text-zinc-400 text-base leading-relaxed">
                <p>
                  Every day, retail investors make portfolio decisions without the risk analytics that
                  institutions take for granted. Monte Carlo simulations, Value-at-Risk models, and
                  sentiment analysis have been locked behind Bloomberg terminals and prop desk budgets
                  for decades.
                </p>
                <p>
                  LiveRisk exists to change that. We started by asking a simple question: why can&apos;t
                  anyone with a browser get the same quality of risk intelligence as a hedge fund?
                </p>
                <p>
                  The answer is that now they can. LiveRisk explores thousands of possible market futures,
                  reads the emotional temperature of financial news, forecasts where your portfolio is heading,
                  and tests it against 12 years of real market storms — all in under 30 seconds.
                </p>
              </div>
            </div>
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-2xl blur-xl" />
              <div className="relative bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-2 h-2 rounded-full bg-red-500" />
                  <div className="w-2 h-2 rounded-full bg-yellow-500" />
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                </div>
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">95% VaR</span>
                    <span className="text-green-400 font-bold">$42,350</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">CVaR</span>
                    <span className="text-red-400 font-bold">$68,120</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Sentiment Score</span>
                    <span className="text-yellow-400 font-bold">+0.324</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Loss Probability</span>
                    <span className="text-zinc-300 font-bold">38%</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-950/30 border border-green-900/30 rounded-lg">
                    <span className="text-zinc-400">Backtest Grade</span>
                    <span className="text-green-400 font-bold text-base">A</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 md:py-28 border-t border-zinc-800/50">
        <div className="max-w-6xl mx-auto px-4 md:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-green-900/50 bg-green-950/30 text-green-400 text-xs font-medium mb-4">
              Three Steps
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-4">
              From Tickers to Risk Metrics in Seconds
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: "01", title: "Enter Your Portfolio", desc: "Type in your tickers and allocation weights. Any combination of stocks, ETFs, or indices — from a single position to a diversified multi-asset portfolio." },
              { step: "02", title: "AI Analyzes Every Angle", desc: "Pathfinder explores 10,000 possible market outcomes. Market Mood reads the news. Horizon Scan looks 60 days ahead. Armor Test stress-tests against real crashes. All in parallel." },
              { step: "03", title: "Get Your Risk Profile", desc: "VaR, CVaR, sentiment-adjusted risk, stress breaches, and a letter-grade backtest validation. Every number comes with context so you know what to act on." },
            ].map((s) => (
              <div key={s.step} className="text-center">
                <div className="text-6xl font-bold text-green-500/20 mb-4">{s.step}</div>
                <h3 className="text-lg font-semibold text-white mb-3">{s.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed max-w-sm mx-auto">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 md:py-28 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-green-950/10 to-green-950/20" />
        <div className="max-w-3xl mx-auto px-4 md:px-8 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-green-900/50 bg-green-950/30 text-green-400 text-xs font-medium mb-4">
            Get Started
          </div>
          <h2 className="text-4xl md:text-6xl font-bold text-white tracking-tight mb-6">
            Your Portfolio Deserves<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-300">
              Better Intelligence
            </span>
          </h2>
          <p className="text-zinc-400 mb-8 max-w-lg mx-auto">
            No setup. No configuration. Just enter your tickers and see what institutional risk models reveal about your portfolio.
          </p>
          <Link href="/login" className="inline-block text-base font-semibold text-black bg-green-500 hover:bg-green-400 px-10 py-4 rounded-lg transition-all hover:shadow-xl hover:shadow-green-500/25">
            Analyze Your Portfolio Now
          </Link>
          <p className="text-xs text-zinc-600 mt-4">Shared password: <code className="text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded select-all">riskmaster2024</code></p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-8">
        <div className="max-w-6xl mx-auto px-4 md:px-8 flex items-center justify-between">
          <span className="text-sm font-bold text-white">LiveRisk</span>
          <span className="text-xs text-zinc-600">&copy; 2026 LiveRisk. Financial Risk Intelligence.</span>
        </div>
      </footer>
    </div>
  );
}
