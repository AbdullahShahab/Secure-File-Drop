import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from .database import init_db
from .cleanup import cleanup_expired_files
from .routes import router

BASE_DIR = os.path.dirname(__file__)

app = FastAPI(title="Secure File Drop")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Module-level scheduler so uvicorn --reload does not spawn duplicate instances
_scheduler = BackgroundScheduler(daemon=True)


@app.on_event("startup")
def startup():
    init_db()

    # Guard against double-start under uvicorn --reload (the reloader forks the
    # process; the scheduler is already running in the parent, not this worker).
    try:
        if not _scheduler.running:
            _scheduler.add_job(
                cleanup_expired_files,
                trigger="interval",
                hours=1,
                id="cleanup_expired_files",
                replace_existing=True,
            )
            _scheduler.start()
            print("[scheduler] Cleanup job scheduled — runs every 1 hour.")
    except Exception as exc:
        print(f"[scheduler] Warning: could not start scheduler — {exc}")


app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
