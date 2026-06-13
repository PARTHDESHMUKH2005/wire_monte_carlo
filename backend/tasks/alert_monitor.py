import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

_twilio_client = None
_sendgrid_client = None


def _get_twilio():
    global _twilio_client
    if _twilio_client is None and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            from twilio.rest import Client
            _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception:
            pass
    return _twilio_client


def _get_sendgrid():
    global _sendgrid_client
    if _sendgrid_client is None and SENDGRID_API_KEY:
        try:
            import sendgrid
            _sendgrid_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        except Exception:
            pass
    return _sendgrid_client


def _get_user_emails_and_phones(user_id: int):
    try:
        from database.connection import SessionLocal
        from database.models import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user.email, user.phone
            return None, None
        except Exception:
            return None, None
        finally:
            db.close()
    except Exception:
        return None, None


def check_all_thresholds():
    logger.info("Checking all alert thresholds...")
    try:
        from database.connection import SessionLocal
        from database.models import Alert
        db = SessionLocal()
        try:
            active_alerts = db.query(Alert).filter(Alert.active == True).all()
        except Exception:
            logger.error("Failed to query alerts")
            return
        finally:
            db.close()

        for alert in active_alerts:
            try:
                _check_single_alert(alert)
            except Exception as e:
                logger.error(f"Alert check failed for alert {alert.id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Alert monitor failed: {e}")


def _check_single_alert(alert):
    user_id = alert.user_id
    metric = alert.metric
    threshold = alert.threshold

    from agent.memory import get_last_risk_run
    last_run = get_last_risk_run(str(user_id))
    if not last_run:
        return

    quant_metrics = last_run.get("quant_metrics", {})
    current_value = None

    if metric == "var_95":
        current_value = quant_metrics.get("var_95", 0) / 1_000_000 * 100
    elif metric == "health_score":
        current_value = last_run.get("health_score", 100)
    elif metric == "volatility":
        current_value = quant_metrics.get("garch_vol", 0) * 100
    elif metric == "cvar":
        current_value = quant_metrics.get("cvar", 0) / 1_000_000 * 100
    else:
        return

    if current_value is None:
        return

    breached = False
    comparison = "above"
    if metric == "health_score":
        breached = current_value < threshold
        comparison = "below"
    else:
        breached = current_value > threshold

    if not breached:
        return

    try:
        from database.connection import SessionLocal
        from database.models import Alert
        db = SessionLocal()
        try:
            stored = db.query(Alert).filter(Alert.id == alert.id).first()
            if stored and stored.last_triggered:
                last = stored.last_triggered
                if hasattr(last, 'timestamp') and (datetime.utcnow() - last).total_seconds() < 3600:
                    db.close()
                    return
            if stored:
                stored.last_triggered = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:
        pass

    email, phone = _get_user_emails_and_phones(user_id)
    health_score = last_run.get("health_score", "N/A")

    alert_msg = (
        f"⚠️ LiveRisk Alert\n\n"
        f"Your {metric} just hit {current_value:.1f} — {comparison} your {threshold} threshold.\n"
        f"Portfolio health: {health_score}/100\n\n"
        f"Verdict: Threshold breach detected for {metric}. Review your portfolio's risk exposure.\n\n"
        f"Open LiveRisk for full analysis."
    )

    if TWILIO_ACCOUNT_SID and phone:
        try:
            client = _get_twilio()
            if client:
                client.messages.create(
                    body=alert_msg[:1600],
                    from_=TWILIO_WHATSAPP_FROM,
                    to=f"whatsapp:{phone}",
                )
                logger.info(f"Alert WhatsApp sent to {phone}")
        except Exception as e:
            logger.error(f"Alert WhatsApp failed: {e}")

    if SENDGRID_API_KEY and email:
        try:
            client = _get_sendgrid()
            if client:
                from sendgrid.helpers.mail import Mail
                message = Mail(
                    from_email="vera@liverisk.app",
                    to_emails=email,
                    subject=f"LiveRisk Alert: {metric} threshold breached",
                    html_content=f"<p>{alert_msg}</p>",
                )
                client.send(message)
                logger.info(f"Alert email sent to {email}")
        except Exception as e:
            logger.error(f"Alert email failed: {e}")

    logger.info(f"Alert triggered for user {user_id}: {metric}={current_value:.1f} vs threshold={threshold}")


def refresh_all_health_scores():
    logger.info("Refreshing all health scores...")
    try:
        from database.connection import SessionLocal
        from database.models import User, Portfolio
        db = SessionLocal()
        try:
            users = db.query(User).all()
        except Exception:
            logger.error("Failed to query users for health refresh")
            return
        finally:
            db.close()

        for user in users:
            try:
                from agent.vera import run_vera
                from agent.memory import get_last_risk_run
                last_run = get_last_risk_run(str(user.id))
                tickers = ["SPY", "QQQ"]
                weights = [0.6, 0.4]
                if last_run:
                    qm = last_run.get("quant_metrics", {})
                    if qm.get("tickers"):
                        tickers = qm["tickers"]
                        weights = qm.get("weights", weights)

                state = {
                    "tickers": tickers,
                    "weights": weights,
                    "user_id": str(user.id),
                    "user_message": "Refresh health score",
                    "conversation_history": [],
                    "portfolio_context": {},
                    "market_data": {},
                    "quant_metrics": {},
                    "sentiment_analysis": {},
                    "forecast": {},
                    "risk_interpretation": "",
                    "report_markdown": "",
                    "action_items": [],
                    "health_score": 50,
                    "intent": "",
                    "mode": "chat",
                }
                run_vera(state)
            except Exception as e:
                logger.debug(f"Health refresh failed for user {user.id}: {e}")
                continue

        logger.info(f"Health scores refreshed for all users")
    except Exception as e:
        logger.error(f"Health score refresh failed: {e}")


def weekly_accountability_all():
    logger.info("Running weekly accountability for all users...")
    try:
        from database.connection import SessionLocal
        from database.models import User
        db = SessionLocal()
        try:
            users = db.query(User).all()
        except Exception:
            return
        finally:
            db.close()

        for user in users:
            try:
                from agent.accountability import weekly_accountability_check
                report = weekly_accountability_check(str(user.id))
                logger.info(f"Accountability for user {user.id}: {len(report)} chars")
            except Exception as e:
                logger.debug(f"Accountability failed for user {user.id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Weekly accountability run failed: {e}")
