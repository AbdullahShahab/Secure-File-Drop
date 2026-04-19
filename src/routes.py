import os
import secrets
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from .database import get_connection

BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(BASE_DIR, "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────

def _format_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _format_expires(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y at %I:%M %p UTC")


# ── Upload ──────────────────────────────────────────────────────────────────

@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    expires_in: int = Form(24),
    one_time_download: str = Form(None),
    passcode: str = Form(""),
):
    contents = await file.read()
    file_size = len(contents)

    token = secrets.token_urlsafe(32)
    ext = Path(file.filename).suffix
    stored_filename = f"{token}{ext}"
    dest = os.path.join(STORAGE_DIR, stored_filename)

    with open(dest, "wb") as f:
        f.write(contents)

    passcode_hash = None
    if passcode:
        passcode_hash = bcrypt.hashpw(passcode.encode(), bcrypt.gensalt()).decode()

    one_time = 1 if one_time_download == "1" else 0
    expires_at = datetime.utcnow() + timedelta(hours=expires_in)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO files
              (stored_filename, original_filename, file_size, file_type,
               token, passcode_hash, one_time_download, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored_filename,
                file.filename,
                file_size,
                file.content_type,
                token,
                passcode_hash,
                one_time,
                expires_at.isoformat(),
            ),
        )
        conn.commit()

    share_url = str(request.base_url) + f"download/{token}"

    return templates.TemplateResponse(request, "upload_result.html", {
        "share_url": share_url,
        "original_filename": file.filename,
        "file_size": _format_size(file_size),
        "expires_at": _format_expires(expires_at),
        "one_time_download": bool(one_time),
        "passcode_set": bool(passcode_hash),
    })


# ── Download ────────────────────────────────────────────────────────────────

def _lookup(token: str):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM files WHERE token = ?", (token,)
        ).fetchone()


def _is_expired(row) -> bool:
    expires_at = datetime.fromisoformat(row["expires_at"])
    return datetime.utcnow() > expires_at


def _is_invalid(row) -> bool:
    return row is None or (row["one_time_download"] and row["is_used"])


@router.get("/download/{token}")
def download_get(token: str, request: Request):
    row = _lookup(token)

    if _is_invalid(row):
        return templates.TemplateResponse(request, "invalid.html", status_code=404)

    if _is_expired(row):
        return templates.TemplateResponse(request, "expired.html", status_code=410)

    if row["passcode_hash"]:
        return templates.TemplateResponse(request, "enter_passcode.html", {
            "token": token,
            "error": False,
        })

    return _serve_file(row)


@router.post("/download/{token}")
def download_post(token: str, request: Request, passcode: str = Form(...)):
    row = _lookup(token)

    if _is_invalid(row):
        return templates.TemplateResponse(request, "invalid.html", status_code=404)

    if _is_expired(row):
        return templates.TemplateResponse(request, "expired.html", status_code=410)

    if not bcrypt.checkpw(passcode.encode(), row["passcode_hash"].encode()):
        return templates.TemplateResponse(request, "enter_passcode.html", {
            "token": token,
            "error": True,
        })

    return _serve_file(row)


def _serve_file(row):
    file_path = os.path.join(STORAGE_DIR, row["stored_filename"])

    if row["one_time_download"]:
        with get_connection() as conn:
            conn.execute("UPDATE files SET is_used = 1 WHERE token = ?", (row["token"],))
            conn.commit()

    return FileResponse(
        path=file_path,
        filename=row["original_filename"],
        media_type=row["file_type"] or "application/octet-stream",
    )
