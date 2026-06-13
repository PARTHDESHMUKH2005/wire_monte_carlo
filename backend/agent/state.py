from typing import TypedDict, Optional


class RiskAgentState(TypedDict):
    tickers: list[str]
    weights: list[float]
    user_id: str
    user_message: str
    conversation_history: list[dict]
    portfolio_context: dict
    market_data: dict
    quant_metrics: dict
    sentiment_analysis: dict
    forecast: dict
    risk_interpretation: str
    report_markdown: str
    action_items: list[str]
    health_score: int
    intent: str
    mode: str
    market_intel: dict
    response: str
