import numpy as np
import pandas as pd
import yfinance as yf
import os, sys, pickle
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, ".risk_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

DEFAULT_ASSETS = {
    "SPY": 0.00078, "QQQ": 0.00100, "AGG": 0.00021, "GLD": 0.00131,
    "NVDA": 0.00150, "AAPL": 0.00095, "MSFT": 0.00088, "GOOGL": 0.00085,
    "AMZN": 0.00110, "META": 0.00120, "TSLA": 0.00180, "VTI": 0.00070,
    "IWM": 0.00075, "EEM": 0.00050, "TLT": 0.00015, "BND": 0.00010,
}
DEFAULT_VOL = 0.015

WIRE_API_KEY = os.environ.get("WIRE_API_KEY", "ask_654fad46faed02cec9e79bacf7786be752a6b27c5b1031019b4a0a8948f5b081")

app = FastAPI(title="LiveRisk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AnalyzeRequest(BaseModel):
    tickers: list[str]
    weights: list[float]

    @field_validator("tickers")
    @classmethod
    def min_one_ticker(cls, v):
        if len(v) < 1:
            raise ValueError("At least one ticker required")
        return v

    @field_validator("weights")
    @classmethod
    def weights_sum_one(cls, v, info):
        if abs(sum(v) - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        return v

def wire_call(action_id: str, params: dict):
    try:
        from anakin import Anakin
        client = Anakin(api_key=WIRE_API_KEY)
        result = client.wire(action_id, params)
        return result.model_dump() if hasattr(result, "model_dump") else result
    except Exception as e:
        print(f"  Wire '{action_id}' failed: {e}")
        return None

def _synthetic_prices(tickers, years=2):
    """Generate synthetic price data when yfinance is unavailable."""
    rng = np.random.default_rng(42)
    n = max(len(tickers), 1)
    n_days = int(years * 252)
    dates = pd.date_range(end=datetime.today(), periods=n_days, freq="B")
    mus = np.array([DEFAULT_ASSETS.get(t.upper(), 0.0008) for t in tickers])
    vol = DEFAULT_VOL
    corr = 0.35
    cov = np.full((n, n), corr * vol * vol)
    np.fill_diagonal(cov, vol * vol)
    try:
        chol = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        chol = np.linalg.cholesky(cov + 1e-6 * np.eye(n))
    shocks = rng.standard_normal((n_days, n)) @ chol.T
    log_rets = mus + shocks
    start_prices = np.array([100.0 + rng.uniform(-10, 10) for _ in range(n)])
    price_array = start_prices * np.exp(np.cumsum(log_rets, axis=0))
    prices = pd.DataFrame(price_array, index=dates, columns=tickers, dtype=float)
    return prices

def fetch_prices(tickers, years=2):
    end = datetime.today()
    start = end - timedelta(days=int(years * 365))
    try:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)
        if raw.empty or (hasattr(raw.columns, 'get_level_values') and len(raw.columns.get_level_values(0)) == 0):
            raise ValueError("Empty data from yfinance")
        if "Adj Close" in raw.columns.get_level_values(0):
            prices = raw["Adj Close"].copy()
        else:
            prices = raw["Close"].copy()
        prices = prices.dropna(axis=1, how="all")
        if prices.empty or prices.shape[1] == 0:
            raise ValueError("No valid price columns after cleaning")
        print(f"  yfinance: fetched {prices.shape[1]} tickers, {prices.shape[0]} days")
        return prices
    except Exception as e:
        print(f"  yfinance failed ({e}), falling back to synthetic data")
        return _synthetic_prices(tickers, years)

def compute_returns(prices):
    returns = np.log(prices / prices.shift(1))
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    return returns

def covariance_bundle(returns):
    mu = returns.mean().to_numpy(dtype=float)
    sample_cov = returns.cov().to_numpy(dtype=float)
    shrinkage = 0.05
    diag_target = np.diag(np.diag(sample_cov))
    cov = (1.0 - shrinkage) * sample_cov + shrinkage * diag_target
    def cholesky_with_jitter(mat, jitter=1e-10):
        eye = np.eye(mat.shape[0])
        for scale in (0.0, jitter, jitter * 10, jitter * 100, jitter * 1000):
            try:
                return np.linalg.cholesky(mat + scale * eye)
            except np.linalg.LinAlgError:
                continue
        raise ValueError("Matrix not positive definite")
    chol = cholesky_with_jitter(cov)
    return mu, cov, chol

def monte_carlo(mu, chol, weights, n_sims=10_000, horizon=252, seed_capital=1_000_000, random_seed=42):
    n_assets = len(mu)
    rng = np.random.default_rng(random_seed)
    shocks = rng.standard_normal((n_sims, horizon, n_assets)) @ chol.T
    asset_returns = mu + shocks
    port_returns = asset_returns @ weights
    paths = seed_capital * np.cumprod(1.0 + port_returns, axis=1)
    terminal = paths[:, -1]
    return paths, terminal

def risk_metrics(terminal, seed_capital, confidence=0.95):
    cutoff = np.percentile(terminal, (1.0 - confidence) * 100.0)
    var = max(0.0, seed_capital - cutoff)
    tail = terminal[terminal <= cutoff]
    cvar = max(0.0, seed_capital - float(np.mean(tail))) if len(tail) > 0 else 0.0
    prob_loss = float(np.mean(terminal < seed_capital))
    return {"var": round(var, 2), "cvar": round(cvar, 2), "prob_loss": round(prob_loss, 4)}

def sentiment_analysis(tickers):
    headlines = []
    for t in tickers:
        result = wire_call("reuters", {"ticker": t, "action": "headlines"})
        if result and "headlines" in result:
            headlines.extend(result["headlines"])
    if not headlines:
        from anakin import Anakin
        client = Anakin(api_key=WIRE_API_KEY)
        search = client.search(f"latest news for {' '.join(tickers)} stock market 2026")
        if search.results:
            for r in search.results[:10]:
                if r.snippet:
                    headlines.append({"title": r.title, "snippet": r.snippet})
    if not headlines:
        return {"score": 0.0, "headlines": [], "summary": "No news data available"}

    try:
        from transformers import pipeline
        classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert", device=-1)
        texts = [h.get("title", "") + ". " + h.get("snippet", "") for h in headlines[:20]]
        results = classifier(texts, truncation=True, max_length=512)
        scores = []
        for r in results:
            label = r["label"]
            score = r["score"]
            if label.lower() == "positive":
                scores.append(score)
            elif label.lower() == "negative":
                scores.append(-score)
            else:
                scores.append(0.0)
        sentiment = round(float(np.mean(scores)), 4) if scores else 0.0
    except Exception:
        sentiment = 0.0

    summary = f"Analyzed {len(headlines)} headlines across {len(tickers)} tickers. "
    if sentiment > 0.3:
        summary += "Overall positive sentiment."
    elif sentiment < -0.3:
        summary += "Overall negative sentiment."
    else:
        summary += "Overall neutral sentiment."

    return {"score": sentiment, "headlines": headlines[:10], "summary": summary}

def reddit_hype(tickers):
    mentions = {}
    for t in tickers:
        result = wire_call("reddit", {"ticker": t, "subreddit": "wallstreetbets", "action": "mentions"})
        if result and "mentions" in result:
            mentions[t] = result["mentions"]
    if not mentions:
        from anakin import Anakin
        client = Anakin(api_key=WIRE_API_KEY)
        search = client.search(f"wallstreetbets {' '.join(tickers)} stock mention count May 2026")
        if search.results:
            mentions = {t: 5 for t in tickers}
    spike = any(v > 10 for v in mentions.values()) if mentions else False
    return {"mentions": mentions, "spike_detected": spike}

def lstm_forecast(prices, weights, forecast_days=60, seed_capital=1_000_000):
    price_index = (prices * weights[:len(prices.columns)]).sum(axis=1)
    scale = seed_capital / float(price_index.iloc[0])
    portfolio_value = price_index * scale

    try:
        from sklearn.preprocessing import MinMaxScaler
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
        from tensorflow.keras.callbacks import EarlyStopping
        import os as _os
        _os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    except ImportError:
        last = float(portfolio_value.iloc[-1])
        drift = 0.0005
        seq = [last * (1 + drift + np.random.normal(0, 0.01)) for _ in range(forecast_days)]
        return {"forecast": [round(last, 2)] + [round(float(v), 2) for v in seq]}

    returns = portfolio_value.pct_change().dropna().to_numpy(dtype=float).reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(returns)
    seq_len = 60
    X, y = [], []
    for i in range(seq_len, len(scaled)):
        X.append(scaled[i - seq_len:i, 0])
        y.append(scaled[i, 0])
    X = np.array(X).reshape(-1, seq_len, 1)
    y = np.array(y)
    if len(X) < 100:
        last = float(portfolio_value.iloc[-1])
        seq = [last * (1 + 0.0005 + np.random.normal(0, 0.01)) for _ in range(forecast_days)]
        return {"forecast": [round(last, 2)] + [round(float(v), 2) for v in seq]}

    model = Sequential([
        Input(shape=(seq_len, 1)),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    split = int(len(X) * 0.8)
    model.fit(X[:split], y[:split], validation_data=(X[split:], y[split:]),
              epochs=30, batch_size=32, callbacks=[EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)], verbose=0)

    last_seq = scaled[-seq_len:].flatten().tolist()
    preds = []
    for _ in range(forecast_days):
        inp = np.array(last_seq[-seq_len:]).reshape(1, seq_len, 1)
        p = float(model.predict(inp, verbose=0)[0, 0])
        preds.append(p)
        last_seq.append(p)
    pred_returns = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
    last_val = float(portfolio_value.iloc[-1])
    future = [last_val]
    for r in pred_returns:
        future.append(future[-1] * (1.0 + r))
    return {"forecast": [round(v, 2) for v in future]}

def stress_scenarios(path_matrix, seed_capital, reddit_info=None):
    scenarios = [
        {"name": "2008-style Crash", "shock": -0.15, "vol_mult": 2.5, "floor": seed_capital * 0.7},
        {"name": "COVID-style Vol Spike", "shock": -0.10, "vol_mult": 3.0, "floor": seed_capital * 0.7},
        {"name": "Inflation / Rate Shock", "shock": -0.08, "vol_mult": 1.8, "floor": seed_capital * 0.7},
        {"name": "Mild Recession", "shock": -0.05, "vol_mult": 1.5, "floor": seed_capital * 0.7},
        {"name": "Dot-com Bust", "shock": -0.25, "vol_mult": 2.0, "floor": seed_capital * 0.5},
    ]
    if reddit_info and reddit_info.get("spike_detected"):
        scenarios.append({
            "name": "Retail Frenzy (WSB Hype)",
            "shock": -0.12, "vol_mult": 2.0, "floor": seed_capital * 0.6
        })

    results = []
    for sc in scenarios:
        centered = path_matrix - path_matrix.mean(axis=0, keepdims=True)
        stressed = path_matrix.mean(axis=0, keepdims=True) + centered * sc["vol_mult"]
        stressed = stressed * (1.0 + sc["shock"])
        terminal = stressed[:, -1]

        cutoff = np.percentile(terminal, 5)
        var95 = max(0.0, seed_capital - cutoff)
        tail = terminal[terminal <= cutoff]
        cvar95 = max(0.0, seed_capital - float(np.mean(tail))) if len(tail) > 0 else 0.0
        mean_term = float(np.mean(terminal))
        breach = bool(sc["floor"] is not None and np.percentile(terminal, 5) < sc["floor"])

        results.append({
            "scenario": sc["name"],
            "shock": sc["shock"],
            "vol_multiplier": sc["vol_mult"],
            "mean_terminal": round(mean_term, 2),
            "var_95": round(var95, 2),
            "cvar_95": round(cvar95, 2),
            "breach": breach,
        })
    return results

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    tickers = req.tickers
    weights = np.array(req.weights, dtype=float)
    weights = weights / weights.sum()

    prices = fetch_prices(tickers)
    returns = compute_returns(prices)
    mu, cov, chol = covariance_bundle(returns)
    paths, terminal = monte_carlo(mu, chol, weights)
    metrics = risk_metrics(terminal, 1_000_000)
    sentiment = sentiment_analysis(tickers)
    reddit = reddit_hype(tickers)

    vol_adjusted_var = metrics["var"]
    if sentiment["score"] < -0.5:
        vol_adjusted_var = round(metrics["var"] * 1.15, 2)

    forec = lstm_forecast(prices, weights)
    stress = stress_scenarios(paths, 1_000_000, reddit)

    return {
        "var": metrics["var"],
        "cvar": metrics["cvar"],
        "sentiment_adjusted_var": vol_adjusted_var,
        "prob_loss": metrics["prob_loss"],
        "sentiment_score": sentiment["score"],
        "news_summary": sentiment["summary"],
        "headlines": sentiment["headlines"],
        "forecast_60d": forec["forecast"],
        "stress_scenarios": stress,
        "reddit_hype": reddit,
        "config": {"tickers": tickers, "weights": [round(float(w), 4) for w in weights]},
    }

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
