import os
from datetime import datetime

from .database import get_connection

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")


def cleanup_expired_files() -> None:
    """
    Delete every file and database record whose expires_at has passed.
    Safe to call at any time — missing files are silently skipped, and
    any unexpected error is caught so it never crashes the caller.
    """
    try:
        now = datetime.utcnow().isoformat()

        with get_connection() as conn:
            expired = conn.execute(
                "SELECT id, stored_filename, original_filename FROM files WHERE expires_at < ?",
                (now,),
            ).fetchall()

            removed = 0
            for row in expired:
                file_path = os.path.join(STORAGE_DIR, row["stored_filename"])
                try:
                    os.remove(file_path)
                except FileNotFoundError:
                    pass  # already gone from disk — still clean up the DB record

                conn.execute("DELETE FROM files WHERE id = ?", (row["id"],))
                removed += 1

            conn.commit()

        print(f"[cleanup] Cleanup complete: {removed} expired file(s) removed.")

    except Exception as exc:
        print(f"[cleanup] Warning: cleanup encountered an error — {exc}")


if __name__ == "__main__":
    # Allow running directly: python -m src.cleanup
    cleanup_expired_files()
