"""
SQLite per tracciare i job già visti e le statistiche giornaliere.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class JobState:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_key TEXT PRIMARY KEY,
                    company TEXT,
                    title TEXT,
                    location TEXT,
                    url TEXT,
                    channel TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_stats (
                    scan_date DATE PRIMARY KEY,
                    scans_count INTEGER DEFAULT 0,
                    strong_matches INTEGER DEFAULT 0,
                    review_matches INTEGER DEFAULT 0,
                    companies_ok INTEGER DEFAULT 0,
                    companies_error INTEGER DEFAULT 0,
                    total_jobs_seen INTEGER DEFAULT 0,
                    last_errors TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_log_sent (
                    log_date DATE PRIMARY KEY,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def is_seen(self, job_key: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT 1 FROM seen_jobs WHERE job_key = ?", (job_key,))
            return cur.fetchone() is not None

    def mark_seen(
        self,
        job_key: str,
        company: str,
        title: str,
        location: str,
        url: str,
        channel: str,
    ):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO seen_jobs
                (job_key, company, title, location, url, channel)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (job_key, company, title, location, url, channel),
            )

    def update_scan_stats(
        self,
        strong: int,
        review: int,
        total_seen: int,
        companies_ok: int,
        companies_err: int,
        errors: list,
    ):
        today = datetime.now().date().isoformat()
        error_text = "\n".join(errors) if errors else ""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO scan_stats
                (scan_date, scans_count, strong_matches, review_matches,
                 total_jobs_seen, companies_ok, companies_error, last_errors)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scan_date) DO UPDATE SET
                    scans_count = scans_count + 1,
                    strong_matches = strong_matches + excluded.strong_matches,
                    review_matches = review_matches + excluded.review_matches,
                    total_jobs_seen = excluded.total_jobs_seen,
                    companies_ok = excluded.companies_ok,
                    companies_error = excluded.companies_error,
                    last_errors = excluded.last_errors
            """,
                (
                    today,
                    strong,
                    review,
                    total_seen,
                    companies_ok,
                    companies_err,
                    error_text,
                ),
            )

    def get_daily_stats(self, date_iso: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM scan_stats WHERE scan_date = ?", (date_iso,)
            )
            row = cur.fetchone()
            return dict(row) if row else {}

    def daily_log_already_sent(self, date_iso: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM daily_log_sent WHERE log_date = ?", (date_iso,)
            )
            return cur.fetchone() is not None

    def mark_daily_log_sent(self, date_iso: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO daily_log_sent (log_date) VALUES (?)",
                (date_iso,),
            )
