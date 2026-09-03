"""
CodeSense - Multi-Language Static Analyzer
Professional-grade static analysis covering complexity, style, security, and quality.
"""

import ast
import re
from typing import Any, Dict, List, Tuple

from constants import (
    COMPLEXITY_THRESHOLDS, MAX_LINE_LENGTH, MAX_FUNCTION_LENGTH,
    MAX_NESTING_DEPTH, MIN_COMMENT_RATIO,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    SEVERITY_SCORES,
)
from logger import get_logger

logger = get_logger(__name__)


# ─── Security Patterns ────────────────────────────────────────────────────────

PYTHON_SECURITY_PATTERNS: List[Tuple[str, str, str, str]] = [
    # (pattern, issue_name, description, severity)
    (r"\beval\s*\(", "eval_usage", "eval() can execute arbitrary code.", SEVERITY_CRITICAL),
    (r"\bexec\s*\(", "exec_usage", "exec() can execute arbitrary code.", SEVERITY_CRITICAL),
    (r"\b__import__\s*\(", "dynamic_import", "Dynamic imports are hard to audit.", SEVERITY_HIGH),
    (r"subprocess\.(call|run|Popen).*shell\s*=\s*True", "shell_injection", "shell=True in subprocess is vulnerable to command injection.", SEVERITY_CRITICAL),
    (r"os\.system\s*\(", "os_system", "os.system() is vulnerable to command injection.", SEVERITY_CRITICAL),
    (r"os\.popen\s*\(", "os_popen", "os.popen() is deprecated and vulnerable.", SEVERITY_HIGH),
    (r"pickle\.(load|loads|dump)\s*\(", "pickle_usage", "pickle can execute arbitrary code on deserialization.", SEVERITY_HIGH),
    (r"yaml\.load\s*\([^)]*\)", "yaml_unsafe_load", "yaml.load() without Loader is unsafe. Use yaml.safe_load().", SEVERITY_HIGH),
    (r"input\s*\(", "raw_input_security", "User input should be validated before use.", SEVERITY_LOW),
    (r"hashlib\.(md5|sha1)\s*\(", "weak_hash", "MD5 and SHA1 are cryptographically weak.", SEVERITY_MEDIUM),
    (r"random\.(random|randint|choice|shuffle)", "weak_random", "random is not cryptographically secure. Use secrets module.", SEVERITY_MEDIUM),
    (r"http\.client|urllib\.request", "unverified_http", "Ensure TLS verification is enabled (verify=True).", SEVERITY_LOW),
    (r"\.execute\s*\(\s*(['\"].*?%s|f['\"].*?\{|.*?\.format\(|.*?\+.*?\))", "sql_injection", "String formatting or concatenation in SQL queries is vulnerable to injection.", SEVERITY_CRITICAL),
    (r"\bpassword\s*=\s*['\"][^'\"]+['\"]", "hardcoded_password", "Hardcoded passwords detected in source code.", SEVERITY_CRITICAL),
    (r"\bsecret\s*=\s*['\"][^'\"]+['\"]", "hardcoded_secret", "Hardcoded secret detected.", SEVERITY_CRITICAL),
    (r"\bapi_key\s*=\s*['\"][^'\"]+['\"]", "hardcoded_api_key", "Hardcoded API key detected.", SEVERITY_CRITICAL),
    (r"\btoken\s*=\s*['\"][A-Za-z0-9+/]{20,}['\"]", "hardcoded_token", "Hardcoded token detected.", SEVERITY_HIGH),
    (r"ssl\._create_unverified_context|ssl\.CERT_NONE", "ssl_disabled", "SSL certificate verification is disabled.", SEVERITY_HIGH),
    (r"DEBUG\s*=\s*True", "debug_enabled", "Debug mode enabled. Disable in production.", SEVERITY_MEDIUM),
    (r"ALLOWED_HOSTS\s*=\s*\[.*\*.*\]", "open_allowed_hosts", "Django ALLOWED_HOSTS is open (*). Restrict in production.", SEVERITY_HIGH),
    (r"\bprint\s*\(.*password|print\s*\(.*secret|print\s*\(.*token", "sensitive_log", "Sensitive data may be printed to output.", SEVERITY_MEDIUM),
    (r"tempfile\.mktemp\s*\(", "insecure_tempfile", "mktemp() is insecure; use mkstemp() instead.", SEVERITY_MEDIUM),
    (r"xmlrpc|xml\.etree\.ElementTree.*parse", "xxe_risk", "XML parsing may be vulnerable to XXE attacks.", SEVERITY_MEDIUM),
    (r"flask\.run.*debug\s*=\s*True", "flask_debug", "Flask debug mode exposes an interactive debugger.", SEVERITY_HIGH),
    (r"jinja2.*autoescape\s*=\s*False", "xss_jinja", "Jinja2 autoescaping disabled — XSS risk.", SEVERITY_HIGH),
]

JAVA_SECURITY_PATTERNS: List[Tuple[str, str, str, str]] = [
    (r'Statement\.execute\(.*\+', "sql_injection", "String concatenation in SQL. Use PreparedStatement.", SEVERITY_CRITICAL),
    (r'Runtime\.getRuntime\(\)\.exec\(', "runtime_exec", "Runtime.exec() is vulnerable to command injection.", SEVERITY_HIGH),
    (r'printStackTrace\(\)', "stack_trace_exposure", "Exposing stack traces leaks implementation details.", SEVERITY_LOW),
    (r'new Random\(\)', "weak_random", "java.util.Random is not cryptographically secure. Use SecureRandom.", SEVERITY_MEDIUM),
    (r'MD5|SHA-1', "weak_hash", "MD5/SHA-1 are cryptographically broken.", SEVERITY_MEDIUM),
    (r'"password"\s*:', "hardcoded_password", "Possible hardcoded password.", SEVERITY_CRITICAL),
    (r'HttpURLConnection.*setHostnameVerifier.*ALLOW_ALL', "ssl_bypass", "Hostname verification bypassed.", SEVERITY_HIGH),
    (r'catch\s*\(\s*Exception\s+\w+\s*\)\s*\{\s*\}', "swallowed_exception", "Exception caught and ignored.", SEVERITY_MEDIUM),
]

CPP_SECURITY_PATTERNS: List[Tuple[str, str, str, str]] = [
    (r'\bgets\s*\(', "gets_usage", "gets() is unsafe — use fgets() instead.", SEVERITY_CRITICAL),
    (r'\bstrcpy\s*\(', "strcpy_usage", "strcpy() has no bounds checking — use strncpy() or strlcpy().", SEVERITY_HIGH),
    (r'\bstrcat\s*\(', "strcat_usage", "strcat() has no bounds checking — use strncat().", SEVERITY_HIGH),
    (r'\bsprintf\s*\(', "sprintf_usage", "sprintf() has no bounds checking — use snprintf().", SEVERITY_HIGH),
    (r'\bscanf\s*\([^)]*%s', "scanf_overflow", "scanf with %s has no width limit — may overflow buffer.", SEVERITY_HIGH),
    (r'\bsystem\s*\(', "system_call", "system() is vulnerable to command injection.", SEVERITY_HIGH),
    (r'\bpassword\s*=\s*"[^"]+"', "hardcoded_password", "Hardcoded password.", SEVERITY_CRITICAL),
    (r'\bmalloc\s*\(.*\)\s*;(?!\s*(if|while))', "unchecked_malloc", "malloc() return value not checked for NULL.", SEVERITY_MEDIUM),
    (r'\bdelete\b.*?;|\bfree\s*\([^)]+\)\s*;', "double_free", "Possible double-free or use-after-free. Verify memory is not freed twice.", SEVERITY_CRITICAL),
]

LANGUAGE_SECURITY_MAP = {
    "python": PYTHON_SECURITY_PATTERNS,
    "java":   JAVA_SECURITY_PATTERNS,
    "cpp":    CPP_SECURITY_PATTERNS,
}


# ─── Python Complexity Visitor ────────────────────────────────────────────────

class ComplexityVisitor(ast.NodeVisitor):
    """Compute cyclomatic complexity and max nesting for Python AST."""

    BRANCH_NODES = (
        ast.If, ast.For, ast.AsyncFor, ast.While,
        ast.ExceptHandler, ast.With, ast.AsyncWith,
        ast.Assert, ast.comprehension,
    )

    def __init__(self) -> None:
        self.complexity  = 1
        self.max_nesting = 0
        self._nesting    = 0

    def _enter_branch(self) -> None:
        self.complexity += 1
        self._nesting   += 1
        self.max_nesting = max(self.max_nesting, self._nesting)

    def _exit_branch(self) -> None:
        self._nesting -= 1

    def visit_If(self, node: ast.If) -> None:
        self._enter_branch()
        self.generic_visit(node)
        self._exit_branch()
        # elif counts as a branch
        for _ in node.orelse:
            if isinstance(_, ast.If):
                self.complexity += 1

    def visit_For(self, node: ast.For) -> None:
        self._enter_branch()
        self.generic_visit(node)
        self._exit_branch()

    visit_AsyncFor = visit_For
    visit_While    = visit_For

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._enter_branch()
        self.generic_visit(node)
        self._exit_branch()

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)


# ─── Main Analyzer ────────────────────────────────────────────────────────────

class StaticAnalyzer:
    """
    Professional multi-language static analyzer.
    Covers: complexity, style, security, documentation, structure.
    """

    def analyze(self, code: str, language: str) -> Dict[str, Any]:
        """
        Run full static analysis on code.

        Args:
            code:     Source code string.
            language: 'python', 'java', or 'cpp'.

        Returns:
            Comprehensive analysis dictionary.
        """
        language = language.lower()
        lines    = code.splitlines()

        results: Dict[str, Any] = {
            "language":    language,
            "metrics":     self._basic_metrics(code, lines),
            "complexity":  self._complexity(code, language, lines),
            "style":       self._style(code, lines, language),
            "security":    self._security(code, lines, language),
            "documentation": self._documentation(code, lines, language),
            "structure":   self._structure(code, lines, language),
        }
        results["overall_health"] = self._overall_health(results)
        return results

    # ─── Basic Metrics ───────────────────────────────────────────────────────

    def _basic_metrics(self, code: str, lines: List[str]) -> Dict[str, Any]:
        total        = len(lines)
        blank        = sum(1 for l in lines if not l.strip())
        comments     = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*", "'")))
        code_lines   = total - blank - comments
        char_count   = len(code)

        return {
            "total_lines":   total,
            "code_lines":    code_lines,
            "blank_lines":   blank,
            "comment_lines": comments,
            "comment_ratio": round(comments / total, 3) if total else 0,
            "char_count":    char_count,
            "avg_line_len":  round(sum(len(l) for l in lines) / total, 1) if total else 0,
            "max_line_len":  max((len(l) for l in lines), default=0),
        }

    # ─── Complexity ──────────────────────────────────────────────────────────

    def _complexity(self, code: str, language: str, lines: List[str]) -> Dict[str, Any]:
        if language == "python":
            return self._python_complexity(code)
        else:
            return self._generic_complexity(code, lines)

    def _python_complexity(self, code: str) -> Dict[str, Any]:
        try:
            tree      = ast.parse(code)
        except SyntaxError:
            return {"error": "Cannot compute complexity due to syntax errors."}

        fn_complexities: List[Dict] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                v = ComplexityVisitor()
                v.visit(node)
                fn_complexities.append({
                    "name":        node.name,
                    "line":        node.lineno,
                    "complexity":  v.complexity,
                    "nesting":     v.max_nesting,
                    "length":      (node.end_lineno or node.lineno) - node.lineno + 1,
                    "params":      len(node.args.args),
                })

        if not fn_complexities:
            v = ComplexityVisitor()
            v.visit(ast.parse(code))
            fn_complexities = [{"name": "<module>", "line": 1,
                                 "complexity": v.complexity, "nesting": v.max_nesting,
                                 "length": 0, "params": 0}]

        complexities = [f["complexity"] for f in fn_complexities]
        nestings     = [f["nesting"]    for f in fn_complexities]

        return {
            "functions":           fn_complexities,
            "avg_complexity":      round(sum(complexities) / len(complexities), 2),
            "max_complexity":      max(complexities),
            "avg_nesting":         round(sum(nestings) / len(nestings), 2),
            "max_nesting":         max(nestings),
            "high_complexity_fns": [f for f in fn_complexities if f["complexity"] > COMPLEXITY_THRESHOLDS["medium"]],
            "deeply_nested_fns":   [f for f in fn_complexities if f["nesting"] > MAX_NESTING_DEPTH],
            "long_functions":      [f for f in fn_complexities if f["length"] > MAX_FUNCTION_LENGTH],
        }

    def _generic_complexity(self, code: str, lines: List[str]) -> Dict[str, Any]:
        """Branch-count heuristic for Java/C++."""
        branch_keywords = re.compile(
            r"\b(if|else if|elif|for|while|do|case|catch|&&|\|\||\?)\b"
        )
        complexity = 1 + len(branch_keywords.findall(code))
        max_nesting = self._max_nesting_depth(lines)
        return {
            "avg_complexity": complexity,
            "max_complexity": complexity,
            "max_nesting":    max_nesting,
            "functions":      [],
        }

    def _max_nesting_depth(self, lines: List[str]) -> int:
        depth = 0
        max_d = 0
        for line in lines:
            depth += line.count("{") - line.count("}")
            max_d  = max(max_d, depth)
        return max_d

    # ─── Style ───────────────────────────────────────────────────────────────

    def _style(self, code: str, lines: List[str], language: str) -> Dict[str, Any]:
        issues: List[Dict] = []
        long_lines         = []
        magic_numbers      = []

        # PEP 8 naming check (Python)
        if language == "python":
            for i, line in enumerate(lines, start=1):
                m = re.search(r"\bdef\s+([A-Z][a-zA-Z0-9]*)\s*\(", line)
                if m:
                    issues.append({
                        "line": i, "type": "NamingConvention",
                        "message": f"Function '{m.group(1)}' should use snake_case, not CamelCase.",
                        "suggestion": f"Rename to '{self._to_snake(m.group(1))}'.",
                    })
                m2 = re.search(r"\bclass\s+([a-z]\w*)\s*[:(]", line)
                if m2:
                    issues.append({
                        "line": i, "type": "NamingConvention",
                        "message": f"Class '{m2.group(1)}' should use CamelCase.",
                        "suggestion": f"Rename to '{m2.group(1).capitalize()}'.",
                    })

        # Long lines
        for i, line in enumerate(lines, start=1):
            if len(line) > MAX_LINE_LENGTH:
                long_lines.append({"line": i, "length": len(line)})

        # Magic numbers
        magic_re = re.compile(r"(?<!['\"\w.])\b([2-9]\d{1,}|[1-9]\d{2,})\b(?!['\"])")
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith(("#", "//")):
                continue
            for m in magic_re.finditer(line):
                num = int(m.group(1))
                if num not in (2, 10, 16, 100, 1000):  # Ignore common constants
                    magic_numbers.append({"line": i, "value": num})

        # Trailing whitespace
        trailing = [i + 1 for i, l in enumerate(lines) if l != l.rstrip()]

        # Consistent quotes (Python)
        single_quotes = len(re.findall(r"'[^']*'", code))
        double_quotes = len(re.findall(r'"[^"]*"', code))
        quote_consistency = "consistent" if (single_quotes == 0 or double_quotes == 0) else "mixed"

        naming_score = max(0, 100 - len(issues) * 10)

        return {
            "issues":            issues,
            "long_lines":        long_lines[:20],
            "long_line_count":   len(long_lines),
            "magic_numbers":     magic_numbers[:20],
            "magic_number_count": len(magic_numbers),
            "trailing_whitespace": trailing[:10],
            "quote_consistency": quote_consistency,
            "naming_score":      naming_score,
        }

    @staticmethod
    def _to_snake(name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    # ─── Security ────────────────────────────────────────────────────────────

    def _security(self, code: str, lines: List[str], language: str) -> Dict[str, Any]:
        patterns = LANGUAGE_SECURITY_MAP.get(language, [])
        findings: List[Dict] = []

        for i, line in enumerate(lines, start=1):
            for pattern, name, description, severity in patterns:
                try:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Contextual filter: don't flag weak_random for non-cryptographic simulation/sleep/workloads
                        if name == "weak_random":
                            lower_line = line.lower()
                            sim_keywords = ("sleep", "delay", "duration", "wait", "mock", "sample", "timeout", "jitter", "step", "priority", "task", "uniform")
                            crypto_keywords = ("pass", "secret", "token", "key", "auth", "hash", "salt", "nonce", "cert", "cipher")
                            if any(k in lower_line for k in sim_keywords) and not any(k in lower_line for k in crypto_keywords):
                                continue

                        findings.append({
                            "line":        i,
                            "type":        name,
                            "description": description,
                            "severity":    severity,
                            "code_snippet": line.strip(),
                            "cvss_score":  SEVERITY_SCORES[severity],
                        })
                except re.error as _re_err:
                    # Skip malformed patterns silently — never crash analysis
                    pass

        # De-duplicate by (type, line)
        seen     = set()
        unique   = []
        for f in findings:
            key = (f["type"], f["line"])
            if key not in seen:
                seen.add(key)
                unique.append(f)

        counts = {s: sum(1 for f in unique if f["severity"] == s)
                  for s in (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
                            SEVERITY_LOW, SEVERITY_INFO)}

        total_score = sum(SEVERITY_SCORES[f["severity"]] for f in unique)

        return {
            "findings":        unique,
            "counts":          counts,
            "total_issues":    len(unique),
            "risk_score":      min(100, total_score),
            "has_critical":    counts[SEVERITY_CRITICAL] > 0,
            "has_high":        counts[SEVERITY_HIGH] > 0,
        }

    # ─── Documentation ───────────────────────────────────────────────────────

    def _documentation(self, code: str, lines: List[str], language: str) -> Dict[str, Any]:
        if language == "python":
            return self._python_docs(code)
        return self._generic_docs(lines)

    def _python_docs(self, code: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"docstring_ratio": 0, "undocumented": []}

        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes   = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        undocumented: List[Dict] = []
        for node in functions + classes:
            doc = ast.get_docstring(node)
            if not doc or not doc.strip():
                undocumented.append({
                    "name": node.name,
                    "line": node.lineno,
                    "type": "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
                })

        total       = len(functions) + len(classes)
        documented  = total - len(undocumented)
        ratio       = round(documented / total, 2) if total else 1.0

        return {
            "docstring_ratio":  ratio,
            "documented":       documented,
            "total_symbols":    total,
            "undocumented":     undocumented,
        }

    def _generic_docs(self, lines: List[str]) -> Dict[str, Any]:
        comment_lines = sum(1 for l in lines if l.strip().startswith(("//", "/*", "*", "#")))
        ratio = round(comment_lines / len(lines), 2) if lines else 0
        return {"comment_ratio": ratio, "comment_lines": comment_lines}

    # ─── Structure ───────────────────────────────────────────────────────────

    def _structure(self, code: str, lines: List[str], language: str) -> Dict[str, Any]:
        if language == "python":
            try:
                tree      = ast.parse(code)
                functions = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes   = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                imports   = [ast.dump(n)[:50] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
                return {"functions": functions, "classes": classes,
                        "num_functions": len(functions), "num_classes": len(classes),
                        "num_imports": len(imports)}
            except SyntaxError:
                pass

        fn_pattern = {"java": r"\b\w+\s+(\w+)\s*\([^)]*\)\s*\{",
                      "cpp":  r"\b\w+[\s*]+(\w+)\s*\([^)]*\)\s*\{"}.get(language, r"")
        functions = re.findall(fn_pattern, code) if fn_pattern else []
        return {"functions": functions, "num_functions": len(functions)}

    # ─── Overall Health ──────────────────────────────────────────────────────

    def _overall_health(self, results: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[str]     = []
        strengths: List[str]  = []

        # Complexity
        cx = results.get("complexity", {})
        if cx.get("max_complexity", 0) > COMPLEXITY_THRESHOLDS["high"]:
            issues.append("Very high cyclomatic complexity")
        elif cx.get("avg_complexity", 0) <= COMPLEXITY_THRESHOLDS["low"]:
            strengths.append("Low average complexity")

        # Security
        sec = results.get("security", {})
        if sec.get("has_critical"):
            issues.append("Critical security vulnerabilities found")
        elif sec.get("total_issues", 0) == 0:
            strengths.append("No security issues detected")

        # Documentation
        doc = results.get("documentation", {})
        ratio = doc.get("docstring_ratio", doc.get("comment_ratio", 0))
        if ratio < MIN_COMMENT_RATIO:
            issues.append("Low documentation coverage")
        elif ratio >= 0.3:
            strengths.append("Good documentation coverage")

        # Style
        style = results.get("style", {})
        if style.get("long_line_count", 0) > 10:
            issues.append("Many lines exceed max length")
        if style.get("naming_score", 100) >= 90:
            strengths.append("Consistent naming conventions")

        return {"issues": issues, "strengths": strengths}