import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()  # pulls GMAIL_USER / GMAIL_APP_PASSWORD from .env into os.environ

# secret.key lives in the project root (one level above src/)
KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "secret.key")


def _load_or_create_key() -> bytes:
    """Return the Fernet key, generating and persisting one if it does not exist."""
    key_path = os.path.abspath(KEY_PATH)
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read().strip()
    # First run — generate a new key and write it to disk
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key


def get_fernet() -> Fernet:
    """Return a ready-to-use Fernet instance backed by the project secret key."""
    return Fernet(_load_or_create_key())


# ── Email notification ─────────────────────────────────────────────────────

def send_download_notification(
    sender_email: str,
    original_filename: str,
    downloaded_at: datetime,
) -> None:
    """
    Send a plain-text notification to sender_email confirming their file
    was downloaded. Swallows all exceptions so a broken SMTP config never
    crashes the download response.
    """
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_user or not gmail_password:
        print("[email] Warning: GMAIL_USER or GMAIL_APP_PASSWORD not set — skipping notification.")
        return

    downloaded_str = downloaded_at.strftime("%B %d, %Y at %I:%M %p UTC")

    msg = EmailMessage()
    msg["Subject"] = "Your file was downloaded — Secure File Drop"
    msg["From"] = gmail_user
    msg["To"] = sender_email
    msg.set_content(
        f"Hi,\n\n"
        f"Your file \"{original_filename}\" was downloaded on {downloaded_str}.\n\n"
        f"If you did not expect this, your share link may have been forwarded.\n\n"
        f"— Secure File Drop"
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
    except Exception as exc:
        print(f"[email] Warning: failed to send download notification — {exc}")
