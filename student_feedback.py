"""
CodeSense - Intelligent Feedback Engine
Context-aware, code-specific, progressive feedback with learning paths.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from logger import get_logger

logger = get_logger(__name__)

LEARNING_RESOURCES = {
    "complexity":      {"title": "Big-O Cheat Sheet", "url": "https://www.bigocheatsheet.com"},
    "security":        {"title": "OWASP Top 10",       "url": "https://owasp.org/www-project-top-ten/"},
    "clean_code":      {"title": "Clean Code Principles", "url": "https://refactoring.guru/refactoring"},
    "design_patterns": {"title": "Refactoring Guru",    "url": "https://refactoring.guru/design-patterns"},
    "testing":         {"title": "Python unittest docs", "url": "https://docs.python.org/3/library/unittest.html"},
    "type_hints":      {"title": "PEP 484 – Type Hints", "url": "https://peps.python.org/pep-0484/"},
    "dsa":             {"title": "Visualgo",             "url": "https://visualgo.net/"},
    "pep8":            {"title": "PEP 8 Style Guide",    "url": "https://peps.python.org/pep-0008/"},
}

LEETCODE_SUGGESTIONS = {
    "binary_search":     ("#704 Binary Search",     "https://leetcode.com/problems/binary-search/"),
    "two_pointer":       ("#167 Two Sum II",         "https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/"),
    "sliding_window":    ("#3 Longest Substring",   "https://leetcode.com/problems/longest-substring-without-repeating-characters/"),
    "bfs":               ("#102 Level Order",        "https://leetcode.com/problems/binary-tree-level-order-traversal/"),
    "dfs":               ("#200 Number of Islands",  "https://leetcode.com/problems/number-of-islands/"),
    "dijkstra":          ("#743 Network Delay",      "https://leetcode.com/problems/network-delay-time/"),
    "fibonacci_dp":      ("#509 Fibonacci Number",   "https://leetcode.com/problems/fibonacci-number/"),
    "knapsack":          ("#416 Partition Equal Subset", "https://leetcode.com/problems/partition-equal-subset-sum/"),
    "lcs":               ("#1143 LCS",               "https://leetcode.com/problems/longest-common-subsequence/"),
    "edit_distance":     ("#72 Edit Distance",        "https://leetcode.com/problems/edit-distance/"),
}


@dataclass
class FeedbackItem:
    category:    str
    severity:    str            # "positive" | "info" | "warning" | "error"
    title:       str
    message:     str
    line:        Optional[int]  = None
    code_before: str            = ""
    code_after:  str            = ""
    resource:    Optional[Dict] = None
    step:        int            = 0


class FeedbackEngine:
    """
    Generates structured, progressive feedback from analysis results.
    Supports Beginner / Intermediate / Advanced modes.
    """

    def generate(
        self,
        code:           str,
        language:       str,
        score:          float,
        grade:          str,
        analysis:       Dict[str, Any],
        dsa:            Dict[str, Any],
        syntax:         Dict[str, Any],
        semantic:       Dict[str, Any],
        fixes:          List[Dict],
        context:        Dict[str, Any],
        level:          str = "intermediate",  # beginner | intermediate | advanced
        previous_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Produce the full feedback report.
        """
        items:     List[FeedbackItem] = []
        strengths: List[str]          = []
        issues:    List[str]          = []

        # ── Overall assessment ────────────────────────────────────────────
        opening = self._opening_message(score, grade, previous_score)

        # ── Positives ────────────────────────────────────────────────────
        strengths = self._extract_strengths(analysis, dsa, syntax, score)
        for s in strengths:
            items.append(FeedbackItem("strength", "positive", "✅ Strength", s))

        # ── Syntax issues ────────────────────────────────────────────────
        for issue in syntax.get("issues", []):
            if issue["severity"] == "ERROR":
                items.append(FeedbackItem(
                    category="syntax",
                    severity="error",
                    title=f"❌ Syntax Error — Line {issue['line']}",
                    message=self._simplify(issue["message"], level),
                    line=issue["line"],
                    code_before=issue.get("code_snippet", ""),
                    code_after=issue.get("suggestion", ""),
                ))

        # ── Semantic issues ───────────────────────────────────────────────
        for issue in semantic.get("issues", [])[:10]:
            sev = "warning" if issue["severity"] == "WARNING" else "info"
            items.append(FeedbackItem(
                category="semantic",
                severity=sev,
                title=f"⚠️ {issue['type'].replace('_', ' ')} — Line {issue['line']}",
                message=self._simplify(issue["message"], level),
                line=issue["line"],
                code_after=issue.get("suggestion", ""),
            ))

        # ── Security issues ───────────────────────────────────────────────
        sec_findings = analysis.get("security", {}).get("findings", [])
        for finding in sec_findings[:8]:
            items.append(FeedbackItem(
                category="security",
                severity="error" if finding["severity"] in ("CRITICAL", "HIGH") else "warning",
                title=f"🔒 Security [{finding['severity']}] — Line {finding['line']}",
                message=finding["description"],
                line=finding["line"],
                code_before=finding.get("code_snippet", ""),
                code_after=self._security_fix_hint(finding["type"]),
                resource=LEARNING_RESOURCES.get("security"),
            ))

        # ── Complexity issues ─────────────────────────────────────────────
        cx = analysis.get("complexity", {})
        for fn in cx.get("high_complexity_fns", [])[:3]:
            items.append(FeedbackItem(
                category="complexity",
                severity="warning",
                title=f"⚡ High Complexity in '{fn['name']}' (Line {fn['line']})",
                message=self._complexity_message(fn, level),
                line=fn["line"],
                resource=LEARNING_RESOURCES.get("complexity"),
            ))

        # ── DSA insights ──────────────────────────────────────────────────
        for algo in dsa.get("algorithms", [])[:3]:
            key = algo["name"]
            lc  = LEETCODE_SUGGESTIONS.get(key)
            item = FeedbackItem(
                category="dsa",
                severity="info",
                title=f"🧠 {algo['display_name']} Detected (Line {algo['start_line']}–{algo['end_line']})",
                message=self._algo_message(algo, level),
                line=algo["start_line"],
                resource={"title": "Visualgo", "url": "https://visualgo.net/"},
            )
            if lc:
                item.resource = {"title": f"Practice: LeetCode {lc[0]}", "url": lc[1]}
            items.append(item)

        # ── Style issues ──────────────────────────────────────────────────
        style = analysis.get("style", {})
        if style.get("long_line_count", 0) > 5:
            items.append(FeedbackItem(
                category="style",
                severity="warning",
                title=f"📏 {style['long_line_count']} Lines Exceed Max Length",
                message=self._long_line_message(style, level),
                resource=LEARNING_RESOURCES.get("pep8"),
            ))

        # ── Auto-fixes ────────────────────────────────────────────────────
        safe_fixes = [f for f in fixes if f.get("is_safe")]

        # ── Context notes ─────────────────────────────────────────────────
        context_notes = context.get("intent_notes", [])

        # ── Learning path ─────────────────────────────────────────────────
        learning_path = self._build_learning_path(items, dsa, score)

        # ── Next steps ────────────────────────────────────────────────────
        next_steps = self._next_steps(items, score, level)

        # ── Encouragement ─────────────────────────────────────────────────
        encouragement = self._encouragement(score, previous_score, grade)

        return {
            "opening":        opening,
            "score":          score,
            "grade":          grade,
            "strengths":      strengths,
            "items":          [self._item_to_dict(i) for i in items],
            "safe_fixes":     safe_fixes,
            "context_notes":  context_notes,
            "learning_path":  learning_path,
            "next_steps":     next_steps,
            "encouragement":  encouragement,
            "summary": {
                "errors":    sum(1 for i in items if i.severity == "error"),
                "warnings":  sum(1 for i in items if i.severity == "warning"),
                "positives": sum(1 for i in items if i.severity == "positive"),
                "infos":     sum(1 for i in items if i.severity == "info"),
            },
        }

    # ── Message helpers ───────────────────────────────────────────────────────

    def _opening_message(self, score: float, grade: str,
                          prev: Optional[float]) -> str:
        if score >= 90:
            msg = f"🌟 Outstanding! Your code scored {score}/100 (Grade {grade}). Excellent quality!"
        elif score >= 75:
            msg = f"👍 Good work! Your code scored {score}/100 (Grade {grade}). A few improvements remain."
        elif score >= 60:
            msg = f"📈 Your code scored {score}/100 (Grade {grade}). Solid foundation with room to grow."
        else:
            msg = f"🔧 Your code scored {score}/100 (Grade {grade}). Let's work through the improvements together."
        if prev is not None:
            delta = round(score - prev, 1)
            if delta > 0:
                msg += f" You improved by +{delta} points since last time — great progress! 🎉"
            elif delta < 0:
                msg += f" Score dropped by {abs(delta)} points — check the issues below."
        return msg

    def _simplify(self, message: str, level: str) -> str:
        """Adapt message verbosity to skill level."""
        if level == "beginner":
            return re.sub(r"\b(AST|heuristic|cyclomatic|cognitive|CVSS)\b", "", message)
        return message

    def _complexity_message(self, fn: Dict, level: str) -> str:
        name = fn.get("name", "this function")
        cc   = fn.get("complexity", 0)
        if level == "beginner":
            return (
                f"'{name}' is quite complex (score: {cc}). "
                f"Try breaking it into smaller helper functions — each doing ONE thing."
            )
        return (
            f"'{name}' has cyclomatic complexity {cc} "
            f"(threshold: 10). Refactor by extracting helper functions or "
            f"using early returns to reduce nesting."
        )

    def _algo_message(self, algo: Dict, level: str) -> str:
        name = algo["display_name"]
        cx   = algo.get("complexity", {})
        avg  = cx.get("avg", "?")
        sugg = algo.get("suggestion", "")
        if level == "beginner":
            return f"Your code uses {name}! Average time complexity is {avg}. {sugg}"
        return (
            f"{name} detected (lines {algo['start_line']}–{algo['end_line']}).\n"
            f"Reason: {algo.get('reason','')}\n"
            f"Complexity: Best {cx.get('best','?')} / Avg {avg} / Worst {cx.get('worst','?')}\n"
            f"Space: {cx.get('space','?')}\n"
            f"Suggestion: {sugg}"
        )

    def _long_line_message(self, style: Dict, level: str) -> str:
        count = style.get("long_line_count", 0)
        if level == "beginner":
            return f"{count} lines are too long (over 120 characters). Try to keep lines under 120 characters for readability."
        return (
            f"{count} lines exceed the maximum line length of 120 characters. "
            f"Break long expressions using Python's implicit line continuation inside brackets, "
            f"or use backslash continuation."
        )

    @staticmethod
    def _security_fix_hint(issue_type: str) -> str:
        hints = {
            "eval_usage":     "Use ast.literal_eval() for data, or refactor to avoid eval().",
            "sql_injection":  "Use parameterised queries: cursor.execute('... WHERE id = ?', (value,))",
            "weak_hash":      "Replace hashlib.md5() with hashlib.sha256().",
            "weak_random":    "Use the 'secrets' module for security-sensitive randomness.",
            "hardcoded_password": "Store credentials in environment variables or a secrets vault.",
            "yaml_unsafe_load": "Use yaml.safe_load() instead of yaml.load().",
            "shell_injection": "Avoid shell=True; pass arguments as a list instead.",
        }
        return hints.get(issue_type, "Review and apply the security best practice.")

    def _extract_strengths(self, analysis: Dict, dsa: Dict,
                            syntax: Dict, score: float) -> List[str]:
        strengths = []
        sec = analysis.get("security", {})
        cx  = analysis.get("complexity", {})
        doc = analysis.get("documentation", {})

        if sec.get("total_issues", 0) == 0:
            strengths.append("No security vulnerabilities detected — great secure coding practices!")
        if cx.get("avg_complexity", 99) <= 5:
            strengths.append(f"Low average cyclomatic complexity ({cx.get('avg_complexity',0):.1f}) — code is clean and readable.")
        ratio = doc.get("docstring_ratio", doc.get("comment_ratio", 0))
        if ratio >= 0.4:
            strengths.append(f"Good documentation coverage ({ratio*100:.0f}%).")
        if not syntax.get("has_errors"):
            strengths.append("Code is syntactically valid — no parse errors.")
        if dsa.get("algorithms"):
            best = dsa["algorithms"][0]["display_name"]
            strengths.append(f"{best} detected — good algorithmic thinking!")
        if score >= 85:
            strengths.append("Overall high code quality — close to production-ready!")

        return strengths[:5]

    def _build_learning_path(self, items: List[FeedbackItem],
                              dsa: Dict, score: float) -> List[Dict]:
        path = []
        categories = {i.category for i in items if i.severity in ("error", "warning")}

        if "syntax" in categories:
            path.append({"step": 1, "title": "Fix Syntax Errors",
                         "resource": LEARNING_RESOURCES.get("pep8"),
                         "description": "Start here — syntax errors prevent the code from running."})
        if "security" in categories:
            path.append({"step": len(path)+1, "title": "Resolve Security Issues",
                         "resource": LEARNING_RESOURCES.get("security"),
                         "description": "Security issues are critical — fix these next."})
        if "complexity" in categories:
            path.append({"step": len(path)+1, "title": "Reduce Complexity",
                         "resource": LEARNING_RESOURCES.get("complexity"),
                         "description": "Break down complex functions into smaller, focused ones."})
        if dsa.get("algorithms"):
            best_key = dsa["algorithms"][0]["name"]
            lc = LEETCODE_SUGGESTIONS.get(best_key)
            if lc:
                path.append({"step": len(path)+1,
                             "title": f"Practice: {lc[0]}",
                             "resource": {"title": lc[0], "url": lc[1]},
                             "description": "Strengthen your algorithm skills with this LeetCode problem."})

        if score < 70:
            path.append({"step": len(path)+1, "title": "Study Clean Code Principles",
                         "resource": LEARNING_RESOURCES.get("clean_code"),
                         "description": "Learn refactoring techniques to improve code quality."})

        return path

    def _next_steps(self, items: List[FeedbackItem],
                    score: float, level: str) -> List[str]:
        steps = []
        errors   = [i for i in items if i.severity == "error"]
        warnings = [i for i in items if i.severity == "warning"]

        if errors:
            steps.append(f"1. Fix the {len(errors)} error(s) highlighted above — these are blocking issues.")
        if warnings:
            steps.append(f"{'2' if errors else '1'}. Address {len(warnings)} warning(s) to improve reliability.")
        if score < 80:
            steps.append(f"{'3' if errors and warnings else '2'}. Review your function structure — aim for single-responsibility functions.")
        steps.append("Run CodeSense again after changes to see your improved score.")

        return steps[:4]

    @staticmethod
    def _encouragement(score: float, prev: Optional[float], grade: str) -> str:
        if prev and score > prev:
            return f"🎉 You improved by {round(score - prev, 1)} points — keep up the great work!"
        if score >= 90:
            return "🏆 Top-tier code quality. You're writing like a professional!"
        if score >= 75:
            return "💪 Solid work! A few more tweaks and you'll hit an A grade."
        if score >= 60:
            return "📚 Good progress! Focus on the top warnings to push past 75."
        return "🌱 Every coder starts somewhere. Work through the steps above and you'll improve quickly!"

    @staticmethod
    def _item_to_dict(item: FeedbackItem) -> Dict:
        return {
            "category":    item.category,
            "severity":    item.severity,
            "title":       item.title,
            "message":     item.message,
            "line":        item.line,
            "code_before": item.code_before,
            "code_after":  item.code_after,
            "resource":    item.resource,
        }