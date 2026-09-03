"""
CodeSense - Code Fixer
Generates specific, actionable fix suggestions with before/after code diffs.
"""

import re
from dataclasses import dataclass
from typing import Dict, List

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class Fix:
    issue_type:  str
    line:        int
    description: str
    before:      str
    after:       str
    explanation: str
    confidence:  float   # 0–1: how certain the fix is correct
    is_safe:     bool    # True = safe auto-apply; False = requires review


class PythonFixer:
    """Generates Python-specific code fixes."""

    def suggest_fixes(self, code: str, issues: List[Dict]) -> List[Fix]:
        fixes: List[Fix] = []
        lines = code.splitlines()

        for issue in issues:
            issue_type = issue.get("type", "")
            line_no    = issue.get("line", 0)
            raw_line   = lines[line_no - 1] if 0 < line_no <= len(lines) else ""

            fix = None
            if issue_type == "UnusedImport":
                fix = self._fix_unused_import(raw_line, line_no, issue.get("symbol", ""))
            elif issue_type == "MutableDefault":
                fix = self._fix_mutable_default(raw_line, line_no, issue.get("symbol", ""))
            elif issue_type == "BareExcept":
                fix = self._fix_bare_except(raw_line, line_no)
            elif issue_type == "NamingConvention":
                fix = self._fix_naming(raw_line, line_no, issue.get("message", ""))
            elif issue_type in ("eval_usage", "exec_usage"):
                fix = self._fix_eval(raw_line, line_no, issue_type)
            elif issue_type == "weak_hash":
                fix = self._fix_weak_hash(raw_line, line_no)
            elif issue_type == "weak_random":
                fix = self._fix_weak_random(raw_line, line_no)
            elif issue_type == "yaml_unsafe_load":
                fix = self._fix_yaml_load(raw_line, line_no)
            elif issue_type == "sql_injection":
                fix = self._fix_sql_injection(raw_line, line_no)

            if fix:
                fixes.append(fix)

        return fixes

    # ── Individual fixers ────────────────────────────────────────────────────

    def _fix_unused_import(self, line: str, lineno: int, symbol: str) -> Fix:
        return Fix(
            issue_type="UnusedImport",
            line=lineno,
            description=f"Remove unused import '{symbol}'",
            before=line,
            after="",  # Line removed
            explanation=f"'{symbol}' is imported but never used. Removing it reduces clutter and startup time.",
            confidence=0.90,
            is_safe=True,
        )

    def _fix_mutable_default(self, line: str, lineno: int, fn_name: str) -> Fix:
        # def fn(items=[]) → def fn(items=None)
        fixed = re.sub(r"=\s*(\[\]|\{\}|set\(\))", "=None", line)
        return Fix(
            issue_type="MutableDefault",
            line=lineno,
            description=f"Replace mutable default argument in '{fn_name}'",
            before=line,
            after=fixed,
            explanation=(
                "Mutable defaults (list/dict/set) are shared across all calls.\n"
                "Replace with None and assign inside the function:\n"
                "  if items is None:\n      items = []"
            ),
            confidence=0.95,
            is_safe=False,  # Requires adding guard inside function
        )

    def _fix_bare_except(self, line: str, lineno: int) -> Fix:
        fixed = line.replace("except:", "except Exception as e:")
        return Fix(
            issue_type="BareExcept",
            line=lineno,
            description="Replace bare 'except:' with specific exception",
            before=line,
            after=fixed,
            explanation="Bare 'except:' catches everything including SystemExit. Use 'except Exception as e:' at minimum.",
            confidence=0.85,
            is_safe=False,
        )

    def _fix_naming(self, line: str, lineno: int, message: str) -> Fix:
        if "snake_case" in message:
            m = re.search(r"def\s+([A-Z][a-zA-Z0-9]*)", line)
            if m:
                old = m.group(1)
                new = re.sub(r"([A-Z])", lambda x: f"_{x.group(1).lower()}", old).lstrip("_")
                fixed = line.replace(f"def {old}", f"def {new}")
                return Fix(
                    issue_type="NamingConvention",
                    line=lineno,
                    description=f"Rename function '{old}' to snake_case '{new}'",
                    before=line, after=fixed,
                    explanation="PEP 8 requires function names to use snake_case.",
                    confidence=0.80, is_safe=False,
                )
        return None

    def _fix_eval(self, line: str, lineno: int, issue_type: str) -> Fix:
        return Fix(
            issue_type=issue_type,
            line=lineno,
            description="Replace eval/exec with a safer alternative",
            before=line,
            after=f"# TODO: Replace eval/exec — consider ast.literal_eval() for data, or refactor logic\n{line}",
            explanation=(
                "eval() and exec() execute arbitrary code and are a major security risk.\n"
                "Use ast.literal_eval() for parsing literals, or refactor to avoid dynamic execution."
            ),
            confidence=0.50,
            is_safe=False,
        )

    def _fix_weak_hash(self, line: str, lineno: int) -> Fix:
        fixed = re.sub(r"hashlib\.(md5|sha1)", "hashlib.sha256", line)
        return Fix(
            issue_type="weak_hash",
            line=lineno,
            description="Upgrade MD5/SHA1 to SHA-256",
            before=line, after=fixed,
            explanation="MD5 and SHA-1 are cryptographically broken. Use SHA-256 or better.",
            confidence=0.90, is_safe=True,
        )

    def _fix_weak_random(self, line: str, lineno: int) -> Fix:
        fixed = line.replace("random.", "secrets.")
        return Fix(
            issue_type="weak_random",
            line=lineno,
            description="Replace random with secrets for security-sensitive use",
            before=line, after=fixed,
            explanation="Use the 'secrets' module for passwords, tokens, and keys.",
            confidence=0.75, is_safe=False,
        )

    def _fix_yaml_load(self, line: str, lineno: int) -> Fix:
        fixed = re.sub(r"yaml\.load\s*\(([^)]+)\)",
                       r"yaml.safe_load(\1)", line)
        return Fix(
            issue_type="yaml_unsafe_load",
            line=lineno,
            description="Replace yaml.load() with yaml.safe_load()",
            before=line, after=fixed,
            explanation="yaml.load() can execute arbitrary Python. yaml.safe_load() restricts to basic types.",
            confidence=0.95, is_safe=True,
        )

    def _fix_sql_injection(self, line: str, lineno: int) -> Fix:
        return Fix(
            issue_type="sql_injection",
            line=lineno,
            description="Use parameterised SQL queries instead of string concatenation",
            before=line,
            after='# Use: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
            explanation=(
                "String concatenation in SQL enables injection attacks.\n"
                "Always use parameterised queries:\n"
                "  cursor.execute('SELECT * FROM t WHERE x = ?', (value,))"
            ),
            confidence=0.85, is_safe=False,
        )


class JavaFixer:
    """Generates Java-specific code fixes."""

    def suggest_fixes(self, code: str, issues: List[Dict]) -> List[Fix]:
        fixes: List[Fix] = []
        lines = code.splitlines()

        for issue in issues:
            issue_type = issue.get("type", "")
            line_no    = issue.get("line", 0)
            raw_line   = lines[line_no - 1] if 0 < line_no <= len(lines) else ""

            fix = None
            if issue_type == "EmptyCatch":
                fix = Fix(
                    issue_type="EmptyCatch",
                    line=line_no,
                    description="Handle or log exception in empty catch block",
                    before=raw_line,
                    after=raw_line.replace("{}", "{\n    logger.error(e.getMessage(), e);\n}"),
                    explanation="Empty catch blocks silently swallow exceptions, making debugging nearly impossible.",
                    confidence=0.90,
                    is_safe=False,
                )
            elif issue_type == "NullDereference":
                fix = Fix(
                    issue_type="NullDereference",
                    line=line_no,
                    description="Add null guard check before accessing object",
                    before=raw_line,
                    after=f"if (obj != null) {{\n    {raw_line}\n}}",
                    explanation="Checking for null before invoking methods prevents NullPointerException.",
                    confidence=0.85,
                    is_safe=False,
                )

            elif issue_type == "SystemOutPrintln":
                fix = Fix(
                    issue_type="SystemOutPrintln",
                    line=line_no,
                    description="Replace System.out.println with logger call",
                    before=raw_line,
                    after=raw_line.replace("System.out.println", "logger.info").replace("System.out.print", "logger.info"),
                    explanation="Using System.out.println in enterprise Java bypasses log level controls.",
                    confidence=0.85,
                    is_safe=True,
                )

            if fix:
                fixes.append(fix)

        return fixes


class CppFixer:
    """Generates C++ specific code fixes."""

    def suggest_fixes(self, code: str, issues: List[Dict]) -> List[Fix]:
        fixes: List[Fix] = []
        lines = code.splitlines()

        for issue in issues:
            issue_type = issue.get("type", "")
            line_no    = issue.get("line", 0)
            raw_line   = lines[line_no - 1] if 0 < line_no <= len(lines) else ""

            fix = None
            if issue_type == "NullPointerDereference":
                fix = Fix(
                    issue_type="NullPointerDereference",
                    line=line_no,
                    description="Add nullptr check before dereferencing pointer",
                    before=raw_line,
                    after=f"if (ptr != nullptr) {{\n    {raw_line}\n}}",
                    explanation="Dereferencing a nullptr causes undefined behavior and segmentation faults.",
                    confidence=0.85,
                    is_safe=False,
                )
            elif issue_type == "EmptyCatch":
                fix = Fix(
                    issue_type="EmptyCatch",
                    line=line_no,
                    description="Log or handle exception in empty catch block",
                    before=raw_line,
                    after=raw_line.replace("{}", "{\n    std::cerr << e.what() << std::endl;\n}"),
                    explanation="Silently ignoring exceptions can mask critical memory or runtime errors.",
                    confidence=0.90,
                    is_safe=False,
                )
            elif issue_type == "UsingNamespaceStd":
                fix = Fix(
                    issue_type="UsingNamespaceStd",
                    line=line_no,
                    description="Remove 'using namespace std;' and use explicit std:: qualification",
                    before=raw_line,
                    after=f"// Remove: {raw_line}\n// Use std::cout, std::vector, etc. explicitly.",
                    explanation="Global namespace pollution in C++ can lead to naming collisions.",
                    confidence=0.95,
                    is_safe=True,
                )

            if fix:
                fixes.append(fix)

        return fixes


class CodeFixer:
    """Dispatcher: selects the right language-specific fixer."""

    _fixers = {
        "python": PythonFixer(),
        "java":   JavaFixer(),
        "cpp":    CppFixer(),
    }

    def suggest_fixes(self, code: str, language: str,
                      semantic_issues: List[Dict],
                      security_issues: List[Dict]) -> List[Dict]:
        """
        Generate fix suggestions for a set of issues.

        Returns:
            List of serialisable fix dicts.
        """
        fixer = self._fixers.get(language.lower())
        if not fixer:
            return []

        all_issues = semantic_issues + security_issues
        fixes      = fixer.suggest_fixes(code, all_issues)

        return [
            {
                "issue_type":  f.issue_type,
                "line":        f.line,
                "description": f.description,
                "before":      f.before,
                "after":       f.after,
                "explanation": f.explanation,
                "confidence":  f.confidence,
                "is_safe":     f.is_safe,
            }
            for f in fixes if f is not None
        ]