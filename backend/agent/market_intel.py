import os
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from data_providers import (
    finnhub_company_news, finnhub_market_news, finnhub_company_profile,
    finnhub_peers, finnhub_recommendations, finnhub_earnings,
    finnhub_basic_financials, finnhub_search, finnhub_ipo_calendar,
    finnhub_news_sentiment, finnhub_euronomy_indicators,
    tavily_search, tavily_get_json,
    worldbank_macro_snapshot, worldbank_data, worldbank_latest,
    search_news as provider_search_news,
    get_geopolitical_intel_tavily, get_macro_outlook_providers,
    COUNTRY_CODE_MAP, WB_INFLATION, WB_GDP_GROWTH, WB_UNEMPLOYMENT, WB_INTEREST_RATE,
)

GLOBAL_INDICES = {
    "US": {"sp500": "^GSPC", "nasdaq": "^IXIC", "dow": "^DJI", "russell": "^RUT"},
    "India": {"nifty": "^NSEI", "sensex": "^BSESN", "banknifty": "^NSEBANK"},
    "Japan": {"nikkei": "^N225", "topix": "^TOPX"},
    "UK": {"ftse100": "^FTSE", "ftse250": "^FTMC"},
    "Germany": {"dax": "^GDAXI"},
    "France": {"cac40": "^FCHI"},
    "China": {"shanghai": "000001.SS", "shenzhen": "^SZSCI", "hang_seng": "^HSI"},
    "Hong_Kong": {"hang_seng": "^HSI"},
    "South_Korea": {"kospi": "^KS11"},
    "Australia": {"asx200": "^AXJO"},
    "Brazil": {"bovespa": "^BVSP"},
    "Canada": {"tsx": "^GSPTSE"},
    "Switzerland": {"smi": "^SSMI"},
    "Singapore": {"straits_times": "^STI"},
    "Taiwan": {"taiex": "^TWII"},
    "Russia": {"rts": "^RTS"},
    "South_Africa": {"jse_top40": "^JN0U.JO"},
    "Mexico": {"mexico_ipc": "^MXX"},
    "Netherlands": {"aex": "^AEX"},
    "Sweden": {"omx30": "^OMX"},
    "Spain": {"ibex35": "^IBEX"},
}

REGION_MAP = {
    "india": "India", "nifty": "India", "sensex": "India", "bse": "India", "nse": "India",
    "china": "China", "shanghai": "China", "shenzhen": "China", "hong kong": "Hong_Kong",
    "japan": "Japan", "nikkei": "Japan", "topix": "Japan",
    "uk": "UK", "london": "UK", "ftse": "UK", "britain": "UK",
    "germany": "Germany", "dax": "Germany", "frankfurt": "Germany",
    "france": "France", "cac": "France", "paris": "France",
    "korea": "South_Korea", "kospi": "South_Korea",
    "australia": "Australia", "asx": "Australia",
    "brazil": "Brazil", "bovespa": "Brazil",
    "canada": "Canada", "tsx": "Canada",
    "russia": "Russia", "rts": "Russia",
    "africa": "South_Africa", "south africa": "South_Africa",
    "mexico": "Mexico",
    "europe": "Europe", "european": "Europe", "eu": "Europe",
    "us": "US", "united states": "US", "america": "US", "wall street": "US", "s&p": "US",
    "global": "Global", "world": "Global", "international": "Global",
    "asia": "Asia", "pacific": "Asia", "emerging": "Emerging_Markets",
}


def _detect_regions(query: str) -> list[str]:
    q = query.lower()
    regions = []
    for keyword, region in REGION_MAP.items():
        if keyword in q and region not in regions:
            regions.append(region)
    return regions if regions else ["Global"]


def get_global_indices() -> dict:
    indices = {}
    try:
        import yfinance as yf
        for region, region_indices in GLOBAL_INDICES.items():
            for name, symbol in region_indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info or {}
                    hist = ticker.history(period="5d")
                    price = info.get("regularMarketPrice") or info.get("currentPrice") or (
                        round(hist["Close"].iloc[-1], 2) if len(hist) > 0 else None
                    )
                    prev_close = info.get("regularMarketPreviousClose") or (
                        round(hist["Close"].iloc[-2], 2) if len(hist) > 1 else None
                    )
                    change_pct = (
                        round(((price - prev_close) / prev_close) * 100, 2)
                        if price and prev_close and prev_close != 0 else None
                    )
                    indices[f"{region}.{name}"] = {
                        "region": region, "name": name, "price": price,
                        "change_pct": change_pct, "currency": info.get("currency", "USD"),
                    }
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"Global indices fetch failed: {e}")
    return indices


def get_global_market_news(query: str) -> dict:
    regions = _detect_regions(query)
    headlines = []
    seen = set()
    for r in regions[:3]:
        batch = provider_search_news(f"{r} stock market financial news", limit=6)
        for h in batch:
            title = h.get("title", "")
            if title and title not in seen:
                seen.add(title)
                headlines.append(h)
    if not headlines:
        headlines = provider_search_news(query or "global stock market news today", limit=10)
    return {
        "headlines": headlines[:12],
        "regions_covered": regions,
        "summary": " ".join(h.get("title", "") for h in headlines[:4]) if headlines else "",
    }


def get_geopolitical_intel(query: str) -> dict:
    intel = {"events": [], "risk_factors": [], "summary": ""}
    regions = _detect_regions(query)
    region_focus = regions[0] if regions and regions[0] != "Global" else "global"

    ti = get_geopolitical_intel_tavily(region_focus)
    if ti.get("summary"):
        intel["summary"] = ti["summary"][:500]
        intel["_sources"] = ti.get("_sources", [])

    news = provider_search_news(f"{region_focus} geopolitics sanctions trade war", limit=6)
    intel["_news"] = news
    if not intel["summary"]:
        intel["summary"] = " ".join(h.get("title", "") for h in news[:3]) if news else ""

    return intel


def get_global_company_intel(query: str) -> dict:
    ticker_pattern = re.search(
        r'\b([A-Z]{1,5}(?:\.(?:NS|L|T|TO|PA|DE|F|MI|AS|KS|SS|SZ|HK|ST|AX|OL|CO|NE|BO|MC|SW))?)\b',
        query.upper()
    )
    company_name = query

    if ticker_pattern:
        ticker = ticker_pattern.group(1)
    else:
        name_map = {
            "apple": "AAPL", "google": "GOOGL", "alphabet": "GOOGL", "microsoft": "MSFT",
            "amazon": "AMZN", "meta": "META", "facebook": "META", "nvidia": "NVDA",
            "tesla": "TSLA", "netflix": "NFLX", "adobe": "ADBE", "salesforce": "CRM",
            "oracle": "ORCL", "ibm": "IBM", "cisco": "CSCO", "intel": "INTC",
            "amd": "AMD", "qualcomm": "QCOM", "broadcom": "AVGO",
            "jpmorgan": "JPM", "goldman sachs": "GS", "morgan stanley": "MS",
            "berkshire": "BRK-B", "visa": "V", "mastercard": "MA", "paypal": "PYPL",
            "johnson & johnson": "JNJ", "pfizer": "PFE", "merck": "MRK",
            "unitedhealth": "UNH", "abbott": "ABT",
            "walmart": "WMT", "costco": "COST", "home depot": "HD",
            "mcdonald's": "MCD", "starbucks": "SBUX", "coca-cola": "KO", "pepsi": "PEP",
            "nike": "NKE", "disney": "DIS",
            "exxon": "XOM", "chevron": "CVX", "shell": "SHEL", "bp": "BP",
            "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY",
            "hdfc bank": "HDFCBANK.NS", "icici bank": "ICICIBANK.NS", "bharti airtel": "BHARTIARTL.NS",
            "samsung": "005930.KS", "toyota": "TM", "sony": "SONY", "honda": "HMC",
            "alibaba": "BABA", "tencent": "TCEHY", "baidu": "BIDU", "jd.com": "JD",
            "novartis": "NVS", "nestle": "NSRGY", "roche": "RHHBY", "ubs": "UBS",
            "volkswagen": "VWAGY", "mercedes": "MBGAF", "bmw": "BMWYY",
            "lvmh": "LVMUY", "totalenergies": "TTE", "airbus": "EADSY",
        }
        ql = query.lower()
        ticker = None
        for name, sym in name_map.items():
            if name in ql:
                ticker = sym
                break
        if not ticker:
            ticker = query.strip().upper()

    intel = {
        "ticker": ticker, "name": company_name,
        "price": None, "change_pct": None, "market_cap": None,
        "sector": None, "country": None, "currency": None,
        "pe_ratio": None, "analyst_target": None, "recommendation": None,
        "dividend_yield": None, "52w_high": None, "52w_low": None,
        "news": [], "events": [], "summary": "",
        "peers": [], "earnings": [],
    }

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        intel["price"] = info.get("currentPrice") or info.get("regularMarketPrice")
        intel["change_pct"] = info.get("regularMarketChangePercent")
        intel["market_cap"] = info.get("marketCap")
        intel["sector"] = info.get("sector", "")
        intel["industry"] = info.get("industry", "")
        intel["country"] = info.get("country", "")
        intel["currency"] = info.get("currency", "USD")
        intel["pe_ratio"] = info.get("trailingPE")
        intel["analyst_target"] = info.get("targetMeanPrice")
        intel["recommendation"] = info.get("recommendationKey", "")
        intel["dividend_yield"] = info.get("dividendYield")
        intel["52w_high"] = info.get("fiftyTwoWeekHigh")
        intel["52w_low"] = info.get("fiftyTwoWeekLow")
        intel["summary"] = (info.get("longBusinessSummary") or "")[:500]
        intel["name"] = info.get("longName") or info.get("shortName") or company_name
    except Exception as e:
        logger.debug(f"yfinance failed for {ticker}: {e}")

    intel["news"] = finnhub_company_news(ticker, limit=6)
    if not intel["news"]:
        intel["news"] = provider_search_news(f"{ticker} stock latest news", limit=6)

    intel["peers"] = finnhub_peers(ticker)
    earnings = finnhub_earnings(ticker, limit=4)
    intel["earnings"] = earnings

    fin_profile = finnhub_company_profile(ticker)
    if fin_profile:
        intel["sector"] = intel["sector"] or fin_profile.get("finnhubIndustry", "")
        intel["country"] = intel["country"] or fin_profile.get("country", "")

    recs = finnhub_recommendations(ticker)
    if recs and isinstance(recs, list) and len(recs) > 0:
        latest = recs[0]
        intel["recommendation"] = intel["recommendation"] or latest.get("buy", 0) > latest.get("sell", 0)

    return intel


def get_global_market_movers(query: str) -> dict:
    movers = {"top_gainers": [], "top_losers": [], "most_active": []}
    regions = _detect_regions(query)
    region_focus = regions[0] if regions else "global"

    data = tavily_get_json(
        f"Get the top stock market gainers and losers in {region_focus} markets today. "
        "Include ticker symbols, company names, prices in local currency, and percentage changes. "
        f"Cover ALL major exchanges in {region_focus}. "
        "Return data with keys: top_gainers, top_losers, most_active.",
        max_results=6
    )
    if data and data.get("raw"):
        pass

    region_indices = GLOBAL_INDICES.get(region_focus, {})
    if not region_indices and region_focus == "Global":
        for ri in list(GLOBAL_INDICES.values())[:3]:
            region_indices.update(ri)
    if region_indices:
        try:
            import yfinance as yf
            for name, symbol in region_indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    if len(hist) >= 2:
                        pct = ((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2]) * 100
                        price = round(hist["Close"].iloc[-1], 2)
                        entry = {"ticker": name, "name": name, "price": price, "change_pct": round(pct, 2)}
                        if pct > 0:
                            movers["top_gainers"].append(entry)
                        elif pct < 0:
                            movers["top_losers"].append(entry)
                except Exception:
                    continue
            movers["top_gainers"] = sorted(movers["top_gainers"], key=lambda x: x["change_pct"], reverse=True)[:5]
            movers["top_losers"] = sorted(movers["top_losers"], key=lambda x: x["change_pct"])[:5]
        except Exception as e:
            logger.debug(f"yfinance global movers failed: {e}")

    return movers


def get_global_ipo_data(query: str) -> dict:
    ipo_data = {"upcoming": [], "recent": [], "notable_fails": []}
    regions = _detect_regions(query)
    region_focus = regions[0] if regions and regions[0] != "Global" else "global"

    cal = finnhub_ipo_calendar()
    if isinstance(cal, dict):
        upcoming = cal.get("ipoCalendar", [])
        if upcoming:
            for item in upcoming[:10]:
                ipo_data["upcoming"].append({
                    "company": item.get("name", ""),
                    "ticker": item.get("symbol", ""),
                    "date": item.get("date", ""),
                    "exchange": item.get("exchange", ""),
                })

    if not ipo_data["upcoming"]:
        data = tavily_get_json(
            f"Get the latest IPO calendar for {region_focus} markets — upcoming IPOs, "
            "recent IPOs that launched, and any notable IPO failures or withdrawals. "
            "Include listings on ALL major exchanges in this region.",
            max_results=5
        )

    news = provider_search_news(f"{region_focus} IPO calendar listings", limit=5)
    ipo_data["_news"] = news
    return ipo_data


def get_macro_outlook(regions: list[str] | None = None) -> dict:
    if not regions:
        regions = ["US", "Eurozone", "China", "Japan", "India", "UK"]

    result = get_macro_outlook_providers(regions)
    return result if result else {}


def get_market_intel(query: str, tickers: list = None) -> dict:
    intel = {
        "query": query, "type": "global", "regions_analyzed": [],
        "market_news": {}, "global_indices": {}, "company_intel": {},
        "market_movers": {}, "ipo_data": {}, "geopolitical": {}, "macro": {},
        "web_research": "", "summary": "", "timestamp": datetime.now().isoformat(),
    }
    query_lower = query.lower()
    regions = _detect_regions(query)
    intel["regions_analyzed"] = regions

    indices_kw = ("index", "market today", "market now", "nifty", "sensex", "nikkei", "ftse",
                  "dax", "cac", "kospi", "asx", "bovespa", "market open", "market close",
                  "how is the", "how are the", "indices")
    event_kw = ("wwdc", "event", "keynote", "launch", "announce", "conference",
                "earnings call", "investor day", "product launch")

    wants_indices = any(kw in query_lower for kw in indices_kw)
    wants_movers = any(kw in query_lower for kw in ("mover", "gain", "loser", "hot", "trending",
                                                     "peak", "top stock", "best", "worst", "rising", "falling"))
    wants_ipo = any(kw in query_lower for kw in ("ipo", "public", "listing", "going public"))
    wants_geopolitical = any(kw in query_lower for kw in ("geopolit", "war", "sanction", "election",
                                                            "trade war", "conflict", "tension", "diplomat", "tariff"))
    wants_macro = any(kw in query_lower for kw in ("macro", "economy", "gdp", "inflation",
                                                    "interest rate", "cpi", "fed", "central bank", "unemployment"))
    wants_company = any(kw in query_lower for kw in ("stock", "share", "price", "ticker",
                                                      "company", "news about", "tell me about",
                                                      "about ")) or tickers
    wants_event = any(kw in query_lower for kw in event_kw)

    if wants_indices:
        intel["global_indices"] = get_global_indices()

    intel["market_news"] = get_global_market_news(query)

    if wants_company and tickers:
        for t in tickers:
            intel["company_intel"][t] = get_global_company_intel(t)

    if wants_movers:
        intel["market_movers"] = get_global_market_movers(query)

    if wants_ipo:
        intel["ipo_data"] = get_global_ipo_data(query)

    if wants_geopolitical:
        intel["geopolitical"] = get_geopolitical_intel(query)

    if wants_macro:
        intel["macro"] = get_macro_outlook(regions if regions != ["Global"] else None)

    if wants_event or (not wants_indices and not wants_movers and not wants_company
                       and not wants_ipo and not wants_geopolitical and not wants_macro):
        research = provider_search_news(query, limit=8)
        if research:
            intel["web_research"] = " \u2022 ".join(h.get("title", "") for h in research[:6])
            if not intel["market_news"].get("headlines"):
                intel["market_news"]["headlines"] = research[:6]

    summary_parts = []
    if intel["global_indices"]:
        index_lines = []
        for key, idx in list(intel["global_indices"].items())[:8]:
            region, name = key.split(".", 1)
            if idx.get("price"):
                chg = idx.get("change_pct")
                chg_str = f" ({chg:+.2f}%)" if chg else ""
                index_lines.append(f"{region}/{name}: {idx['price']}{chg_str}")
        if index_lines:
            summary_parts.append("Indices: " + " | ".join(index_lines))

    if intel["market_news"].get("headlines"):
        summary_parts.append("News: " + "; ".join(h["title"] for h in intel["market_news"]["headlines"][:4]))

    for t, ci in intel["company_intel"].items():
        if ci.get("price"):
            chg = ci.get("change_pct")
            chg_str = f" ({chg:+.2f}%)" if chg else ""
            currency = ci.get("currency", "USD")
            symbol = "$" if currency == "USD" else (currency + " ")
            summary_parts.append(f"{t}: {symbol}{ci['price']}{chg_str}")

    if intel["market_movers"].get("top_gainers"):
        g = intel["market_movers"]["top_gainers"][:3]
        summary_parts.append("Gainers: " + ", ".join(
            f"{x['ticker']} ({x['change_pct']:+.2f}%)" for x in g if x.get('change_pct')
        ))
    if intel["market_movers"].get("top_losers"):
        l = intel["market_movers"]["top_losers"][:3]
        summary_parts.append("Losers: " + ", ".join(
            f"{x['ticker']} ({x['change_pct']:.2f}%)" for x in l if x.get('change_pct')
        ))
    if intel["ipo_data"].get("upcoming"):
        ipo_list = intel["ipo_data"]["upcoming"][:3]
        summary_parts.append("IPOs: " + ", ".join(x.get("company", "") for x in ipo_list))
    if intel["geopolitical"].get("summary"):
        summary_parts.append("Geopolitics: " + intel["geopolitical"]["summary"][:200])
    if intel["web_research"]:
        summary_parts.append("Research: " + intel["web_research"])

    intel["summary"] = " | ".join(summary_parts) if summary_parts else ""
    return intel
