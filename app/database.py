import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'oneliner.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'creator',
    status TEXT NOT NULL DEFAULT 'active',
    balance_pending REAL NOT NULL DEFAULT 0,
    balance_paid REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    budget_pool REAL NOT NULL,
    budget_spent REAL NOT NULL DEFAULT 0,
    cpm_rate REAL NOT NULL,
    max_payout REAL NOT NULL,
    deadline TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    allowed_platforms TEXT NOT NULL DEFAULT 'youtube,tiktok,instagram',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    video_url TEXT NOT NULL,
    platform TEXT NOT NULL,
    platform_video_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    fraud_score INTEGER NOT NULL DEFAULT 0,
    views_count INTEGER NOT NULL DEFAULT 0,
    views_credited INTEGER NOT NULL DEFAULT 0,
    payout_amount REAL NOT NULL DEFAULT 0,
    moderation_note TEXT,
    last_tracked_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS payouts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    method TEXT NOT NULL DEFAULT 'bank_transfer',
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    admin_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);
"""

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

@contextmanager
def db_context():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db_context() as conn:
        conn.executescript(SCHEMA)
