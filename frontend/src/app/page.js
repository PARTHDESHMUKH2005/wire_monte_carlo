"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const features = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
      </svg>
    ),
    title: "Pathfinder",
    desc: "Explores thousands of possible market paths your portfolio could take — mapping out every twist and turn so you see the risks others miss.",
    tag: "10K paths",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
      </svg>
    ),
    title: "Market Mood",
    desc: "Scans thousands of financial headlines to read the market's emotional temperature — telling you whether fear or greed is driving the room.",
    tag: "Live",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
    title: "Armor Test",
    desc: "Drops your portfolio into real historical storms — 2008 crash, COVID panic, rate hikes — to show you exactly how much punishment it can take.",
    tag: "Stress",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
      </svg>
    ),
    title: "Horizon Scan",
    desc: "Looks ahead 60 trading days using LSTM deep learning — pattern recognition at scale, trained on your portfolio's own history.",
    tag: "60-day",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
      </svg>
    ),
    title: "Proof Track",
    desc: "Checks predictions against 12 years of real market chaos — from COVID to the banking crisis — and grades how well we protect you.",
    tag: "12yr",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
      </svg>
    ),
    title: "Live Wire",
    desc: "Pulls real-time pricing and breaking news from institutional-grade feeds — so your analysis is always working with what's happening right now.",
    tag: "Real-time",
  },
];

const pricingPlans = [
  {
    name: "Starter",
    price: "Free",
    period: "forever",
    desc: "For individual investors exploring risk intelligence.",
    features: [
      "1 portfolio analysis",
      "Monte Carlo 10K simulation",
      "FinBERT sentiment analysis",
      "60-day LSTM forecast",
      "Basic risk metrics (VaR, CVaR)",
      "Email support",
    ],
    cta: "Get Started",
    featured: false,
    highlight: "",
  },
  {
    name: "Professional",
    price: "$29",
    period: "/month",
    desc: "For serious investors who want institutional-grade risk tools.",
    features: [
      "Up to 5 portfolios",
      "Everything in Starter",
      "Stress testing (5 crisis scenarios)",
      "Backtest vs 12 years of history",
      "Email reports to your Gmail",
      "Alert thresholds & notifications",
      "Full chat history with Vera AI",
      "Priority email support",
    ],
    cta: "Start Free Trial",
    featured: true,
    highlight: "Most Popular",
  },
  {
    name: "Enterprise",
    price: "$99",
    period: "/month",
    desc: "For teams and professionals who need the full arsenal.",
    features: [
      "Unlimited portfolios",
      "Everything in Professional",
      "Real-time alerts (WhatsApp + Email)",
      "Morning briefs at 6:30 AM",
      "API access for custom integrations",
      "Dedicated account manager",
      "White-label reports",
      "99.9% uptime SLA",
    ],
    cta: "Contact Sales",
    featured: false,
    highlight: "",
  },
];

const stats = [
  { value: "10,000", label: "Market Paths Explored" },
  { value: "60", label: "Day LSTM Forecast Horizon" },
  { value: "5", label: "Real Crises Tested" },
  { value: "12", label: "Years of Data Analyzed" },
];

const BUILDINGS = [
  { left: "2%", width: "3%", height: "55%", windows: 8 },
  { left: "6%", width: "4%", height: "70%", windows: 12 },
  { left: "11%", width: "2.5%", height: "45%", windows: 6 },
  { left: "14.5%", width: "3.5%", height: "80%", windows: 15 },
  { left: "19%", width: "4%", height: "60%", windows: 10 },
  { left: "24%", width: "5%", height: "85%", windows: 18 },
  { left: "30%", width: "3%", height: "50%", windows: 7 },
  { left: "34%", width: "4.5%", height: "90%", windows: 20 },
  { left: "39.5%", width: "3%", height: "65%", windows: 11 },
  { left: "43.5%", width: "5%", height: "75%", windows: 14 },
  { left: "49.5%", width: "2%", height: "40%", windows: 5 },
  { left: "52.5%", width: "4%", height: "88%", windows: 19 },
  { left: "57.5%", width: "3.5%", height: "60%", windows: 9 },
  { left: "62%", width: "5%", height: "78%", windows: 16 },
  { left: "68%", width: "3%", height: "55%", windows: 8 },
  { left: "72%", width: "4.5%", height: "92%", windows: 22 },
  { left: "77.5%", width: "3%", height: "48%", windows: 6 },
  { left: "81.5%", width: "4%", height: "72%", windows: 13 },
  { left: "86.5%", width: "5%", height: "82%", windows: 17 },
  { left: "92.5%", width: "3.5%", height: "58%", windows: 9 },
  { left: "97%", width: "3%", height: "65%", windows: 10 },
];

function useClientRandom() {
  const [particles, setParticles] = useState([]);
  const [buildingWindows, setBuildingWindows] = useState([]);

  useEffect(() => {
    setParticles(
      Array.from({ length: 20 }).map(() => ({
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        size: 2 + Math.random() * 3,
        delay: `${Math.random() * 5}s`,
        duration: `${4 + Math.random() * 4}s`,
      }))
    );
    setBuildingWindows(
      BUILDINGS.map((b) => {
        const cols = Math.floor(b.width / 0.8);
        const rows = b.windows;
        const w = [];
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const lit = Math.random() > 0.6;
            w.push({ lit, left: `${12 + c * 22}%`, top: `${8 + r * 10}%`, opacity: lit ? 0.3 + Math.random() * 0.4 : 0.05 });
          }
        }
        return w;
      })
    );
  }, []);

  return { particles, buildingWindows };
}

function BuildingBackground({ windows }) {
  return (
    <div className="building-silhouette" aria-hidden="true">
      {BUILDINGS.map((b, i) => {
        const gradientDir = 180 + (i % 3) * 30;
        return (
          <div
            key={i}
            className="building"
            style={{
              left: b.left,
              width: b.width,
              height: b.height,
              background: `linear-gradient(${gradientDir}deg, rgba(0,230,118,0.03) 0%, transparent 70%)`,
            }}
          >
            {(windows[i] || []).map((w, j) => (
              <div
                key={j}
                className={`building-window ${w.lit ? "lit" : ""}`}
                style={{ left: w.left, top: w.top, opacity: w.opacity }}
              />
            ))}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: "1px",
                background: "linear-gradient(90deg, transparent, rgba(0,230,118,0.06), transparent)",
              }}
            />
          </div>
        );
      })}
    </div>
  );
}

function FloatingParticles({ particles }) {
  if (particles.length === 0) return null;
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
      {particles.map((p, i) => (
        <div
          key={i}
          className="animate-float"
          style={{
            position: "absolute",
            left: p.left,
            top: p.top,
            width: `${p.size}px`,
            height: `${p.size}px`,
            borderRadius: "50%",
            background: "rgba(0, 230, 118, 0.08)",
            animationDelay: p.delay,
            animationDuration: p.duration,
          }}
        />
      ))}
    </div>
  );
}

function Section({ id, className = "", children, style = {} }) {
  return (
    <section id={id} className={className} style={{ width: "100%", ...style }}>
      {children}
    </section>
  );
}

function Container({ children, maxW = 1280, style = {} }) {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: maxW,
        marginLeft: "auto",
        marginRight: "auto",
        paddingLeft: 24,
        paddingRight: 24,
        ...style,
      }}
      className="md:px-10"
    >
      {children}
    </div>
  );
}

function Pill({ children }) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 16px",
        borderRadius: 9999,
        border: "1px solid rgba(0,230,118,0.2)",
        background: "rgba(0,230,118,0.04)",
        color: "#00e676",
        fontSize: 12,
        fontWeight: 500,
        marginBottom: 24,
      }}
    >
      {children}
    </div>
  );
}

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { particles, buildingWindows } = useClientRandom();

  useEffect(() => {
    setMounted(true);
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navBg = scrolled
    ? "rgba(5,5,8,0.85)"
    : "transparent";
  const navBorder = scrolled
    ? "1px solid rgba(255,255,255,0.05)"
    : "1px solid transparent";

  return (
    <div style={{ minHeight: "100vh", background: "#050508", width: "100%" }}>
      {mounted && <FloatingParticles particles={particles} />}

      {/* Navigation */}
      <nav
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          background: navBg,
          backdropFilter: scrolled ? "blur(32px)" : "none",
          borderBottom: navBorder,
          transition: "all 0.5s",
        }}
      >
        <Container>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              paddingTop: 20,
              paddingBottom: 20,
            }}
          >
            <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 20, fontWeight: 700, color: "#fff", textDecoration: "none" }}>
              <span style={{ width: 32, height: 32, borderRadius: 8, background: "#00e676", display: "flex", alignItems: "center", justifyContent: "center", color: "#000", fontWeight: 800, fontSize: 14 }}>LR</span>
              LiveRisk
            </Link>
            <div className="nav-links" style={{ alignItems: "center", gap: 32 }}>
              <a href="#features" style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", textDecoration: "none", transition: "color 0.2s" }}>Features</a>
              <a href="#pricing" style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", textDecoration: "none", transition: "color 0.2s" }}>Pricing</a>
              <a href="#why" style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", textDecoration: "none", transition: "color 0.2s" }}>Why LiveRisk</a>
            </div>
            <Link
              href="/login"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                fontWeight: 600,
                color: "#000",
                background: "#00e676",
                padding: "10px 24px",
                borderRadius: 12,
                textDecoration: "none",
                transition: "all 0.2s",
              }}
            >
              Sign In
            </Link>
          </div>
        </Container>
      </nav>

      {/* Hero */}
      <Section className="hero-gradient" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
        {mounted && <BuildingBackground windows={buildingWindows} />}
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, transparent, transparent, #050508)", zIndex: 1 }} />
        <div style={{ position: "relative", zIndex: 10, textAlign: "center", padding: "0 24px" }}>
          <Container maxW={1024} style={{ textAlign: "center" }}>
            <Pill>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#00e676" }} />
              Institutional-Grade Risk Intelligence
            </Pill>
            <h1 style={{ fontSize: "clamp(2.5rem, 8vw, 6rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", lineHeight: 0.95, marginBottom: 32 }}>
              See Risk Before<br />
              <span className="gradient-text">It Moves</span>
            </h1>
            <p style={{ fontSize: "clamp(1rem, 2vw, 1.25rem)", color: "rgba(255,255,255,0.4)", maxWidth: 640, margin: "0 auto 40px", lineHeight: 1.7 }}>
              LiveRisk turns hidden portfolio risks into a clear dashboard — mapping thousands of possible market outcomes,
              reading financial news sentiment, forecasting with LSTM deep learning, and stress-testing against real crashes.
            </p>
            <div className="btn-row">
              <Link
                href="/login"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 16,
                  fontWeight: 600,
                  color: "#000",
                  background: "#00e676",
                  padding: "16px 40px",
                  borderRadius: 16,
                  textDecoration: "none",
                  transition: "all 0.2s",
                }}
              >
                Start Free Analysis
              </Link>
              <a
                href="#pricing"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 16,
                  fontWeight: 500,
                  color: "#fff",
                  padding: "16px 40px",
                  borderRadius: 16,
                  textDecoration: "none",
                  border: "1px solid rgba(255,255,255,0.08)",
                  transition: "all 0.2s",
                }}
              >
                View Pricing
              </a>
            </div>
            <div className="hero-badges">
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span style={{ width: 4, height: 4, borderRadius: "50%", background: "#00e676" }} />No credit card</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span style={{ width: 4, height: 4, borderRadius: "50%", background: "#00e676" }} />JWT secured</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span style={{ width: 4, height: 4, borderRadius: "50%", background: "#00e676" }} />Instant results</span>
            </div>
          </Container>
        </div>
        <div style={{ position: "absolute", bottom: 32, left: "50%", transform: "translateX(-50%)", zIndex: 10 }}>
          <svg style={{ width: 20, height: 20, color: "rgba(255,255,255,0.15)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </div>
      </Section>

      {/* Stats */}
      <Section style={{ paddingTop: 96, paddingBottom: 96, borderTop: "1px solid rgba(255,255,255,0.04)", borderBottom: "1px solid rgba(255,255,255,0.04)", position: "relative", zIndex: 10 }}>
        <Container>
          <div className="grid-4">
            {stats.map((s) => (
              <div key={s.label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", marginBottom: 8 }}>{s.value}</div>
                <div style={{ fontSize: 14, color: "rgba(255,255,255,0.3)" }}>{s.label}</div>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      {/* Features */}
      <Section id="features" style={{ paddingTop: 128, paddingBottom: 128, position: "relative", zIndex: 10 }}>
        <Container>
          <div style={{ textAlign: "center", marginBottom: 96 }}>
            <Pill>Everything You Need</Pill>
            <h2 style={{ fontSize: "clamp(2rem, 5vw, 3.75rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", marginBottom: 16, lineHeight: 1.15 }}>
              Six Powers. One Platform.
            </h2>
            <p style={{ color: "rgba(255,255,255,0.4)", maxWidth: 640, margin: "0 auto", fontSize: 18, lineHeight: 1.7 }}>
              Every tool you need to know what your portfolio is really exposed to — no complex models to understand, just clear answers from Vera AI.
            </p>
          </div>
          <div className="grid-auto">
            {features.map((f) => (
              <div
                key={f.title}
                className="glass-card group"
                style={{ cursor: "default", position: "relative" }}
              >
                <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "1px", background: "linear-gradient(90deg, transparent, rgba(0,230,118,0.15), transparent)", opacity: 0 }} />
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
                  <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", color: "#00e676", padding: 10, borderRadius: 12, background: "rgba(0,230,118,0.06)", border: "1px solid rgba(0,230,118,0.08)" }}>{f.icon}</div>
                  <span style={{ display: "inline-flex", alignItems: "center", fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", background: "rgba(255,255,255,0.03)", padding: "4px 12px", borderRadius: 9999, border: "1px solid rgba(255,255,255,0.05)" }}>{f.tag}</span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#fff", marginBottom: 8 }}>{f.title}</h3>
                <p style={{ fontSize: 14, color: "rgba(255,255,255,0.4)", lineHeight: 1.7 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      {/* Why LiveRisk */}
      <Section id="why" style={{ paddingTop: 128, paddingBottom: 128, position: "relative", overflow: "hidden", zIndex: 10 }}>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, rgba(0,230,118,0.03), transparent, transparent)" }} />
        <Container style={{ position: "relative", zIndex: 10 }}>
          <div className="why-grid">
            <div>
              <Pill>Our Mission</Pill>
              <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", marginBottom: 32, lineHeight: 1.05 }}>
                Your Portfolio Has a Blind Spot.<br />
                <span className="gradient-text">We Illuminate It.</span>
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 20, color: "rgba(255,255,255,0.45)", fontSize: 16, lineHeight: 1.8 }}>
                <p>Every day, retail investors make portfolio decisions without the risk analytics that institutions take for granted. Monte Carlo simulations, Value-at-Risk models, LSTM forecasts, and sentiment analysis have been locked behind Bloomberg terminals and prop desk budgets for decades.</p>
                <p>LiveRisk exists to change that. We started by asking a simple question: why can't anyone with a browser get the same quality of risk intelligence as a hedge fund?</p>
                <p>The answer is that now they can. Vera AI explores thousands of possible market futures, reads the emotional temperature of financial news, forecasts with deep learning, and tests against 12 years of real market storms — all through natural conversation.</p>
              </div>
            </div>
            <div style={{ position: "relative" }}>
              <div style={{ position: "absolute", top: -24, right: -24, bottom: -24, left: -24, background: "linear-gradient(to right, rgba(0,230,118,0.06), transparent)", borderRadius: 24 }} />
              <div className="glass-card" style={{ position: "relative", padding: 32 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5252" }} />
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ffd740" }} />
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#00e676" }} />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {[
                    { label: "95% VaR", value: "$42,350", color: "#00e676" },
                    { label: "CVaR", value: "$68,120", color: "#ff5252" },
                    { label: "Sentiment Score", value: "+0.324", color: "#ffd740" },
                    { label: "LSTM 60d Forecast", value: "$1,089,420", color: "#448aff" },
                    { label: "Backtest Grade", value: "A", color: "#00e676", big: true },
                  ].map((item) => (
                    <div
                      key={item.label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: 16,
                        borderRadius: 12,
                        background: item.big ? "rgba(0,230,118,0.04)" : "rgba(255,255,255,0.03)",
                        border: item.big ? "1px solid rgba(0,230,118,0.1)" : "1px solid rgba(255,255,255,0.04)",
                      }}
                    >
                      <span style={{ fontSize: 14, color: "rgba(255,255,255,0.4)" }}>{item.label}</span>
                      <span style={{ color: item.color, fontWeight: 700, fontSize: item.big ? 20 : 18 }}>{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* How It Works */}
      <Section style={{ paddingTop: 128, paddingBottom: 128, borderTop: "1px solid rgba(255,255,255,0.04)", position: "relative", zIndex: 10 }}>
        <Container>
          <div style={{ textAlign: "center", marginBottom: 96 }}>
            <Pill>Three Steps</Pill>
            <h2 style={{ fontSize: "clamp(2rem, 5vw, 3.75rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", marginBottom: 16, lineHeight: 1.15 }}>
              From Tickers to Risk Metrics in Seconds
            </h2>
            <p style={{ color: "rgba(255,255,255,0.4)", maxWidth: 640, margin: "0 auto", fontSize: 18, lineHeight: 1.7 }}>
              No PhD required. Enter your holdings, and Vera AI does the rest.
            </p>
          </div>
          <div className="grid-3">
            {[
              { step: "01", title: "Enter Your Portfolio", desc: "Type in your tickers and allocation weights. Any combination of stocks, ETFs, or indices — from a single position to a diversified multi-asset portfolio." },
              { step: "02", title: "Vera AI Analyzes Every Angle", desc: "Pathfinder explores 10,000 market outcomes. Market Mood reads the news. Horizon Scan looks 60 days ahead with LSTM. Armor Test stress-tests against 5 real crashes. All in parallel." },
              { step: "03", title: "Get Your Risk Profile", desc: "VaR, CVaR, sentiment-adjusted risk, LSTM forecast, stress breaches, and a letter-grade backtest. Every number comes with context from Vera AI so you know what to act on." },
            ].map((s) => (
              <div key={s.step} className="glass-card group" style={{ textAlign: "center", padding: 32, cursor: "default" }}>
                <div style={{ width: 56, height: 56, borderRadius: 16, background: "rgba(0,230,118,0.06)", border: "1px solid rgba(0,230,118,0.08)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px", color: "#00e676", fontSize: 24, fontWeight: 800 }}>{s.step}</div>
                <h3 style={{ fontSize: 18, fontWeight: 600, color: "#fff", marginBottom: 16 }}>{s.title}</h3>
                <p style={{ fontSize: 14, color: "rgba(255,255,255,0.4)", lineHeight: 1.7 }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      {/* Pricing */}
      <Section id="pricing" style={{ paddingTop: 128, paddingBottom: 128, position: "relative", zIndex: 10 }}>
        <Container>
          <div style={{ textAlign: "center", marginBottom: 96 }}>
            <Pill>Pricing</Pill>
            <h2 style={{ fontSize: "clamp(2rem, 5vw, 3.75rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", marginBottom: 16, lineHeight: 1.15 }}>
              Choose Your <span className="gradient-text">Intelligence Tier</span>
            </h2>
            <p style={{ color: "rgba(255,255,255,0.4)", maxWidth: 640, margin: "0 auto", fontSize: 18, lineHeight: 1.7 }}>
              Start free. Upgrade when you need deeper insights, alerts, and institutional-grade reporting.
            </p>
          </div>
          <div className="grid-3" style={{ maxWidth: 1152, margin: "0 auto" }}>
            {pricingPlans.map((plan) => (
              <div key={plan.name} className={`pricing-card ${plan.featured ? "featured" : ""}`} style={{ position: "relative" }}>
                {plan.highlight && (
                  <div style={{ position: "absolute", top: 20, right: 20, padding: "4px 12px", borderRadius: 9999, background: "rgba(0,230,118,0.1)", border: "1px solid rgba(0,230,118,0.2)", color: "#00e676", fontSize: 10, fontWeight: 600 }}>
                    {plan.highlight}
                  </div>
                )}
                <div style={{ marginBottom: 24 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 600, color: "#fff", marginBottom: 8 }}>{plan.name}</h3>
                  <p style={{ fontSize: 14, color: "rgba(255,255,255,0.35)" }}>{plan.desc}</p>
                </div>
                <div style={{ marginBottom: 32 }}>
                  <span style={{ fontSize: 48, fontWeight: 700, color: "#fff" }}>{plan.price}</span>
                  <span style={{ fontSize: 14, color: "rgba(255,255,255,0.3)", marginLeft: 4 }}>{plan.period}</span>
                </div>
                <ul style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 40 }}>
                  {plan.features.map((f) => (
                    <li key={f} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 14, color: "rgba(255,255,255,0.55)" }}>
                      <svg style={{ width: 16, height: 16, color: "#00e676", flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/login"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "100%",
                    fontSize: 14,
                    fontWeight: 600,
                    padding: 16,
                    borderRadius: 16,
                    textDecoration: "none",
                    transition: "all 0.2s",
                    ...(plan.featured
                      ? { color: "#000", background: "#00e676" }
                      : { color: "#fff", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.06)" }),
                  }}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      {/* CTA */}
      <Section style={{ paddingTop: 128, paddingBottom: 128, position: "relative", overflow: "hidden", zIndex: 10 }}>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, transparent, rgba(0,230,118,0.02), rgba(0,230,118,0.04))" }} />
        <Container maxW={896} style={{ textAlign: "center", position: "relative", zIndex: 10 }}>
          <Pill>Get Started</Pill>
          <h2 style={{ fontSize: "clamp(2rem, 6vw, 4.5rem)", fontWeight: 700, color: "#fff", letterSpacing: "-0.03em", marginBottom: 32, lineHeight: 1.0 }}>
            Your Portfolio Deserves<br />
            <span className="gradient-text">Better Intelligence</span>
          </h2>
          <p style={{ color: "rgba(255,255,255,0.4)", marginBottom: 48, maxWidth: 640, margin: "0 auto 48px", fontSize: 18, lineHeight: 1.7 }}>
            No setup. No configuration. Just enter your tickers and see what institutional risk models reveal about your portfolio.
          </p>
          <div className="btn-row">
            <Link
              href="/login"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 16,
                fontWeight: 600,
                color: "#000",
                background: "#00e676",
                padding: "20px 48px",
                borderRadius: 16,
                textDecoration: "none",
                transition: "all 0.2s",
              }}
            >
              Analyze Your Portfolio Now
            </Link>
            <a
              href="#features"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 16,
                fontWeight: 500,
                color: "#fff",
                padding: "20px 40px",
                borderRadius: 16,
                textDecoration: "none",
                border: "1px solid rgba(255,255,255,0.08)",
                transition: "all 0.2s",
              }}
            >
              Explore Features
            </a>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32, maxWidth: 480, margin: "64px auto 0" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#fff" }}>10K+</div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", marginTop: 4 }}>Paths Simulated</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#fff" }}>12yr</div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", marginTop: 4 }}>Backtest History</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#fff" }}>5</div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", marginTop: 4 }}>Crisis Scenarios</div>
            </div>
          </div>
        </Container>
      </Section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid rgba(255,255,255,0.04)", position: "relative", zIndex: 10 }}>
        <Container>
          <div className="footer-grid">
            <div>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 16, fontWeight: 700, color: "#fff", marginBottom: 16 }}>
                <span style={{ width: 28, height: 28, borderRadius: 8, background: "#00e676", display: "flex", alignItems: "center", justifyContent: "center", color: "#000", fontWeight: 800, fontSize: 10 }}>LR</span>
                LiveRisk
              </span>
              <p style={{ fontSize: 14, color: "rgba(255,255,255,0.3)", maxWidth: 400, lineHeight: 1.7 }}>
                Institutional-grade financial risk intelligence for everyone. Monte Carlo simulations, 
                LSTM forecasting, sentiment analysis, and stress testing — powered by Vera AI.
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 24 }}>
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.15)" }}>SOC 2</span>
                <span style={{ width: 1, height: 12, background: "rgba(255,255,255,0.08)" }} />
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.15)" }}>GDPR</span>
                <span style={{ width: 1, height: 12, background: "rgba(255,255,255,0.08)" }} />
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.15)" }}>256-bit AES</span>
              </div>
            </div>
            <div>
              <h4 style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>Product</h4>
              <ul style={{ display: "flex", flexDirection: "column", gap: 12, listStyle: "none", padding: 0, margin: 0 }}>
                <li><a href="#features" style={{ fontSize: 14, color: "rgba(255,255,255,0.3)", textDecoration: "none", transition: "color 0.2s" }}>Features</a></li>
                <li><a href="#pricing" style={{ fontSize: 14, color: "rgba(255,255,255,0.3)", textDecoration: "none", transition: "color 0.2s" }}>Pricing</a></li>
                <li><Link href="/login" style={{ fontSize: 14, color: "rgba(255,255,255,0.3)", textDecoration: "none", transition: "color 0.2s" }}>Dashboard</Link></li>
              </ul>
            </div>
            <div>
              <h4 style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>Company</h4>
              <ul style={{ display: "flex", flexDirection: "column", gap: 12, listStyle: "none", padding: 0, margin: 0 }}>
                <li><a href="#why" style={{ fontSize: 14, color: "rgba(255,255,255,0.3)", textDecoration: "none", transition: "color 0.2s" }}>About</a></li>
                <li><span style={{ fontSize: 14, color: "rgba(255,255,255,0.3)" }}>Privacy</span></li>
                <li><span style={{ fontSize: 14, color: "rgba(255,255,255,0.3)" }}>Terms</span></li>
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.15)" }}>&copy; 2026 LiveRisk. Financial Risk Intelligence.</span>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.1)" }}>Built with Vera AI</span>
          </div>
        </Container>
      </footer>
    </div>
  );
}
