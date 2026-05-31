# ── Imports ──────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import warnings
import os
warnings.filterwarnings('ignore')

WIRE_API_KEY = os.environ.get("WIRE_API_KEY", "ask_654fad46faed02cec9e79bacf7786be752a6b27c5b1031019b4a0a8948f5b081")

from anakin import Anakin
wire = Anakin(api_key=WIRE_API_KEY)

# ── 1. Load simulation results ────────────────────────────────────────
sim = joblib.load('simulation_result.pkl')
path_matrix = sim['path_matrix']
terminal_values = sim['terminal_values']
seed_capital = sim['seed_capital']
n_sims = sim['n_sims']
assets = sim['assets']

print(f"Loaded {n_sims:,} simulation paths for {assets}")

# ── 2a. Pull headlines via Wire reuters action ────────────────────────

print("Fetching news headlines via Wire reuters action...")

headlines = []
for t in assets:
    try:
        result = wire.wire("reuters", {"ticker": t, "action": "headlines", "limit": 10})
        if result and hasattr(result, 'model_dump'):
            data = result.model_dump()
        elif result and isinstance(result, dict):
            data = result
        else:
            data = {}
        if data and 'headlines' in data:
            for h in data['headlines']:
                headlines.append(h.get('title', h.get('headline', '')))
            print(f"  {t}: {len(data['headlines'])} headlines")
    except Exception as e:
        print(f"  {t}: Wire failed ({e}) — will use Anakin search fallback")

# Fallback: use Anakin search for news
if not headlines:
    print("\n  Using Anakin search as fallback for news...")
    try:
        search = wire.search(f"latest financial news for {' '.join(assets)} 2026")
        if search.results:
            for r in search.results[:20]:
                headlines.append(f"{r.title}: {r.snippet}")
    except Exception as e:
        print(f"  Search fallback also failed: {e}")

print(f"\nTotal headlines collected: {len(headlines)}")
for h in headlines[:5]:
    print(f"  • {h[:100]}")

# ── 2b. Compute FinBERT sentiment score ───────────────────────────────

sentiment_score = 0.0
sentiment_details = []

if headlines:
    try:
        from transformers import pipeline
        classifier = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            device=-1  # use CPU
        )
        
        # Truncate each headline to 512 tokens for FinBERT
        results = classifier(headlines, truncation=True, max_length=512)
        
        # Convert to numeric: positive → +score, negative → -score, neutral → 0
        scores = []
        for r in results:
            label = r['label']
            score = r['score']
            if label.lower() == 'positive':
                scores.append(score)
            elif label.lower() == 'negative':
                scores.append(-score)
            else:
                scores.append(0.0)
        
        sentiment_score = round(float(np.mean(scores)), 4)
        sentiment_details = [
            {"headline": h[:80], "label": r['label'], "confidence": round(r['score'], 3)}
            for h, r in zip(headlines[:10], results[:10])
        ]
        
        print(f"FinBERT Sentiment Score: {sentiment_score:.4f} (range: -1 to +1)")
        print(f"\nSample classifications:")
        for d in sentiment_details[:5]:
            print(f"  [{d['label']:>8} @ {d['confidence']:.2f}] {d['headline'][:70]}")
            
    except ImportError as e:
        print(f"FinBERT unavailable ({e}). Using fallback heuristic.")
        sentiment_score = 0.0
    except Exception as e:
        print(f"FinBERT error: {e}. Using sentiment score of 0.")
        sentiment_score = 0.0
else:
    print("No headlines to analyze. Sentiment score = 0.0")

# Determine sentiment category
if sentiment_score > 0.3:
    sentiment_label = "BULLISH"
elif sentiment_score < -0.3:
    sentiment_label = "BEARISH"
else:
    sentiment_label = "NEUTRAL"

news_summary = (
    f"Analyzed {len(headlines)} headlines across {len(assets)} tickers. "
    f"FinBERT sentiment: {sentiment_score:.3f} ({sentiment_label}). "
    + ("Volatility adjusted +15% due to bearish sentiment." if sentiment_score < -0.5 else "No volatility adjustment needed.")
)
print(f"\n{news_summary}")

# ── 3. Value at Risk (VaR) ────────────────────────────────────────────

confidence = 0.95
percentile_rank = (1.0 - confidence) * 100.0
cutoff_value = np.percentile(terminal_values, percentile_rank)
var_95 = max(0.0, seed_capital - cutoff_value)

cutoff_value_99 = np.percentile(terminal_values, 1.0)
var_99 = max(0.0, seed_capital - cutoff_value_99)

print(f"95% VaR: ${var_95:,.2f}")
print(f"99% VaR: ${var_99:,.2f}")

# ── 4. Conditional VaR (CVaR / Expected Shortfall) ────────────────────

def compute_cvar(values, confidence=0.95, reference_value=None):
    cutoff = np.percentile(values, (1.0 - confidence) * 100.0)
    tail = values[values <= cutoff]
    if len(tail) == 0:
        return 0.0
    initial = float(np.mean(values)) if reference_value is None else reference_value
    return max(0.0, initial - float(np.mean(tail)))

cvar_95 = compute_cvar(terminal_values, confidence=0.95, reference_value=seed_capital)
cvar_99 = compute_cvar(terminal_values, confidence=0.99, reference_value=seed_capital)

print(f"95% CVaR: ${cvar_95:,.2f}")
print(f"99% CVaR: ${cvar_99:,.2f}")

# ── 5. Sentiment-Adjusted VaR ─────────────────────────────────────────

# If FinBERT sentiment is < -0.5, increase VaR by 15%
sentiment_adjusted_var = var_95
if sentiment_score < -0.5:
    sentiment_adjusted_var = round(var_95 * 1.15, 2)
    print(f"⚠️  Bearish sentiment ({sentiment_score:.3f}) — adjusting VaR +15%")

print(f"\nStandard 95% VaR:         ${var_95:,.2f}")
print(f"Sentiment-Adjusted VaR:   ${sentiment_adjusted_var:,.2f}")
print(f"Adjustment factor:        {'1.15x (bearish)' if sentiment_score < -0.5 else '1.0x (neutral/bullish)'}")

# ── 6. Max Drawdown & Probability of Loss ────────────────────────────

def compute_max_drawdown(paths):
    running_peak = np.maximum.accumulate(paths, axis=1)
    drawdowns = (running_peak - paths) / np.where(running_peak > 0, running_peak, 1)
    return drawdowns.max(axis=1)

drawdowns = compute_max_drawdown(path_matrix)
prob_loss = np.mean(terminal_values < seed_capital)

print(f"Max drawdown stats:")
print(f"  Mean: {np.mean(drawdowns):.2%}")
print(f"  Median: {np.median(drawdowns):.2%}")
print(f"  P95: {np.percentile(drawdowns, 95):.2%}")
print(f"  Worst: {np.max(drawdowns):.2%}")
print(f"\nProbability of loss: {prob_loss:.2%}")

# ── 7. Summary with sentiment data ────────────────────────────────────

summary = {
    'Seed Capital': f'${seed_capital:,.0f}',
    'Mean Terminal': f'${np.mean(terminal_values):,.0f}',
    'Median Terminal': f'${np.median(terminal_values):,.0f}',
    'Worst Terminal': f'${np.min(terminal_values):,.0f}',
    '95% VaR': f'${var_95:,.0f}',
    'Sentiment-Adj VaR': f'${sentiment_adjusted_var:,.0f}',
    '99% VaR': f'${var_99:,.0f}',
    '95% CVaR': f'${cvar_95:,.0f}',
    '99% CVaR': f'${cvar_99:,.0f}',
    'Mean Max DD': f'{np.mean(drawdowns):.2%}',
    'P95 Max DD': f'{np.percentile(drawdowns, 95):.2%}',
    'Prob of Loss': f'{prob_loss:.2%}',
    '---': '---',
    'Sentiment Score': f'{sentiment_score:.4f}',
    'Sentiment Label': sentiment_label,
    'News Summary': news_summary,
    'Headlines Analyzed': str(len(headlines)),
}

print("\n" + "="*50)
print("RISK SUMMARY WITH SENTIMENT".center(50))
print("="*50)
for k, v in summary.items():
    print(f"  {k:25s}: {v}")

# ── 8. Visualize ──────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: terminal distribution with VaR/CVaR + sentiment marker
ax = axes[0]
ax.hist(terminal_values, bins=80, density=True, alpha=0.5, color='steelblue')
ax.axvline(seed_capital, color='red', ls='--', lw=2, label='Seed')
ax.axvline(cutoff_value, color='orange', ls='--', lw=2,
           label=f'95% VaR cutoff (${cutoff_value:,.0f})')
if sentiment_score < -0.5:
    adj_cutoff = np.percentile(terminal_values * 1.15, 5)
    ax.axvline(adj_cutoff, color='darkred', ls=':', lw=2,
               label=f'Sentiment-adj VaR (${adj_cutoff:,.0f})')
ax.set_title(f'Terminal Distribution (sentiment: {sentiment_label})')
ax.set_xlabel('Portfolio Value ($)')
ax.set_ylabel('Density')
ax.legend()
ax.grid(alpha=0.3)

# Right: drawdown distribution
ax = axes[1]
ax.hist(drawdowns, bins=60, density=True, alpha=0.5, color='coral')
ax.axvline(np.mean(drawdowns), color='red', ls='--', lw=2,
           label=f'Mean DD: {np.mean(drawdowns):.2%}')
ax.axvline(np.percentile(drawdowns, 95), color='darkred', ls='--', lw=2,
           label=f'P95 DD: {np.percentile(drawdowns, 95):.2%}')
ax.set_title('Maximum Drawdown Distribution')
ax.set_xlabel('Drawdown (%)')
ax.set_ylabel('Density')
ax.legend()
ax.grid(alpha=0.3)

plt.tight_layout()
plt.show()

print("\n✓ Risk metrics complete with sentiment adjustment.")
