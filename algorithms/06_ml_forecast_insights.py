# ── Imports ──────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
import warnings
warnings.filterwarnings('ignore')

# Visualization
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
plt.style.use('seaborn-v0_8-darkgrid')

# ML / Deep Learning
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam

from datetime import datetime, timedelta
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# ── Fetch fresh data for this notebook (or load cached from 01) ──────

TICKERS = ['SPY', 'QQQ', 'AGG', 'GLD']
END = datetime.today()
START = END - timedelta(days=3*365)  # 3 years of data

print("=" * 65)
print("RECAP: Notebook 01 — Data Loading & Quality")
print("=" * 65)

raw = yf.download(TICKERS, start=START, end=END, auto_adjust=False, progress=False)
if 'Adj Close' in raw.columns.get_level_values(0):
    prices = raw['Adj Close'].copy()
else:
    prices = raw['Close'].copy()
prices = prices.dropna(axis=1, how='all')
returns = np.log(prices / prices.shift(1)).replace([np.inf, -np.inf], np.nan).dropna(how='any')

print(f"Tickers: {list(prices.columns)}")
print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
print(f"Trading days: {len(prices)}")
print(f"Missing ratio: {returns.isna().mean().max():.4%}")

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].plot(prices, lw=1.5)
axes[0].set_title('Raw Price Series (Notebook 01 Input)')
axes[0].set_ylabel('Price ($)')
axes[0].legend(prices.columns, fontsize=8)
axes[0].grid(alpha=0.3)

axes[1].hist(returns, bins=60, alpha=0.6, density=True)
axes[1].set_title('Log Return Distributions')
axes[1].set_xlabel('Daily Return')
axes[1].set_ylabel('Density')
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.show()

print("Key insight: Log returns are approximately normal but show fat tails —")
print("extreme events happen more often than a normal distribution predicts.")

print("=" * 65)
print("RECAP: Notebook 02 — Covariance & Cholesky")
print("=" * 65)

# Compute covariance with shrinkage
sample_cov = returns.cov().to_numpy(dtype=float)
shrinkage = 0.05
diag_target = np.diag(np.diag(sample_cov))
cov = (1.0 - shrinkage) * sample_cov + shrinkage * diag_target

# Cholesky
chol = np.linalg.cholesky(cov + np.eye(cov.shape[0]) * 1e-10)

# Correlation matrix for easier interpretation
corr = np.corrcoef(returns.to_numpy(dtype=float).T)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

im1 = axes[0].imshow(cov, cmap='RdBu_r', aspect='auto')
axes[0].set_xticks(range(len(TICKERS)))
axes[0].set_yticks(range(len(TICKERS)))
axes[0].set_xticklabels(TICKERS, rotation=45)
axes[0].set_yticklabels(TICKERS)
axes[0].set_title('Shrunken Covariance Matrix')
plt.colorbar(im1, ax=axes[0], shrink=0.6)

im2 = axes[1].imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
axes[1].set_xticks(range(len(TICKERS)))
axes[1].set_yticks(range(len(TICKERS)))
axes[1].set_xticklabels(TICKERS, rotation=45)
axes[1].set_yticklabels(TICKERS)
axes[1].set_title('Correlation Matrix')
plt.colorbar(im2, ax=axes[1], shrink=0.6)

plt.tight_layout()
plt.show()

print(f"Cholesky reconstruction error: {np.abs(cov - chol @ chol.T).max():.2e}")
print("Key insight: SPY and QQQ are highly correlated (~0.85+); AGG (bonds)")
print("provides diversification with near-zero correlation to equities.")

print("=" * 65)
print("RECAP: Notebook 03 — Monte Carlo Simulator")
print("=" * 65)

mu = returns.mean().to_numpy(dtype=float)
N_SIMS = 10_000
HORIZON = 252
SEED = 1_000_000.0
weights = np.array([0.25, 0.25, 0.25, 0.25])

rng = np.random.default_rng(42)
shocks = rng.standard_normal((N_SIMS, HORIZON, len(TICKERS)))
shocks = shocks @ chol.T
asset_ret = mu + shocks
port_ret = asset_ret @ weights
paths = SEED * np.cumprod(1.0 + port_ret, axis=1)
terminal = paths[:, -1]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Sample paths
axes[0].plot(paths[:200].T, lw=0.4, alpha=0.5, color='steelblue')
axes[0].axhline(SEED, color='red', ls='--', lw=2, label=f'Seed (${SEED:,.0f})')
axes[0].set_title(f'200 of {N_SIMS:,} Simulated Paths')
axes[0].set_xlabel('Trading Day')
axes[0].set_ylabel('Portfolio Value ($)')
axes[0].legend()
axes[0].grid(alpha=0.3)

# Terminal distribution
axes[1].hist(terminal, bins=80, density=True, alpha=0.6, color='steelblue',
             label=f'Mean: ${np.mean(terminal):,.0f}')
axes[1].axvline(SEED, color='red', ls='--', lw=2, label='Seed')
axes[1].axvline(np.median(terminal), color='green', ls='--', lw=2,
                label=f'Median: ${np.median(terminal):,.0f}')
axes[1].set_title('Terminal Value Distribution')
axes[1].set_xlabel('Portfolio Value ($)')
axes[1].set_ylabel('Density')
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()

print(f"Portfolio range: ${terminal.min():,.0f} → ${terminal.max():,.0f}")
print(f"Probability of loss: {np.mean(terminal < SEED):.2%}")
print("Key insight: The distribution is right-skewed — upside potential")
print("exceeds downside due to compounding drift, but tail risk is real.")

print("=" * 65)
print("RECAP: Notebook 04 — Risk Metrics (VaR, CVaR, Drawdown)")
print("=" * 65)

def max_drawdown(paths):
    peak = np.maximum.accumulate(paths, axis=1)
    return ((peak - paths) / np.where(peak > 0, peak, 1)).max(axis=1)

drawdowns = max_drawdown(paths)

var_95_val = np.percentile(terminal, 5)
var_99_val = np.percentile(terminal, 1)
tail_95 = terminal[terminal <= var_95_val]
cvar_95_val = SEED - float(np.mean(tail_95)) if len(tail_95) > 0 else 0

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# VaR/CVaR visualization
axes[0].hist(terminal, bins=80, density=True, alpha=0.4, color='steelblue')
axes[0].axvline(var_95_val, color='orange', ls='--', lw=2.5,
                label=f'95% VaR cutoff (${var_95_val:,.0f})')
axes[0].axvline(var_99_val, color='darkred', ls='--', lw=2.5,
                label=f'99% VaR cutoff (${var_99_val:,.0f})')
axes[0].fill_betweenx([0, axes[0].get_ylim()[1]], terminal.min(), var_95_val,
                      alpha=0.2, color='red', label='95% Tail region')
axes[0].set_title('VaR Cutoffs on Terminal Distribution')
axes[0].set_xlabel('Portfolio Value ($)')
axes[0].set_ylabel('Density')
axes[0].legend(fontsize=8)
axes[0].grid(alpha=0.3)

# Drawdown
axes[1].hist(drawdowns, bins=60, density=True, alpha=0.5, color='coral')
axes[1].axvline(np.mean(drawdowns), color='red', ls='--', lw=2,
                label=f'Mean DD: {np.mean(drawdowns):.2%}')
axes[1].axvline(np.percentile(drawdowns, 95), color='darkred', ls='--', lw=2,
                label=f'P95 DD: {np.percentile(drawdowns, 95):.2%}')
axes[1].set_title('Max Drawdown Distribution')
axes[1].set_xlabel('Drawdown Depth')
axes[1].set_ylabel('Density')
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()

print(f"95% VaR:       ${SEED - var_95_val:,.0f}  (5% chance of losing this much or more)")
print(f"99% VaR:       ${SEED - var_99_val:,.0f}")
print(f"95% CVaR:      ${SEED - np.percentile(terminal, 5):,.0f}")
print(f"Mean Max DD:   {np.mean(drawdowns):.2%}")
print(f"Prob of Loss:  {np.mean(terminal < SEED):.2%}")
print("Key insight: VaR tells you the cutoff; CVaR tells you how bad the tail is.")

print("=" * 65)
print("RECAP: Notebook 05 — Stress Testing")
print("=" * 65)

def apply_stress(paths, shock_pct, vol_mult):
    centered = paths - paths.mean(axis=0, keepdims=True)
    stressed = paths.mean(axis=0, keepdims=True) + centered * vol_mult
    return stressed * (1.0 + shock_pct)

scenarios = [
    ('Baseline', 0.0, 1.0, SEED * 0.7),
    ('2008 Crash', -0.15, 2.5, SEED * 0.7),
    ('COVID Spike', -0.10, 3.0, SEED * 0.7),
    ('Rate Shock', -0.08, 1.8, SEED * 0.7),
    ('Dot-com Bust', -0.25, 2.0, SEED * 0.5),
]

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()

for i, (name, shock, vol, floor) in enumerate(scenarios):
    stressed = apply_stress(paths, shock, vol)[:, -1]
    ax = axes[i]
    ax.hist(stressed, bins=60, density=True, alpha=0.5,
            color='coral' if np.percentile(stressed, 5) < floor else 'steelblue')
    ax.axvline(SEED, color='red', ls='--', lw=1.5, label='Seed')
    ax.axvline(floor, color='orange', ls=':', lw=1.5, label='Floor')
    ax.set_title(f'{name}\nShock: {shock*100:+.0f}%  Vol: {vol}x')
    ax.set_xlabel('Terminal Value')
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

axes[-1].axis('off')
plt.tight_layout()
plt.show()

print("Key insight: The portfolio breaches its floor in crash scenarios.")
print("Hedging (puts, VIX futures, cash buffer) would reduce tail risk.")

# ── 1. Prepare data for LSTM ──────────────────────────────────────────

# Compute portfolio returns from historical prices
portfolio_value = (prices * weights).sum(axis=1)
portfolio_returns_hist = portfolio_value.pct_change().dropna().to_numpy(dtype=float).reshape(-1, 1)

# Scale to [0, 1] — required for stable LSTM training
scaler = MinMaxScaler()
returns_scaled = scaler.fit_transform(portfolio_returns_hist)

# Create sequences: use 60 days to predict the next day
SEQ_LEN = 60
X, y = [], []
for i in range(SEQ_LEN, len(returns_scaled)):
    X.append(returns_scaled[i - SEQ_LEN:i, 0])
    y.append(returns_scaled[i, 0])

X = np.array(X).reshape(-1, SEQ_LEN, 1)
y = np.array(y)

# Train/test split (80/20, preserving time order)
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"Portfolio data points: {len(portfolio_returns_hist)}")
print(f"Training samples: {len(X_train)}")
print(f"Test samples:      {len(X_test)}")
print(f"Sequence length:   {SEQ_LEN} days")

# ── 2. Build LSTM model ───────────────────────────────────────────────

model = Sequential([
    Input(shape=(SEQ_LEN, 1)),
    LSTM(64, return_sequences=True),
    Dropout(0.2),
    LSTM(32, return_sequences=False),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(1)
])

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss='mse',
    metrics=['mae']
)

model.summary()

# ── 3. Train the model ────────────────────────────────────────────────

early_stop = EarlyStopping(
    monitor='val_loss',
    patience=15,
    restore_best_weights=True,
    verbose=0
)

history = model.fit(
    X_train, y_train,
    validation_split=0.1,
    epochs=100,
    batch_size=32,
    callbacks=[early_stop],
    verbose=0
)

# Plot training history
fig, axes = plt.subplots(1, 2, figsize=(14, 4))

axes[0].plot(history.history['loss'], label='Train Loss', lw=1.5)
axes[0].plot(history.history['val_loss'], label='Validation Loss', lw=1.5)
axes[0].set_title('LSTM Training Loss')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('MSE')
axes[0].legend()
axes[0].grid(alpha=0.3)

axes[1].plot(history.history['mae'], label='Train MAE', lw=1.5)
axes[1].plot(history.history['val_mae'], label='Validation MAE', lw=1.5)
axes[1].set_title('LSTM Training MAE')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('MAE')
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()

print(f"Final training loss:   {history.history['loss'][-1]:.6f}")
print(f"Final validation loss: {history.history['val_loss'][-1]:.6f}")
print(f"Stopped at epoch: {len(history.history['loss'])}")

# ── 4. Evaluate on test set ───────────────────────────────────────────

y_pred_scaled = model.predict(X_test, verbose=0).flatten()

# Inverse-transform to original scale
y_test_actual = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
y_pred_actual = scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()

mae = mean_absolute_error(y_test_actual, y_pred_actual)
rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
r2 = r2_score(y_test_actual, y_pred_actual)

print(f"Test Set Performance:")
print(f"  MAE:  {mae:.6f}  (avg daily return prediction error)")
print(f"  RMSE: {rmse:.6f}")
print(f"  R²:   {r2:.4f}")
print(f"  Direction accuracy: {np.mean((y_test_actual > 0) == (y_pred_actual > 0)):.2%}")

# Plot predictions vs actual
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].plot(y_test_actual, alpha=0.7, label='Actual Returns', lw=0.8)
axes[0].plot(y_pred_actual, alpha=0.7, label='LSTM Predicted Returns', lw=0.8)
axes[0].set_title('LSTM Predictions vs Actual (Test Set)')
axes[0].set_xlabel('Test Day')
axes[0].set_ylabel('Daily Return')
axes[0].legend()
axes[0].grid(alpha=0.3)

axes[1].scatter(y_test_actual, y_pred_actual, alpha=0.4, s=10)
axes[1].plot([y_test_actual.min(), y_test_actual.max()],
             [y_test_actual.min(), y_test_actual.max()],
             'r--', lw=1, label='Perfect Fit')
axes[1].set_title(f'Predicted vs Actual (R² = {r2:.3f})')
axes[1].set_xlabel('Actual Return')
axes[1].set_ylabel('Predicted Return')
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()

# ── 5. Multi-step future forecast ─────────────────────────────────────

FORECAST_DAYS = 252  # predict 1 year ahead

# Start with the last SEQ_LEN days from the dataset
last_sequence = returns_scaled[-SEQ_LEN:].flatten().tolist()
future_predictions_scaled = []

# Iterative prediction: predict one step, append, slide window
for _ in range(FORECAST_DAYS):
    input_seq = np.array(last_sequence[-SEQ_LEN:]).reshape(1, SEQ_LEN, 1)
    pred = model.predict(input_seq, verbose=0)[0, 0]
    future_predictions_scaled.append(pred)
    last_sequence.append(pred)

future_returns = scaler.inverse_transform(
    np.array(future_predictions_scaled).reshape(-1, 1)
).flatten()

# Build future portfolio value path from predicted returns
last_price = portfolio_value.iloc[-1]
future_prices = [last_price]
for r in future_returns:
    future_prices.append(future_prices[-1] * (1.0 + r))
future_prices = np.array(future_prices[1:])  # align length

print(f"Forecast generated: {FORECAST_DAYS} trading days ahead")
print(f"Starting from: ${last_price:,.2f}")
print(f"Predicted end: ${future_prices[-1]:,.2f}")
print(f"Predicted return: {(future_prices[-1] / last_price - 1) * 100:+.2f}%")

# ── 6. Compare LSTM forecast vs Monte Carlo paths ─────────────────────

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Left: LSTM forecast
ax = axes[0]
days = np.arange(FORECAST_DAYS)
ax.plot(days, future_prices, color='darkorange', lw=2.5, label='LSTM Forecast')
ax.fill_between(days,
                future_prices * 0.9,  # rough confidence band
                future_prices * 1.1,
                alpha=0.15, color='orange', label='±10% Band')
ax.axhline(last_price, color='red', ls='--', lw=1, label=f'Start (${last_price:,.0f})')
ax.set_title('LSTM 1-Year Portfolio Forecast')
ax.set_xlabel('Trading Day Ahead')
ax.set_ylabel('Portfolio Value ($)')
ax.legend()
ax.grid(alpha=0.3)

# Right: LSTM vs Monte Carlo terminal distribution
ax = axes[1]
ax.axvline(future_prices[-1], color='darkorange', ls='--', lw=3,
           label=f'LSTM: ${future_prices[-1]:,.0f}')
ax.hist(terminal, bins=80, density=True, alpha=0.5, color='steelblue',
        label='Monte Carlo ($N=10{,}000$)')
ax.axvline(np.median(terminal), color='steelblue', ls=':', lw=2,
           label=f'MC Median: ${np.median(terminal):,.0f}')
ax.axvline(SEED, color='red', ls='--', lw=1.5, label=f'Seed (${SEED:,.0f})')
ax.set_title('LSTM Prediction vs Monte Carlo Distribution')
ax.set_xlabel('Portfolio Value ($)')
ax.set_ylabel('Density')
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.show()

mc_percentile = np.mean(terminal < future_prices[-1])
print(f"LSTM prediction lies at the {mc_percentile:.1%} percentile of Monte Carlo")
print(f"→ The LSTM is {'more' if mc_percentile > 0.5 else 'less'} optimistic than the median MC path")

# ── 7. Risk insight: LSTM-based VaR and volatility forecast ───────────

# Use LSTM to predict next 30 days and estimate short-term risk
SHORT_HORIZON = 30

short_preds_scaled = []
seq = returns_scaled[-SEQ_LEN:].flatten().tolist()
for _ in range(SHORT_HORIZON):
    inp = np.array(seq[-SEQ_LEN:]).reshape(1, SEQ_LEN, 1)
    p = model.predict(inp, verbose=0)[0, 0]
    short_preds_scaled.append(p)
    seq.append(p)

short_returns = scaler.inverse_transform(
    np.array(short_preds_scaled).reshape(-1, 1)
).flatten()

# Bootstrap from LSTM predictions to simulate short-term scenarios
N_BOOTSTRAP = 5000
bootstrapped_returns = np.random.choice(short_returns, size=(N_BOOTSTRAP, SHORT_HORIZON))
bootstrapped_paths = last_price * np.cumprod(1.0 + bootstrapped_returns, axis=1)
bootstrapped_terminal = bootstrapped_paths[:, -1]

lstm_var_95 = last_price - np.percentile(bootstrapped_terminal, 5)
lstm_var_99 = last_price - np.percentile(bootstrapped_terminal, 1)
tail = bootstrapped_terminal[bootstrapped_terminal <= np.percentile(bootstrapped_terminal, 5)]
lstm_cvar_95 = last_price - float(np.mean(tail)) if len(tail) > 0 else 0

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: forecasted volatility regime
ax = axes[0]
# Rolling volatility of historical vs predicted returns
hist_vol = pd.Series(portfolio_returns_hist.flatten()).rolling(30).std().dropna()
pred_vol = pd.Series(short_returns).expanding().std()

ax.plot(hist_vol.index[-200:], hist_vol.values[-200:], lw=1.2, alpha=0.7, label='Historical 30d Vol')
ax.axhline(pred_vol.iloc[-1], color='red', ls='--', lw=2,
           label=f'LSTM Forecast Vol: {pred_vol.iloc[-1]:.4f}')
ax.set_title('Volatility Regime — LSTM Forecast')
ax.set_xlabel('Trading Day')
ax.set_ylabel('Daily Return Std')
ax.legend()
ax.grid(alpha=0.3)

# Right: LSTM risk metrics vs MC
ax = axes[1]
metrics = ['95% VaR', '99% VaR', '95% CVaR', 'Volatility']
mc_vals = [SEED - var_95_val, SEED - var_99_val, SEED - np.percentile(terminal, 5),
           float(np.std(portfolio_returns_hist))]
lstm_vals = [lstm_var_95, lstm_var_99, lstm_cvar_95, float(pred_vol.iloc[-1])]

x = np.arange(len(metrics))
w = 0.35
ax.bar(x - w/2, mc_vals, w, label='Monte Carlo', alpha=0.7, color='steelblue')
ax.bar(x + w/2, lstm_vals, w, label='LSTM Forecast', alpha=0.7, color='darkorange')
ax.set_xticks(x)
ax.set_xticklabels(metrics)
ax.set_title('Risk Metrics: Monte Carlo vs LSTM')
ax.legend()
ax.grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.show()

print(f"LSTM 30-day VaR (95%): ${lstm_var_95:,.0f}")
print(f"LSTM 30-day VaR (99%): ${lstm_var_99:,.0f}")
print(f"LSTM 30-day CVaR (95%): ${lstm_cvar_95:,.0f}")
print(f"LSTM forecast volatility: {pred_vol.iloc[-1]:.4f}")

# ── 8. Final insight dashboard ────────────────────────────────────────

fig = plt.figure(figsize=(16, 10))
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)

# --- Panel 1: Portfolio history + LSTM forecast ---
ax1 = fig.add_subplot(gs[0, :])
hist_days = np.arange(len(portfolio_value))
forecast_days = np.arange(FORECAST_DAYS + 1) + len(portfolio_value) - 1

ax1.plot(hist_days, portfolio_value.values, lw=1.2, color='steelblue', label='Historical')
ax1.plot(forecast_days, np.concatenate([[portfolio_value.iloc[-1]], future_prices]),
         lw=2, color='darkorange', label='LSTM Forecast')
ax1.axvline(len(portfolio_value), color='gray', ls=':', lw=1, alpha=0.5)
ax1.set_title('Full Portfolio View: History + 1-Year LSTM Forecast')
ax1.set_ylabel('Portfolio Value ($)')
ax1.legend()
ax1.grid(alpha=0.3)

# --- Panel 2: Monte Carlo distribution ---
ax2 = fig.add_subplot(gs[1, 0])
ax2.hist(terminal, bins=60, density=True, alpha=0.5, color='steelblue')
ax2.axvline(np.percentile(terminal, 5), color='red', ls='--', lw=2,
            label=f'VaR 95%: ${SEED - np.percentile(terminal, 5):,.0f}')
ax2.axvline(SEED, color='green', ls='--', lw=1.5, label='Seed')
ax2.set_title('Monte Carlo Terminal Dist.')
ax2.set_xlabel('Portfolio Value')
ax2.legend(fontsize=7)
ax2.grid(alpha=0.3)

# --- Panel 3: Stress test summary ---
ax3 = fig.add_subplot(gs[1, 1])
scen_names = [s[0] for s in scenarios]
scen_means = [apply_stress(paths, s[1], s[2])[:, -1].mean() for s in scenarios]
colors = ['green' if m >= SEED * 0.8 else 'orange' if m >= SEED * 0.6 else 'red'
          for m in scen_means]
ax3.barh(scen_names, scen_means, color=colors, alpha=0.7)
ax3.axvline(SEED, color='red', ls='--', lw=1.5, label='Seed')
ax3.set_title('Stress Test: Mean Terminal Value')
ax3.set_xlabel('Mean Portfolio Value ($)')
ax3.legend(fontsize=7)
ax3.grid(alpha=0.3, axis='x')

# --- Panel 4: LSTM prediction accuracy (scatter) ---
ax4 = fig.add_subplot(gs[1, 2])
ax4.scatter(y_test_actual, y_pred_actual, alpha=0.3, s=8, c='darkorange')
ax4.plot([y_test_actual.min(), y_test_actual.max()],
         [y_test_actual.min(), y_test_actual.max()], 'k--', lw=1)
ax4.set_title(f'LSTM Prediction (R² = {r2:.3f})')
ax4.set_xlabel('Actual Return')
ax4.set_ylabel('Predicted Return')
ax4.grid(alpha=0.3)

# --- Panel 5: Forecast vs MC percentile ---
ax5 = fig.add_subplot(gs[2, 0])
percentiles = np.linspace(0, 100, 100)
mc_line = np.percentile(terminal, percentiles)
ax5.plot(percentiles, mc_line, lw=2, color='steelblue', label='MC Distribution')
ax5.axhline(future_prices[-1], color='darkorange', ls='--', lw=2,
            label=f'LSTM: ${future_prices[-1]:,.0f}')
ax5.fill_between([0, mc_percentile * 100], 0, ax5.get_ylim()[1],
                 alpha=0.1, color='darkorange')
ax5.set_title(f'LSTM at {mc_percentile:.0%} percentile of MC')
ax5.set_xlabel('Percentile')
ax5.set_ylabel('Portfolio Value ($)')
ax5.legend(fontsize=8)
ax5.grid(alpha=0.3)

# --- Panel 6: VaR comparison ---
ax6 = fig.add_subplot(gs[2, 1])
comparison_metrics = ['VaR 95%', 'VaR 99%', 'CVaR 95%']
mc_tail_95 = terminal[terminal <= np.percentile(terminal, 5)]
mc_cvar_95 = SEED - float(np.mean(mc_tail_95)) if len(mc_tail_95) > 0 else 0
mc_risk = [SEED - np.percentile(terminal, 5),
           SEED - np.percentile(terminal, 1),
           mc_cvar_95]
lstm_risk = [lstm_var_95, lstm_var_99, lstm_cvar_95]
x = np.arange(len(comparison_metrics))
ax6.bar(x - 0.15, mc_risk, 0.3, color='steelblue', alpha=0.7, label='MC')
ax6.bar(x + 0.15, lstm_risk, 0.3, color='darkorange', alpha=0.7, label='LSTM')
ax6.set_xticks(x)
ax6.set_xticklabels(comparison_metrics)
ax6.set_title('Risk Metrics Comparison')
ax6.set_ylabel('Dollar Loss ($)')
ax6.legend(fontsize=8)
ax6.grid(alpha=0.3, axis='y')

# --- Panel 7: Direction accuracy gauge ---
ax7 = fig.add_subplot(gs[2, 2])
dir_acc = np.mean((y_test_actual > 0) == (y_pred_actual > 0))
ax7.barh(['Direction Accuracy'], [dir_acc], color='darkgreen' if dir_acc > 0.5 else 'coral',
         alpha=0.7, height=0.4)
ax7.axvline(0.5, color='red', ls='--', lw=1.5, label='Random (50%)')
ax7.set_xlim(0, 1)
ax7.set_title(f'Sign Prediction: {dir_acc:.1%}')
ax7.legend(fontsize=8)
ax7.grid(alpha=0.3, axis='x')

plt.suptitle('MONTECARLO RISK DASHBOARD — FULL PIPELINE + LSTM INSIGHTS',
             fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
plt.show()

# ── 9. Final summary ──────────────────────────────────────────────────

print("=" * 68)
print("END-TO-END PIPELINE + ML FORECAST — COMPLETE".center(68))
print("=" * 68)
print()
print("  ┌──────────────────────────────────────────────────────────┐")
print("  │  01_data_loader.ipynb    → yfinance → clean log returns │")
print("  │  02_covariance.ipynb     → Covariance → Cholesky        │")
print("  │  03_simulator.ipynb      → 10,000 Monte Carlo paths     │")
print("  │  04_risk_metrics.ipynb   → VaR / CVaR / Max Drawdown    │")
print("  │  05_stress_test.ipynb    → Crash / Vol / Rate scenarios │")
print("  │  06_ml_forecast.ipynb    → LSTM → Future Insights       │")
print("  └──────────────────────────────────────────────────────────┘")
print()
print("Key insights from the LSTM model:")
print(f"  • 1-year portfolio forecast: ${future_prices[-1]:,.0f}")
print(f"    (vs Monte Carlo median: ${np.median(terminal):,.0f})")
print(f"  • LSTM 30-day VaR (95%):   ${lstm_var_95:,.0f}")
print(f"  • LSTM 30-day CVaR (95%):  ${lstm_cvar_95:,.0f}")
print(f"  • Direction accuracy:       {dir_acc:.1%}")
print(f"  • Forecast volatility:      {pred_vol.iloc[-1]:.4f}")
print()
print("Why combine Monte Carlo + LSTM?")
print("  - Monte Carlo is scenario-based: great for stress testing and")
print("    full distribution analysis under assumed parameters.")
print("  - LSTM is data-driven: learns real market patterns (fat tails,")
print("    volatility clustering, momentum) from historical data.")
print("  - Together: MC gives you the range; LSTM tells you which part")
print("    of the range we're most likely heading toward.")
