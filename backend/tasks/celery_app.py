import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_AVAILABLE = False
CELERY_BROKER_AVAILABLE = False

try:
    import redis as _redis_check
    c = _redis_check.from_url(REDIS_URL)
    c.ping()
    CELERY_BROKER_AVAILABLE = True
except Exception:
    logger.warning("Redis not available — Celery tasks will not run. Start Redis with: docker run -d -p 6379:6379 redis:alpine")

if CELERY_BROKER_AVAILABLE:
    try:
        from celery import Celery
        from celery.schedules import crontab

        celery_app = Celery(
            "vera_tasks",
            broker=REDIS_URL,
            backend=REDIS_URL,
        )

        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="Asia/Kolkata",
            enable_utc=True,
            beat_schedule={
                "morning-brief-daily": {
                    "task": "backend.tasks.morning_brief.send_all_morning_briefs",
                    "schedule": crontab(hour=6, minute=30),
                    "options": {"expires": 600},
                },
                "alert-check-quarterly": {
                    "task": "backend.tasks.alert_monitor.check_all_thresholds",
                    "schedule": crontab(hour="9-15", minute="*/15"),
                    "options": {"expires": 300},
                },
                "health-score-hourly": {
                    "task": "backend.tasks.alert_monitor.refresh_all_health_scores",
                    "schedule": crontab(minute="*/60"),
                    "options": {"expires": 300},
                },
                "weekly-accountability-monday": {
                    "task": "backend.tasks.alert_monitor.weekly_accountability_all",
                    "schedule": crontab(hour=8, minute=0, day_of_week=1),
                    "options": {"expires": 600},
                },
            },
            task_track_started=True,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
        )

        CELERY_AVAILABLE = True
        logger.info("Celery app initialized with beat schedule")
    except Exception as e:
        logger.warning(f"Celery initialization failed: {e}")
        CELERY_AVAILABLE = False
else:
    celery_app = None
