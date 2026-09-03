"""
CodeSense - Utilities
File handling, GitHub integration, exports, and helper functions.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse

from constants import LANGUAGE_EXTENSIONS, MAX_FILE_SIZE_MB, MAX_CODE_LINES
from logger import get_logger

logger = get_logger(__name__)


# ─── File Handling ────────────────────────────────────────────────────────────

def read_file(path: str) -> Tuple[str, str]:
    """
    Read a source file and detect its language.

    Returns:
        (code, language)

    Raises:
        ValueError on unsupported file types.
        OSError on read errors.
    """
    p      = Path(path)
    suffix = p.suffix.lower()

    if suffix not in LANGUAGE_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{suffix}'.")

    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Max: {MAX_FILE_SIZE_MB} MB.")

    code = p.read_text(encoding="utf-8", errors="replace")

    if len(code.splitlines()) > MAX_CODE_LINES:
        raise ValueError(f"File exceeds {MAX_CODE_LINES} lines.")

    return code, LANGUAGE_EXTENSIONS[suffix]


def detect_language_from_code(code: str) -> str:
    """Heuristic language detection from code content."""
    if re.search(r"#include\s*<|::\w+|std::", code):
        return "cpp"
    if re.search(r"\bpublic\s+class\b|\bimport\s+java\.|@Override", code):
        return "java"
    if re.search(r"\bdef\s+\w+\(|import\s+\w+|from\s+\w+\s+import", code):
        return "python"
    # Count keywords
    python_score = len(re.findall(r"\b(def|import|print|elif|lambda|None|True|False)\b", code))
    java_score   = len(re.findall(r"\b(public|private|protected|void|int|String|class)\b", code))
    cpp_score    = len(re.findall(r"\b(#include|cout|cin|namespace|template|nullptr)\b", code))
    scores = {"python": python_score, "java": java_score, "cpp": cpp_score}
    return max(scores, key=scores.get)


def code_hash(code: str) -> str:
    """Return SHA-256 hash of source code."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


# ─── GitHub Integration ───────────────────────────────────────────────────────

def fetch_github_file(url: str, timeout: int = 10) -> Tuple[str, str]:
    """
    Fetch a file from GitHub (raw URL or repository URL).

    Args:
        url:     GitHub URL (repo page or raw).
        timeout: Request timeout in seconds.

    Returns:
        (code, language)
    """
    raw_url = _github_to_raw_url(url)
    logger.info("Fetching GitHub file: %s", raw_url)

    try:
        req = Request(raw_url, headers={"User-Agent": "CodeSense/2.0"})
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status} from GitHub.")
            content = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise ValueError(f"GitHub returned HTTP {exc.code}: {exc.reason}")
    except URLError as exc:
        raise ValueError(f"Could not reach GitHub: {exc.reason}")

    # Detect language from URL extension
    parsed = urlparse(raw_url)
    suffix = Path(parsed.path).suffix.lower()
    language = LANGUAGE_EXTENSIONS.get(suffix, detect_language_from_code(content))

    return content, language


def _github_to_raw_url(url: str) -> str:
    """Convert a github.com URL to raw.githubusercontent.com."""
    url = url.strip()
    if "raw.githubusercontent.com" in url:
        return url
    # github.com/user/repo/blob/branch_or_sha/path → raw.githubusercontent.com/user/repo/branch_or_sha/path
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/(?:blob|raw)/([^/]+)/(.+)", url
    )
    if m:
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}/{m.group(4)}"
    raise ValueError(f"Cannot convert GitHub URL to raw format: {url}. Please provide a file link containing '/blob/<branch>/<path>'")


# ─── Timing ──────────────────────────────────────────────────────────────────

class Timer:
    """Simple context manager for timing code blocks."""

    def __init__(self) -> None:
        self._start = 0.0
        self.elapsed_ms = 0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)


# ─── Export Helpers ───────────────────────────────────────────────────────────

def results_to_markdown(results: Dict[str, Any]) -> str:
    """Convert analysis results to a readable Markdown report."""
    score   = results.get("score", 0)
    grade   = results.get("grade", "?")
    lang    = results.get("language", "unknown")
    fb      = results.get("feedback", {})

    lines = [
        f"# CodeSense Analysis Report",
        f"",
        f"**Score:** {score}/100  |  **Grade:** {grade}  |  **Language:** {lang.upper()}",
        f"",
        f"## Summary",
        f"{fb.get('opening', '')}",
        f"",
    ]

    strengths = fb.get("strengths", [])
    if strengths:
        lines += ["## ✅ Strengths", ""]
        for s in strengths:
            lines.append(f"- {s}")
        lines.append("")

    items = fb.get("items", [])
    errors   = [i for i in items if i["severity"] == "error"]
    warnings = [i for i in items if i["severity"] == "warning"]

    if errors:
        lines += ["## ❌ Errors", ""]
        for i in errors:
            lines.append(f"### {i['title']}")
            lines.append(i["message"])
            if i.get("code_before"):
                lines += ["```", i["code_before"], "```"]
            if i.get("code_after"):
                lines += ["**Fix:**", "```", i["code_after"], "```"]
            lines.append("")

    if warnings:
        lines += ["## ⚠️ Warnings", ""]
        for i in warnings:
            lines.append(f"### {i['title']}")
            lines.append(i["message"])
            lines.append("")

    next_steps = fb.get("next_steps", [])
    if next_steps:
        lines += ["## 📋 Next Steps", ""]
        for step in next_steps:
            lines.append(f"- {step}")

    learning = fb.get("learning_path", [])
    if learning:
        lines += ["", "## 📚 Learning Path", ""]
        for item in learning:
            r = item.get("resource", {})
            url = r.get("url", "#") if r else "#"
            lines.append(f"{item['step']}. **{item['title']}** — {item['description']} [{r.get('title','')}]({url})")

    return "\n".join(lines)


def results_to_json(results: Dict[str, Any], indent: int = 2) -> str:
    """Serialise results to pretty-printed JSON."""
    return json.dumps(results, indent=indent, default=str)


# ─── Formatting ──────────────────────────────────────────────────────────────

def truncate(text: str, max_len: int = 100) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def format_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms/1000:.1f}s"


def percentage(value: float, total: float) -> str:
    if total == 0:
        return "0%"
    return f"{(value / total * 100):.1f}%"


# ─── Direct Binary PDF Generators (FPDF2) ────────────────────────────────────

def _clean_pdf_text(text: Any) -> str:
    """Sanitize text for standard Helvetica PDF encoding by replacing unicode symbols."""
    if text is None:
        return ""
    s = str(text)
    replacements = {
        "—": " - ",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "-",
        "…": "...",
        "→": "->",
        "←": "<-",
        "✅": "[OK]",
        "❌": "[X]",
        "⚠️": "[!]",
        "💡": "[*]",
        "🧠": "",
        "🏆": "",
        "📄": "",
        "📊": "",
        "🔒": "",
        "🔍": "",
        "⚡": "",
        "🎉": "",
        "±": "+-",
        "²": "^2",
        "³": "^3",
    }
    for orig, rep in replacements.items():
        s = s.replace(orig, rep)
    # Encode to latin-1 replacing any remaining exotic unicode characters with '?'
    return s.encode("latin-1", "replace").decode("latin-1")


def generate_user_activity_pdf_bytes(user: Dict[str, Any], stats: Dict[str, Any], analyses: List[Dict[str, Any]], achievements: List[Dict[str, Any]]) -> bytes:
    """Generate a clean binary PDF document for user activity and performance transcript."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(30, 136, 229)
            self.cell(0, 10, "CodeSense - Performance Transcript", ln=True, align="L")
            self.set_font("Helvetica", "", 10)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, "Official AI-Powered Code Quality Record", ln=True, align="L")
            self.line(10, 26, 200, 26)
            self.ln(8)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()} | Generated by CodeSense AI", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    name = _clean_pdf_text(user.get("full_name") or user.get("username", "Student"))
    email = _clean_pdf_text(user.get("email", ""))
    created_at = _clean_pdf_text(str(user.get("created_at", ""))[:10])
    total = stats.get("total", len(analyses))
    avg_score = stats.get("avg_score", 0) or 0
    max_score = stats.get("max_score", 0) or 0
    impr = stats.get("recent_improvement", 0) or 0

    # User Profile Section
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, f"Student: {name}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, f"Email: {email}  |  Member Since: {created_at}", ln=True)
    pdf.ln(5)

    # Key Statistics Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 244, 248)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(47, 8, "Total Analyses", 1, 0, "C", True)
    pdf.cell(47, 8, "Average Score", 1, 0, "C", True)
    pdf.cell(47, 8, "Best Score", 1, 0, "C", True)
    pdf.cell(47, 8, "Improvement", 1, 1, "C", True)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(47, 10, str(total), 1, 0, "C")
    pdf.cell(47, 10, f"{avg_score:.1f}", 1, 0, "C")
    pdf.cell(47, 10, f"{max_score:.0f}", 1, 0, "C")
    pdf.cell(47, 10, f"{'+' if impr >= 0 else ''}{impr:.1f}", 1, 1, "C")
    pdf.ln(8)

    # Achievements
    if achievements:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 136, 229)
        pdf.cell(0, 7, "Earned Achievements", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for a in achievements[:8]:
            title = _clean_pdf_text(a.get("title", ""))
            desc = _clean_pdf_text(a.get("description", ""))
            pdf.cell(0, 6, f"- {title}: {desc}", ln=True)
        pdf.ln(6)

    # Analysis History Table
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 136, 229)
    pdf.cell(0, 7, "Recent Code Analyses", ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 244, 248)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(40, 7, "Date", 1, 0, "L", True)
    pdf.cell(60, 7, "File / Submission", 1, 0, "L", True)
    pdf.cell(28, 7, "Language", 1, 0, "C", True)
    pdf.cell(32, 7, "Score & Grade", 1, 0, "C", True)
    pdf.cell(28, 7, "Latency", 1, 1, "C", True)

    pdf.set_font("Helvetica", "", 9)
    for a in analyses[:20]:
        date_s = _clean_pdf_text(str(a.get("created_at", ""))[:16].replace("T", " "))
        fname = _clean_pdf_text(str(a.get("filename") or "Pasted Code")[:28])
        lang = _clean_pdf_text(str(a.get("language", "")).upper())
        score = a.get("score", 0)
        grade = _clean_pdf_text(a.get("grade", "N/A"))
        ms = a.get("processing_ms", 0)

        pdf.cell(40, 6, date_s, 1, 0, "L")
        pdf.cell(60, 6, fname, 1, 0, "L")
        pdf.cell(28, 6, lang, 1, 0, "C")
        pdf.cell(32, 6, f"{score:.0f} ({grade})", 1, 0, "C")
        pdf.cell(28, 6, f"{ms}ms", 1, 1, "C")

    return bytes(pdf.output())


def generate_analysis_pdf_bytes(results: Dict[str, Any], code: str) -> bytes:
    """Generate a clean binary PDF document for a single code quality analysis."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(30, 136, 229)
            self.cell(0, 10, "CodeSense - Code Quality Audit Certificate", ln=True, align="L")
            self.set_font("Helvetica", "", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, "Automated Static, DSA & Security Evaluation", ln=True, align="L")
            self.line(10, 24, 200, 24)
            self.ln(6)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()} | Generated by CodeSense AI Quality Analyzer", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    score = results.get("score", 0)
    grade = _clean_pdf_text(results.get("grade", "N/A"))
    label = _clean_pdf_text(results.get("label", "N/A"))
    lang = _clean_pdf_text(results.get("language", "Python").upper())
    confidence = results.get("confidence", 3.0)
    feedback = results.get("feedback", {})
    analysis = results.get("analysis", {})
    dsa = results.get("dsa", {})
    metrics = analysis.get("metrics", {})
    cx = analysis.get("complexity", {})
    sec = analysis.get("security", {})

    # Score Box
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(240, 244, 248)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(62, 8, "Quality Score", 1, 0, "C", True)
    pdf.cell(62, 8, "Evaluation Grade", 1, 0, "C", True)
    pdf.cell(64, 8, "Language & Scope", 1, 1, "C", True)

    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(62, 10, f"{score:.1f}/100 (+-{confidence:.1f})", 1, 0, "C")
    pdf.cell(62, 10, f"{grade} ({label})", 1, 0, "C")
    pdf.cell(64, 10, f"{lang} ({metrics.get('code_lines', 0)} LOC)", 1, 1, "C")
    pdf.ln(6)

    # Key Metrics
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 136, 229)
    pdf.cell(0, 6, "Key Code Metrics", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 5, _clean_pdf_text(f"- Cyclomatic Avg: {cx.get('avg_complexity', 1):.1f} | Max Nesting: {cx.get('max_nesting', 0)} | Comment Ratio: {metrics.get('comment_ratio', 0)*100:.1f}%"), ln=True)
    pdf.cell(0, 5, _clean_pdf_text(f"- Security Vulnerabilities: {sec.get('total_issues', 0)} | DSA Score: {dsa.get('summary', {}).get('complexity_score', 0):.0f}/100"), ln=True)
    pdf.ln(5)

    # Strengths
    strengths = feedback.get("strengths", [])
    if strengths:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(40, 167, 69)
        pdf.cell(0, 6, "Identified Strengths", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(40, 40, 40)
        for s in strengths[:4]:
            pdf.cell(0, 5, _clean_pdf_text(f"[OK] {s}"), ln=True)
        pdf.ln(5)

    # Algorithms
    algos = dsa.get("algorithms", [])
    if algos:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 136, 229)
        pdf.cell(0, 6, "Detected Algorithms & Complexity", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(40, 40, 40)
        for a in algos[:5]:
            cx_info = a.get("complexity", {}) if isinstance(a.get("complexity"), dict) else {}
            name = a.get("display_name") or a.get("name", "").replace("_", " ").title()
            time_cx = cx_info.get("time_avg") or a.get("time_complexity") or "O(n)"
            space_cx = cx_info.get("space") or a.get("space_complexity") or "O(1)"
            pdf.cell(0, 5, _clean_pdf_text(f"- {name}: Time {time_cx}, Space {space_cx}"), ln=True)
        pdf.ln(5)

    # Issues
    items = [i for i in feedback.get("items", []) if i.get("severity") != "positive"]
    if items:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(220, 53, 69)
        pdf.cell(0, 6, "Flagged Issues & Recommendations", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(40, 40, 40)
        for item in items[:6]:
            t = item.get('title', 'Issue')
            m = item.get('message', '')[:90]
            pdf.cell(0, 5, _clean_pdf_text(f"- {t}: {m}"), ln=True)
        pdf.ln(5)

    return bytes(pdf.output())