"""
CodeSense - Context Engine
Understands code intent, file type, domain-specific rules, and pattern context.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class CodeContext:
    file_type:       str              # "test" | "production" | "config" | "script" | "library"
    domain:          str              # "web" | "data_science" | "algorithms" | "system" | "general"
    detected_patterns: List[str]      = field(default_factory=list)
    relaxed_rules:   List[str]        = field(default_factory=list)
    strict_rules:    List[str]        = field(default_factory=list)
    intent_notes:    List[str]        = field(default_factory=list)


# ─── File Type Detection ──────────────────────────────────────────────────────

def detect_file_type(code: str, filename: str = "") -> str:
    """
    Determine the purpose of the file.
    """
    fname = filename.lower()

    # Filename-based
    if any(t in fname for t in ("test_", "_test", "spec_", "_spec", "tests.")):
        return "test"
    if any(t in fname for t in ("config", "settings", "conf.", "cfg.")):
        return "config"
    if any(t in fname for t in ("setup.py", "conftest", "manage.py", "wsgi", "asgi")):
        return "script"

    # Content-based
    test_indicators = [
        r"\bimport\s+unittest\b|\bimport\s+pytest\b",
        r"\bclass\s+\w+Test\b|\bclass\s+Test\w+\b",
        r"\bdef\s+test_\w+|\b@pytest\.fixture",
        r"\bassertEqual\b|\bassertTrue\b|\bassertRaises\b",
        r"\bJUnit\b|\b@Test\b",
        r"\bBEFORE_EACH\b|\bAFTER_EACH\b|describe\(|it\(",
    ]
    if any(re.search(p, code) for p in test_indicators):
        return "test"

    config_indicators = [
        r"DEBUG\s*=|SECRET_KEY\s*=|DATABASE_URL\s*=",
        r"\[DEFAULT\]|\[settings\]",
        r"log4j|logging\.basicConfig",
    ]
    if any(re.search(p, code) for p in config_indicators):
        return "config"

    if re.search(r"\bif\s+__name__\s*==\s*['\"]__main__['\"]", code):
        return "script"

    return "production"


# ─── Domain Detection ─────────────────────────────────────────────────────────

def detect_domain(code: str, language: str) -> str:
    """
    Identify the code's problem domain.
    """
    domains = {
        "web": [
            r"\bflask\b|\bdjango\b|\bfastapi\b|\baiohttp\b",
            r"\brequest\b|\bresponse\b|\burl\b|\bhttp\b",
            r"@app\.route|@router\.|HttpResponse",
        ],
        "data_science": [
            r"\bpandas\b|\bnumpy\b|\bmatplotlib\b|\bseaborn\b",
            r"\bscikit.learn\b|\bsklearn\b|\btensorflow\b|\btorch\b",
            r"\bDataFrame\b|\bnp\.array\b|\bplt\.\w+\(",
        ],
        "algorithms": [
            r"\bsort\b.*\bO\(|\balgorithm\b|\bcomplexity\b",
            r"\bgraph\b|\btree\b|\bheap\b|\bdynamic.*programming\b",
            r"def\s+\w+sort|def\s+\w+search|def\s+\w+tree",
        ],
        "system": [
            r"\bos\.\w+|\bsys\.\w+|\bsubprocess\b",
            r"\bsocket\b|\bthreading\b|\bmultiprocessing\b",
            r"#include\s*<(unistd|sys/|pthread|signal)",
        ],
        "database": [
            r"\bsqlite\b|\bpsycopg\b|\bmysql\b|\bSQLAlchemy\b",
            r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b",
            r"\.execute\(|\.cursor\(\)",
        ],
    }

    scores: Dict[str, int] = {}
    for domain, patterns in domains.items():
        scores[domain] = sum(
            1 for p in patterns if re.search(p, code, re.IGNORECASE)
        )

    best = max(scores, key=lambda k: scores[k]) if scores else "general"
    return best if scores.get(best, 0) > 0 else "general"


# ─── Context Engine ───────────────────────────────────────────────────────────

class ContextEngine:
    """
    Combines file type, domain, and code patterns to produce
    context-aware analysis guidance.
    """

    def analyze(self, code: str, language: str,
                filename: str = "", analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Produce a rich context report.

        Returns:
            {
              file_type, domain, relaxed_rules, strict_rules,
              intent_notes, adjustment_hints
            }
        """
        file_type = detect_file_type(code, filename)
        domain    = detect_domain(code, language)

        ctx = CodeContext(file_type=file_type, domain=domain)
        self._apply_file_type_rules(ctx, file_type)
        self._apply_domain_rules(ctx, domain, code, analysis or {})
        self._detect_intentional_patterns(ctx, code, domain, analysis or {})

        return {
            "file_type":          ctx.file_type,
            "domain":             ctx.domain,
            "relaxed_rules":      ctx.relaxed_rules,
            "strict_rules":       ctx.strict_rules,
            "intent_notes":       ctx.intent_notes,
            "adjustment_hints":   self._adjustment_hints(ctx),
        }

    def _apply_file_type_rules(self, ctx: CodeContext, file_type: str) -> None:
        if file_type == "test":
            ctx.relaxed_rules += [
                "security_checks",   # Test code may use eval, exec for fixtures
                "magic_numbers",     # Test assertions often have literal expected values
                "long_functions",    # Test methods can be verbose
            ]
            ctx.intent_notes.append(
                "This appears to be a test file. Security rules and magic number warnings are relaxed."
            )
        elif file_type == "config":
            ctx.relaxed_rules += [
                "long_functions",
                "complexity",
            ]
            ctx.strict_rules += ["hardcoded_secrets"]
            ctx.intent_notes.append(
                "Configuration file detected. Hardcoded secrets are strictly flagged."
            )
        elif file_type == "script":
            ctx.relaxed_rules += ["naming_convention"]
            ctx.intent_notes.append(
                "Script/entry-point file. Naming conventions slightly relaxed."
            )

    def _apply_domain_rules(self, ctx: CodeContext, domain: str,
                             code: str, analysis: Dict) -> None:
        if domain == "algorithms":
            ctx.relaxed_rules += ["complexity"]
            ctx.intent_notes.append(
                "Algorithm-focused code detected. High complexity may be intentional."
            )
        elif domain == "data_science":
            ctx.relaxed_rules += ["long_line_length", "magic_numbers"]
            ctx.intent_notes.append(
                "Data science code detected. Long chains and numeric constants are common."
            )
        elif domain == "web":
            ctx.strict_rules += ["sql_injection", "xss", "csrf"]
            ctx.intent_notes.append(
                "Web framework detected. Security checks are prioritised."
            )

    def _detect_intentional_patterns(self, ctx: CodeContext, code: str,
                                      domain: str, analysis: Dict) -> None:
        """Identify patterns that look bad but are intentional."""
        cx = analysis.get("complexity", {})

        # Nested loops: matrix operations
        if domain in ("data_science", "algorithms"):
            deeply_nested = cx.get("deeply_nested_fns", [])
            for fn in deeply_nested:
                if re.search(r"matrix|grid|dp\[|table\[|board\[", code, re.IGNORECASE):
                    ctx.intent_notes.append(
                        f"Function '{fn.get('name','')}' has deep nesting "
                        f"— likely intentional for matrix/DP operations."
                    )

        # O(n²) or O(n³) loops for small n
        if re.search(r"n\s*<=?\s*(10|20|50|100)\b", code):
            ctx.intent_notes.append(
                "Small input size detected. High complexity may be acceptable for n ≤ 100."
            )

        # Graph traversal — DFS/BFS recursion depth is expected
        if re.search(r"\bdfs\b|\bbfs\b|\brecursive\b", code, re.IGNORECASE):
            ctx.relaxed_rules.append("max_recursion_depth")

    @staticmethod
    def _adjustment_hints(ctx: CodeContext) -> Dict[str, float]:
        """
        Produce score adjustment hints based on context.
        Actual adjustment capped by MAX_SCORE_ADJUSTMENT in predictor.
        """
        hints: Dict[str, float] = {}
        if "complexity" in ctx.relaxed_rules:
            hints["complexity_penalty_reduction"] = 0.5
        if "hardcoded_secrets" in ctx.strict_rules:
            hints["security_penalty_multiplier"]  = 1.5
        return hints