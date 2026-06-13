import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None and REDIS_URL:
        try:
            import redis as _redis_module
            _redis_client = _redis_module.from_url(REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            _redis_client = None
    return _redis_client


def save_conversation_turn(user_id: str, role: str, content: str, intent: str = None):
    try:
        from database.connection import SessionLocal
        from database.models import Conversation
        db = SessionLocal()
        try:
            from database.models import User
            user = db.query(User).filter(User.id == int(user_id)).first()
            uid = user.id if user else int(user_id)
            conv = Conversation(user_id=uid, role=role, content=content, intent=intent)
            db.add(conv)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Save conversation failed: {e}")


def get_conversation_history(user_id: str, limit: int = 8) -> list:
    try:
        from database.connection import SessionLocal
        from database.models import Conversation
        db = SessionLocal()
        try:
            from database.models import User
            user = db.query(User).filter(User.id == int(user_id)).first()
            uid = user.id if user else int(user_id)
            rows = (
                db.query(Conversation)
                .filter(Conversation.user_id == uid)
                .order_by(Conversation.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {"role": r.role, "content": r.content, "intent": r.intent, "timestamp": r.timestamp.isoformat() if r.timestamp else ""}
                for r in reversed(rows)
            ]
        except Exception:
            return []
        finally:
            db.close()
    except Exception:
        return []


def extract_user_preferences(conversation_history: list) -> dict:
    if not conversation_history:
        return {}
    try:
        from agent.litellm_config import get_llm_response
        messages = [
            {
                "role": "system",
                "content": "Extract user preferences from this conversation history. Return ONLY JSON with these optional fields: horizon (short/medium/long), risk_tolerance (low/medium/high), tax_sensitivity (low/medium/high), concerns (list of strings), goals (list of strings). If not enough info, return {}.",
            },
            {
                "role": "user",
                "content": json.dumps([{"role": h["role"], "content": h["content"]} for h in conversation_history[-6:]]),
            },
        ]
        response = get_llm_response(messages, temperature=0.1, max_tokens=500)
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        prefs = json.loads(text) if text.startswith("{") else {}
        if prefs and isinstance(prefs, dict):
            try:
                from database.connection import SessionLocal
                from database.models import UserPreference
                db = SessionLocal()
                try:
                    existing = db.query(UserPreference).filter(
                        UserPreference.user_id == int(conversation_history[-1].get("user_id", 0))
                    ).first()
                    if existing:
                        existing.horizon = prefs.get("horizon", existing.horizon)
                        existing.risk_tolerance = prefs.get("risk_tolerance", existing.risk_tolerance)
                        existing.tax_sensitivity = prefs.get("tax_sensitivity", existing.tax_sensitivity)
                        existing.concerns_json = json.dumps(prefs.get("concerns", []))
                        existing.goals_json = json.dumps(prefs.get("goals", []))
                    else:
                        up = UserPreference(
                            user_id=int(conversation_history[-1].get("user_id", 0)),
                            horizon=prefs.get("horizon"),
                            risk_tolerance=prefs.get("risk_tolerance"),
                            tax_sensitivity=prefs.get("tax_sensitivity"),
                            concerns_json=json.dumps(prefs.get("concerns", [])),
                            goals_json=json.dumps(prefs.get("goals", [])),
                        )
                        db.add(up)
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()
            except Exception:
                pass
        return prefs
    except Exception as e:
        logger.debug(f"Extract preferences failed: {e}")
        return {}


def save_risk_run(user_id: str, quant_metrics: dict, forecast: dict, report_markdown: str, health_score: int):
    try:
        from database.connection import SessionLocal
        from database.models import RiskRun
        db = SessionLocal()
        try:
            run = RiskRun(
                user_id=int(user_id),
                quant_metrics_json=json.dumps(quant_metrics),
                forecast_json=json.dumps(forecast),
                report_markdown=report_markdown,
                health_score=health_score,
            )
            db.add(run)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Save risk run failed: {e}")

    r = _get_redis()
    if r:
        try:
            r.setex(f"risk:{user_id}:latest", 3600, json.dumps({
                "quant_metrics": quant_metrics,
                "forecast": forecast,
                "health_score": health_score,
            }))
        except Exception:
            pass


def get_last_risk_run(user_id: str) -> dict:
    r = _get_redis()
    if r:
        try:
            data = r.get(f"risk:{user_id}:latest")
            if data:
                return json.loads(data)
        except Exception:
            pass
    try:
        from database.connection import SessionLocal
        from database.models import RiskRun
        db = SessionLocal()
        try:
            run = (
                db.query(RiskRun)
                .filter(RiskRun.user_id == int(user_id))
                .order_by(RiskRun.created_at.desc())
                .first()
            )
            if run:
                return {
                    "quant_metrics": json.loads(run.quant_metrics_json) if run.quant_metrics_json else {},
                    "forecast": json.loads(run.forecast_json) if run.forecast_json else {},
                    "health_score": run.health_score,
                }
            return {}
        except Exception:
            return {}
        finally:
            db.close()
    except Exception:
        return {}
