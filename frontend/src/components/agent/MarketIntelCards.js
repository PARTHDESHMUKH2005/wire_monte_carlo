"use client";

function Tag({ label, color }) {
  return (
    <div
      style={{
        display: "inline-block",
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: 10,
        marginBottom: 8,
        background: `${color}20`,
        color,
      }}
    >
      {label}
    </div>
  );
}

function Card({ children, style }) {
  return (
    <div
      style={{
        background: "#14141a",
        border: "1px solid #27272a",
        borderRadius: 10,
        padding: 12,
        marginBottom: 8,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export default function MarketIntelCards({ marketIntel }) {
  if (!marketIntel) return null;
  const { market_news, company_intel, market_movers, ipo_data, global_indices, geopolitical, macro, summary } = marketIntel;

  const hasAny =
    (global_indices && Object.keys(global_indices).length > 0) ||
    (market_movers?.top_gainers?.length || market_movers?.top_losers?.length) ||
    (company_intel && Object.keys(company_intel).length > 0) ||
    (ipo_data?.upcoming?.length || ipo_data?.recent?.length) ||
    (geopolitical?.events?.length || geopolitical?.summary) ||
    (macro && Object.keys(macro).length > 0) ||
    market_news?.headlines?.length;

  if (!hasAny) return null;

  return (
    <div style={{ margin: "12px 0 4px" }}>
      {/* Global Indices */}
      {global_indices && Object.keys(global_indices).length > 0 && (
        <Card>
          <Tag label="Global Indices" color="#3b82f6" />
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
            gap: 8,
          }}>
            {Object.entries(global_indices).slice(0, 18).map(([key, idx]) => {
              const region = idx.region || key.split(".")[0];
              const name = idx.name || key.split(".")[1] || key;
              const chg = idx.change_pct;
              const isUp = chg > 0;
              const isDown = chg < 0;
              return (
                <div key={key} style={{ fontSize: 11 }}>
                  <div style={{ color: "#71717a", fontSize: 9, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    {region.replace(/_/g, " ")}
                  </div>
                  <div style={{ color: "#e4e4e7", fontWeight: 600 }}>
                    {idx.price != null ? idx.price.toLocaleString() : "—"}
                  </div>
                  {chg != null && (
                    <div style={{ color: isUp ? "#00e676" : isDown ? "#ef4444" : "#a1a1aa", fontSize: 10 }}>
                      {isUp ? "+" : ""}{chg.toFixed(2)}%
                    </div>
                  )}
                  <div style={{ color: "#71717a", fontSize: 8, marginTop: 1 }}>{idx.currency || ""}</div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Market Movers */}
      {(market_movers?.top_gainers?.length || market_movers?.top_losers?.length) && (
        <Card>
          <Tag label="Market Movers" color="#00e676" />
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 10, color: "#00e676", fontWeight: 600, marginBottom: 4 }}>Gainers</div>
              {market_movers.top_gainers?.slice(0, 5).map((s, i) => (
                <div key={`g-${i}`} style={{ fontSize: 11, color: "#e4e4e7", marginBottom: 2 }}>
                  <strong>{s.ticker}</strong>{" "}
                  <span style={{ color: "#00e676" }}>+{s.change_pct?.toFixed(2)}%</span>
                  <span style={{ color: "#71717a", fontSize: 10 }}> @ {s.price}</span>
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#ef4444", fontWeight: 600, marginBottom: 4 }}>Losers</div>
              {market_movers.top_losers?.slice(0, 5).map((s, i) => (
                <div key={`l-${i}`} style={{ fontSize: 11, color: "#e4e4e7", marginBottom: 2 }}>
                  <strong>{s.ticker}</strong>{" "}
                  <span style={{ color: "#ef4444" }}>{s.change_pct?.toFixed(2)}%</span>
                  <span style={{ color: "#71717a", fontSize: 10 }}> @ {s.price}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* Company Intel */}
      {company_intel && Object.keys(company_intel).length > 0 && (
        <Card>
          {Object.entries(company_intel).map(([ticker, ci]) => (
            <div key={ticker} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <Tag label={`${ticker} — ${ci.country || ci.sector || "Global"}`} color="#8b5cf6" />
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 11, color: "#a1a1aa" }}>
                {ci.price && <span>Price: <strong style={{ color: "#e4e4e7" }}>{ci.currency === "USD" ? "$" : ci.currency + " "}{ci.price}</strong></span>}
                {ci.change_pct && (
                  <span>
                    Change:{" "}
                    <strong style={{ color: ci.change_pct >= 0 ? "#00e676" : "#ef4444" }}>
                      {ci.change_pct >= 0 ? "+" : ""}{ci.change_pct.toFixed(2)}%
                    </strong>
                  </span>
                )}
                {ci.market_cap && <span>Mkt Cap: <strong style={{ color: "#e4e4e7" }}>{(ci.market_cap / 1e9).toFixed(1)}B</strong></span>}
                {ci.pe_ratio && <span>P/E: <strong style={{ color: "#e4e4e7" }}>{ci.pe_ratio.toFixed(1)}</strong></span>}
                {ci.analyst_target && <span>Target: <strong style={{ color: "#e4e4e7" }}>{ci.currency === "USD" ? "$" : ""}{ci.analyst_target}</strong></span>}
                {ci.recommendation && <span>Rating: <strong style={{ color: "#e4e4e7" }}>{ci.recommendation}</strong></span>}
                {ci.dividend_yield && <span>Div: <strong style={{ color: "#e4e4e7" }}>{(ci.dividend_yield * 100).toFixed(2)}%</strong></span>}
                {ci["52w_high"] && <span>52W High: <strong style={{ color: "#e4e4e7" }}>{ci["52w_high"]}</strong></span>}
                {ci["52w_low"] && <span>52W Low: <strong style={{ color: "#e4e4e7" }}>{ci["52w_low"]}</strong></span>}
              </div>
              {ci.news?.length > 0 && (
                <div style={{ marginTop: 6, fontSize: 11, color: "#71717a" }}>
                  <div style={{ fontWeight: 600, color: "#a1a1aa", marginBottom: 4, fontSize: 10 }}>News</div>
                  {ci.news.slice(0, 3).map((n, i) => (
                    <div key={i} style={{ marginBottom: 2, lineHeight: 1.3 }}>
                      {n.url ? (
                        <a href={n.url} target="_blank" rel="noopener noreferrer" style={{ color: "#3b82f6", fontSize: 11 }}>
                          {n.title}
                        </a>
                      ) : (
                        <span>{n.title}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </Card>
      )}

      {/* Geopolitical */}
      {(geopolitical?.events?.length > 0 || geopolitical?.risk_factors?.length > 0) && (
        <Card>
          <Tag label="Geopolitical Risk" color="#ef4444" />
          {geopolitical.events?.slice(0, 4).map((ev, i) => (
            <div key={i} style={{ fontSize: 11, marginBottom: 6, borderLeft: `3px solid ${ev.impact_level === "high" ? "#ef4444" : ev.impact_level === "medium" ? "#f59e0b" : "#3b82f6"}`, paddingLeft: 8 }}>
              <div style={{ color: "#e4e4e7", fontWeight: 600 }}>{ev.title}</div>
              {ev.description && <div style={{ color: "#a1a1aa", fontSize: 10, marginTop: 2 }}>{ev.description}</div>}
            </div>
          ))}
          {geopolitical.risk_factors?.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <div style={{ fontSize: 10, color: "#a1a1aa", fontWeight: 600, marginBottom: 4 }}>Risk Factors</div>
              {geopolitical.risk_factors.slice(0, 4).map((rf, i) => (
                <div key={i} style={{ fontSize: 10, color: "#ef4444", marginBottom: 2 }}>⚠ {rf}</div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Macro */}
      {macro && Object.keys(macro).length > 0 && (
        <Card>
          <Tag label="Macro Outlook" color="#f59e0b" />
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {Object.entries(macro).map(([region, data]) => {
              if (typeof data !== "object" || data === null) {
                return (
                  <div key={region} style={{ fontSize: 11 }}>
                    <div style={{ color: "#71717a", fontSize: 9, textTransform: "uppercase" }}>{region.replace(/_/g, " ")}</div>
                    <div style={{ color: "#e4e4e7" }}>{String(data)}</div>
                  </div>
                );
              }
              return (
                <div key={region} style={{ fontSize: 11, minWidth: 120 }}>
                  <div style={{ color: "#71717a", fontSize: 9, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>
                    {region.replace(/_/g, " ")}
                  </div>
                  {data.rate && <div>Rate: <strong style={{ color: "#e4e4e7" }}>{data.rate}</strong></div>}
                  {data.inflation && <div>CPI: <strong style={{ color: "#e4e4e7" }}>{data.inflation}</strong></div>}
                  {data.gdp_growth && <div>GDP: <strong style={{ color: "#e4e4e7" }}>{data.gdp_growth}</strong></div>}
                  {data.unemployment && <div>U/E: <strong style={{ color: "#e4e4e7" }}>{data.unemployment}</strong></div>}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* IPOs */}
      {(ipo_data?.upcoming?.length || ipo_data?.recent?.length) && (
        <Card>
          <Tag label="IPOs" color="#a855f7" />
          {ipo_data.upcoming?.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: "#a1a1aa", marginBottom: 4 }}>Upcoming</div>
              {ipo_data.upcoming.slice(0, 4).map((ipo, i) => (
                <div key={i} style={{ fontSize: 11, color: "#e4e4e7", marginBottom: 2 }}>
                  <strong>{ipo.company}</strong> {ipo.ticker && `(${ipo.ticker})`}
                  {ipo.date && <span style={{ color: "#71717a" }}> — {ipo.date}</span>}
                  {ipo.exchange && <span style={{ color: "#71717a", fontSize: 10 }}> on {ipo.exchange}</span>}
                </div>
              ))}
            </div>
          )}
          {ipo_data.recent?.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 600, color: "#a1a1aa", marginBottom: 4 }}>Recent</div>
              {ipo_data.recent.slice(0, 3).map((ipo, i) => (
                <div key={i} style={{ fontSize: 11, color: "#e4e4e7", marginBottom: 2 }}>
                  <strong>{ipo.company}</strong> {ipo.ticker && `(${ipo.ticker})`}
                  {ipo.return_pct && <span style={{ color: ipo.return_pct >= 0 ? "#00e676" : "#ef4444" }}> — {ipo.return_pct >= 0 ? "+" : ""}{ipo.return_pct}%</span>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Market News */}
      {market_news?.headlines?.length > 0 && (
        <Card>
          <Tag label="Market News" color="#f59e0b" />
          {market_news.regions_covered?.length > 0 && (
            <div style={{ fontSize: 9, color: "#71717a", marginBottom: 6 }}>
              Regions: {market_news.regions_covered.join(", ")}
            </div>
          )}
          {market_news.headlines.slice(0, 6).map((h, i) => (
            <div key={i} style={{ fontSize: 11, marginBottom: 4, lineHeight: 1.3 }}>
              {h.url ? (
                <a href={h.url} target="_blank" rel="noopener noreferrer" style={{ color: "#a1a1aa", textDecoration: "none" }}>
                  {h.title}
                </a>
              ) : (
                <span style={{ color: "#a1a1aa" }}>{h.title}</span>
              )}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
