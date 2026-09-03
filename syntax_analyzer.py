"""
CodeSense - Syntax Analyzer
Detects and explains syntax errors across Python, Java, and C++.
"""

import ast
import re
import tokenize
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class SyntaxIssue:
    line:        int
    column:      int
    error_type:  str
    message:     str
    suggestion:  str
    code_snippet: str = ""
    severity:    str  = "ERROR"   # ERROR | WARNING


@dataclass
class SyntaxResult:
    has_errors:   bool
    issues:       List[SyntaxIssue] = field(default_factory=list)
    token_count:  int               = 0
    is_valid:     bool              = True


class PythonSyntaxAnalyzer:
    """Analyzes Python syntax using the built-in AST and tokenizer."""

    # Common error patterns with user-friendly messages
    ERROR_PATTERNS = [
        (r"EOL while scanning string literal",
         "String is not closed. Make sure every opening quote has a matching closing quote."),
        (r"EOF while scanning triple-quoted string literal",
         "Triple-quoted string (\"\"\" or ''') is not properly closed."),
        (r"unexpected EOF",
         "The code ended unexpectedly. A bracket, parenthesis, or colon may be missing."),
        (r"invalid syntax",
         "Python cannot parse this line. Check for missing colons after if/for/def, mismatched brackets, or typos."),
        (r"unmatched '(.)'",
         "Found an unmatched bracket or parenthesis: '{match}'."),
        (r"'(.+)' was never closed",
         "Opened '{match}' but never closed it."),
        (r"cannot assign to (.+)",
         "You are trying to assign a value to something that cannot be assigned to (e.g., a literal)."),
        (r"f-string: (.+)",
         "Invalid f-string expression: {match}."),
        (r"expected an indented block",
         "An indented block is expected here (e.g., after def/class/if). Add at least one indented statement."),
        (r"unexpected indent",
         "This line is indented more than expected. Check your indentation is consistent (spaces vs tabs)."),
        (r"unindent does not match",
         "This line's indentation does not match any outer block. Fix your indentation."),
    ]

    def analyze(self, code: str) -> SyntaxResult:
        lines    = code.splitlines()
        issues: List[SyntaxIssue] = []

        # ── AST parse ──────────────────────────────────────────────────────
        try:
            tree = ast.parse(code)
            ast.fix_missing_locations(tree)
        except SyntaxError as exc:
            msg        = self._friendly_message(str(exc.msg or ""))
            snippet    = lines[exc.lineno - 1] if exc.lineno and exc.lineno <= len(lines) else ""
            suggestion = self._suggest_fix(str(exc.msg or ""), snippet)
            issues.append(SyntaxIssue(
                line=exc.lineno or 0,
                column=exc.offset or 0,
                error_type="SyntaxError",
                message=msg,
                suggestion=suggestion,
                code_snippet=snippet,
            ))
            return SyntaxResult(has_errors=True, issues=issues)
        except Exception as exc:
            issues.append(SyntaxIssue(
                line=0, column=0,
                error_type="ParseError",
                message=f"Could not parse code: {exc}",
                suggestion="Ensure the file is valid Python.",
            ))
            return SyntaxResult(has_errors=True, issues=issues)

        # ── Tokenizer pass (catches tokenize errors AST misses) ────────────
        token_count = 0
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
            token_count = len(tokens)
        except tokenize.TokenError as exc:
            issues.append(SyntaxIssue(
                line=exc.args[1][0] if len(exc.args) > 1 else 0,
                column=exc.args[1][1] if len(exc.args) > 1 else 0,
                error_type="TokenizeError",
                message=self._friendly_message(exc.args[0]),
                suggestion="Check for unclosed strings or brackets.",
                severity="ERROR",
            ))

        # ── Soft style warnings ────────────────────────────────────────────
        for i, line in enumerate(lines, start=1):
            stripped = line.rstrip()
            if "\t" in stripped and any(l.startswith("    ") for l in lines if l.strip()):
                issues.append(SyntaxIssue(
                    line=i, column=0,
                    error_type="IndentationWarning",
                    message="Mixed tabs and spaces detected.",
                    suggestion="Use 4 spaces per indent level consistently.",
                    severity="WARNING",
                ))
                break   # Warn once

        return SyntaxResult(
            has_errors=any(i.severity == "ERROR" for i in issues),
            issues=issues,
            token_count=token_count,
            is_valid=len(issues) == 0 or all(i.severity == "WARNING" for i in issues),
        )

    def _friendly_message(self, raw: str) -> str:
        for pattern, friendly in self.ERROR_PATTERNS:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                groups = m.groups()
                match  = groups[0] if groups else ""
                return friendly.format(match=match)
        return raw

    def _suggest_fix(self, error_msg: str, line: str) -> str:
        msg = error_msg.lower()
        if "invalid syntax" in msg:
            if re.search(r"\bif\b|\bfor\b|\bwhile\b|\bdef\b|\bclass\b|\belif\b|\belse\b|\btry\b|\bexcept\b", line):
                if not line.rstrip().endswith(":"):
                    return "Add a colon (:) at the end of the line."
            if line.count("(") != line.count(")"):
                return "Unbalanced parentheses — check opening and closing ( )."
            if line.count("[") != line.count("]"):
                return "Unbalanced square brackets — check opening and closing [ ]."
            return "Review this line carefully for missing punctuation or typos."
        if "eol" in msg or "eof" in msg:
            return "Close the string with the matching quote character."
        if "indent" in msg:
            return "Use exactly 4 spaces per indentation level. Do not mix tabs and spaces."
        return "Review the syntax carefully near this line."


class JavaSyntaxAnalyzer:
    """Heuristic Java syntax checker (no JVM required)."""

    MISSING_SEMICOLON = re.compile(
        r"^(?!\s*\/\/|.*\{|.*\}|.*:|\s*@|\s*$)"
        r".*[a-zA-Z0-9_\)\]\"']$"
    )

    def analyze(self, code: str) -> SyntaxResult:
        lines  = code.splitlines()
        issues: List[SyntaxIssue] = []

        open_braces  = 0
        open_parens  = 0
        in_block_comment = False

        for i, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            # Track block comments
            if "/*" in line:
                in_block_comment = True
            if "*/" in line:
                in_block_comment = False
                continue
            if in_block_comment or line.startswith("//"):
                continue

            # Brace/paren balance
            open_braces += line.count("{") - line.count("}")
            open_parens += line.count("(") - line.count(")")

            # Missing semicolons on statement lines
            if self.MISSING_SEMICOLON.match(raw_line):
                if not any(kw in line for kw in (
                    "class ", "interface ", "enum ", "if(", "if (",
                    "for(", "for (", "while(", "while (", "else", "try",
                    "catch", "finally", "do", "switch", ")) {", "-> {"
                )):
                    issues.append(SyntaxIssue(
                        line=i, column=len(raw_line),
                        error_type="MissingSemicolon",
                        message="Statement may be missing a semicolon.",
                        suggestion=f"Add ';' at the end of line {i}.",
                        code_snippet=raw_line,
                        severity="WARNING",
                    ))

        if open_braces > 0:
            issues.append(SyntaxIssue(
                line=len(lines), column=0,
                error_type="UnmatchedBrace",
                message=f"{open_braces} opening brace(s) '{{' are never closed.",
                suggestion="Add the missing closing brace(s) '}'.",
            ))
        elif open_braces < 0:
            issues.append(SyntaxIssue(
                line=len(lines), column=0,
                error_type="UnmatchedBrace",
                message=f"{abs(open_braces)} extra closing brace(s) '}}'.",
                suggestion="Remove extra '}' or add matching '{'.",
            ))

        return SyntaxResult(
            has_errors=any(i.severity == "ERROR" for i in issues),
            issues=issues,
        )


class CppSyntaxAnalyzer:
    """Heuristic C++ syntax checker."""

    def analyze(self, code: str) -> SyntaxResult:
        lines  = code.splitlines()
        issues: List[SyntaxIssue] = []

        open_braces = 0
        in_block_comment = False

        for i, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            if "/*" in line:
                in_block_comment = True
            if "*/" in line:
                in_block_comment = False
                continue
            if in_block_comment or line.startswith("//") or line.startswith("#"):
                continue

            open_braces += line.count("{") - line.count("}")

            # Check for printf/scanf without format string
            if re.search(r"\b(printf|scanf)\s*\(\s*\)", line):
                issues.append(SyntaxIssue(
                    line=i, column=0,
                    error_type="MissingFormatString",
                    message="printf/scanf called without a format string.",
                    suggestion='Provide a format string, e.g., printf("%d", value);',
                    code_snippet=raw_line,
                    severity="WARNING",
                ))

            # Common mistake: assignment in condition
            if re.search(r"\bif\s*\(\s*[^=!<>]+=[^=]", line):
                issues.append(SyntaxIssue(
                    line=i, column=0,
                    error_type="AssignmentInCondition",
                    message="Assignment '=' inside if-condition — did you mean '=='?",
                    suggestion="Use '==' for comparison. Add extra parentheses if assignment is intentional: if ((x = y)).",
                    code_snippet=raw_line,
                    severity="WARNING",
                ))

        if open_braces != 0:
            diff = abs(open_braces)
            kind = "opening" if open_braces > 0 else "closing"
            issues.append(SyntaxIssue(
                line=len(lines), column=0,
                error_type="UnmatchedBrace",
                message=f"{diff} unmatched {kind} brace(s).",
                suggestion="Ensure every '{' has a matching '}'.",
            ))

        return SyntaxResult(
            has_errors=any(i.severity == "ERROR" for i in issues),
            issues=issues,
        )


class SyntaxAnalyzer:
    """Dispatcher: selects the right language-specific analyzer."""

    _analyzers = {
        "python": PythonSyntaxAnalyzer(),
        "java":   JavaSyntaxAnalyzer(),
        "cpp":    CppSyntaxAnalyzer(),
    }

    def analyze(self, code: str, language: str) -> Dict[str, Any]:
        analyzer = self._analyzers.get(language.lower())
        if not analyzer:
            return {"has_errors": False, "issues": [], "message": f"Syntax checking not supported for {language}."}

        try:
            result = analyzer.analyze(code)
            return {
                "has_errors":   result.has_errors,
                "is_valid":     result.is_valid,
                "token_count":  result.token_count,
                "error_count":  sum(1 for i in result.issues if i.severity == "ERROR"),
                "warning_count": sum(1 for i in result.issues if i.severity == "WARNING"),
                "issues": [
                    {
                        "line":         i.line,
                        "column":       i.column,
                        "type":         i.error_type,
                        "message":      i.message,
                        "suggestion":   i.suggestion,
                        "code_snippet": i.code_snippet,
                        "severity":     i.severity,
                    }
                    for i in result.issues
                ],
            }
        except Exception as exc:
            logger.error("Syntax analysis failed: %s", exc, exc_info=True)
            return {"has_errors": False, "issues": [], "error": str(exc)}