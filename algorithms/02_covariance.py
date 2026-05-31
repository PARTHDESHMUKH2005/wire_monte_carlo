# ── Imports ──────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# ── 1. Load data from notebook 01 ─────────────────────────────────────
market_data = joblib.load('market_data.pkl')
returns = market_data['returns']
assets = market_data['metadata']['assets']

print(f"Loaded {len(returns)} rows for {assets}")

# ── 2. Estimate drift (mean return per asset) ────────────────────────

# Drift is the historical average daily log return.
# It feeds into the simulation as the expected growth rate.
# NOTE: Historical mean is a noisy estimate — in practice you'd blend
#       with a forward-looking view (e.g., CAPM or analyst forecasts).

mu = returns.mean().to_numpy(dtype=float)
print("Annualized drift (%):")
for asset, m in zip(assets, mu * 252 * 100):
    print(f"  {asset}: {m:.2f}%")

# ── 3. Compute sample covariance ──────────────────────────────────────

# Raw sample covariance from historical data
sample_cov = returns.cov().to_numpy(dtype=float)

# Visualize as a heatmap
plt.figure(figsize=(6, 5))
sns.heatmap(sample_cov, annot=True, fmt='.6f', xticklabels=assets, yticklabels=assets,
            cmap='RdBu_r', center=0)
plt.title('Sample Covariance Matrix')
plt.tight_layout()
plt.show()

print("Annualized covariance:\n", sample_cov * 252)

# ── 4. Apply shrinkage regularization ─────────────────────────────────

# Shrinkage pulls the sample covariance toward a diagonal target.
# This reduces extreme correlations from noisy data and ensures
# the matrix is positive definite (required for Cholesky).
#
# shrinkage=0   → pure sample covariance (may be noisy)
# shrinkage=1   → diagonal matrix (assumes no correlation)
# shrinkage=0.05 → 5% toward diagonal, 95% sample (sensible default)

shrinkage = 0.05
diagonal_target = np.diag(np.diag(sample_cov))
cov = (1.0 - shrinkage) * sample_cov + shrinkage * diagonal_target

print("Shrunken covariance matrix:")
print(pd.DataFrame(cov, index=assets, columns=assets).round(8))

# ── 5. Cholesky decomposition ─────────────────────────────────────────

# Cholesky decomposes Cov = L @ L.T where L is lower triangular.
# If we draw independent standard normal variables Z, then
#   correlated shocks = Z @ L.T
# This is how we generate correlated random paths in the simulator.

# The matrix must be positive definite. If the sample is nearly singular
# (e.g., two assets are perfectly correlated), we add a small "jitter"
# to the diagonal to make it decomposable.

def cholesky_with_jitter(mat, jitter=1e-10):
    """Try Cholesky with increasing jitter until it succeeds."""
    eye = np.eye(mat.shape[0])
    for scale in (0.0, jitter, jitter*10, jitter*100, jitter*1000):
        try:
            return np.linalg.cholesky(mat + scale * eye)
        except np.linalg.LinAlgError:
            continue
    raise ValueError("Matrix not positive definite — check for redundant assets")

chol = cholesky_with_jitter(cov)

print("Cholesky lower-triangular factor (L):")
print(pd.DataFrame(chol, index=assets, columns=assets).round(6))

# Verify: L @ L.T should equal the original covariance
reconstructed = chol @ chol.T
error = np.abs(cov - reconstructed).max()
print(f"\nReconstruction error (max abs): {error:.2e}")
assert error < 1e-8, "Cholesky reconstruction failed!"
print("✓ Cholesky verified — L @ L.T == Cov")

# ── 6. Bundle and save ───────────────────────────────────────────────-

covariance_bundle = {
    'mu': mu,
    'covariance': cov,
    'cholesky': chol,
    'assets': assets,
}

joblib.dump(covariance_bundle, 'covariance_bundle.pkl')
print("Saved covariance_bundle.pkl — ready for simulation.")
