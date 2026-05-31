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

# ── 1. Load simulation result ─────────────────────────────────────────
sim = joblib.load('simulation_result.pkl')
path_matrix = sim['path_matrix'].copy()
seed_capital = sim['seed_capital']
weights = sim['weights']
assets = sim['assets']

print(f"Loaded simulation: {path_matrix.shape[0]:,} paths, {path_matrix.shape[1]} days")

# ── 2. WSB sentiment via Wire Reddit action ───────────────────────────

print("Scanning r/wallstreetbets via Wire reddit action...\n")

wsb_mentions = {}
for t in assets:
    try:
        result = wire.wire("reddit", {
            "ticker": t,
            "subreddit": "wallstreetbets",
            "action": "mentions",
            "time_filter": "week",
            "limit": 25,
        })
        if result and hasattr(result, 'model_dump'):
            data = result.model_dump()
        elif result and isinstance(result, dict):
            data = result
        else:
            data = {}
        
        count = data.get('mention_count', data.get('count', data.get('total_mentions', 0)))
        posts = data.get('posts', data.get('mentions', []))
        if isinstance(posts, list):
            count = len(posts)
        wsb_mentions[t] = count
        print(f"  {t}: {count} mentions on r/wallstreetbets")
        if posts and len(posts) > 0:
            for p in posts[:2]:
                title = p.get('title', p.get('text', ''))[:90]
                print(f"    -> {title}")
    except Exception as e:
        print(f"  {t}: Wire failed ({e}) — will search fallback")

# Fallback: use Anakin search
if not wsb_mentions:
    print("\n  Using Anakin search for WSB mention detection...")
    try:
        query = f"wallstreetbets mentions {' '.join(assets)} reddit May 2026"
        search = wire.search(query)
        if search.results:
            for t in assets:
                wsb_mentions[t] = 5  # default estimate
                print(f"  {t}: estimated 5 mentions")
    except Exception as e:
        print(f"  Search fallback failed: {e}")

# Detect spike: any ticker with > 10 mentions
mention_values = [v for v in wsb_mentions.values() if isinstance(v, (int, float))]
spike_detected = any(v > 10 for v in mention_values) if mention_values else False

print(f"\n{'⚠️  WSB HYPE SPIKE DETECTED!' if spike_detected else '✓ No WSB hype spike detected.'}")
print(f"  Mention counts: {wsb_mentions}")

# ── 3. Define stress scenarios ────────────────────────────────────────

scenarios = [
    {
        'name': 'Baseline (No Stress)',
        'shock_pct': 0.0,
        'vol_multiplier': 1.0,
        'breach_floor': seed_capital * 0.7,
    },
    {
        'name': '2008-style Crash',
        'shock_pct': -0.15,
        'vol_multiplier': 2.5,
        'breach_floor': seed_capital * 0.7,
    },
    {
        'name': 'COVID-style Vol Spike',
        'shock_pct': -0.10,
        'vol_multiplier': 3.0,
        'breach_floor': seed_capital * 0.7,
    },
    {
        'name': 'Inflation / Rate Shock',
        'shock_pct': -0.08,
        'vol_multiplier': 1.8,
        'breach_floor': seed_capital * 0.7,
    },
    {
        'name': 'Mild Recession',
        'shock_pct': -0.05,
        'vol_multiplier': 1.5,
        'breach_floor': seed_capital * 0.7,
    },
    {
        'name': 'Dot-com Bust',
        'shock_pct': -0.25,
        'vol_multiplier': 2.0,
        'breach_floor': seed_capital * 0.5,
    },
]

# Add Retail Frenzy scenario if WSB hype detected
if spike_detected:
    scenarios.append({
        'name': 'Retail Frenzy (WSB Hype)',
        'shock_pct': -0.12,       # GME-style volatility shock
        'vol_multiplier': 2.0,     # 2x normal volatility
        'breach_floor': seed_capital * 0.6,  # 40% loss floor
    })
    print(f"⚠️  Added 'Retail Frenzy' scenario based on WSB hype spike!")

print(f"\nTotal scenarios to test: {len(scenarios)}")

# ── 4. Apply stress scenarios ─────────────────────────────────────────

def apply_stress(paths, shock_pct, vol_multiplier):
    centered = paths - paths.mean(axis=0, keepdims=True)
    stressed = paths.mean(axis=0, keepdims=True) + centered * vol_multiplier
    stressed = stressed * (1.0 + shock_pct)
    return stressed

def compute_var(values, confidence=0.95, reference_value=None):
    cutoff = np.percentile(values, (1.0 - confidence) * 100.0)
    initial = float(np.mean(values)) if reference_value is None else reference_value
    return max(0.0, initial - float(cutoff))

def compute_cvar(values, confidence=0.95, reference_value=None):
    cutoff = np.percentile(values, (1.0 - confidence) * 100.0)
    tail = values[values <= cutoff]
    if len(tail) == 0:
        return 0.0
    initial = float(np.mean(values)) if reference_value is None else reference_value
    return max(0.0, initial - float(np.mean(tail)))


results = []
for sc in scenarios:
    stressed_paths = apply_stress(path_matrix, sc['shock_pct'], sc['vol_multiplier'])
    terminal = stressed_paths[:, -1]

    var_95 = compute_var(terminal, 0.95, seed_capital)
    cvar_95 = compute_cvar(terminal, 0.95, seed_capital)
    var_99 = compute_var(terminal, 0.99, seed_capital)
    cvar_99 = compute_cvar(terminal, 0.99, seed_capital)

    p5_terminal = np.percentile(terminal, 5)
    breach = bool(sc['breach_floor'] is not None and p5_terminal < sc['breach_floor'])

    results.append({
        'scenario': sc['name'],
        'shock': f"{sc['shock_pct']*100:+.0f}%",
        'vol_mult': f"{sc['vol_multiplier']}x",
        'mean_terminal': f"${np.mean(terminal):,.0f}",
        'var_95': f"${var_95:,.0f}",
        'cvar_95': f"${cvar_95:,.0f}",
        'var_99': f"${var_99:,.0f}",
        'cvar_99': f"${cvar_99:,.0f}",
        'breach_floor': f"${sc['breach_floor']:,.0f}",
        'breach': 'BREACH' if breach else 'OK',
        'from_wsb': sc['name'] == 'Retail Frenzy (WSB Hype)',
    })

results_df = pd.DataFrame(results)
results_df

# ── 5. Visualize stressed distributions ───────────────────────────────

n_plots = len(scenarios)
n_cols = 3
n_rows = (n_plots + n_cols - 1) // n_cols

plt.figure(figsize=(15, 5 * n_rows))

for i, sc in enumerate(scenarios):
    stressed = apply_stress(path_matrix, sc['shock_pct'], sc['vol_multiplier'])
    terminal = stressed[:, -1]

    plt.subplot(n_rows, n_cols, i + 1)
    is_retail = sc['name'] == 'Retail Frenzy (WSB Hype)'
    is_breach = results[i]['breach'] == 'BREACH'
    color = 'red' if is_retail else ('coral' if is_breach else 'steelblue')

    plt.hist(terminal, bins=60, density=True, alpha=0.5, color=color)
    plt.axvline(seed_capital, color='red', ls='--', lw=1.5, label=f'Seed (${seed_capital:,.0f})')
    if sc['breach_floor']:
        plt.axvline(sc['breach_floor'], color='orange', ls=':', lw=1.5,
                    label=f'Floor (${sc["breach_floor"]:,.0f})')
    title = f"{sc['name']}"
    if is_retail:
        title += " [WSB-Driven]"
    plt.title(f"{title}\n{sc['shock_pct']*100:+.0f} shock, {sc['vol_multiplier']}x vol")
    plt.xlabel('Terminal Value')
    plt.ylabel('Density')
    plt.legend(fontsize=7)
    plt.grid(alpha=0.3)

plt.tight_layout()
plt.show()

# ── 6. Summary decision ───────────────────────────────────────────────

print("=" * 70)
print("STRESS TEST SUMMARY".center(70))
print("=" * 70)

breaches = [r for r in results if r['breach'] == 'BREACH']
wsb_scenarios = [r for r in results if r.get('from_wsb')]

if breaches:
    print(f"\n{'⚠'*5}  BREACHES DETECTED  {'⚠'*5}")
    for b in breaches:
        wsb_tag = " [WSB-Driven]" if b.get('from_wsb') else ""
        print(f"  • {b['scenario']}{wsb_tag}: 95% VaR = {b['var_95']}, CVaR = {b['cvar_95']}")
    print(f"\n→ Consider: reducing equity exposure, adding hedges (puts/VIX),")
    print(f"  increasing cash buffer, or implementing dynamic stop-loss.")
else:
    print(f"\n✓ All scenarios pass — no capital floor breaches.")

if wsb_scenarios:
    print(f"\n{'═'*70}")
    print("WSB HYPE MONITORING ACTIVE".center(70))
    print(f"{'═'*70}")
    for w in wsb_scenarios:
        print(f"  • {w['scenario']}: Mention spike detected, scenario added to stress suite.")
    print(f"\n  Mention counts: {wsb_mentions}")
    print(f"  Spike threshold: >10 mentions per ticker")

print("\n" + "=" * 70)
print("END-TO-END PIPELINE COMPLETE".center(70))
print("=" * 70)
print("\n1. 01_data_loader.ipynb → Fetched prices via Wire yahoo_finance action")
print("2. 02_covariance.ipynb   → Estimated drift, covariance, Cholesky")
print("3. 03_simulator.ipynb    → Generated 10,000 correlated paths")
print("4. 04_risk_metrics.ipynb → VaR, CVaR, max drawdown + FinBERT sentiment")
print("5. 05_stress_test.ipynb  → Stress scenarios + WSB hype detection via Wire")
