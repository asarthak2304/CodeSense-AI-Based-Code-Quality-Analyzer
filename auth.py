"""
CodeSense - Authentication
Secure authentication with bcrypt, OTP, session management, and brute-force protection.
"""

import secrets
import string
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Tuple

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    import hashlib
    _HAS_BCRYPT = False

from config import get_config
from db import Database, get_db
from logger import get_logger
from validators import validate_email, validate_password, validate_username

logger = get_logger(__name__)


class AuthError(Exception):
    """Authentication-related errors."""


class Auth:
    """Handles registration, login, OTP, and session management."""

    def __init__(self, db: Database) -> None:
        self.db  = db
        self.cfg = get_config().auth

    # ─── Password Helpers ────────────────────────────────────────────────────

    def hash_password(self, plain: str) -> str:
        if _HAS_BCRYPT:
            return bcrypt.hashpw(
                plain.encode("utf-8"),
                bcrypt.gensalt(rounds=self.cfg.bcrypt_rounds),
            ).decode("utf-8")
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000)
        return f"pbkdf2${salt}${h.hex()}"

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            if hashed.startswith("pbkdf2$"):
                _, salt, h = hashed.split("$", 2)
                check = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000)
                return secrets.compare_digest(check.hex(), h)
            if _HAS_BCRYPT:
                return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
            return False
        except Exception:
            return False

    # ─── Registration ────────────────────────────────────────────────────────

    def register(self, username: str, email: str, password: str,
                 full_name: str = "") -> Tuple[bool, str, Optional[int]]:
        """
        Register a new user.

        Returns:
            (success, message, user_id)
        """
        valid, msg = validate_username(username)
        if not valid:
            return False, msg, None

        valid, msg = validate_email(email)
        if not valid:
            return False, msg, None

        valid, msg = validate_password(password)
        if not valid:
            return False, msg, None

        pw_hash = self.hash_password(password)
        user_id = self.db.create_user(username, email.lower(), pw_hash, full_name)

        if user_id is None:
            return False, "Email or username already registered.", None

        logger.info("New user registered: %s (id=%s)", username, user_id)
        return True, "Registration successful. Please verify your email.", user_id

    # ─── Login ───────────────────────────────────────────────────────────────

    def login(self, identifier: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify credentials using either username or email.

        Returns:
            (success, message, user_dict)
        """
        user = self.db.get_user_by_login(identifier.strip())
        if not user:
            return False, "Invalid username/email or password.", None

        if user.get("locked_until"):
            locked = datetime.fromisoformat(user["locked_until"])
            if datetime.utcnow() < locked:
                remaining = int((locked - datetime.utcnow()).total_seconds() / 60)
                return False, f"Account locked. Try again in {remaining} minutes.", None
            self.db.reset_login_attempts(user["id"])

        if not self.verify_password(password, user["password_hash"]):
            attempts = self.db.increment_login_attempts(user["id"])
            if attempts >= self.cfg.max_attempts:
                lock_until = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
                self.db.update_user(user["id"], locked_until=lock_until)
                return False, "Too many failed attempts. Account locked for 30 minutes.", None
            remaining = self.cfg.max_attempts - attempts
            return False, f"Invalid email or password. {remaining} attempts remaining.", None

        if not user.get("is_verified"):
            return False, "Please verify your email address before logging in.", None

        self.db.reset_login_attempts(user["id"])
        logger.info("User logged in: %s", user["username"])
        return True, "Login successful.", user

    # ─── OTP ─────────────────────────────────────────────────────────────────

    def generate_otp(self) -> str:
        """Generate a numeric OTP."""
        from constants import OTP_LENGTH
        alphabet = string.digits
        return "".join(secrets.choice(alphabet) for _ in range(OTP_LENGTH))

    def send_otp(self, email: str) -> Tuple[bool, str]:
        """Generate and optionally email an OTP to the user."""
        valid, msg = validate_email(email)
        if not valid:
            return False, msg

        user = self.db.get_user_by_email(email.lower())
        if not user:
            # Don't reveal whether email exists
            return True, "If that email is registered, you will receive an OTP."

        otp    = self.generate_otp()
        expiry = (datetime.utcnow() + timedelta(minutes=self.cfg.otp_expiry)).isoformat()
        self.db.set_otp(email.lower(), otp, expiry)

        sent = self._email_otp(email, otp, user.get("full_name") or user["username"])
        if not sent:
            logger.warning("Could not email OTP to %s – check SMTP config. OTP: %s", email, otp)
            # In development/test mode without SMTP, provide the OTP directly in message
            return True, f"OTP generated: {otp} (SMTP not configured, showing for testing)."

        logger.info("OTP generated and emailed to %s", email)
        return True, "OTP sent successfully."

    def verify_otp(self, email: str, otp: str) -> Tuple[bool, str]:
        """Verify OTP and mark user as verified."""
        user = self.db.get_user_by_email(email.lower())
        if not user:
            return False, "Email not found."

        if user.get("otp_code") != otp.strip():
            return False, "Invalid OTP."

        if user.get("otp_expiry"):
            expiry = datetime.fromisoformat(user["otp_expiry"])
            if datetime.utcnow() > expiry:
                return False, "OTP has expired. Please request a new one."

        self.db.verify_user(user["id"])
        self.db.update_user(user["id"], otp_code=None, otp_expiry=None)
        logger.info("User %s email verified.", email)
        return True, "Email verified successfully."

    # ─── Sessions ────────────────────────────────────────────────────────────

    def create_session(self, user_id: int, ip: str = "", ua: str = "") -> str:
        token      = secrets.token_urlsafe(48)
        expires_at = (datetime.utcnow() + timedelta(hours=self.cfg.session_hours)).isoformat()
        self.db.create_session(user_id, token, expires_at, ip, ua)
        return token

    def validate_session(self, token: str) -> Optional[Dict]:
        session = self.db.get_session(token)
        if not session:
            return None
        return self.db.get_user_by_id(session["user_id"])

    def logout(self, token: str) -> bool:
        return self.db.delete_session(token)

    # ─── Email ───────────────────────────────────────────────────────────────

    def _email_otp(self, to_email: str, otp: str, name: str) -> bool:
        """Send OTP via SMTP. Returns False if SMTP is not configured."""
        if not self.cfg.smtp_user or not self.cfg.smtp_pass:
            return False  # SMTP not configured; OTP can be shown in UI for dev
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "CodeSense – Your Verification Code"
            msg["From"]    = self.cfg.from_email
            msg["To"]      = to_email

            html = f"""
            <html><body style="font-family:Inter,sans-serif;background:#0E1117;color:#fff;padding:40px">
              <div style="max-width:480px;margin:0 auto;background:#1E1E2E;border-radius:12px;padding:32px">
                <h1 style="color:#1E88E5;margin:0 0 8px">CodeSense 🧠</h1>
                <p>Hi <strong>{name}</strong>,</p>
                <p>Your verification code is:</p>
                <div style="background:#0E1117;border-radius:8px;padding:24px;text-align:center;
                            font-size:36px;font-weight:700;letter-spacing:12px;color:#1E88E5">
                  {otp}
                </div>
                <p style="color:#757575;font-size:14px;margin-top:16px">
                  This code expires in {self.cfg.otp_expiry} minutes.
                  If you didn't request this, ignore this email.
                </p>
              </div>
            </body></html>
            """
            msg.attach(MIMEText(html, "html"))

            smtp_pass = self.cfg.smtp_pass.replace(" ", "").strip()
            smtp_user = self.cfg.smtp_user.strip()

            with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(self.cfg.from_email or smtp_user, to_email, msg.as_string())
            return True
        except Exception as exc:
            logger.error("SMTP send failed: %s", exc)
            return False

    def get_last_active_user(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recently active authenticated user with valid session."""
        try:
            with get_db(self.db.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT u.id, u.username, u.email, u.full_name, u.created_at, u.role
                    FROM sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.expires_at > CURRENT_TIMESTAMP
                    ORDER BY s.created_at DESC
                    LIMIT 1
                    """
                ).fetchone()
                if row:
                    return dict(row)
        except Exception as exc:
            logger.error("Failed to get last active user: %s", exc)
        return None