# LiveRisk — Algorithms & Research

These Python scripts were extracted from the Jupyter notebooks used to develop and validate every risk model in the LiveRisk platform. Each script corresponds to a step in the pipeline and maps directly to the production code in `backend/main.py`.

```

├── 01_data_loader.py      → fetch_prices(), sentiment_analysis()
├── 02_covariance.py       → covariance_bundle()
├── 03_simulator.py        → monte_carlo()
├── 04_risk_metrics.py     → risk_metrics(), sentiment_adjustment
├── 05_stress_test.py      → stress_scenarios()
└── 06_ml_forecast_insights.py → lstm_forecast()

```

### Pipeline Flow

```
Wire API / yfinance
    │
    ▼
01_data_loader ───► 02_covariance ───► 03_simulator ───► 04_risk_metrics
    │                                                         │
    ▼                                                         ▼
06_ml_forecast    │                                         05_stress_test
    │                                                         │
    └──────────────────────┐                                  │
                          ▼                                  ▼
                    LSTM Forecast                     Scenarios + Breach
                          │                                  │
                          └──────────┬───────────────────────┘
                                     ▼
                            Dashboard API (/analyze)
```

### Key Techniques Used

| Step | Technique | What It Does |
|------|-----------|-------------|
| 01 | Log returns | Normalizes price data for statistical modeling |
| 02 | Shrinkage covariance | Reduces noise in the covariance matrix |
| 02 | Cholesky decomposition | Enables correlated random sampling |
| 03 | Monte Carlo simulation | Generates 10,000+ possible portfolio paths |
| 04 | Historical VaR/CVaR | Quantifies downside risk from simulated distribution |
| 04 | Sentiment-adjusted VaR | Bumps risk by 15% when FinBERT sentiment drops below -0.5 |
| 05 | Stress scenario engine | Applies historical crash shocks to portfolio paths |
| 05 | WSB hype detection | Adds retail frenzy scenario on mention spikes |
| 06 | LSTM neural network | 2-layer LSTM forecasting 60-day portfolio trajectory |

### Original Notebooks

The `.ipynb` originals are in the project root and render natively on GitHub with markdown explanations, code, and visualizations side-by-side.
