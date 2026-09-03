"""
CodeSense - Standalone Command-Line Interface (CLI)
Used for local developer audits and automated DevSecOps / CI/CD pipeline quality gates.
Usage:
    python cli.py <file_or_dir> [--min-score 75] [--fail-on-sec] [--format text|json|markdown]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure UTF-8 output across Windows, Linux, macOS
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import StaticAnalyzer
from dsa_detector import DSADetector
from features import FeatureExtractor
from train_model import QualityPredictor, calculate_contextual_adjustments, score_to_grade, score_to_label
from syntax_analyzer import SyntaxAnalyzer
from semantic_analyzer import SemanticAnalyzer
from context_engine import ContextEngine
from code_fixer import CodeFixer
from student_feedback import FeedbackEngine
from utils import detect_language_from_code, results_to_markdown, results_to_json, Timer, LANGUAGE_EXTENSIONS
from validators import validate_code, sanitize_code
from constants import SEVERITY_CRITICAL, SEVERITY_HIGH


def analyze_single_file(file_path: Path, language: str = None) -> Dict[str, Any]:
    """Analyze a single source code file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    code = file_path.read_text(encoding="utf-8", errors="replace")
    code = sanitize_code(code)
    
    if not language:
        ext = file_path.suffix.lower()
        language = LANGUAGE_EXTENSIONS.get(ext, detect_language_from_code(code))

    valid, err = validate_code(code)
    if not valid:
        return {
            "filename": str(file_path),
            "language": language,
            "error": err,
            "score": 0.0,
            "grade": "F",
        }

    static = StaticAnalyzer()
    dsa_det = DSADetector()
    feat_ext = FeatureExtractor()
    syntax_an = SyntaxAnalyzer()
    semantic_an = SemanticAnalyzer()
    ctx_eng = ContextEngine()
    fixer = CodeFixer()
    feedback_eng = FeedbackEngine()
    predictor = QualityPredictor()
    predictor.ensure_model()

    with Timer() as t:
        syntax = syntax_an.analyze(code, language)
        semantic = semantic_an.analyze(code, language)
        analysis = static.analyze(code, language)
        dsa = dsa_det.detect(code, language)
        context = ctx_eng.analyze(code, language, file_path.name, analysis)

        feat_dict = feat_ext.extract(code, language, analysis, dsa)
        feat_array = feat_ext.to_array(feat_dict)

        ctx_adj = calculate_contextual_adjustments(analysis, dsa, language)
        sem_err_count = sum(1 for i in semantic.get("issues", []) if i.get("severity") in ("WARNING", "ERROR"))
        syntax_err_count = len(syntax.get("errors", []))
        penalty = (sem_err_count * 15.0) + (syntax_err_count * 25.0)

        ml_score, confidence = predictor.predict(feat_array, ctx_adj)
        ml_score = max(10.0, min(100.0, ml_score - penalty))

        grade = score_to_grade(ml_score)
        label = score_to_label(ml_score)

        fixes = fixer.suggest_fixes(
            code, language,
            semantic.get("issues", []),
            analysis.get("security", {}).get("findings", []),
        )

        feedback = feedback_eng.generate(
            code=code, language=language, score=ml_score, grade=grade,
            analysis=analysis, dsa=dsa, syntax=syntax, semantic=semantic,
            fixes=fixes, context=context, level="intermediate",
        )

    return {
        "filename": str(file_path),
        "language": language,
        "score": ml_score,
        "grade": grade,
        "label": label,
        "confidence": confidence,
        "syntax": syntax,
        "semantic": semantic,
        "analysis": analysis,
        "dsa": dsa,
        "context": context,
        "fixes": fixes,
        "feedback": feedback,
        "features": feat_dict,
        "processing_ms": t.elapsed_ms,
    }


def format_terminal_output(result: Dict[str, Any]) -> str:
    """Format single result as an ANSI colored terminal report."""
    if "error" in result:
        return f"\033[91m[ERROR] {result['filename']}: {result['error']}\033[0m"

    score = result["score"]
    color = "\033[92m" if score >= 85 else ("\033[94m" if score >= 70 else ("\033[93m" if score >= 50 else "\033[91m"))
    reset = "\033[0m"
    bold = "\033[1m"

    lines = [
        f"{bold}═══════════════════════════════════════════════════════════════{reset}",
        f" 🧠 {bold}CodeSense Quality Audit:{reset} {result['filename']} ({result['language'].upper()})",
        f"{bold}═══════════════════════════════════════════════════════════════{reset}",
        f" Quality Score: {color}{bold}{score:.1f}/100 ({result['grade']}) — {result['label']}{reset} (±{result['confidence']:.1f})",
        f" Processing:    {result['processing_ms']}ms",
        f" Lines of Code: {result['analysis'].get('metrics', {}).get('code_lines', 0)}",
        f" Max Nesting:   {result['analysis'].get('complexity', {}).get('max_nesting', 0)}",
        f" Security Flaws:{result['analysis'].get('security', {}).get('total_issues', 0)}",
        "",
    ]

    # Strengths
    strengths = result["feedback"].get("strengths", [])
    if strengths:
        lines.append(f" {bold}\033[92m✅ Strengths:\033[0m")
        for s in strengths[:4]:
            lines.append(f"   • {s}")
        lines.append("")

    # Security
    sec_findings = result["analysis"].get("security", {}).get("findings", [])
    if sec_findings:
        lines.append(f" {bold}\033[91m🔒 Security Vulnerabilities:\033[0m")
        for f in sec_findings:
            sev_col = "\033[91m" if f["severity"] in (SEVERITY_CRITICAL, SEVERITY_HIGH) else "\033[93m"
            lines.append(f"   • [{sev_col}{f['severity']}{reset}] Line {f['line']}: {f['description']}")
        lines.append("")

    # Algorithms
    algos = result["dsa"].get("algorithms", [])
    if algos:
        lines.append(f" {bold}\033[94m🧮 Detected Algorithms:\033[0m")
        for a in algos:
            cx = a.get("complexity", {})
            name = a.get("display_name") or a.get("name", "").replace("_", " ").title()
            time_cx = cx.get("time_avg") or a.get("time_complexity") or "O(n)"
            space_cx = cx.get("space") or a.get("space_complexity") or "O(1)"
            lines.append(f"   • {name} -> Time: {time_cx}, Space: {space_cx}")
        lines.append("")

    # Fixes
    fixes = result.get("fixes", [])
    if fixes:
        lines.append(f" {bold}\033[93m💡 Suggested Refactoring Fixes ({len(fixes)}):\033[0m")
        for fix in fixes[:3]:
            lines.append(f"   • Line {fix['line']}: {fix['description']}")
        lines.append("")

    lines.append(f"{bold}═══════════════════════════════════════════════════════════════{reset}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="codesense",
        description="CodeSense CLI - AI-Powered Code Quality & Security Gatekeeper"
    )
    parser.add_argument("path", help="Path to file or directory to analyze")
    parser.add_argument("--language", "-l", choices=["python", "java", "cpp"], help="Explicit language override")
    parser.add_argument("--min-score", "-m", type=float, default=0.0, help="Minimum quality score threshold (0-100) to pass")
    parser.add_argument("--fail-on-sec", action="store_true", help="Fail build if CRITICAL or HIGH security issues are found")
    parser.add_argument("--format", "-f", choices=["text", "json", "markdown"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="File to write report output to")

    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Error: Path '{args.path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    files_to_analyze: List[Path] = []
    if target.is_file():
        files_to_analyze.append(target)
    else:
        for ext in LANGUAGE_EXTENSIONS:
            files_to_analyze.extend(target.rglob(f"*{ext}"))

    if not files_to_analyze:
        print(f"No supported source code files found in '{args.path}'.", file=sys.stderr)
        sys.exit(0)

    results: List[Dict[str, Any]] = []
    failed_quality = False
    failed_security = False

    for file_p in files_to_analyze:
        # Skip venv, cache, git directories
        if any(part in file_p.parts for part in ("venv", ".git", "__pycache__", "cache", "logs")):
            continue
        res = analyze_single_file(file_p, language=args.language)
        results.append(res)

        if res.get("score", 0) < args.min_score:
            failed_quality = True

        sec_findings = res.get("analysis", {}).get("security", {}).get("findings", [])
        if args.fail_on_sec and any(f.get("severity") in (SEVERITY_CRITICAL, SEVERITY_HIGH) for f in sec_findings):
            failed_security = True

    # Output Formatting
    if args.format == "json":
        clean_res = [{k: v for k, v in r.items() if k != "features"} for r in results]
        out_str = json.dumps(clean_res if len(clean_res) > 1 else clean_res[0], indent=2, default=str)
    elif args.format == "markdown":
        out_str = "\n\n---\n\n".join(results_to_markdown(r) for r in results)
    else:
        out_str = "\n\n".join(format_terminal_output(r) for r in results)

    if args.output:
        Path(args.output).write_text(out_str, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(out_str)

    # Exit code determination
    if failed_quality:
        print(f"\n❌ Quality Gate Failed: Score below required minimum of {args.min_score}/100.", file=sys.stderr)
        sys.exit(1)

    if failed_security:
        print("\n❌ Security Gate Failed: Critical or High severity security vulnerabilities detected.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
