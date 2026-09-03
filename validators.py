"""
CodeSense - Input Validation
Validates all user inputs before processing.
"""

import re
from pathlib import Path
from typing import Tuple

from constants import (
    SUPPORTED_LANGUAGES, LANGUAGE_EXTENSIONS,
    MAX_FILE_SIZE_MB, MAX_CODE_LINES, MIN_CODE_LINES,
)
from logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = "general"):
        super().__init__(message)
        self.field   = field
        self.message = message


def validate_code(code: str) -> Tuple[bool, str]:
    """
    Validate raw code input.

    Returns:
        (is_valid, error_message)
    """
    if not code or not code.strip():
        return False, "Code cannot be empty."

    lines = code.splitlines()

    if len(lines) < MIN_CODE_LINES:
        return False, f"Code must have at least {MIN_CODE_LINES} lines."

    if len(lines) > MAX_CODE_LINES:
        return False, f"Code exceeds maximum of {MAX_CODE_LINES} lines."

    size_mb = len(code.encode("utf-8")) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"Code size ({size_mb:.1f} MB) exceeds limit of {MAX_FILE_SIZE_MB} MB."

    return True, ""


def validate_language(language: str) -> Tuple[bool, str]:
    """Ensure language is supported."""
    if language.lower() not in SUPPORTED_LANGUAGES:
        return False, f"Language '{language}' is not supported. Choose from: {', '.join(SUPPORTED_LANGUAGES)}"
    return True, ""


def validate_file(file_path: str) -> Tuple[bool, str, str]:
    """
    Validate uploaded file path.

    Returns:
        (is_valid, error_message, detected_language)
    """
    path = Path(file_path)

    if not path.exists():
        return False, "File does not exist.", ""

    if not path.is_file():
        return False, "Path is not a file.", ""

    suffix = path.suffix.lower()
    if suffix not in LANGUAGE_EXTENSIONS:
        supported = ", ".join(LANGUAGE_EXTENSIONS.keys())
        return False, f"Unsupported file type '{suffix}'. Supported: {supported}", ""

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File size ({size_mb:.1f} MB) exceeds limit of {MAX_FILE_SIZE_MB} MB.", ""

    language = LANGUAGE_EXTENSIONS[suffix]
    return True, "", language


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email address format."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email.strip()):
        return False, "Invalid email address format."
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Enforce password policy:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 30:
        return False, "Username must be 30 characters or fewer."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        return False, "Username may only contain letters, digits, underscores, hyphens, and dots."
    return True, ""


def validate_github_url(url: str) -> Tuple[bool, str]:
    """Validate GitHub raw or repo URL."""
    patterns = [
        r"^https://github\.com/[\w.\-]+/[\w.\-]+",
        r"^https://raw\.githubusercontent\.com/",
    ]
    for pattern in patterns:
        if re.match(pattern, url):
            return True, ""
    return False, "Invalid GitHub URL. Must be a github.com or raw.githubusercontent.com URL."


def sanitize_code(code: str) -> str:
    """Strip null bytes and normalize line endings."""
    code = code.replace("\x00", "")
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    return code