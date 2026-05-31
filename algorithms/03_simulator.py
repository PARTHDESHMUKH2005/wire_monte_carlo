# ── Imports ──────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ── 1. Load covariance bundle from notebook 02 ────────────────────────
bundle = joblib.load('covariance_bundle.pkl')
mu = bundle['mu']
cov = bundle['covariance']
chol = bundle['cholesky']
assets = bundle['assets']
n_assets = len(assets)

print(f"Loaded covariance bundle for {n_assets} assets: {assets}")

# ── 2. Set simulation parameters ──────────────────────────────────────

N_SIMS = 10_000       # number of Monte Carlo paths
HORIZON = 252         # trading days (1 year)
SEED_CAPITAL = 1_000_000.0  # starting portfolio value
RANDOM_SEED = 42      # for reproducibility

# Portfolio weights — equal weight for simplicity
# You can change this to test different allocations
weights = np.array([0.25, 0.25, 0.25, 0.25])
weights = weights / weights.sum()  # normalize to sum to 1

print(f"Simulation settings:")
print(f"  Sims: {N_SIMS:,}")
print(f"  Horizon: {HORIZON} days")
print(f"  Seed capital: ${SEED_CAPITAL:,.0f}")
print(f"  Weights: {dict(zip(assets, weights))}")

# ── 3. Generate correlated Monte Carlo paths ─────────────────────────

# Step-by-step breakdown of the core simulation logic:

# a) Independent shocks: (n_sims x horizon x n_assets) standard normals
rng = np.random.default_rng(RANDOM_SEED)
independent_shocks = rng.standard_normal((N_SIMS, HORIZON, n_assets))

# b) Correlated shocks: multiply by Cholesky factor (transposed)
#    chol is lower-triangular, so independent_shocks @ chol.T gives
#    the correct correlated structure
correlated_shocks = independent_shocks @ chol.T

# c) Asset returns = drift + correlated shocks
#    mu is the mean daily return; shocks add random noise around it
asset_returns = mu + correlated_shocks

# d) Portfolio returns: weighted sum of asset returns
portfolio_returns = asset_returns @ weights

# e) Capital paths: compound returns from seed capital
#    cumprod(1 + return) simulates the growth/decline of capital
path_matrix = SEED_CAPITAL * np.cumprod(1.0 + portfolio_returns, axis=1)

# f) Terminal values: final portfolio value at end of horizon
terminal_values = path_matrix[:, -1]

print(f"Path matrix shape: {path_matrix.shape}")
print(f"Terminal values: min=${terminal_values.min():,.0f}, "
      f"median=${np.median(terminal_values):,.0f}, "
      f"max=${terminal_values.max():,.0f}")

# ── 4. Visualize the simulation paths ─────────────────────────────────

# Plot a sample of paths (first 100) to see the range of outcomes
plt.figure(figsize=(12, 5))

# Subplot 1: Sample paths
plt.subplot(1, 2, 1)
plt.plot(path_matrix[:100].T, lw=0.5, alpha=0.7)
plt.axhline(SEED_CAPITAL, color='red', ls='--', lw=1, label=f'Seed (${SEED_CAPITAL:,.0f})')
plt.title(f'100 Monte Carlo Paths (of {N_SIMS:,})')
plt.xlabel('Trading Day')
plt.ylabel('Portfolio Value ($)')
plt.legend()
plt.grid(alpha=0.3)

# Subplot 2: Terminal distribution
plt.subplot(1, 2, 2)
plt.hist(terminal_values, bins=80, density=True, alpha=0.6, color='steelblue')
plt.axvline(SEED_CAPITAL, color='red', ls='--', lw=2, label=f'Seed (${SEED_CAPITAL:,.0f})')
plt.axvline(np.median(terminal_values), color='green', ls='--', lw=2,
            label=f'Median ${np.median(terminal_values):,.0f}')
plt.title('Distribution of Terminal Portfolio Value')
plt.xlabel('Portfolio Value ($)')
plt.ylabel('Density')
plt.legend()
plt.grid(alpha=0.3)

plt.tight_layout()
plt.show()

# ── 5. Save simulation results ────────────────────────────────────────

simulation_result = {
    'path_matrix': path_matrix,
    'terminal_values': terminal_values,
    'weights': weights,
    'assets': assets,
    'seed_capital': SEED_CAPITAL,
    'n_sims': N_SIMS,
    'horizon': HORIZON,
}

joblib.dump(simulation_result, 'simulation_result.pkl')
print("Saved simulation_result.pkl — ready for risk metrics.")
