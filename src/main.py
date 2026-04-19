import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import init_db
from .routes import router

BASE_DIR = os.path.dirname(__file__)

app = FastAPI(title="Secure File Drop")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.on_event("startup")
def startup():
    init_db()

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}
