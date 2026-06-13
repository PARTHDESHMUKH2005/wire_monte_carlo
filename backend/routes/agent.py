import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

agent_router = APIRouter(prefix="/agent")


class ChatRequest(BaseModel):
    message: str
    user_id: str = "0"
    tickers: Optional[list[str]] = None
    weights: Optional[list[float]] = None


class ReportRequest(BaseModel):
    user_id: str = "0"


class AlertRequest(BaseModel):
    user_id: str
    metric: str
    threshold: float


class SubscribeRequest(BaseModel):
    user_id: str
    email: str = ""
    phone: str = ""
    tier: str = "free"


@agent_router.post("/chat")
async def agent_chat(req: ChatRequest):
    try:
        from agent.vera import run_vera

        state = {
            "tickers": req.tickers or [],
            "weights": req.weights or [],
            "user_id": req.user_id,
            "user_message": req.message,
            "conversation_history": [],
            "portfolio_context": {},
            "market_data": {},
            "quant_metrics": {},
            "sentiment_analysis": {},
            "forecast": {},
            "risk_interpretation": "",
            "report_markdown": "",
            "action_items": [],
            "health_score": None,
            "intent": "",
            "mode": "chat",
            "market_intel": {},
            "response": "",
        }

        async def event_stream():
            yield f"data: {json.dumps({'token': '', 'node': 'intent_classifier'})}\n\n"
            try:
                from fastapi.concurrency import run_in_threadpool
                result = await run_in_threadpool(run_vera, state)

                response_text = result.get("response", "") or result.get("risk_interpretation", "")
                health_score = result.get("health_score") or None
                action_items = result.get("action_items", [])
                forecast = result.get("forecast", {})
                quant_metrics = result.get("quant_metrics", {})
                tickers = result.get("tickers", [])

                if not response_text:
                    response_text = "I'm Vera. Ask me about your portfolio, market news, or run a risk analysis."

                words = response_text.split(" ")
                chunk_size = max(1, len(words) // 20) if len(words) > 20 else 1

                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i + chunk_size])
                    yield f"data: {json.dumps({'token': chunk + ' ', 'node': 'response_writer'})}\n\n"

                done_payload = {
                    'done': True,
                    'action_items': action_items,
                    'health_score': health_score,
                }
                market_intel = result.get("market_intel", {})
                if market_intel and isinstance(market_intel, dict):
                    done_payload['market_intel'] = {
                        k: v for k, v in market_intel.items()
                        if k in ("summary", "company_intel", "market_movers", "ipo_data", "market_news")
                    }
                if forecast and isinstance(forecast, dict) and 'bull' in forecast:
                    done_payload['forecast'] = forecast
                if quant_metrics and isinstance(quant_metrics, dict) and 'var_95' in quant_metrics:
                    safe_qm = {k: v for k, v in quant_metrics.items() if k != 'stress_results'}
                    done_payload['metrics'] = safe_qm

                yield f"data: {json.dumps(done_payload)}\n\n"
            except Exception as e:
                logger.error(f"Agent chat error: {e}", exc_info=True)
                yield f"data: {json.dumps({'token': 'I encountered an error processing your request. Please try again.', 'node': 'response_writer'})}\n\n"
                yield f"data: {json.dumps({'done': True, 'action_items': [], 'health_score': None})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Agent chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/report")
async def agent_report(req: ReportRequest):
    try:
        from agent.vera import run_vera
        from agent.memory import get_conversation_history, get_last_risk_run
        from fastapi.concurrency import run_in_threadpool

        history = get_conversation_history(req.user_id, limit=4)
        last_run = get_last_risk_run(req.user_id)

        tickers = []
        weights = []

        if last_run:
            qm = last_run.get("quant_metrics", {})
            if qm.get("tickers"):
                tickers = qm["tickers"]
                weights = qm.get("weights", weights)

        state = {
            "tickers": tickers,
            "weights": weights,
            "user_id": req.user_id,
            "user_message": "Generate full portfolio risk report",
            "conversation_history": history,
            "portfolio_context": {},
            "market_data": {},
            "quant_metrics": {},
            "sentiment_analysis": {},
            "forecast": {},
            "risk_interpretation": "",
            "report_markdown": "",
            "action_items": [],
            "health_score": None,
            "intent": "",
            "mode": "report",
        }

        result = await run_in_threadpool(run_vera, state)

        return {
            "report_markdown": result.get("report_markdown", ""),
            "health_score": result.get("health_score") or None,
            "forecast": result.get("forecast", {}),
            "action_items": result.get("action_items", []),
        }
    except Exception as e:
        logger.error(f"Agent report endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.get("/report/pdf/{user_id}")
async def agent_report_pdf(user_id: str):
    try:
        from agent.memory import get_last_risk_run
        from database.connection import SessionLocal
        from database.models import RiskRun
        from agent.pdf_generator import generate_pdf

        db = SessionLocal()
        try:
            run = (
                db.query(RiskRun)
                .filter(RiskRun.user_id == int(user_id))
                .order_by(RiskRun.created_at.desc())
                .first()
            )
            if not run or not run.report_markdown:
                raise HTTPException(status_code=404, detail="No report found")
            report_md = run.report_markdown
        except HTTPException:
            raise
        except Exception:
            last_run = get_last_risk_run(user_id)
            report_md = last_run.get("report_markdown", "")
            if not report_md:
                raise HTTPException(status_code=404, detail="No report found. Generate one first via POST /api/agent/report")
        finally:
            db.close()

        pdf_bytes = generate_pdf(report_md, user_id)

        temp_path = f"/tmp/liverisk_report_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)

        return FileResponse(
            temp_path,
            media_type="application/pdf",
            filename=f"LiveRisk_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            headers={"Content-Disposition": f'attachment; filename="LiveRisk_Report_{datetime.now().strftime("%Y%m%d")}.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/alerts")
async def create_alert(req: AlertRequest):
    try:
        from database.connection import SessionLocal
        from database.models import Alert

        db = SessionLocal()
        try:
            existing = db.query(Alert).filter(
                Alert.user_id == int(req.user_id),
                Alert.metric == req.metric,
            ).first()
            if existing:
                existing.threshold = req.threshold
                existing.active = True
            else:
                alert = Alert(
                    user_id=int(req.user_id),
                    metric=req.metric,
                    threshold=req.threshold,
                    active=True,
                )
                db.add(alert)
            db.commit()
            return {"success": True, "metric": req.metric, "threshold": req.threshold}
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save alert")
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.get("/history/{user_id}")
async def get_agent_history(user_id: str):
    try:
        from agent.memory import get_conversation_history
        history = get_conversation_history(user_id, limit=50)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.get("/accountability/{user_id}")
async def get_accountability(user_id: str):
    try:
        from agent.accountability import weekly_accountability_check
        report = weekly_accountability_check(user_id)
        return {"accountability": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/subscribe")
async def subscribe(req: SubscribeRequest):
    try:
        from database.connection import SessionLocal
        from database.models import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(req.user_id)).first()
            if user:
                user.email = req.email or user.email
                user.phone = req.phone or user.phone
                user.subscription_tier = req.tier
                user.briefs_enabled = True
                if req.phone:
                    user.whatsapp_enabled = True
            else:
                user = User(
                    id=int(req.user_id),
                    email=req.email,
                    phone=req.phone,
                    subscription_tier=req.tier,
                    briefs_enabled=True,
                    whatsapp_enabled=bool(req.phone),
                )
                db.add(user)
            db.commit()
            return {"success": True}
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save subscription")
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/unsubscribe/{user_id}")
async def unsubscribe(user_id: str):
    try:
        from database.connection import SessionLocal
        from database.models import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.briefs_enabled = False
                db.commit()
            return {"success": True}
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update subscription")
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
