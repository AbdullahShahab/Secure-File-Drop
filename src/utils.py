import os
import resend
from datetime import datetime

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Resolve .env relative to the project root (one level above src/)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# secret.key lives in the project root (one level above src/)
KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "secret.key")


def _load_or_create_key() -> bytes:
    # Prefer env var so the key survives container restarts/redeploys (e.g. Railway)
    env_key = os.environ.get("FERNET_KEY", "").strip()
    if env_key:
        return env_key.encode()

    key_path = os.path.abspath(KEY_PATH)
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key


def get_fernet() -> Fernet:
    return Fernet(_load_or_create_key())


# ── Email notification ─────────────────────────────────────────────────────

def send_download_notification(
    recipient_email: str,
    filename: str,
    downloaded_at: datetime,
) -> None:
    """Send a download notification email via Resend. Never raises."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_address = os.environ.get("RESEND_FROM", "Secure File Drop <noreply@resend.dev>").strip()

    if not api_key:
        print("[email] Warning: RESEND_API_KEY not set — skipping notification.")
        return

    resend.api_key = api_key

    timestamp = downloaded_at.strftime("%B %d, %Y at %I:%M %p UTC")

    try:
        resend.Emails.send({
            "from": from_address,
            "to": [recipient_email],
            "subject": f"Your file \"{filename}\" was downloaded",
            "html": (
                f"<p>Hi,</p>"
                f"<p>Your file <strong>{filename}</strong> was downloaded on {timestamp}.</p>"
                f"<p>— Secure File Drop</p>"
            ),
        })
        print(f"[email] Notification sent to {recipient_email} for '{filename}'.")
    except Exception as e:
        print(f"[email] Warning: failed to send notification — {e}")
