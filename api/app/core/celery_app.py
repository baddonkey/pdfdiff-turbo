from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("pdfdiff")
celery_app.conf.broker_url = settings.celery_broker_url
celery_app.conf.result_backend = settings.celery_result_backend
celery_app.conf.task_track_started = True
celery_app.conf.result_extended = True
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True
celery_app.conf.task_default_queue = "pages"
celery_app.conf.task_routes = {
	"run_job": {"queue": "jobs"},
	"enqueue_pages": {"queue": "jobs"},
	"compare_page": {"queue": "pages"},
	"extract_text": {"queue": "jobs"},
	"cleanup_retention": {"queue": "jobs"},
}
celery_app.conf.include = ["app.worker.tasks"]
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
	"cleanup-retention-daily": {
		"task": "cleanup_retention",
		"schedule": crontab(minute=0, hour=2),
	}
}
