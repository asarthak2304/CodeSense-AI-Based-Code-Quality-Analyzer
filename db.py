"""
CodeSense - Database Layer
Optimized SQLite database with connection pooling, indexes, and migrations.
"""

import sqlite3
import json
import hashlib
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from logger import get_logger

logger = get_logger(__name__)

# Thread-local storage for connections
_local = threading.local()


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Return a thread-local SQLite connection."""
    if not hasattr(_local, "connections"):
        _local.connections = {}
    if db_path not in _local.connections:
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=-64000")   # 64 MB page cache
        _local.connections[db_path] = conn
    return _local.connections[db_path]


@contextmanager
def get_db(db_path: str = "codesense.db") -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection, committing on success or rolling back on error."""
    conn = _get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


class Database:
    """High-level database interface for CodeSense."""

    SCHEMA_VERSION = 4

    def __init__(self, db_path: str = "codesense.db") -> None:
        self.db_path = db_path
        self._init_schema()

    # ─── Schema ──────────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        with get_db(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version    INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    username     TEXT UNIQUE NOT NULL,
                    email        TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name    TEXT DEFAULT '',
                    avatar_url   TEXT DEFAULT '',
                    is_verified  INTEGER DEFAULT 0,
                    is_active    INTEGER DEFAULT 1,
                    otp_code     TEXT,
                    otp_expiry   TEXT,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT,
                    preferences  TEXT DEFAULT '{}',
                    created_at   TEXT NOT NULL,
                    updated_at   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analyses (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    language     TEXT NOT NULL,
                    filename     TEXT DEFAULT '',
                    code_hash    TEXT NOT NULL,
                    score        REAL NOT NULL,
                    grade        TEXT NOT NULL,
                    confidence   REAL DEFAULT 0,
                    ml_score     REAL NOT NULL,
                    features     TEXT DEFAULT '{}',
                    results      TEXT DEFAULT '{}',
                    analysis_level TEXT DEFAULT 'standard',
                    processing_ms INTEGER DEFAULT 0,
                    created_at   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id  INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
                    user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    category     TEXT NOT NULL,
                    severity     TEXT NOT NULL,
                    message      TEXT NOT NULL,
                    line_number  INTEGER,
                    suggestion   TEXT DEFAULT '',
                    code_snippet TEXT DEFAULT '',
                    fixed_code   TEXT DEFAULT '',
                    is_applied   INTEGER DEFAULT 0,
                    created_at   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS achievements (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    achievement_key TEXT NOT NULL,
                    title         TEXT NOT NULL,
                    description   TEXT NOT NULL,
                    icon          TEXT DEFAULT '🏆',
                    earned_at     TEXT NOT NULL,
                    UNIQUE(user_id, achievement_key)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    token        TEXT UNIQUE NOT NULL,
                    ip_address   TEXT DEFAULT '',
                    user_agent   TEXT DEFAULT '',
                    expires_at   TEXT NOT NULL,
                    created_at   TEXT NOT NULL
                );

                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_analyses_user_id     ON analyses(user_id);
                CREATE INDEX IF NOT EXISTS idx_analyses_created_at  ON analyses(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_analyses_score       ON analyses(score);
                CREATE INDEX IF NOT EXISTS idx_analyses_language    ON analyses(language);
                CREATE INDEX IF NOT EXISTS idx_feedback_analysis_id ON feedback(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_token       ON sessions(token);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id     ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_achievements_user_id ON achievements(user_id);
            """)
        logger.info("Database schema initialized at %s", self.db_path)

    # ─── Users ───────────────────────────────────────────────────────────────

    def create_user(self, username: str, email: str, password_hash: str,
                    full_name: str = "") -> Optional[int]:
        now = datetime.utcnow().isoformat()
        try:
            with get_db(self.db_path) as conn:
                cur = conn.execute(
                    """INSERT INTO users
                       (username, email, password_hash, full_name, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (username, email, password_hash, full_name, now, now),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError as exc:
            logger.warning("create_user conflict: %s", exc)
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower(),)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1", (username.strip(),)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_login(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Look up user by either email or username."""
        ident = identifier.strip()
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE (email = ? OR username = ?) AND is_active = 1",
                (ident.lower(), ident),
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_user(self, user_id: int, **kwargs) -> bool:
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        sets   = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        with get_db(self.db_path) as conn:
            cur = conn.execute(f"UPDATE users SET {sets} WHERE id = ?", values)
            return cur.rowcount > 0

    def verify_user(self, user_id: int) -> bool:
        return self.update_user(user_id, is_verified=1)

    def set_otp(self, email: str, otp: str, expiry: str) -> bool:
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE users SET otp_code = ?, otp_expiry = ? WHERE email = ?",
                (otp, expiry, email),
            )
            return cur.rowcount > 0

    def increment_login_attempts(self, user_id: int) -> int:
        with get_db(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET login_attempts = login_attempts + 1 WHERE id = ?",
                (user_id,),
            )
            row = conn.execute(
                "SELECT login_attempts FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return row["login_attempts"] if row else 0

    def reset_login_attempts(self, user_id: int) -> None:
        self.update_user(user_id, login_attempts=0, locked_until=None)

    # ─── Sessions ────────────────────────────────────────────────────────────

    def create_session(self, user_id: int, token: str, expires_at: str,
                       ip: str = "", ua: str = "") -> bool:
        now = datetime.utcnow().isoformat()
        try:
            with get_db(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO sessions
                       (user_id, token, ip_address, user_agent, expires_at, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, token, ip, ua, expires_at, now),
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE token = ? AND expires_at > ?",
                (token, datetime.utcnow().isoformat()),
            ).fetchone()
            return dict(row) if row else None

    def delete_session(self, token: str) -> bool:
        with get_db(self.db_path) as conn:
            cur = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return cur.rowcount > 0

    def delete_user_sessions(self, user_id: int) -> bool:
        with get_db(self.db_path) as conn:
            cur = conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            return cur.rowcount > 0

    def cleanup_expired_sessions(self) -> int:
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM sessions WHERE expires_at <= ?",
                (datetime.utcnow().isoformat(),),
            )
            return cur.rowcount

    # ─── Analyses ────────────────────────────────────────────────────────────

    def save_analysis(self, user_id: int, language: str, filename: str,
                      code: str, score: float, grade: str, confidence: float,
                      ml_score: float, features: dict, results: dict,
                      analysis_level: str = "standard",
                      processing_ms: int = 0) -> Optional[int]:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        now = datetime.utcnow().isoformat()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO analyses
                   (user_id, language, filename, code_hash, score, grade, confidence,
                    ml_score, features, results, analysis_level, processing_ms, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id, language, filename, code_hash,
                    round(score, 2), grade, round(confidence, 2),
                    round(ml_score, 2),
                    json.dumps(features, default=str),
                    json.dumps(results, default=str),
                    analysis_level, processing_ms, now,
                ),
            )
            return cur.lastrowid

    def get_user_analyses(self, user_id: int, limit: int = 50,
                          language: Optional[str] = None) -> List[Dict[str, Any]]:
        query  = "SELECT * FROM analyses WHERE user_id = ?"
        params: list = [user_id]
        if language:
            query  += " AND language = ?"
            params.append(language)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with get_db(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                d["features"] = json.loads(d.get("features") or "{}")
                d["results"]  = json.loads(d.get("results")  or "{}")
                results.append(d)
            return results

    def get_analysis_stats(self, user_id: int) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*)           AS total,
                       AVG(score)         AS avg_score,
                       MAX(score)         AS max_score,
                       MIN(score)         AS min_score,
                       AVG(processing_ms) AS avg_ms
                   FROM analyses WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            stats = dict(row) if row else {}

            # Improvement: compare last 5 vs previous 5
            recent = conn.execute(
                "SELECT score FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
                (user_id,),
            ).fetchall()
            scores = [r["score"] for r in recent]
            if len(scores) >= 10:
                stats["recent_improvement"] = round(
                    sum(scores[:5]) / 5 - sum(scores[5:]) / 5, 2
                )
            else:
                stats["recent_improvement"] = 0.0
            return stats

    # ─── Achievements ────────────────────────────────────────────────────────

    def award_achievement(self, user_id: int, key: str, title: str,
                          description: str, icon: str = "🏆") -> bool:
        now = datetime.utcnow().isoformat()
        try:
            with get_db(self.db_path) as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO achievements
                       (user_id, achievement_key, title, description, icon, earned_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, key, title, description, icon, now),
                )
                return True
        except Exception:
            return False

    def get_user_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM achievements WHERE user_id = ? ORDER BY earned_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def has_achievement(self, user_id: int, key: str) -> bool:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_key = ?",
                (user_id, key),
            ).fetchone()
            return row is not None

    def close(self) -> None:
        """Close connection for this database path if opened in current thread."""
        if hasattr(_local, "connections") and self.db_path in _local.connections:
            try:
                _local.connections[self.db_path].close()
            except Exception:
                pass
            del _local.connections[self.db_path]