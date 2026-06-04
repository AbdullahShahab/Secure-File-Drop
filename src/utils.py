import os
import requests
from datetime import datetime

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Resolve .env relative to the project root (one level above src/)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

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


# ── Download webhook ───────────────────────────────────────────────────────

def fire_download_webhook(
    recipient_email: str,
    filename: str,
    downloaded_at: datetime,
) -> None:
    """
    POST to the Node webhook service to trigger a download notification email.
    Never raises — all failures are printed and the download response is unaffected.
    """
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

    webhook_url    = os.environ.get("WEBHOOK_URL", "http://localhost:3001/notify").strip()
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "").strip()

    if not webhook_secret:
        print("[webhook] Warning: WEBHOOK_SECRET not set — skipping notification.")
        return

    payload = {
        "recipient_email": recipient_email,
        "filename":        filename,
        "downloaded_at":   downloaded_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Authorization": f"Bearer {webhook_secret}"},
            timeout=5,
        )
        response.raise_for_status()
        print(f"[webhook] Webhook fired successfully → {response.json()}")
    except Exception as e:
        print(f"[webhook] Warning: webhook call failed — {e}")
