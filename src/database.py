import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "instance", "files.db")

CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    stored_filename   TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size         INTEGER,
    file_type         TEXT,
    token             TEXT UNIQUE NOT NULL,
    passcode_hash     TEXT,
    one_time_download BOOLEAN DEFAULT 0,
    is_used           BOOLEAN DEFAULT 0,
    expires_at        DATETIME NOT NULL,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_FILES_TABLE)
        conn.commit()
