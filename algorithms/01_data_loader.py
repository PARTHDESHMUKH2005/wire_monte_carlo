# ── Imports ──────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings('ignore')

# Wire API config
WIRE_API_KEY = os.environ.get("WIRE_API_KEY", "ask.........81")

from anakin import Anakin
wire = Anakin(api_key=WIRE_API_KEY)

def wire_call(action_id: str, params: dict):
    """Call a Wire action. Returns structured data or None on failure."""
    try:
        result = wire.wire(action_id, params)
        return result.model_dump() if hasattr(result, 'model_dump') else result
    except Exception as e:
        print(f"  Wire '{action_id}' failed: {e}")
        return None

# ── 1. Fetch real data via Wire API (yahoo_finance action) ────────────

TICKERS = ['SPY', 'QQQ', 'AGG', 'GLD']
END = datetime.today()
START = END - timedelta(days=2*365)

print(f"Fetching {TICKERS} via Wire yahoo_finance action...")
print(f"From {START.date()} to {END.date()}")
print()

# Try Wire first
prices = None
for t in TICKERS:
    print(f"  Fetching {t}...")
    data = wire_call("yahoo_finance", {
        "ticker": t,
        "action": "price",
        "start_date": START.strftime("%Y-%m-%d"),
        "end_date": END.strftime("%Y-%m-%d"),
    })
    if data and 'prices' in data:
        df = pd.DataFrame(data['prices'])
        if 'date' in df.columns:
            df.set_index('date', inplace=True)
        if prices is None:
            prices = df[['close']].rename(columns={'close': t})
        else:
            prices[t] = df['close']
        print(f"    Got {len(df)} rows via Wire")

# Fallback to yfinance if Wire didn't work
if prices is None or len(prices.columns) < len(TICKERS):
    print("\n  Wire unavailable — falling back to yfinance...")
    raw = yf.download(TICKERS, start=START, end=END, auto_adjust=False, progress=False)
    if 'Adj Close' in raw.columns.get_level_values(0):
        prices = raw['Adj Close'].copy()
    else:
        prices = raw['Close'].copy()
    prices = prices.dropna(axis=1, how='all')

print(f"\nDownloaded {len(prices)} rows x {len(prices.columns)} assets")
prices.head()

# ── 1b. Fetch fundamentals via Wire yahoo_finance action ──────────────

print("Fetching fundamentals via Wire yahoo_finance action...")
fundamentals = {}
for t in TICKERS:
    data = wire_call("yahoo_finance", {
        "ticker": t,
        "action": "fundamentals",
    })
    if data:
        fundamentals[t] = data
        print(f"  {t}: market_cap={data.get('market_cap', 'N/A')}, pe_ratio={data.get('pe_ratio', 'N/A')}")
    else:
        print(f"  {t}: Wire unavailable for fundamentals")

fundamentals

# ── 1c. Fetch technical indicators via Wire finviz action ─────────────

print("Fetching technical indicators via Wire finviz action...")
technicals = {}
for t in TICKERS:
    data = wire_call("finviz", {
        "ticker": t,
        "action": "technical_indicators",
    })
    if data:
        technicals[t] = data
        print(f"  {t}: rsi={data.get('rsi', 'N/A')}, sma_50={data.get('sma_50', 'N/A')}")
    else:
        print(f"  {t}: Wire unavailable for finviz")

technicals

# ── 1d. Fetch latest news via Wire reuters action ─────────────────────

print("Fetching latest news via Wire reuters action...")
news_data = {}
for t in TICKERS:
    data = wire_call("reuters", {
        "ticker": t,
        "action": "headlines",
        "limit": 10,
    })
    if data and 'headlines' in data:
        news_data[t] = data['headlines']
        print(f"  {t}: {len(data['headlines'])} headlines")
        for h in data['headlines'][:3]:
            print(f"    - {h.get('title', h.get('headline', ''))[:80]}")
    else:
        print(f"  {t}: Wire unavailable for reuters")

news_data

# ── 5. Compute log returns ────────────────────────────────────────────

returns = np.log(prices / prices.shift(1))
returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how='any')

print(f"Returns shape: {returns.shape[0]} days, {returns.shape[1]} assets")
returns.head()

# ── 6. Data quality validation ────────────────────────────────────────

missing_ratio = returns.isna().mean().max()
print(f"Max missing ratio across assets: {missing_ratio:.4%}")

if missing_ratio > 0.02:
    print("WARNING: Missing ratio exceeds 2% threshold — consider re-fetching or forward-fill")
else:
    print("PASS: Missing ratio within acceptable range")

stats = returns.describe().T[['mean', 'std', 'min', 'max']]
print("\nReturn statistics per asset:")
stats

# ── 7. Bundle into a clean MarketData object ──────────────────────────

market_data = {
    'prices': prices,
    'returns': returns,
    'fundamentals': fundamentals,
    'technicals': technicals,
    'news_headlines': news_data,
    'wire_summary': {
        'sources': ['yahoo_finance', 'finviz', 'reuters'],
        'status': 'Wire action data integrated where available',
        'fallback': 'yfinance used as backup if Wire actions not yet created in dashboard',
    },
    'metadata': {
        'rows': len(returns),
        'assets': list(returns.columns),
        'start': str(returns.index[0].date()),
        'end': str(returns.index[-1].date()),
        'max_missing_ratio': float(missing_ratio),
        'source': 'Wire API (yahoo_finance) + yfinance fallback',
    }
}

print("\nMarket data summary:")
for k, v in market_data['metadata'].items():
    print(f"  {k}: {v}")

import joblib
joblib.dump(market_data, 'market_data.pkl')
print("\nSaved market_data.pkl — ready for covariance estimation.")
