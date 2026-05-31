import numpy as np
import pandas as pd
import yfinance as yf
import os, sys, pickle, json, sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator, model_validator
import jwt

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, ".risk_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

_DATA_IS_SYNTHETIC = False

DEFAULT_ASSETS = {
    "SPY": 0.00078, "QQQ": 0.00100, "AGG": 0.00021, "GLD": 0.00131,
    "NVDA": 0.00150, "AAPL": 0.00095, "MSFT": 0.00088, "GOOGL": 0.00085,
    "AMZN": 0.00110, "META": 0.00120, "TSLA": 0.00180, "VTI": 0.00070,
    "IWM": 0.00075, "EEM": 0.00050, "TLT": 0.00015, "BND": 0.00010,
}
DEFAULT_VOL = 0.015

WIRE_API_KEY = os.environ.get("WIRE_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SHARED_PASSWORD = "riskmaster2024"
JWT_SECRET = os.environ.get("JWT_SECRET", "liverisk-jwt-secret-key-2024-abcdef1234567890")
JWT_ALGORITHM = "HS256"

DB_PATH = os.path.join(PROJECT_ROOT, "liverisk.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            tickers TEXT NOT NULL,
            weights TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="LiveRisk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

security = HTTPBearer(auto_error=False)

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

    @model_validator(mode="after")
    def lengths_match(self):
        if len(self.tickers) != len(self.weights):
            raise ValueError(f"Tickers ({len(self.tickers)}) and weights ({len(self.weights)}) must have the same length")
        return self

class LoginRequest(BaseModel):
    name: str
    password: str

def create_token(name: str) -> str:
    payload = {
        "sub": name,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    name = verify_token(credentials.credentials)
    if name is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return name

@app.post("/login")
def login(req: LoginRequest):
    if req.password != SHARED_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token(req.name)
    return {"token": token, "name": req.name, "password_hint": SHARED_PASSWORD}

def _synthetic_prices(tickers, years=2):
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
    global _DATA_IS_SYNTHETIC
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
        _DATA_IS_SYNTHETIC = False
        print(f"  yfinance: fetched {prices.shape[1]} tickers, {prices.shape[0]} days")
        return prices
    except Exception as e:
        print(f"  yfinance failed ({e}), falling back to synthetic data")
        _DATA_IS_SYNTHETIC = True
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

    try:
        from anakin import Anakin
        client = Anakin(api_key=WIRE_API_KEY)
        search = client.search(f"latest news for {' '.join(tickers)} stock market 2026", limit=10)
        if search.results:
            for r in search.results:
                if r.snippet:
                    headlines.append({"title": r.title or "", "snippet": r.snippet})
    except Exception:
        pass

    if not headlines:
        for t in tickers:
            try:
                tk = yf.Ticker(t)
                news = tk.news or []
                for item in news[:5]:
                    headlines.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("summary", "")
                    })
            except Exception:
                pass

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
    try:
        from anakin import Anakin
        client = Anakin(api_key=WIRE_API_KEY)
        search = client.search(f"wallstreetbets {' '.join(tickers)} stock mention count May 2026", limit=5)
        if search.results:
            mentions = {t: 5 for t in tickers}
    except Exception:
        pass
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

CRISIS_PERIODS = [
    {"name": "COVID Crash (2020)", "start": "2020-02-19", "end": "2020-03-23",
     "desc": "Pandemic selloff — fastest bear market in history, VIX hit 82"},
    {"name": "2022 Rate Hike Selloff", "start": "2022-01-03", "end": "2022-10-12",
     "desc": "Fed hiking cycle — growth stocks crushed, bond yields surged"},
    {"name": "2018 Q4 Meltdown", "start": "2018-10-01", "end": "2018-12-24",
     "desc": "Trade war fears + Fed tightening — S&P 500 fell ~20% in 3 months"},
    {"name": "2023 Banking Crisis", "start": "2023-03-08", "end": "2023-03-23",
     "desc": "SVB/CS collapse — regional bank stocks hammered, system stress"},
]

def compute_max_drawdown(series):
    peak = np.maximum.accumulate(series)
    dd = (series - peak) / peak
    return float(np.min(dd))

def backtest_portfolio(tickers, weights, seed_capital=1_000_000):
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    prices = fetch_prices(tickers, years=12)
    if prices.empty or prices.shape[1] == 0:
        return {"error": "No price data available for backtest", "crises": [], "accuracy": None}

    aligned = prices[tickers] if all(t in prices.columns for t in tickers) else prices
    port_val = (aligned * weights[:len(aligned.columns)]).sum(axis=1)
    scale = seed_capital / float(port_val.iloc[0])
    port_val = port_val * scale

    results = []
    for crisis in CRISIS_PERIODS:
        crisis_start = pd.Timestamp(crisis["start"])
        crisis_end = pd.Timestamp(crisis["end"])
        mask = (port_val.index >= crisis_start) & (port_val.index <= crisis_end)
        crisis_data = port_val[mask]
        if len(crisis_data) < 5:
            continue

        pre_mask = port_val.index < crisis_start
        pre_data = port_val[pre_mask]
        if len(pre_data) < 60:
            continue

        actual_return = float((crisis_data.iloc[-1] - crisis_data.iloc[0]) / crisis_data.iloc[0])
        max_dd = compute_max_drawdown(crisis_data.values)
        actual_var_pct = abs(max_dd)
        actual_var_dollar = actual_var_pct * seed_capital

        pre_returns = pre_data.pct_change().dropna().to_numpy(dtype=float)
        if len(pre_returns) < 10:
            continue
        crisis_days = max(len(crisis_data), 21)
        daily_var = abs(float(np.percentile(pre_returns, 5)))
        var_over_horizon = daily_var * np.sqrt(crisis_days)
        pre_var_pct = min(1.0, var_over_horizon)
        predicted_var = round(pre_var_pct * seed_capital, 2)
        pre_var_pct_display = round(pre_var_pct * 100, 2)

        error_pct = abs(actual_var_dollar - predicted_var) / max(actual_var_dollar, 1)
        within_20pct = error_pct <= 0.20
        within_50pct = error_pct <= 0.50

        results.append({
            "crisis": crisis["name"],
            "desc": crisis["desc"],
            "start": crisis["start"],
            "end": crisis["end"],
            "actual_return_pct": round(actual_return * 100, 2),
            "actual_max_drawdown_pct": round(max_dd * 100, 2),
            "actual_var_dollar": round(actual_var_dollar, 2),
            "predicted_var": predicted_var,
            "predicted_var_pct": pre_var_pct_display,
            "error_pct": round(error_pct * 100, 2),
            "within_20pct": bool(within_20pct),
            "within_50pct": bool(within_50pct),
        })

    if not results:
        return {"error": "Insufficient historical data for backtest", "crises": [], "accuracy": None}

    total = len(results)
    within20 = sum(1 for r in results if r["within_20pct"])
    within50 = sum(1 for r in results if r["within_50pct"])
    avg_error = float(np.mean([r["error_pct"] for r in results]))

    if avg_error < 20:
        grade = "A"
        verdict = "Model predicts actual crisis losses with high accuracy. You can trust the VaR numbers."
    elif avg_error < 40:
        grade = "B"
        verdict = "Model is directionally correct but may underestimate tail risk in severe downturns."
    elif avg_error < 60:
        grade = "C"
        verdict = "Model captures general risk direction but has meaningful error. Use VaR as a guide, not gospel."
    else:
        grade = "D"
        verdict = "Model shows low correlation with actual crisis losses. Consider diversification or hedging."

    accuracy = {
        "grade": grade,
        "verdict": verdict,
        "crises_tested": total,
        "avg_error_pct": round(avg_error, 2),
        "within_20pct": within20,
        "within_50pct": within50,
        "within_20pct_pct": round(within20 / total * 100, 1),
        "within_50pct_pct": round(within50 / total * 100, 1),
    }
    return {"crises": results, "accuracy": accuracy, "using_synthetic_data": _DATA_IS_SYNTHETIC}


@app.post("/analyze")
def analyze(req: AnalyzeRequest, user: str = Depends(get_current_user)):
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

    result = {
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

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO history (user_name, tickers, weights, result) VALUES (?, ?, ?, ?)",
        (user, json.dumps(tickers), json.dumps([round(float(w), 4) for w in weights]), json.dumps(result))
    )
    conn.commit()
    conn.close()

    return result

class SummaryRequest(BaseModel):
    tickers: list[str]
    weights: list[float]
    var: float
    cvar: float
    sentiment_score: float
    prob_loss: float
    forecast_60d: list[float]
    stress_scenarios: list[dict] = []
    backtest_grade: str = ""
    backtest_verdict: str = ""

def groq_summary(data: dict) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        tickers = ", ".join(data.get("tickers", []))
        weights = ", ".join(f"{w*100:.0f}%" for w in data.get("weights", []))
        var = data.get("var", 0)
        cvar = data.get("cvar", 0)
        sentiment = data.get("sentiment_score", 0)
        prob_loss = data.get("prob_loss", 0)
        forecast_start = data.get("forecast_60d", [0])[0] if data.get("forecast_60d") else 0
        forecast_end = data.get("forecast_60d", [0])[-1] if data.get("forecast_60d") else 0
        scenarios = data.get("stress_scenarios", [])
        worst_scenario = max(scenarios, key=lambda s: s.get("var_95", 0)) if scenarios else None
        grade = data.get("backtest_grade", "")
        verdict = data.get("backtest_verdict", "")

        prompt = f"""You are a financial risk analyst explaining portfolio risk to a retail investor. Use plain English. No jargon without defining it. Keep it to 3-4 sentences. The user is looking at a dashboard — tell them what matters.

Portfolio: {tickers} with weights {weights}
95% VaR (Value at Risk): ${var:,.0f} — this means there's a 5% chance of losing more than this in a year
95% CVaR (average loss in worst 5%): ${cvar:,.0f}
FinBERT news sentiment: {sentiment:.2f} (positive = bullish, negative = bearish)
Probability of any loss: {prob_loss*100:.1f}%
60-day LSTM forecast: ${forecast_start:,.0f} → ${forecast_end:,.0f}
Risk grade (backtest vs history): {grade} — {verdict}"""

        if worst_scenario:
            name = worst_scenario.get("scenario") or worst_scenario.get("name", "Unknown")
            loss = worst_scenario.get("var_95", 0)
            prompt += f"\nWorst stress scenario: {name} — estimated loss ${loss:,.0f}"

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.4,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq summary failed: {e}")
        return ""

@app.post("/summary")
def summary(req: SummaryRequest):
    text = groq_summary(req.model_dump())
    return {"summary": text}

@app.post("/backtest")
def backtest(req: AnalyzeRequest, user: str = Depends(get_current_user)):
    tickers = req.tickers
    weights = np.array(req.weights, dtype=float)
    weights = weights / weights.sum()
    return backtest_portfolio(tickers, weights)

@app.get("/history")
def get_history(user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, tickers, weights, result, created_at FROM history WHERE user_name = ? ORDER BY created_at DESC",
        (user,)
    )
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "tickers": json.loads(r[1]),
            "weights": json.loads(r[2]),
            "result": json.loads(r[3]),
            "created_at": r[4],
        }
        for r in rows
    ]

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
