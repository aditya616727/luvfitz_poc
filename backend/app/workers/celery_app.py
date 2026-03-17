"""
Celery application configuration.
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "outfit_builder",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.scrape_tasks",
        "app.workers.refresh_tasks",
        "app.workers.outfit_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,  # 10 min
    task_time_limit=900,  # 15 min
)

# ── Periodic task schedule (beat) ──
celery_app.conf.beat_schedule = {
    "daily-price-refresh": {
        "task": "app.workers.refresh_tasks.refresh_all_products",
        "schedule": crontab(hour=3, minute=0),  # 3 AM UTC daily
        "options": {"queue": "refresh"},
    },
    "daily-outfit-generation": {
        "task": "app.workers.outfit_tasks.regenerate_outfits",
        "schedule": crontab(hour=4, minute=0),  # 4 AM UTC daily (after refresh)
        "options": {"queue": "outfits"},
    },
}
