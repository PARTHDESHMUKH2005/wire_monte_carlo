import os
import json
import logging
import pandas as pd
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "d8kog6hr01qt3kobcodgd8kog6hr01qt3kobcoe0")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")
WIRE_API_KEY = os.environ.get("WIRE_API_KEY", "")

_finnhub_session = None
_wire_client = None


# ── Finnhub ─────────────────────────────────────────────────────────

def _get_finnhub():
    global _finnhub_session
    if _finnhub_session is None:
        _finnhub_session = requests.Session()
    return _finnhub_session


def finnhub_get(endpoint: str, params: dict = None) -> dict | list:
    if not FINNHUB_API_KEY:
        return {}
    s = _get_finnhub()
    p = {"token": FINNHUB_API_KEY, **(params or {})}
    url = f"https://finnhub.io/api/v1/{endpoint.lstrip('/')}"
    try:
        r = s.get(url, params=p, timeout=15)
        if r.status_code == 200:
            return r.json()
        logger.debug(f"Finnhub {endpoint} returned {r.status_code}")
    except Exception as e:
        logger.debug(f"Finnhub {endpoint} failed: {e}")
    return {}


def finnhub_company_news(ticker: str, limit: int = 8) -> list:
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = finnhub_get("company-news", {"symbol": ticker, "from": from_date, "to": to_date})
    if isinstance(data, list) and data:
        return [
            {"title": a.get("headline", ""), "snippet": a.get("summary", "")[:300], "url": a.get("url", ""),
             "source": a.get("source", ""), "datetime": a.get("datetime", "")}
            for a in data[:limit]
        ]
    return []


def finnhub_market_news(category: str = "general", limit: int = 8) -> list:
    data = finnhub_get("news", {"category": category})
    if isinstance(data, list) and data:
        return [
            {"title": a.get("headline", ""), "snippet": a.get("summary", "")[:300], "url": a.get("url", ""),
             "source": a.get("source", ""), "datetime": a.get("datetime", "")}
            for a in data[:limit]
        ]
    return []


def finnhub_news_sentiment(ticker: str) -> dict:
    data = finnhub_get("news-sentiment", {"symbol": ticker})
    if isinstance(data, dict):
        return {
            "score": data.get("sentimentScore", 0) or 0,
            "bullish_percent": data.get("bullishPercent", 0),
            "bearish_percent": data.get("bearishPercent", 0),
            "mention_count": data.get("mentionCount", 0),
        }
    return {}


def finnhub_company_profile(ticker: str) -> dict:
    data = finnhub_get("stock/profile2", {"symbol": ticker})
    return data if isinstance(data, dict) else {}


def finnhub_peers(ticker: str) -> list:
    data = finnhub_get("stock/peers", {"symbol": ticker})
    return data if isinstance(data, list) else []


def finnhub_recommendations(ticker: str) -> list:
    data = finnhub_get("stock/recommendation", {"symbol": ticker})
    return data if isinstance(data, list) else []


def finnhub_earnings(ticker: str, limit: int = 4) -> list:
    data = finnhub_get("stock/earnings", {"symbol": ticker, "limit": limit})
    return data if isinstance(data, list) else []


def finnhub_euronomy_indicators() -> dict:
    return finnhub_get("economic")


def finnhub_basic_financials(ticker: str) -> dict:
    data = finnhub_get("stock/metric", {"symbol": ticker, "metric": "all"})
    if isinstance(data, dict) and "metric" in data:
        return data["metric"]
    return {}


def finnhub_search(query: str) -> list:
    data = finnhub_get("search", {"q": query})
    if isinstance(data, dict) and "result" in data:
        return data["result"]
    return []


def finnhub_market_holidays(exchange: str = "US") -> list:
    data = finnhub_get("stock/market-holiday")
    if isinstance(data, list):
        return data
    return []


def finnhub_ipo_calendar() -> dict:
    from_date = datetime.now().strftime("%Y-%m-%d")
    to_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    data = finnhub_get("ipo/calendar", {"from": from_date, "to": to_date})
    return data if isinstance(data, dict) else {}


# ── Tavily Search ───────────────────────────────────────────────────

TAVILY_API_URL = "https://api.tavily.com/search"


def tavily_search(query: str, max_results: int = 5, search_depth: str = "basic") -> list:
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — skipping search")
        return []
    try:
        resp = requests.post(
            TAVILY_API_URL,
            json={"api_key": TAVILY_API_KEY, "query": query, "max_results": max_results, "search_depth": search_depth},
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            return [
                {"title": r.get("title", ""), "content": r.get("content", ""), "url": r.get("url", "")}
                for r in results
            ]
        logger.debug(f"Tavily returned {resp.status_code}")
    except Exception as e:
        logger.debug(f"Tavily search failed: {e}")
    return []


def tavily_get_json(prompt: str, max_results: int = 5) -> dict | None:
    results = tavily_search(prompt, max_results=max_results, search_depth="advanced")
    if results:
        combined = "\n".join(r.get("content", "") for r in results[:3])
        combined += "\n\n" + "\n".join(r.get("title", "") for r in results[:5])
        combined += "\n\n" + "\n".join(r.get("url", "") for r in results[:5])
        return {"raw": combined, "results": results}
    return None


# ── World Bank API ──────────────────────────────────────────────────

WORLD_BANK_URL = "https://api.worldbank.org/v2"


def worldbank_data(country: str, indicator: str, start: int = 2000, end: int = None) -> list:
    if end is None:
        end = datetime.now().year
    country = country.upper()
    url = f"{WORLD_BANK_URL}/country/{country}/indicator/{indicator}"
    params = {"format": "json", "date": f"{start}:{end}", "per_page": 100}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            raw = r.json()
            if len(raw) > 1 and raw[1]:
                return [{"year": d.get("date"), "value": d.get("value")} for d in raw[1] if d.get("value")]
    except Exception as e:
        logger.debug(f"World Bank {country}/{indicator} failed: {e}")
    return []


def worldbank_latest(country: str, indicator: str) -> float | None:
    data = worldbank_data(country, indicator, start=datetime.now().year - 3)
    if data:
        try:
            return float(data[-1]["value"])
        except (ValueError, TypeError, IndexError):
            pass
    return None


# Indicator codes
WB_INFLATION = "FP.CPI.TOTL.ZG"
WB_GDP_GROWTH = "NY.GDP.MKTP.KD.ZG"
WB_UNEMPLOYMENT = "SL.UEM.TOTL.ZS"
WB_INTEREST_RATE = "FR.INR.RINR"
WB_GDP_PER_CAPITA = "NY.GDP.PCAP.CD"
WB_POPULATION = "SP.POP.TOTL"

COUNTRY_CODE_MAP = {
    "US": "US", "usa": "US", "united states": "US", "america": "US",
    "IN": "IN", "india": "IN",
    "CN": "CN", "china": "CN",
    "JP": "JP", "japan": "JP",
    "GB": "GB", "uk": "GB", "united kingdom": "GB", "britain": "GB",
    "DE": "DE", "germany": "DE",
    "FR": "FR", "france": "FR",
    "BR": "BR", "brazil": "BR",
    "CA": "CA", "canada": "CA",
    "AU": "AU", "australia": "AU",
    "KR": "KR", "south korea": "KR", "korea": "KR",
    "RU": "RU", "russia": "RU",
    "ZA": "ZA", "south africa": "ZA",
    "MX": "MX", "mexico": "MX",
    "IT": "IT", "italy": "IT",
    "ES": "ES", "spain": "ES",
    "NL": "NL", "netherlands": "NL",
    "SE": "SE", "sweden": "SE",
    "CH": "CH", "switzerland": "CH",
    "SG": "SG", "singapore": "SG",
    "HK": "HK", "hong kong": "HK",
    "TW": "TW", "taiwan": "TW",
    "ID": "ID", "indonesia": "ID",
    "NG": "NG", "nigeria": "NG",
    "AE": "AE", "uae": "AE", "united arab emirates": "AE",
    "SA": "SA", "saudi arabia": "SA",
}


def worldbank_macro_snapshot(region_name: str) -> dict:
    code = COUNTRY_CODE_MAP.get(region_name.lower())
    if not code:
        return {}
    return {
        "inflation": worldbank_latest(code, WB_INFLATION),
        "gdp_growth": worldbank_latest(code, WB_GDP_GROWTH),
        "unemployment": worldbank_latest(code, WB_UNEMPLOYMENT),
        "interest_rate": worldbank_latest(code, WB_INTEREST_RATE),
        "country_code": code,
    }


# ── Wire (keep as fallback, not primary) ────────────────────────────

def _get_wire():
    global _wire_client
    if _wire_client is None and WIRE_API_KEY:
        try:
            from anakin import Anakin
            _wire_client = Anakin(api_key=WIRE_API_KEY)
        except Exception as e:
            logger.debug(f"Wire not available: {e}")
            _wire_client = None
    return _wire_client


def wire_search(query: str, limit: int = 8) -> list:
    client = _get_wire()
    if not client:
        return []
    try:
        result = client.search(query, limit=limit)
        if result and hasattr(result, 'results') and result.results:
            return [
                {"title": r.title or "", "snippet": r.snippet or "", "url": r.url or ""}
                for r in result.results[:limit]
            ]
    except Exception:
        pass
    return []


# ── Finnhub Stock Prices ───────────────────────────────────────────

def finnhub_stock_prices(tickers: list[str], years: int = 2) -> pd.DataFrame | None:
    if not FINNHUB_API_KEY:
        return None
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=int(years * 365))
    from_ts = int(start_dt.timestamp())
    to_ts = int(end_dt.timestamp())
    price_data = {}
    s = _get_finnhub()
    for ticker in tickers:
        try:
            url = f"https://finnhub.io/api/v1/stock/candle"
            params = {"symbol": ticker.upper(), "resolution": "D", "from": from_ts, "to": to_ts, "token": FINNHUB_API_KEY}
            r = s.get(url, params=params, timeout=15)
            if r.status_code != 200:
                logger.debug(f"Finnhub candle {ticker} returned {r.status_code}")
                continue
            data = r.json()
            if data.get("s") != "ok" or "c" not in data or "t" not in data:
                continue
            timestamps = data["t"]
            closes = data["c"]
            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
            price_data[ticker.upper()] = pd.Series(closes, index=dates, dtype=float)
        except Exception as e:
            logger.debug(f"Finnhub candle {ticker} failed: {e}")
            continue
    if not price_data:
        return None
    df = pd.DataFrame(price_data)
    df.index.name = "Date"
    df = df.sort_index()
    df = df.dropna(axis=1, how="all")
    return df if not df.empty else None


# ── Aggregated helpers ──────────────────────────────────────────────

def search_news(query: str, limit: int = 8) -> list:
    headlines = finnhub_market_news("general", limit=limit)
    if not headlines:
        taxily_fallback = tavily_search(query, max_results=limit)
        if taxily_fallback:
            headlines = [{"title": r["title"], "snippet": r["content"][:300], "url": r["url"]} for r in taxily_fallback]
    if not headlines:
        headlines = wire_search(query, limit=limit)
    return headlines


def get_company_news(ticker: str, limit: int = 8) -> list:
    return finnhub_company_news(ticker, limit=limit)


def get_news_sentiment(tickers: list[str]) -> dict:
    if not FINNHUB_API_KEY:
        return {}
    all_headlines = []
    aggregate_score = 0.0
    for t in tickers[:5]:
        news = finnhub_company_news(t, limit=3)
        all_headlines.extend(news)
        sent = finnhub_news_sentiment(t)
        score = sent.get("score", 0)
        try:
            aggregate_score += float(score)
        except (ValueError, TypeError):
            pass
    avg_score = round(aggregate_score / max(len(tickers[:5]), 1), 4) if tickers else 0
    return {"score": avg_score, "headlines": all_headlines[:10]}


def get_reddit_sentiment(tickers: list[str]) -> dict:
    if not FINNHUB_API_KEY:
        return {"mentions": {}, "spike_detected": False}
    mentions = {}
    for t in tickers:
        sent = finnhub_news_sentiment(t)
        count = sent.get("mention_count", 0)
        try:
            mentions[t] = int(count)
        except (ValueError, TypeError):
            mentions[t] = 0
    spike = any(v > 20 for v in mentions.values())
    return {"mentions": mentions, "spike_detected": spike}


def get_geopolitical_intel_tavily(region: str) -> dict:
    prompt = f"Latest geopolitical events and risk factors affecting {region} financial markets. Trade tensions, sanctions, elections, central bank policy shifts, military conflicts, supply chain disruptions."
    data = tavily_get_json(prompt, max_results=6)
    intel = {"events": [], "risk_factors": [], "summary": ""}
    if data and data.get("raw"):
        summary = data["raw"][:500]
        intel["summary"] = summary
        intel["_sources"] = data.get("results", [])
    return intel


def get_macro_outlook_providers(regions: list[str]) -> dict:
    result = {}
    for region in regions:
        code = COUNTRY_CODE_MAP.get(region.lower())
        if code:
            snapshot = worldbank_macro_snapshot(region)
            if snapshot:
                result[region] = snapshot
    try:
        import yfinance as yf
        treasury = yf.Ticker("^TNX")
        tnx_info = treasury.info or {}
        result["US_10Y_Yield"] = tnx_info.get("regularMarketPrice")
    except Exception:
        pass
    return result
