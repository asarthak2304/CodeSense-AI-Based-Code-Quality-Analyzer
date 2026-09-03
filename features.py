"""
CodeSense - Feature Extraction
Extracts 33 features for the ML model from static analysis results.
All features are normalized to [0, 1] or standard ranges for ML consumption.
"""

import re
from typing import Any, Dict, List

import numpy as np

from constants import FEATURE_NAMES, NUM_FEATURES
from logger import get_logger

logger = get_logger(__name__)


class FeatureExtractor:
    """
    Extracts NUM_FEATURES numerical features from code and analysis results.
    Features are ordered to match FEATURE_NAMES in constants.py.
    """

    def extract(self, code: str, language: str,
                analysis: Dict[str, Any],
                dsa: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute all 33 features.

        Args:
            code:     Raw source code.
            language: Detected language.
            analysis: Output from StaticAnalyzer.analyze().
            dsa:      Output from DSADetector.detect().

        Returns:
            Dict mapping feature name → float value.
        """
        lines   = code.splitlines()
        metrics = analysis.get("metrics", {})
        cx      = analysis.get("complexity", {})
        style   = analysis.get("style", {})
        sec     = analysis.get("security", {})
        doc     = analysis.get("documentation", {})
        struct  = analysis.get("structure", {})

        total_lines = max(1, metrics.get("total_lines", len(lines)))
        num_fns     = max(1, struct.get("num_functions", 1))

        features: Dict[str, float] = {}

        # ── 1–8: Basic metrics ───────────────────────────────────────────────
        features["lines_of_code"]    = float(metrics.get("code_lines", len(lines)))
        features["blank_lines"]      = float(metrics.get("blank_lines", 0))
        features["comment_lines"]    = float(metrics.get("comment_lines", 0))
        features["comment_ratio"]    = float(metrics.get("comment_ratio", 0))
        features["avg_line_length"]  = float(metrics.get("avg_line_len", 0))
        features["max_line_length"]  = float(metrics.get("max_line_len", 0))
        features["num_functions"]    = float(num_fns - 1)  # ≥0
        features["num_classes"]      = float(struct.get("num_classes", 0))

        # ── 9–14: Complexity ─────────────────────────────────────────────────
        features["avg_cyclomatic_complexity"] = float(cx.get("avg_complexity", 1))
        features["max_cyclomatic_complexity"] = float(cx.get("max_complexity", 1))
        features["avg_cognitive_complexity"]  = self._cognitive_complexity(code, language)
        features["max_nesting_depth"]         = float(cx.get("max_nesting", 0))
        features["avg_function_length"]       = self._avg_fn_length(cx)
        features["max_function_length"]       = self._max_fn_length(cx)

        # ── 15–19: Style ─────────────────────────────────────────────────────
        features["naming_consistency_score"] = float(style.get("naming_score", 100)) / 100.0
        features["long_line_ratio"]   = (
            style.get("long_line_count", 0) / total_lines
        )
        features["magic_number_count"] = float(min(style.get("magic_number_count", 0), 50))
        features["docstring_ratio"]    = float(
            doc.get("docstring_ratio", doc.get("comment_ratio", 0))
        )
        features["avg_parameters"]    = self._avg_parameters(cx)

        # ── 20–23: Security ──────────────────────────────────────────────────
        features["security_issue_count"]   = float(min(sec.get("total_issues", 0), 20))
        features["critical_security_count"] = float(
            min(sec.get("counts", {}).get("CRITICAL", 0), 10)
        )
        features["high_security_count"]    = float(
            min(sec.get("counts", {}).get("HIGH", 0), 10)
        )
        features["has_input_validation"]   = self._has_input_validation(code, language)

        # ── 24–26: DSA ───────────────────────────────────────────────────────
        dsa_summary = dsa.get("summary", {})
        features["dsa_complexity_score"] = float(dsa_summary.get("complexity_score", 0)) / 100.0
        features["algorithm_count"]      = float(min(dsa_summary.get("algorithm_count", 0), 10))
        features["data_structure_count"] = float(min(dsa_summary.get("data_structure_count", 0), 10))

        # ── 27–33: Contextual (NEW) ──────────────────────────────────────────
        features["code_duplication_score"]      = self._duplication_score(code, lines)
        features["exception_handling_coverage"] = self._exception_coverage(code, language)
        features["test_coverage_estimate"]      = self._test_coverage_estimate(code, language)
        features["code_reusability_score"]      = self._reusability_score(code, language, num_fns)
        features["design_pattern_usage"]        = self._design_patterns(code, language)
        features["code_smell_count"]            = float(min(self._code_smells(code, cx, style, language), 20))
        features["technical_debt_minutes"]      = self._technical_debt(features)

        # ── Snippet & Short Script Calibration ─────────────────────────────
        # If code is short (< 15 lines) or simple script without functions,
        # adjust features ONLY IF there are no security flaws or syntax/semantic errors.
        is_short_snippet = total_lines < 15 and struct.get("num_functions", 0) == 0
        has_semantic_issues = sec.get("total_issues", 0) > 0
        if is_short_snippet and not has_semantic_issues:
            # Fallback docstrings to comment_ratio or 0.8 if clean
            c_ratio = float(doc.get("comment_ratio", 0))
            features["docstring_ratio"] = max(1.0 if c_ratio > 0 else 0.8, c_ratio)
            features["test_coverage_estimate"] = 1.0
            features["code_reusability_score"] = 1.0
            features["exception_handling_coverage"] = 1.0
            features["design_pattern_usage"] = 1.0
            features["technical_debt_minutes"] = 0.0

        assert len(features) == NUM_FEATURES, \
            f"Expected {NUM_FEATURES} features, got {len(features)}"

        return features

    def to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Return features as ordered numpy array matching FEATURE_NAMES."""
        return np.array([features[name] for name in FEATURE_NAMES], dtype=np.float32)

    # ─── Feature Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _avg_fn_length(cx: Dict) -> float:
        fns = cx.get("functions", [])
        if not fns:
            return 0.0
        return sum(f.get("length", 0) for f in fns) / len(fns)

    @staticmethod
    def _max_fn_length(cx: Dict) -> float:
        fns = cx.get("functions", [])
        if not fns:
            return 0.0
        return max((f.get("length", 0) for f in fns), default=0)

    @staticmethod
    def _avg_parameters(cx: Dict) -> float:
        fns = cx.get("functions", [])
        if not fns:
            return 0.0
        return sum(f.get("params", 0) for f in fns) / len(fns)

    @staticmethod
    def _cognitive_complexity(code: str, language: str) -> float:
        """
        Simplified cognitive complexity heuristic:
        nested control structures score higher than unnested ones.
        """
        nesting = 0
        score   = 0.0
        increment_kws = re.compile(
            r"\b(if|else|elif|for|while|do|catch|case|switch|&&|\|\|)\b"
        )
        lines = code.splitlines()
        for line in lines:
            stripped = line.strip()
            nesting  += stripped.count("{")
            nesting  -= stripped.count("}")
            nesting   = max(0, nesting)
            if increment_kws.search(stripped):
                score += 1 + nesting * 0.5
        return round(min(score, 200), 2)

    @staticmethod
    def _has_input_validation(code: str, language: str) -> float:
        """1.0 if code validates user input, 0.0 otherwise."""
        patterns = {
            "python": [r"isinstance\(|type\(|re\.(match|search|fullmatch)|\.strip\(\)|len\(.*\)\s*[<>]=?",
                       r"try:.*except|validate|sanitize"],
            "java":   [r"\.isEmpty\(\)|\.matches\(|Objects\.requireNonNull|Validate\.",
                       r"try\s*\{.*catch"],
            "cpp":    [r"if\s*\(.*cin|if\s*\(.*strlen|if\s*\(.*strcmp|isdigit|isalpha"],
        }
        for pattern in patterns.get(language, []):
            if re.search(pattern, code, re.DOTALL | re.IGNORECASE):
                return 1.0
        return 0.0

    @staticmethod
    def _duplication_score(code: str, lines: List[str]) -> float:
        """
        Approximate duplication ratio using identical non-trivial line hashing.
        Returns 0.0 (no duplication) to 1.0 (entirely duplicated).
        """
        non_trivial = [l.strip() for l in lines
                       if len(l.strip()) > 10 and not l.strip().startswith(("#", "//"))]
        if len(non_trivial) < 5:
            return 0.0
        unique = len(set(non_trivial))
        dup_ratio = 1.0 - (unique / len(non_trivial))
        return round(max(0.0, min(1.0, dup_ratio)), 3)

    @staticmethod
    def _exception_coverage(code: str, language: str) -> float:
        """
        Ratio of try/except/suppress blocks to total function count.
        Clamped to [0, 1].
        """
        if language == "python":
            try_count = len(re.findall(r"\btry\s*:|contextlib\.suppress", code))
            fn_count  = max(1, len(re.findall(r"\bdef\s+\w+|async\s+def\s+\w+", code)))
        else:
            try_count = len(re.findall(r"\btry\s*\{", code))
            fn_count  = max(1, len(re.findall(r"\b\w+\s+\w+\s*\([^)]*\)\s*\{", code)))
        return round(min(1.0, try_count / fn_count), 2)

    @staticmethod
    def _test_coverage_estimate(code: str, language: str) -> float:
        """Estimate test coverage based on test function presence."""
        if language == "python":
            test_fns = len(re.findall(r"\bdef\s+test_\w+|class\s+Test\w+", code))
            all_fns  = max(1, len(re.findall(r"\bdef\s+\w+|async\s+def\s+\w+", code)))
        elif language == "java":
            test_fns = len(re.findall(r"@Test|void\s+test\w+\(", code))
            all_fns  = max(1, len(re.findall(r"\bpublic\s+\w+\s+\w+\s*\(", code)))
        else:
            test_fns = len(re.findall(r"\bTEST\s*\(|void\s+test_\w+", code))
            all_fns  = max(1, len(re.findall(r"\b\w+\s+\w+\s*\([^)]*\)\s*\{", code)))
        return round(min(1.0, test_fns / all_fns), 2)

    @staticmethod
    def _reusability_score(code: str, language: str, num_fns: int) -> float:
        """
        Score based on: function count, parameter usage, and absence of global state.
        """
        score = 0.5
        # Reward having functions
        if num_fns >= 2:
            score += 0.2
        # Penalize global variables
        global_count = len(re.findall(r"\bglobal\b", code))
        score -= min(0.3, global_count * 0.05)
        # Reward type hints (Python)
        if language == "python":
            typed = len(re.findall(r"(?:def|async\s+def)\s+\w+\s*\([^)]*:\s*\w+|->\s*\w+", code))
            score += min(0.3, typed * 0.1)
        return round(max(0.0, min(1.0, score)), 2)

    @staticmethod
    def _design_patterns(code: str, language: str) -> float:
        """Detect common design pattern usage; score 0–1."""
        patterns = [
            r"Singleton|singleton|_instance",
            r"Factory|factory.*method|create_\w+",
            r"Observer|observer|subscribe|notify|listener",
            r"Decorator|@\w+\s*\ndef|decorator",
            r"Strategy|strategy.*pattern|Context.*strategy",
            r"Iterator|__iter__|__next__",
            r"Builder|build\(\)|with_\w+\(",
            r"Producer|Consumer|worker.*queue|asyncio\.PriorityQueue|ThreadPool",
            r"@dataclass",
        ]
        found = sum(1 for p in patterns if re.search(p, code, re.IGNORECASE))
        return round(min(1.0, found * 0.2), 2)

    @staticmethod
    def _code_smells(code: str, cx: Dict, style: Dict, language: str) -> int:
        """Count code smells."""
        smells = 0

        # Long methods
        smells += len([f for f in cx.get("functions", []) if f.get("length", 0) > 50])

        # Large class (many methods in one class context)
        if cx.get("num_functions", 0) > 20:
            smells += 2

        # Long parameter list
        smells += len([f for f in cx.get("functions", []) if f.get("params", 0) > 7])

        # Magic numbers
        smells += min(3, style.get("magic_number_count", 0) // 5)

        # Deeply nested code
        smells += len(cx.get("deeply_nested_fns", []))

        # High complexity
        smells += len(cx.get("high_complexity_fns", []))

        return smells

    @staticmethod
    def _technical_debt(features: Dict[str, float]) -> float:
        """
        Estimate technical debt in minutes using SQALE-like model.
        """
        debt = 0.0

        # Complexity debt: only if function complexity exceeds thresholds
        max_cc = features.get("max_cyclomatic_complexity", 0)
        if max_cc > 10:
            debt += (max_cc - 10) * 5

        # Security debt: critical issues are expensive
        debt += features.get("critical_security_count", 0) * 60
        debt += features.get("high_security_count", 0) * 30
        debt += features.get("security_issue_count", 0) * 10

        # Style debt
        debt += features.get("magic_number_count", 0) * 5
        debt += (1.0 - features.get("naming_consistency_score", 1)) * 30

        # Documentation debt
        doc_ratio = features.get("docstring_ratio", 0)
        if doc_ratio < 0.2:
            debt += (0.2 - doc_ratio) * 100

        # Duplication debt
        debt += features.get("code_duplication_score", 0) * 120

        return round(min(debt, 9999), 1)