"""
CodeSense - Configuration Management
Loads and validates all configuration from environment variables and defaults.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

def _get_setting(key: str, default: Any, cast_type: Optional[type] = None) -> Any:
    """Retrieve setting from os.environ, st.secrets, or default with safe type casting."""
    val = os.getenv(key)
    if val is None:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and key in st.secrets:
                val = st.secrets[key]
        except Exception:
            pass

    if val is None:
        val = default

    if cast_type is bool:
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("true", "1", "yes", "on")
    if cast_type is int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return int(default)
    if cast_type is float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return float(default)
    return str(val) if val is not None else ""


@dataclass
class DatabaseConfig:
    path: str          = field(default_factory=lambda: _get_setting("DB_PATH", "codesense.db"))
    pool_size: int     = field(default_factory=lambda: _get_setting("DB_POOL_SIZE", 5, int))
    timeout: int       = field(default_factory=lambda: _get_setting("DB_TIMEOUT", 30, int))
    echo: bool         = field(default_factory=lambda: _get_setting("DB_ECHO", False, bool))


@dataclass
class AuthConfig:
    secret_key: str    = field(default_factory=lambda: _get_setting("SECRET_KEY", "change-me-in-production-32chars!!"))
    otp_expiry: int    = field(default_factory=lambda: _get_setting("OTP_EXPIRY_MINUTES", 10, int))
    max_attempts: int  = field(default_factory=lambda: _get_setting("MAX_LOGIN_ATTEMPTS", 5, int))
    session_hours: int = field(default_factory=lambda: _get_setting("SESSION_TIMEOUT_HOURS", 24, int))
    bcrypt_rounds: int = field(default_factory=lambda: _get_setting("BCRYPT_ROUNDS", 12, int))
    smtp_host: str     = field(default_factory=lambda: _get_setting("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int     = field(default_factory=lambda: _get_setting("SMTP_PORT", 587, int))
    smtp_user: str     = field(default_factory=lambda: _get_setting("SMTP_USER", ""))
    smtp_pass: str     = field(default_factory=lambda: _get_setting("SMTP_PASS", ""))
    from_email: str    = field(default_factory=lambda: _get_setting("FROM_EMAIL", "noreply@codesense.ai"))


@dataclass
class MLConfig:
    model_path: str    = field(default_factory=lambda: _get_setting("MODEL_PATH", "models/codesense_model.pkl"))
    scaler_path: str   = field(default_factory=lambda: _get_setting("SCALER_PATH", "models/codesense_scaler.pkl"))
    features_path: str = field(default_factory=lambda: _get_setting("FEATURES_PATH", "models/feature_names.json"))
    retrain_days: int  = field(default_factory=lambda: _get_setting("MODEL_RETRAIN_DAYS", 7, int))
    min_samples: int   = field(default_factory=lambda: _get_setting("MIN_TRAIN_SAMPLES", 5000, int))
    target_r2: float   = field(default_factory=lambda: _get_setting("TARGET_R2", 0.90, float))


@dataclass
class CacheConfig:
    ttl: int           = field(default_factory=lambda: _get_setting("CACHE_TTL", 3600, int))
    max_size: int      = field(default_factory=lambda: _get_setting("CACHE_MAX_SIZE", 500, int))
    directory: str     = field(default_factory=lambda: _get_setting("CACHE_DIR", "cache"))
    enabled: bool      = field(default_factory=lambda: _get_setting("CACHE_ENABLED", True, bool))


@dataclass
class AnalysisConfig:
    timeout: int       = field(default_factory=lambda: _get_setting("ANALYSIS_TIMEOUT", 30, int))
    max_file_mb: float = field(default_factory=lambda: _get_setting("MAX_FILE_MB", 5.0, float))
    max_lines: int     = field(default_factory=lambda: _get_setting("MAX_CODE_LINES", 5000, int))
    min_lines: int     = field(default_factory=lambda: _get_setting("MIN_CODE_LINES", 3, int))
    parallel: bool     = field(default_factory=lambda: _get_setting("PARALLEL_ANALYSIS", True, bool))
    max_workers: int   = field(default_factory=lambda: _get_setting("MAX_WORKERS", 4, int))


@dataclass
class AppConfig:
    debug: bool        = field(default_factory=lambda: _get_setting("DEBUG", False, bool))
    log_level: str     = field(default_factory=lambda: _get_setting("LOG_LEVEL", "INFO"))
    log_dir: str       = field(default_factory=lambda: _get_setting("LOG_DIR", "logs"))
    port: int          = field(default_factory=lambda: _get_setting("PORT", 8501, int))
    env: str           = field(default_factory=lambda: _get_setting("ENVIRONMENT", "development"))

    db: DatabaseConfig     = field(default_factory=DatabaseConfig)
    auth: AuthConfig       = field(default_factory=AuthConfig)
    ml: MLConfig           = field(default_factory=MLConfig)
    cache: CacheConfig     = field(default_factory=CacheConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)

    def __post_init__(self) -> None:
        """Ensure required directories exist."""
        for directory in [self.log_dir, self.cache.directory,
                          Path(self.ml.model_path).parent]:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def is_production(self) -> bool:
        return self.env == "production"

    def to_dict(self) -> dict:
        return {
            "debug": self.debug,
            "env": self.env,
            "log_level": self.log_level,
        }


# Singleton instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Return the singleton AppConfig, creating it on first call."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """Force reload configuration (useful after env changes)."""
    global _config
    load_dotenv(override=True)
    _config = AppConfig()
    return _config