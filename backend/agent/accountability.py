import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def weekly_accountability_check(user_id: str) -> str:
    try:
        from database.connection import SessionLocal
        from database.models import RiskRun
        db = SessionLocal()
        try:
            four_weeks_ago = datetime.utcnow() - timedelta(days=28)
            runs = (
                db.query(RiskRun)
                .filter(RiskRun.user_id == int(user_id), RiskRun.created_at >= four_weeks_ago)
                .order_by(RiskRun.created_at.asc())
                .all()
            )
        except Exception:
            return "Accountability data not available yet. Start using Vera to get tracked recommendations."
        finally:
            db.close()

        if not runs or len(runs) < 2:
            return "Not enough historical data for accountability tracking. Continue using Vera for weekly updates."

        try:
            import yfinance as yf
        except ImportError:
            return "Accountability tracking requires yfinance. Install with: pip install yfinance"

        messages = []
        total_pnl = 0.0

        for run in runs:
            try:
                forecast = json.loads(run.forecast_json) if run.forecast_json else {}
            except (json.JSONDecodeError, TypeError):
                forecast = {}
            try:
                metrics = json.loads(run.quant_metrics_json) if run.quant_metrics_json else {}
            except (json.JSONDecodeError, TypeError):
                metrics = {}

            tickers = metrics.get("tickers", [])
            weights = metrics.get("weights", [])

            if not tickers:
                continue

            run_date = run.created_at
            action = ""
            bear = forecast.get("bear", {})
            base = forecast.get("base", {})
            bull = forecast.get("bull", {})

            if bear and bear.get("probability", 0) > 30:
                action = bear.get("action", "Hedge portfolio")
            elif bull and bull.get("probability", 0) > 50:
                action = bull.get("action", "Maintain exposure")
            else:
                action = base.get("action", "Hold steady")

            lookback_end = run_date + timedelta(days=7)
            lookback_end = min(lookback_end, datetime.utcnow())

            try:
                data = yf.download(tickers, start=run_date.strftime("%Y-%m-%d"), end=lookback_end.strftime("%Y-%m-%d"), progress=False)
                if data.empty:
                    continue
                if "Adj Close" in data.columns.get_level_values(0):
                    prices = data["Adj Close"]
                elif "Close" in data.columns.get_level_values(0):
                    prices = data["Close"]
                else:
                    continue
                if prices.empty or len(prices) < 2:
                    continue

                start_prices = prices.iloc[0]
                end_prices = prices.iloc[-1]
                port_return = 0.0
                for i, t in enumerate(tickers):
                    if i < len(weights) and t in start_prices.index and t in end_prices.index:
                        ret = (end_prices[t] / start_prices[t]) - 1.0
                        port_return += weights[i] * ret
                pnl = port_return * 1_000_000
                total_pnl += pnl

                direction = "ahead" if pnl > 0 else "behind"
                messages.append(
                    f"- Week of {run_date.strftime('%b %d')}: Recommended '{action}'. "
                    f"Portfolio would be ${abs(pnl):,.0f} {direction}."
                )
            except Exception as e:
                logger.debug(f"Accountability calc failed for run {run.id}: {e}")
                continue

        if not messages:
            return "No actionable recommendations found in the last 4 weeks."

        overall = f"**ahead by ${total_pnl:,.0f}**" if total_pnl > 0 else f"**behind by ${abs(total_pnl):,.0f}**"
        accountability = (
            f"## Vera Accountability Report\n\n"
            f"**Period:** Last 4 weeks | **Tracking:** {len(runs)} analyses\n\n"
            f"### Recommendations vs. Market\n\n"
            + "\n".join(messages) +
            f"\n\n### Net Impact\n\n"
            f"Over the past 4 weeks, following Vera's recommendations would have left you {overall}.\n\n"
            f"*Past performance does not guarantee future results. This is not financial advice.*"
        )

        return accountability

    except Exception as e:
        logger.error(f"Accountability check failed: {e}")
        return "Accountability tracking encountered an error. Please try again later."
