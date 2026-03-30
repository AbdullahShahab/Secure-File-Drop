from fastapi import FastAPI  # type: ignore
from .database import init_db

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}