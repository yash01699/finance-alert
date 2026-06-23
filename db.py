"""SQLite storage for transactions and per-month budget-alert state."""
import sqlite3
from datetime import datetime
from contextlib import contextmanager

import config


@contextmanager
def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,      -- ISO timestamp when recorded
                month       TEXT NOT NULL,      -- 'YYYY-MM' bucket
                amount      REAL NOT NULL,      -- debit amount (positive = spent)
                merchant    TEXT,               -- best-effort, parsed from SMS
                effavl      REAL,               -- account balance left after txn
                raw_sms     TEXT                -- original SMS text, for audit
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_alerts (
                month       TEXT PRIMARY KEY,   -- 'YYYY-MM'
                alerted_at  TEXT NOT NULL       -- when we sent the over-budget ping
            )
            """
        )


def month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def record_transaction(amount, merchant, effavl, raw_sms, now=None):
    now = now or datetime.now()
    with _conn() as c:
        c.execute(
            "INSERT INTO transactions (ts, month, amount, merchant, effavl, raw_sms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now.isoformat(timespec="seconds"), month_key(now), amount,
             merchant, effavl, raw_sms),
        )


def month_total(now=None) -> float:
    now = now or datetime.now()
    with _conn() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE month = ?",
            (month_key(now),),
        ).fetchone()
        return float(row["total"])


def already_alerted_this_month(now=None) -> bool:
    now = now or datetime.now()
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM budget_alerts WHERE month = ?", (month_key(now),)
        ).fetchone()
        return row is not None


def mark_alerted(now=None):
    now = now or datetime.now()
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO budget_alerts (month, alerted_at) VALUES (?, ?)",
            (month_key(now), now.isoformat(timespec="seconds")),
        )
