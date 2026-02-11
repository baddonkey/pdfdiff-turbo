import asyncio
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.report_events import start_report_event_consumer
from app.core.report_ws import report_ws_manager
from app.db.session import engine
from app.features.admin.router import router as admin_router
from app.features.auth.router import router as auth_router
from app.features.config.router import router as config_router
from app.features.jobs.router import router as jobs_router
from app.features.reports.router import router as reports_router
from app.version import API_VERSION

app = FastAPI(
    title=settings.project_name,
    version=API_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:4201",
        "http://127.0.0.1:4201",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(config_router)


@app.on_event("startup")
async def start_report_event_listener() -> None:
    loop = asyncio.get_running_loop()
    stop_event = threading.Event()
    app.state.report_events_stop = stop_event

    def on_message(payload: dict) -> None:
        user_id = payload.pop("user_id", None)
        if not user_id:
            return
        asyncio.run_coroutine_threadsafe(
            report_ws_manager.broadcast_to_user(user_id, payload),
            loop,
        )

    thread = threading.Thread(
        target=start_report_event_consumer,
        args=(settings.celery_broker_url, on_message, stop_event),
        daemon=True,
        name="report-events-consumer",
    )
    app.state.report_events_thread = thread
    thread.start()


@app.on_event("shutdown")
async def stop_report_event_consumer() -> None:
    stop_event = getattr(app.state, "report_events_stop", None)
    if stop_event:
        stop_event.set()


@app.get("/version")
async def version() -> dict:
    return {"version": API_VERSION}


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ready"}
