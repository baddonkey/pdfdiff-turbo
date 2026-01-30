from celery import Celery

from app.core.config import settings

celery_app = Celery("pdfdiff")
celery_app.conf.broker_url = settings.celery_broker_url
celery_app.conf.result_backend = settings.celery_result_backend
celery_app.conf.task_track_started = True
celery_app.conf.result_extended = True
celery_app.conf.include = ["app.worker.tasks"]
