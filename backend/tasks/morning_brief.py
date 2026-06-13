import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

_twilio_client = None
_sendgrid_client = None


def _get_twilio():
    global _twilio_client
    if _twilio_client is None and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            from twilio.rest import Client
            _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception as e:
            logger.warning(f"Twilio init failed: {e}")
    return _twilio_client


def _get_sendgrid():
    global _sendgrid_client
    if _sendgrid_client is None and SENDGRID_API_KEY:
        try:
            import sendgrid
            _sendgrid_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        except Exception as e:
            logger.warning(f"SendGrid init failed: {e}")
    return _sendgrid_client


def _get_all_subscribed_users():
    try:
        from database.connection import SessionLocal
        from database.models import User
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.briefs_enabled == True).all()
            return [(u.id, u.email, u.phone) for u in users]
        except Exception:
            return []
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get subscribed users: {e}")
        return []


def _get_portfolio_for_user(user_id: int) -> tuple:
    try:
        from database.connection import SessionLocal
        from database.models import Portfolio
        db = SessionLocal()
        try:
            port = db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.updated_at.desc()).first()
            if port and port.portfolio_json:
                data = json.loads(port.portfolio_json)
                tickers = data.get("tickers", [])
                weights = data.get("weights", [])
                if tickers and weights:
                    return tickers, weights
        except Exception:
            pass
        finally:
            db.close()
    except Exception:
        pass
    return ["SPY", "QQQ", "AGG", "GLD"], [0.4, 0.3, 0.2, 0.1]


def _send_whatsapp(phone: str, message: str) -> bool:
    client = _get_twilio()
    if not client or not phone:
        logger.warning("Twilio not configured or no phone — skipping WhatsApp")
        return False
    try:
        msg = client.messages.create(
            body=message[:1600],
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{phone}",
        )
        logger.info(f"WhatsApp sent to {phone}: SID {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Twilio send failed for {phone}: {e}")
        return False


def _send_email(email: str, subject: str, html: str, attachment_pdf: bytes = None) -> bool:
    client = _get_sendgrid()
    if not client or not email:
        logger.warning("SendGrid not configured or no email — skipping")
        return False
    try:
        from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
        message = Mail(
            from_email="vera@liverisk.app",
            to_emails=email,
            subject=subject,
            html_content=html,
        )
        if attachment_pdf:
            import base64
            encoded = base64.b64encode(attachment_pdf).decode()
            attachment = Attachment(
                FileContent(encoded),
                FileName("LiveRisk_Report.pdf"),
                FileType("application/pdf"),
                Disposition("attachment"),
            )
            message.add_attachment(attachment)
        response = client.send(message)
        logger.info(f"Email sent to {email}: status {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"SendGrid send failed for {email}: {e}")
        return False


def _log_brief(user_id: int, channel: str, success: bool, error: str = None):
    try:
        from database.connection import SessionLocal
        from database.models import BriefLog
        db = SessionLocal()
        try:
            log = BriefLog(user_id=user_id, channel=channel, success=success, error_message=error)
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:
        pass


def send_morning_brief_for_user(user_id: int, email: str, phone: str):
    try:
        from agent.vera import run_vera
        tickers, weights = _get_portfolio_for_user(user_id)

        state = {
            "tickers": tickers,
            "weights": weights,
            "user_id": str(user_id),
            "user_message": "Generate my morning brief",
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
            "mode": "morning_brief",
        }

        result = run_vera(state)
        report = result.get("report_markdown", "")
        health_score = result.get("health_score", 50)
        forecast = result.get("forecast", {})
        interpretation = result.get("risk_interpretation", "")

        today = datetime.now().strftime("%b %d, %Y")
        base_ret = forecast.get("base", {}).get("return_pct", "N/A")
        bull_ret = forecast.get("bull", {}).get("return_pct", "N/A")
        bear_ret = forecast.get("bear", {}).get("return_pct", "N/A")

        score_trend = "↑" if health_score >= 75 else "→" if health_score >= 50 else "↓"
        changes = interpretation[:200] if interpretation else "No significant changes detected."
        action = result.get("action_items", ["No action required"])[0]
        link = f"{FRONTEND_URL}/vera"

        whatsapp_msg = (
            f"LiveRisk Morning Brief · {today}\n\n"
            f"Portfolio health: {health_score}/100 {score_trend}\n\n"
            f"What changed:\n{changes}\n\n"
            f"60-day outlook:\n"
            f"Base: {base_ret}% | Bull: {bull_ret}% | Bear: {bear_ret}%\n\n"
            f"Action: {action}\n\n"
            f"Full analysis: {link}\n"
            f"Reply REBALANCE for optimization\n"
            f"Reply STOP to pause briefs"
        )

        email_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: linear-gradient(135deg, #0a1628, #1a1a3e); padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="color: #22c55e; margin: 0;">LiveRisk Morning Brief</h1>
            <p style="color: #94a3b8; margin: 4px 0 0;">{today}</p>
          </div>
          <div style="padding: 20px; background: #fff; color: #1a1a2e; border: 1px solid #e2e8f0;">
            <p><strong>Portfolio Health:</strong> {health_score}/100</p>
            <hr>
            {report[:2000] if report else '<p>Brief content unavailable.</p>'}
            <hr>
            <p style="color: #64748b; font-size: 12px;">
              <a href="{link}" style="color: #22c55e;">Open LiveRisk Dashboard</a> |
              Reply to this email to adjust preferences
            </p>
          </div>
        </div>
        """

        pdf_bytes = None
        if report:
            try:
                from agent.pdf_generator import generate_pdf
                pdf_bytes = generate_pdf(report, str(user_id))
            except Exception as e:
                logger.warning(f"PDF generation failed for brief: {e}")

        wa_success = False
        email_success = False

        if phone:
            wa_success = _send_whatsapp(phone, whatsapp_msg)
            _log_brief(user_id, "whatsapp", wa_success)

        if email:
            email_success = _send_email(
                email,
                f"LiveRisk Morning Brief — {today}",
                email_html,
                pdf_bytes,
            )
            _log_brief(user_id, "email", email_success)

        logger.info(f"Morning brief sent to user {user_id}: WA={wa_success}, Email={email_success}")

    except Exception as e:
        logger.error(f"Morning brief failed for user {user_id}: {e}")
        _log_brief(user_id, "internal", False, str(e))


def send_all_morning_briefs():
    logger.info("Starting all morning briefs...")
    users = _get_all_subscribed_users()
    if not users:
        logger.info("No subscribed users found")
        return

    for user_id, email, phone in users:
        try:
            send_morning_brief_for_user(user_id, email, phone)
        except Exception as e:
            logger.error(f"Brief failed for user {user_id}, continuing: {e}")
            continue

    logger.info(f"Completed {len(users)} morning briefs")
