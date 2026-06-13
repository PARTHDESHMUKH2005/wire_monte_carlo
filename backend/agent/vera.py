from __future__ import annotations
import os
import sys
import re
import json
import logging
import numpy as np
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

LANGGRAPH_AVAILABLE = False
try:
    from langgraph.graph import StateGraph, END
    from agent.state import RiskAgentState
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("LangGraph not available — Vera will run in fallback mode")


def _import_quant():
    try:
        from main import (
            fetch_prices, compute_returns, covariance_bundle,
            monte_carlo, risk_metrics, sentiment_analysis,
            lstm_forecast, stress_scenarios, _DATA_IS_SYNTHETIC,
        )
    except ImportError:
        from __main__ import (
            fetch_prices, compute_returns, covariance_bundle,
            monte_carlo, risk_metrics, sentiment_analysis,
            lstm_forecast, stress_scenarios, _DATA_IS_SYNTHETIC,
        )
    return {
        "fetch_prices": fetch_prices,
        "compute_returns": compute_returns,
        "covariance_bundle": covariance_bundle,
        "monte_carlo": monte_carlo,
        "risk_metrics": risk_metrics,
        "sentiment_analysis": sentiment_analysis,
        "lstm_forecast": lstm_forecast,
        "stress_scenarios": stress_scenarios,
    }


_quant = None


def _get_quant():
    global _quant
    if _quant is None:
        _quant = _import_quant()
    return _quant


def _get_llm():
    from agent.litellm_config import get_llm_response, get_model_for_intent
    return get_llm_response, get_model_for_intent


def _get_langfuse_handler():
    from agent.langfuse_config import get_langfuse_handler
    return get_langfuse_handler()


def _get_memory():
    from agent.memory import (
        save_conversation_turn, get_conversation_history,
        save_risk_run, get_last_risk_run,
    )
    return {
        "save_turn": save_conversation_turn,
        "get_history": get_conversation_history,
        "save_run": save_risk_run,
        "get_last": get_last_risk_run,
    }


SEED_CAPITAL = 1_000_000

_GREETINGS = {"hi", "hello", "hey", "greetings", "good morning", "good afternoon",
               "good evening", "sup", "yo", "howdy", "whats up", "what's up",
               "how are you", "how r u", "howdy", "nice to meet"}


def _is_greeting(msg: str) -> bool:
    msg = msg.strip().lower()
    if len(msg.split()) > 5:
        return False
    return any(msg.startswith(g) or g in msg for g in _GREETINGS)


# ---------------------------------------------------------------------------
# Market Intelligence Node
# ---------------------------------------------------------------------------

def market_intel_node(state: RiskAgentState) -> dict:
    user_message = state.get("user_message", "").strip().lower()
    tickers = state.get("tickers", [])
    intent = state.get("intent", "general_chat")

    should_fetch = (
        intent in ("general_chat", "stock_query", "explain", "market_news", "ipo_query", "trending", "geopolitical")
        and any(kw in user_message for kw in ("ipo", "market", "news", "stock", "gain", "loser",
                                              "trend", "hot", "peak", "crash", "event",
                                              "wwdc", "earnings", "sector", "fed", "rate",
                                              "economy", "company", "india", "china", "japan",
                                              "europe", "global", "world", "trade", "war",
                                              "geopolit", "sanction", "election", "nifty",
                                              "nikkei", "ftse", "dax", "hangseng", "kospi",
                                              "asx", "bse", "sensex"))
    )
    if not should_fetch:
        return {"market_intel": {}}

    try:
        from agent.market_intel import get_market_intel
        intel = get_market_intel(user_message, tickers)
        return {"market_intel": intel}
    except Exception as e:
        logger.error(f"Market intel node failed: {e}")
        return {"market_intel": {}}


# ---------------------------------------------------------------------------
# Node Implementations
# ---------------------------------------------------------------------------

_STOP_WORDS = {"AND", "THE", "MY", "YOUR", "WITH", "FOR", "OF", "IN", "ON", "AT", "TO", "A", "AN", "IS", "IT", "OR", "PORTFOLIO"}

_PORTFOLIO_PATTERNS = [
    r"(?:analyse|analyze|scan|check|run)\s+(?:my\s+)?portfolio\s+(?:risk\s+)?(?:analysis\s+)?(?:for|with|of|on)?\s*([A-Za-z0-9,.\s%]+?)(?:\s+with\s+weights?\s+([\d.,\s]+))?\s*$",
    r"(?:analyse|analyze|scan|check|run)\s+(?:risk\s+)?(?:analysis\s+)?(?:for|on|of)?\s*([A-Za-z0-9,.\s%]+?)(?:\s+with\s+weights?\s+([\d.,\s]+))?\s*$",
    r"what\s+is\s+(?:the\s+)?(?:risk|var|cvar|health)\s+(?:of|for|on)?\s+([A-Za-z0-9,.\s%]+?)\s*$",
]


def _parse_tickers(raw: str) -> list:
    raw = re.sub(r"\d+%", "", raw)
    parts = re.split(r"[,;\s]+", raw)
    tickers = []
    for p in parts:
        p = p.strip().upper().rstrip(".")
        if p and p not in _STOP_WORDS and len(p) <= 10 and not p.isdigit():
            tickers.append(p)
    seen = []
    for t in tickers:
        if t not in seen:
            seen.append(t)
    return seen if len(seen) >= 1 else None


def _parse_portfolio_request(msg: str, state_tickers: list = None) -> tuple:
    msg_lower = msg.strip().lower()
    for pat in _PORTFOLIO_PATTERNS:
        m = re.search(pat, msg_lower)
        if m:
            raw_tickers = m.group(1).strip()
            tickers = _parse_tickers(raw_tickers)
            if not tickers:
                continue
            weights = None
            if m.lastindex >= 2 and m.group(2):
                raw_w = m.group(2).strip()
                w_parts = [float(x) for x in re.split(r"[,;\s]+", raw_w) if x.strip()]
                if len(w_parts) == len(tickers) and abs(sum(w_parts) - 1.0) < 0.05:
                    weights = [w / sum(w_parts) for w in w_parts]
            return tickers, weights
    if state_tickers:
        return state_tickers, None
    return None, None


def intent_classifier(state: RiskAgentState) -> dict:
    user_message = state.get("user_message", "").strip().lower()
    mode = state.get("mode", "chat")

    if mode == "morning_brief":
        return {"intent": "morning_brief"}
    if mode == "report":
        return {"intent": "report"}

    if not user_message:
        return {"intent": "general_chat"}

    # Specific intents take priority over generic portfolio → risk_check
    if any(kw in user_message for kw in ("forecast", "predict", "60-day", "outlook", "bull, base, and bear", "bull base bear")):
        tickers, weights = _parse_portfolio_request(user_message, state.get("tickers"))
        result = {"intent": "forecast"}
        if tickers:
            result["tickers"] = tickers
        if weights:
            result["weights"] = weights
        return result

    if any(kw in user_message for kw in ("stress", "crash 2008", "2008 crash", "black swan", "adverse scenario")):
        tickers, weights = _parse_portfolio_request(user_message, state.get("tickers"))
        result = {"intent": "scenario"}
        if tickers:
            result["tickers"] = tickers
        if weights:
            result["weights"] = weights
        return result

    if any(kw in user_message for kw in ("rebalance", "allocate", "diversify")):
        return {"intent": "rebalance"}

    if any(kw in user_message for kw in ("portfolio", "analyse my", "analyze my", "my portfolio")):
        parsed_tickers, parsed_weights = _parse_portfolio_request(user_message, state.get("tickers"))
        if parsed_tickers:
            result = {"intent": "risk_check", "tickers": parsed_tickers}
            if parsed_weights:
                result["weights"] = parsed_weights
            return result
        if any(kw in user_message for kw in ("analyse my", "analyze my", "my portfolio", "analyse my portfolio", "analyze my portfolio")):
            return {"intent": "risk_check"}

    try:
        get_llm_response, _ = _get_llm()
        messages = [
            {
                "role": "system",
                "content": (
                    "Classify the user message into exactly one of these intents: "
                    "stock_query, risk_check, rebalance, scenario, forecast, morning_brief, explain, market_news, ipo_query, trending, geopolitical, general_chat. "
                    "Return only the intent string, nothing else."
                ),
            },
            {"role": "user", "content": user_message},
        ]
        response = get_llm_response(messages, temperature=0.1, max_tokens=20)
        intent = response.choices[0].message.content.strip().lower()
        valid_intents = {"stock_query", "risk_check", "rebalance", "scenario", "forecast", "morning_brief", "explain", "market_news", "ipo_query", "trending", "geopolitical", "general_chat"}
        if intent not in valid_intents:
            intent = "general_chat"
        return {"intent": intent}
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        if any(kw in user_message for kw in ("var", "risk", "cvar", "health", "safe")):
            return {"intent": "risk_check"}
        if any(kw in user_message for kw in ("stock", "ticker", "hold", "buy", "sell", "company")):
            return {"intent": "stock_query"}
        if any(kw in user_message for kw in ("rebalance", "allocate", "diversify")):
            return {"intent": "rebalance"}
        if any(kw in user_message for kw in ("forecast", "predict", "60-day", "outlook")):
            return {"intent": "forecast"}
        if any(kw in user_message for kw in ("scenario", "stress", "crash", "what if")):
            return {"intent": "scenario"}
        if any(kw in user_message for kw in ("news", "market", "today", "happening")):
            return {"intent": "market_news"}
        if any(kw in user_message for kw in ("ipo", "public offering", "listing")):
            return {"intent": "ipo_query"}
        if any(kw in user_message for kw in ("gain", "loser", "hot", "trend", "moon", "dump")):
            return {"intent": "trending"}
        if any(kw in user_message for kw in ("geopolit", "war", "sanction", "election", "trade war", "central bank", "fed", "rate")):
            return {"intent": "geopolitical"}
        return {"intent": "general_chat"}


def portfolio_loader(state: RiskAgentState) -> dict:
    user_id = state.get("user_id", "0")
    memory = _get_memory()
    history = memory["get_history"](user_id, limit=8)
    last_run = memory["get_last"](user_id)

    tickers = state.get("tickers", [])
    weights = state.get("weights", [])
    intent = state.get("intent", "")

    if last_run:
        qm = last_run.get("quant_metrics", {})
        if qm and not tickers:
            tickers = qm.get("tickers", tickers)
            weights = qm.get("weights", weights)

    if not tickers:
        if intent in ("forecast", "scenario", "rebalance", "risk_check"):
            if last_run and qm:
                tickers = qm.get("tickers", tickers)
                weights = qm.get("weights", weights)
            if not tickers:
                return {
                    "tickers": [],
                    "weights": [],
                    "conversation_history": history,
                    "portfolio_context": {"tickers": tickers, "weights": weights, "last_run_available": bool(last_run)},
                }

    portfolio_context = {
        "tickers": tickers,
        "weights": weights,
        "last_run_available": bool(last_run),
    }

    if not tickers:
        return {
            "tickers": [],
            "weights": [],
            "conversation_history": history,
            "portfolio_context": portfolio_context,
        }

    return {
        "tickers": tickers,
        "weights": weights,
        "conversation_history": history,
        "portfolio_context": portfolio_context,
    }


def quant_node(state: RiskAgentState) -> dict:
    tickers = state.get("tickers", [])
    if not tickers:
        return {
            "quant_metrics": {},
            "health_score": None,
        }
    weights_list = state.get("weights", [1.0] * len(tickers))
    if not weights_list or len(weights_list) < len(tickers):
        weights_list = [1.0] * len(tickers)
    weights_arr = [float(w) / sum(weights_list) for w in weights_list]

    quant = _get_quant()
    try:
        prices = quant["fetch_prices"](tickers)
        returns = quant["compute_returns"](prices)
        mu, cov, chol = quant["covariance_bundle"](returns)
        paths, terminal = quant["monte_carlo"](mu, chol, weights_arr, seed_capital=SEED_CAPITAL)
        metrics = quant["risk_metrics"](terminal, SEED_CAPITAL)

        sentiment_raw = quant["sentiment_analysis"](tickers)
        sent_score = sentiment_raw.get("score", 0.0)

        vol_adjusted_var = metrics["var"]
        if sent_score < -0.5:
            vol_adjusted_var = round(metrics["var"] * 1.15, 2)

        concentration_penalty = max(0, (1.0 / len(tickers) - min(weights_arr)) * 2)
        sent_penalty = max(0, -sent_score * 0.3)
        var_95_pct = metrics["var"] / SEED_CAPITAL
        health_score = max(0, min(100, int(100 - (var_95_pct * 100 * 0.4 + concentration_penalty * 30 + sent_penalty * 30))))

        quant_metrics = {
            "tickers": tickers,
            "weights": [round(float(w), 4) for w in weights_arr],
            "var_95": round(metrics["var"], 2),
            "var_99": round(float(SEED_CAPITAL - np.percentile(terminal, 1)), 2),
            "cvar": round(metrics["cvar"], 2),
            "vol_adjusted_var": vol_adjusted_var,
            "prob_loss": metrics["prob_loss"],
            "health_score": health_score,
            "garch_vol": round(float(np.std(returns.values) if hasattr(returns, 'values') else 0), 6),
            "component_var": [round(float(w) * metrics["var"], 2) for w in weights_arr],
            "sentiment_score": sent_score,
        }

        stress = quant["stress_scenarios"](paths if isinstance(paths, np.ndarray) else np.array(paths), SEED_CAPITAL)
        quant_metrics["stress_results"] = stress

        return {"quant_metrics": quant_metrics, "health_score": health_score}
    except Exception as e:
        logger.error(f"Quant node failed: {e}")
        return {
            "quant_metrics": {
                "var_95": 0, "var_99": 0, "cvar": 0, "prob_loss": 0,
                "health_score": 50, "garch_vol": 0, "component_var": [],
                "sentiment_score": 0, "stress_results": [],
                "tickers": tickers, "weights": [round(float(w), 4) for w in weights_arr],
            },
            "health_score": 50,
        }


def sentiment_node(state: RiskAgentState) -> dict:
    tickers = state.get("tickers", [])
    quant_metrics = state.get("quant_metrics", {})
    sent_score = quant_metrics.get("sentiment_score", 0)

    score = sent_score
    headlines = []

    try:
        quant = _get_quant()
        sentiment_raw = quant["sentiment_analysis"](tickers)
        headlines = sentiment_raw.get("headlines", [])
        score = sentiment_raw.get("score", sent_score)

        get_llm_response, _ = _get_llm()
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior risk analyst. Given these FinBERT sentiment scores and headlines "
                    "for a portfolio, write a 2-paragraph institutional sentiment analysis. "
                    "Be specific about which news items drive risk. "
                    "End with: regime=bullish|neutral|bearish and risk_adjustment=float between 0.0 and 0.3"
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "scores": {"finbert_score": score},
                    "headlines": headlines[:10],
                    "tickers": tickers,
                }),
            },
        ]
        response = get_llm_response(messages, temperature=0.3, max_tokens=600)
        narrative = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Sentiment node LLM failed: {e}")
        narrative = f"Sentiment score: {score:.4f}. "
        if score > 0.3:
            narrative += "Overall bullish sentiment driven by positive news flow."
        elif score < -0.3:
            narrative += "Overall bearish sentiment with elevated risk."
        else:
            narrative += "Neutral sentiment — no dominant directional bias."

    regime = "neutral"
    risk_adjustment = 0.0
    if "regime=bullish" in narrative.lower():
        regime = "bullish"
        risk_adjustment = 0.05
    elif "regime=bearish" in narrative.lower():
        regime = "bearish"
        risk_adjustment = 0.20
    elif "regime=neutral" in narrative.lower():
        regime = "neutral"
        risk_adjustment = 0.10

    return {
        "sentiment_analysis": {
            "narrative": narrative,
            "regime": regime,
            "risk_adjustment": risk_adjustment,
            "finbert_scores": {"overall": score},
            "headlines": headlines[:5] if isinstance(headlines, list) else [],
        }
    }


def forecast_node(state: RiskAgentState) -> dict:
    quant_metrics = state.get("quant_metrics", {})
    sentiment = state.get("sentiment_analysis", {})
    tickers = state.get("tickers", [])
    weights = state.get("weights", [])
    conversation_history = state.get("conversation_history", [])
    today = datetime.now().strftime("%Y-%m-%d")

    quant = _get_quant()
    try:
        prices = quant["fetch_prices"](tickers)
        lstm_result = quant["lstm_forecast"](prices, weights, seed_capital=SEED_CAPITAL)
        lstm_forecast_values = lstm_result.get("forecast", [])
    except Exception as e:
        logger.error(f"LSTM forecast failed: {e}")
        lstm_forecast_values = []

    tf_available = False
    try:
        import tensorflow as tf
        tf_available = True
    except ImportError:
        pass

    try:
        get_llm_response, get_model_for_intent = _get_llm()
        model = get_model_for_intent("forecast")

        conv_text = ""
        if conversation_history:
            conv_text = "Conversation history:\n" + "\n".join(
                f"{h.get('role', 'user')}: {h.get('content', '')[:200]}"
                for h in conversation_history[-4:]
            )

        lstm_last_display = f"${lstm_forecast_values[-1]:,.2f}" if lstm_forecast_values else "N/A"
        prompt = f"""You are Vera, a senior portfolio risk analyst with 15 years at institutional asset managers. You are direct, specific, and always cite exact numbers. You never say 'it depends' without immediately saying what it depends on. Every analysis ends with one concrete time-bound action.

Today's date: {today}
Portfolio: {json.dumps(tickers)} with weights {json.dumps([round(w, 4) for w in weights])}
VaR 95%: ${quant_metrics.get('var_95', 0):,.2f}
CVaR: ${quant_metrics.get('cvar', 0):,.2f}
Health Score: {quant_metrics.get('health_score', 50)}/100
Sentiment regime: {sentiment.get('regime', 'neutral')}
GARCH volatility: {quant_metrics.get('garch_vol', 0)}
LSTM 60-day forecast (last value): {lstm_last_display}

{conv_text}

Produce three scenarios as valid JSON ONLY with this exact structure, no other text:
{{
  "bull": {{"probability": float, "return_pct": float, "trigger": str, "action": str}},
  "base": {{"probability": float, "return_pct": float, "trigger": str, "action": str}},
  "bear": {{"probability": float, "return_pct": float, "trigger": str, "action": str, "watch_date": str}},
  "60_day_outlook": str,
  "rebalancing_triggers": list[str],
  "vol_regime_forecast": str
}}"""

        messages = [
            {"role": "system", "content": "You are Vera, a senior portfolio risk analyst. Output ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ]
        response = get_llm_response(messages, model=model, temperature=0.4, max_tokens=1200)
        text = response.choices[0].message.content.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]

        forecast = json.loads(text) if text.startswith("{") else {}
    except Exception as e:
        logger.error(f"Forecast node LLM failed: {e}")
        forecast = {
            "bull": {"probability": 25, "return_pct": 8.0, "trigger": "Rate cut + earnings beat", "action": "Maintain equity overweight"},
            "base": {"probability": 50, "return_pct": 2.5, "trigger": "Current conditions persist", "action": "Hold steady"},
            "bear": {"probability": 25, "return_pct": -10.0, "trigger": "Recession + geopolitical shock", "action": "Hedge with TLT/GLD", "watch_date": (datetime.now().strftime("%Y-%m-%d"))},
            "60_day_outlook": "Mixed with downside tail risk. Base case dominated by current trend momentum.",
            "rebalancing_triggers": ["VIX > 25", "Portfolio VaR > 12%", "Sentiment < -0.5"],
            "vol_regime_forecast": "Low-to-moderate volatility expected near term with potential spike risk.",
        }

    return {"forecast": forecast}


def _format_stress_results(stress_results: list) -> str:
    if not stress_results:
        return ""
    lines = []
    for s in stress_results[:5]:
        name = s.get("scenario", "")
        loss = s.get("loss", 0)
        recovery = s.get("recovery_days", "N/A")
        lines.append(f"• **{name}** — portfolio impact: {loss:+.1f}%, recovery: {recovery} days")
    return "**Stress Test Results:**\n" + "\n".join(lines)


def risk_interpreter(state: RiskAgentState) -> dict:
    quant_metrics = state.get("quant_metrics", {})
    sentiment = state.get("sentiment_analysis", {})
    forecast = state.get("forecast", {})
    mode = state.get("mode", "chat")
    intent = state.get("intent", "general_chat")
    stress_results = quant_metrics.get("stress_results", [])

    try:
        get_llm_response, _ = _get_llm()

        if mode == "morning_brief":
            length_instruction = "Maximum 200 words. WhatsApp-friendly format with clear bullet points."
        else:
            length_instruction = "Full, detailed institutional analysis with natural narrative flow. Write like a senior analyst explaining complex concepts to an intelligent client — thorough, specific, and engaging. Never dumb it down, but make it readable. Use analogies where helpful."

        prompt_data = {
            "quant_metrics": {k: v for k, v in quant_metrics.items() if k != "stress_results"},
            "sentiment_regime": sentiment.get("regime", "neutral"),
            "sentiment_narrative": sentiment.get("narrative", ""),
            "forecast_60day": forecast.get("60_day_outlook", ""),
            "forecast_scenarios": {k: v for k, v in forecast.items() if k in ("bull", "base", "bear")},
            "user_intent": intent,
            "user_message": state.get("user_message", ""),
        }

        if intent in ("scenario", "forecast") and stress_results:
            prompt_data["stress_test_results"] = stress_results

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Vera, a senior portfolio risk analyst with a gift for making complex risk concepts click. "
                    "You have 15 years in institutional asset management and you've seen every market cycle. "
                    f"{length_instruction} "
                    "Guidelines for your response:\n"
                    "1. Open with a strong framing sentence that sets the scene — connect the numbers to a real-world story.\n"
                    "2. Explain VaR, CVaR, and health score in plain English with an analogy or concrete example. Never just state the number — tell them what it means for their money.\n"
                    "3. If stress test results are provided, reference them — compare portfolio drawdowns to historical crises like 2008, COVID, or the dot-com bust. Make it visceral.\n"
                    "4. Weave sentiment analysis and forecast scenarios into the narrative naturally — don't just list them.\n"
                    "5. Every response ends with one concrete action item or 'no action needed today, here is why'.\n"
                    "6. Cite exact numbers from the data — precision builds trust."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt_data),
            },
        ]
        response = get_llm_response(messages, temperature=0.4, max_tokens=1200)
        interpretation = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Risk interpreter failed: {e}")

        market_intel = state.get("market_intel", {})

        if market_intel and market_intel.get("summary"):
            interpretation = f"Here's your real-time financial snapshot:\n\n{market_intel['summary']}\n\n"
            if quant_metrics:
                interpretation += f"**Portfolio Health:** {quant_metrics.get('health_score', 50)}/100\n"
                interpretation += f"**VaR 95%:** ${quant_metrics.get('var_95', 0):,.0f}\n"
            if market_intel.get("ipo_data", {}).get("upcoming"):
                ipo_text = "**Upcoming IPOs:** " + ", ".join(
                    f"{x.get('company', '')} ({x.get('ticker', '')})"
                    for x in market_intel["ipo_data"]["upcoming"][:3]
                )
                interpretation += ipo_text + "\n"
            if market_intel.get("market_movers", {}).get("top_gainers"):
                interpretation += "**Hot stocks today:** " + ", ".join(
                    f"{x['ticker']} ({x['change_pct']:+.2f}%)"
                    for x in market_intel["market_movers"]["top_gainers"][:3]
                ) + "\n"
            interpretation += "\nI'm your real-time financial intelligence agent. Ask me about any stock, IPO, sector trend, or company event."
        else:
            var_95 = quant_metrics.get("var_95", 0)
            cvar = quant_metrics.get("cvar", 0)
            health = quant_metrics.get("health_score", 50)
            prob_loss = quant_metrics.get("prob_loss", 0)
            bear = forecast.get("bear", {})
            bear_prob = bear.get("probability", 0) if isinstance(bear, dict) else 0

            interpretation = (
                f"Here's your portfolio risk snapshot:\n\n"
                f"**Health Score:** {health}/100 — {'Looking good' if health >= 75 else 'Moderate risk' if health >= 50 else 'Needs attention'}\n\n"
                f"**Value at Risk (VaR 95%):** ${var_95:,.0f}\n"
                f"Think of this as: on any given day, there's a 5% chance your portfolio could lose ${var_95:,.0f} or more. "
                f"It's your 'worst usual case' number.\n\n"
                f"**Conditional VaR (CVaR):** ${cvar:,.0f}\n"
                f"This is the average loss when things really go wrong — in that worst 5% of scenarios, "
                f"you'd typically lose around ${cvar:,.0f}.\n\n"
                f"**Loss Probability:** {prob_loss*100:.0f}% chance of any loss over the forecast period.\n\n"
            )

            if stress_results and intent in ("scenario", "forecast"):
                interpretation += _format_stress_results(stress_results) + "\n\n"

            if bear_prob > 30:
                interpretation += (
                    f"**Heads up:** The bear scenario has a {bear_prob}% probability. "
                    f"{bear.get('trigger', 'Keep an eye on market conditions')}. "
                    f"{bear.get('action', 'Consider defensive positioning')}.\n\n"
                )
            if health >= 75:
                interpretation += "**Bottom line:** Your portfolio looks well-balanced. No urgent changes needed — just keep an eye on market conditions."
            elif health >= 50:
                interpretation += "**Bottom line:** Your portfolio has some moderate risk. Consider checking your sector concentration and maybe adding some defensive positions."
            else:
                interpretation += "**Bottom line:** Your portfolio is showing elevated risk. Look into rebalancing toward safer assets or adding hedges."

    action_items = []
    if quant_metrics.get("health_score", 50) < 50:
        action_items.append("Review portfolio hedge — elevated risk detected")
    if sentiment.get("regime") == "bearish":
        action_items.append("Consider reducing equity exposure or adding tail hedges")
    if forecast.get("bear", {}).get("probability", 0) > 30:
        action_items.append(f"Watch date: {forecast.get('bear', {}).get('watch_date', 'N/A')} for bear scenario trigger")
    if stress_results and intent in ("scenario", "forecast"):
        worst = min(stress_results, key=lambda x: x.get("loss", 0)) if stress_results else None
        if worst:
            action_items.append(f"Hedge against {worst.get('scenario', 'adverse')} scenario — {worst.get('loss', 0):.1f}% impact")

    if not action_items:
        action_items.append("No action needed today. Current risk profile is within acceptable parameters.")

    return {"risk_interpretation": interpretation, "action_items": action_items}


def report_assembler(state: RiskAgentState) -> dict:
    quant_metrics = state.get("quant_metrics", {})
    sentiment = state.get("sentiment_analysis", {})
    forecast = state.get("forecast", {})
    tickers = state.get("tickers", [])
    health_score = state.get("health_score", 50)
    interpretation = state.get("risk_interpretation", "")
    action_items = state.get("action_items", [])

    today = datetime.now().strftime("%B %d, %Y")
    tickers_str = ", ".join(tickers)

    try:
        get_llm_response, _ = _get_llm()
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior risk analyst writing an institutional portfolio risk report. "
                    "Every number in the report must come from the provided data — never invent figures. "
                    "Output valid markdown. Include tables for risk metrics, stress test results, and scenario analysis. "
                    "Use professional institutional language."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "tickers": tickers,
                    "health_score": health_score,
                    "var_95": quant_metrics.get("var_95", 0),
                    "var_99": quant_metrics.get("var_99", 0),
                    "cvar": quant_metrics.get("cvar", 0),
                    "prob_loss": quant_metrics.get("prob_loss", 0),
                    "garch_vol": quant_metrics.get("garch_vol", 0),
                    "stress_results": quant_metrics.get("stress_results", []),
                    "sentiment_regime": sentiment.get("regime", "neutral"),
                    "sentiment_narrative": sentiment.get("narrative", ""),
                    "forecast_bull": forecast.get("bull", {}),
                    "forecast_base": forecast.get("base", {}),
                    "forecast_bear": forecast.get("bear", {}),
                    "outlook_60day": forecast.get("60_day_outlook", ""),
                    "rebalancing_triggers": forecast.get("rebalancing_triggers", []),
                    "vol_regime_forecast": forecast.get("vol_regime_forecast", ""),
                    "risk_interpretation": interpretation,
                    "action_items": action_items,
                }),
            },
        ]
        response = get_llm_response(messages, temperature=0.3, max_tokens=2000)
        report_markdown = response.choices[0].message.content.strip()

        header = f"# LiveRisk Portfolio Intelligence Report\n\n"
        header += f"**Generated:** {today} | **Portfolio:** {tickers_str} | **Health:** {health_score}/100\n\n"
        report_markdown = header + "---\n\n" + report_markdown
    except Exception as e:
        logger.error(f"Report assembler failed: {e}")
        report_markdown = f"""# LiveRisk Portfolio Intelligence Report

**Generated:** {today} | **Portfolio:** {tickers_str} | **Health:** {health_score}/100

---

## Executive Summary

Portfolio health score is {health_score}/100. VaR 95% at ${quant_metrics.get('var_95', 0):,.2f} with CVaR of ${quant_metrics.get('cvar', 0):,.2f}. Sentiment regime is {sentiment.get('regime', 'neutral')}.

## Risk Metrics

| Metric | Value |
|---|---|
| 95% VaR | ${quant_metrics.get('var_95', 0):,.2f} |
| 99% VaR | ${quant_metrics.get('var_99', 0):,.2f} |
| CVaR | ${quant_metrics.get('cvar', 0):,.2f} |
| Prob. of Loss | {quant_metrics.get('prob_loss', 0)*100:.1f}% |
| GARCH Vol | {quant_metrics.get('garch_vol', 0):.6f} |
| Health Score | {health_score}/100 |

## Sentiment Analysis

{sentiment.get('narrative', 'No sentiment data available.')}

## 60-Day Scenario Analysis

| Scenario | Probability | Return | Trigger |
|---|---|---|---|
| Bull | {forecast.get('bull', {}).get('probability', 'N/A')}% | {forecast.get('bull', {}).get('return_pct', 'N/A')}% | {forecast.get('bull', {}).get('trigger', 'N/A')} |
| Base | {forecast.get('base', {}).get('probability', 'N/A')}% | {forecast.get('base', {}).get('return_pct', 'N/A')}% | {forecast.get('base', {}).get('trigger', 'N/A')} |
| Bear | {forecast.get('bear', {}).get('probability', 'N/A')}% | {forecast.get('bear', {}).get('return_pct', 'N/A')}% | {forecast.get('bear', {}).get('trigger', 'N/A')} |

{interpretation}

## Recommendations

{chr(10).join(f'- {a}' for a in action_items)}

## Disclaimer

This report is generated by Vera AI, an automated risk analysis system. It is for informational purposes only and does not constitute financial advice. Past performance and simulated scenarios do not guarantee future results.
"""

    return {"report_markdown": report_markdown}


def response_writer(state: RiskAgentState) -> dict:
    interpretation = state.get("risk_interpretation", "")
    report = state.get("report_markdown", "")
    mode = state.get("mode", "chat")
    intent = state.get("intent", "general_chat")
    action_items = state.get("action_items", [])
    health_score = state.get("health_score") or None
    tickers = state.get("tickers", [])
    weights = state.get("weights", [])
    forecast = state.get("forecast", {})
    user_message = state.get("user_message", "")
    market_intel = state.get("market_intel", {})

    if not interpretation:
        if market_intel and isinstance(market_intel, dict) and market_intel.get("summary"):
            try:
                get_llm_response, _ = _get_llm()
                msgs = [
                    {
                        "role": "system",
                        "content": (
                            "You are Vera, a senior financial intelligence analyst with a knack for making markets make sense. "
                            "You analyze global markets, geopolitics, and macroeconomic trends. "
                            "You are specific, cite exact numbers, and give actionable insights. "
                            "Write in natural, flowing prose — 3-4 paragraphs that tell a coherent story about what's happening and why it matters. "
                            "Connect the dots across regions and asset classes. Cover ALL major regions: US, Europe, Asia-Pacific, Emerging Markets. "
                            "End with a clear, actionable takeaway."
                        ),
                    },
                    {
                        "role": "user",
                        "content": user_message + "\n\nReal-time market intelligence:\n" + market_intel.get("summary", ""),
                    },
                ]
                resp = get_llm_response(msgs, temperature=0.5, max_tokens=800)
                interpretation = resp.choices[0].message.content.strip()
            except Exception:
                pass
        if not interpretation:
            interpretation = _build_intent_response(intent, market_intel) or (
                "How can I help you today? Ask me about stocks, markets, IPOs, or global events."
            )

    _get_memory()["save_turn"](state.get("user_id", "0"), "user", user_message, intent)
    _get_memory()["save_turn"](state.get("user_id", "0"), "assistant", interpretation[:500], intent)

    qm = state.get("quant_metrics", {})
    if qm and qm.get("tickers"):
        _get_memory()["save_run"](state.get("user_id", "0"), qm, forecast, report or "", health_score)

    has_portfolio = bool(tickers)
    if mode == "morning_brief":
        follow_up = "\n\nReply **REBALANCE** for optimization | Reply **STOP** to pause briefs"
    elif mode == "report":
        follow_up = ""
    elif has_portfolio:
        follow_up = "\n\nReply `rebalance` to model optimization | `stress` for scenario testing | `report` for full PDF"
    else:
        follow_up = ""

    response = interpretation + follow_up

    return {
        "response": response,
        "health_score": health_score,
        "action_items": action_items,
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def should_run_quant(state: RiskAgentState) -> str:
    intent = state.get("intent", "")
    if intent in ("general_chat", "explain", "market_news", "ipo_query", "trending", "geopolitical"):
        return "skip_quant"
    tickers = state.get("tickers", [])
    if not tickers:
        if intent in ("forecast", "scenario", "rebalance", "risk_check"):
            return "run_quant"
        return "skip_quant"
    return "run_quant"


def should_skip_quant(state: RiskAgentState) -> str:
    if state.get("intent") == "explain":
        return "educational"
    return "direct"


def should_generate_report(state: RiskAgentState) -> str:
    if state.get("mode") in ("morning_brief", "report"):
        return "generate_report"
    if state.get("intent") in ("forecast", "scenario", "rebalance"):
        return "generate_report"
    return "skip_report"


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

_vera_graph = None


def build_vera_graph():
    global _vera_graph
    if not LANGGRAPH_AVAILABLE:
        logger.warning("LangGraph not installed — Vera running in procedural mode")
        return None

    if _vera_graph is not None:
        return _vera_graph

    workflow = StateGraph(RiskAgentState)

    workflow.add_node("intent_classifier", intent_classifier)
    workflow.add_node("market_intel_node", market_intel_node)
    workflow.add_node("portfolio_loader", portfolio_loader)
    workflow.add_node("quant_node", quant_node)
    workflow.add_node("sentiment_node", sentiment_node)
    workflow.add_node("forecast_node", forecast_node)
    workflow.add_node("risk_interpreter", risk_interpreter)
    workflow.add_node("report_assembler", report_assembler)
    workflow.add_node("response_writer", response_writer)

    workflow.set_entry_point("intent_classifier")

    workflow.add_edge("intent_classifier", "market_intel_node")

    workflow.add_conditional_edges(
        "market_intel_node",
        should_run_quant,
        {"run_quant": "portfolio_loader", "skip_quant": "response_writer"},
    )

    workflow.add_conditional_edges(
        "portfolio_loader",
        should_skip_quant,
        {"educational": "response_writer", "direct": "quant_node"},
    )

    workflow.add_edge("quant_node", "sentiment_node")
    workflow.add_edge("quant_node", "forecast_node")
    workflow.add_edge("sentiment_node", "risk_interpreter")
    workflow.add_edge("forecast_node", "risk_interpreter")

    workflow.add_conditional_edges(
        "risk_interpreter",
        should_generate_report,
        {"generate_report": "report_assembler", "skip_report": "response_writer"},
    )

    workflow.add_edge("report_assembler", "response_writer")
    workflow.add_edge("response_writer", END)

    _vera_graph = workflow.compile()
    return _vera_graph


# ---------------------------------------------------------------------------
# Main entry point (works with or without LangGraph)
# ---------------------------------------------------------------------------

def run_vera(state: dict) -> dict:
    graph = build_vera_graph()

    if graph is not None:
        try:
            handler = _get_langfuse_handler()
            config = {"callbacks": [handler]} if handler else {}
            result = graph.invoke(state, config=config)
            return dict(result)
        except Exception as e:
            logger.error(f"LangGraph execution failed, falling back to procedural: {e}")

    return _run_procedural(state)


def _build_intent_response(intent: str, market_intel: dict) -> str:
    ipo = market_intel.get("ipo_data", {})
    news = market_intel.get("market_news", {})
    movers = market_intel.get("market_movers", {})
    geo = market_intel.get("geopolitical", {})
    company = market_intel.get("company_intel", {})
    indices = market_intel.get("global_indices", {})

    if intent in ("forecast", "scenario"):
        return (
            "I need a portfolio to analyze. "
            "Run an analysis first: **Analyse my portfolio with NVDA and AMZN with weights 0.7, 0.3**"
            ", or use the dashboard to analyse your holdings, then ask me for a forecast or stress test."
        )

    if intent == "ipo_query":
        upcoming = ipo.get("upcoming", [])
        if upcoming:
            lines = [f"**{x['company']}** ({x.get('ticker', '')}) — {x.get('date', 'TBA')}" for x in upcoming[:5]]
            return "**Upcoming IPOs:**\n" + "\n".join(lines)
        recent = ipo.get("recent", [])
        if recent:
            lines = [f"**{x['company']}** ({x.get('ticker', '')}) — {x.get('date', 'TBA')}" for x in recent[:5]]
            return "**Recent IPOs:**\n" + "\n".join(lines)
        return "No upcoming IPOs currently listed on major exchanges. Ask me about a specific company or market."

    if intent == "market_news":
        headlines = news.get("headlines", [])
        if headlines:
            lines = [f"• {h.get('title', '')}" for h in headlines[:8]]
            regions = news.get("regions_covered", [])
            header = f"**Market News** ({', '.join(regions)}):\n" if regions else "**Market News:**\n"
            return header + "\n".join(lines)
        return "No recent market news found. Try asking about a specific region or stock."

    if intent == "trending":
        gainers = movers.get("top_gainers", [])
        losers = movers.get("top_losers", [])
        parts = []
        if gainers:
            parts.append("**Gainers:** " + ", ".join(f"{x['ticker']} ({x['change_pct']:+.2f}%)" for x in gainers[:5]))
        if losers:
            parts.append("**Losers:** " + ", ".join(f"{x['ticker']} ({x['change_pct']:.2f}%)" for x in losers[:5]))
        if parts:
            return "\n".join(parts)
        return "No market movers data available right now."

    if intent == "geopolitical":
        summary = geo.get("summary", "")
        if summary:
            return "**Geopolitical Risk Intel:**\n" + summary[:500]
        return "No specific geopolitical alerts right now."

    if intent == "stock_query":
        if company:
            parts = []
            for t, ci in company.items():
                name = ci.get("name", t)
                price = ci.get("price")
                if price:
                    chg = ci.get("change_pct")
                    chg_str = f" ({chg:+.2f}%)" if chg else ""
                    parts.append(f"**{name}** ({t}): ${price}{chg_str}")
            if parts:
                return "\n".join(parts)
        return "I don't have enough info on that ticker. Try a specific symbol like AAPL or TSLA."

    if intent == "explain":
        lines = []
        if indices:
            for key, idx in list(indices.items())[:5]:
                region, name = key.split(".", 1)
                if idx.get("price"):
                    chg = idx.get("change_pct")
                    chg_str = f" ({chg:+.2f}%)" if chg else ""
                    lines.append(f"{region}/{name}: {idx['price']}{chg_str}")
        if news.get("headlines"):
            lines.append("News: " + "; ".join(h["title"] for h in news["headlines"][:3]))
        if lines:
            return "**Market Overview:**\n" + "\n".join(lines)
        return "Ask me about any stock, market, region, or event."

    return market_intel.get("summary", "") or "How can I help you today?"


def _run_procedural(state: dict) -> dict:
    current = dict(state)

    cn = intent_classifier(current)
    current.update(cn)

    msg = state.get("user_message", "")

    mi = market_intel_node(current)
    current.update(mi)

    global_intents = {"general_chat", "explain", "market_news", "ipo_query", "trending", "geopolitical", "stock_query"}

    if current.get("intent") in global_intents:
        msg = state.get("user_message", "")
        market_intel = current.get("market_intel", {})
        from agent.litellm_config import get_llm_response
        try:
            system_prompt = (
                "You are Vera, a senior financial intelligence analyst with a gift for making markets make sense. "
                "You analyze global markets, geopolitics, and macroeconomic trends. "
                "You are specific, cite exact numbers, and give actionable insights. "
                "Write in natural, flowing prose — 3-4 paragraphs that tell a coherent story about what's happening and why it matters. "
                "Connect the dots across regions and asset classes. Cover ALL major regions: US, Europe, Asia-Pacific, Emerging Markets. "
                "End with a clear, actionable takeaway."
            )
            market_summary = market_intel.get("summary", "")
            context = msg
            if market_summary:
                context = msg + "\n\nReal-time market intelligence:\n" + market_summary
            resp = get_llm_response([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ], temperature=0.5, max_tokens=800)
            current["risk_interpretation"] = resp.choices[0].message.content.strip()
        except Exception:
            intent = current.get("intent", "general_chat")
            current["risk_interpretation"] = _build_intent_response(intent, market_intel)
        current["action_items"] = current.get("action_items", []) or ["Ask Vera about stocks, IPOs, market news, geopolitics, or your portfolio risk"]
        current["health_score"] = current.get("health_score") or None
        current["report_markdown"] = ""
        rw = response_writer(current)
        current.update(rw)
        return current

    pl = portfolio_loader(current)
    current.update(pl)

    if not current.get("tickers"):
        current["risk_interpretation"] = (
            "I don't have a portfolio to analyze. Try asking me about specific markets, "
            "global events, or use the dashboard to run an analysis first."
        )
        current["action_items"] = ["Run a portfolio analysis on the dashboard", "Ask about global markets"]
        current["health_score"] = None
        current["report_markdown"] = ""
        rw = response_writer(current)
        current.update(rw)
        return current

    qn = quant_node(current)
    current.update(qn)

    sn = sentiment_node(current)
    current.update(sn)

    fn = forecast_node(current)
    current.update(fn)

    ri = risk_interpreter(current)
    current.update(ri)

    if current.get("mode") in ("morning_brief", "report") or current.get("intent") in ("forecast", "scenario", "rebalance"):
        ra = report_assembler(current)
        current.update(ra)

    rw = response_writer(current)
    current.update(rw)

    return current
