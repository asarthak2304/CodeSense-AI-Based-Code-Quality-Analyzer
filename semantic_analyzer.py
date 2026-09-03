"""
CodeSense - Semantic Analyzer
Deep semantic analysis: unused variables, dead code, scope tracking, logic issues.
"""

import ast
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class SemanticIssue:
    line:       int
    issue_type: str
    message:    str
    suggestion: str
    severity:   str = "WARNING"   # INFO | WARNING | ERROR
    symbol:     str = ""


class PythonSemanticVisitor(ast.NodeVisitor):
    """
    Walks Python AST to collect semantic information:
    - Variable assignments and usages
    - Function definitions and calls
    - Import usage
    - Unreachable code after return/raise
    - Mutable default arguments
    - Broad exception catches
    """

    def __init__(self) -> None:
        self.issues:       List[SemanticIssue] = []
        # Each scope entry is a dict: {"defined": {name: lineno}, "used": set()}
        self.scopes:       List[Dict[str, Any]] = [{"defined": {}, "used": set()}]
        self.functions:    Dict[str, int]       = {}
        self.called_fns:   Set[str]             = set()
        self.imports:      Dict[str, int]       = {}
        self.used_imports: Set[str]             = set()

    # ── Scope helpers ──────────────────────────────────────────────────────

    def _current_scope(self) -> Dict[str, Any]:
        return self.scopes[-1]

    def _define(self, name: str, lineno: int) -> None:
        self._current_scope()["defined"][name] = lineno

    def _use(self, name: str) -> None:
        # Mark used in current and enclosing scopes
        for scope in reversed(self.scopes):
            scope["used"].add(name)
            if name in scope["defined"]:
                break

    # ── Visitor methods ────────────────────────────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._define(node.name, node.lineno)
        self.functions[node.name] = node.lineno
        self._check_mutable_default(node)
        self.scopes.append({"defined": {}, "used": set()})
        for arg in node.args.args:
            self._define(arg.arg, node.lineno)
        # Also include kwonlyargs and vararg/kwarg
        for arg in node.args.kwonlyargs:
            self._define(arg.arg, node.lineno)
        if node.args.vararg:
            self._define(node.args.vararg.arg, node.lineno)
        if node.args.kwarg:
            self._define(node.args.kwarg.arg, node.lineno)
        self.generic_visit(node)
        self._check_unused_vars(node.lineno)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._define(node.name, node.lineno)
        self.scopes.append({"defined": {}, "used": set()})
        self.generic_visit(node)
        self.scopes.pop()

    def _define_target(self, target: ast.AST, lineno: int) -> None:
        if isinstance(target, ast.Name):
            self._define(target.id, lineno)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._define_target(elt, lineno)
        elif isinstance(target, ast.Starred):
            self._define_target(target.value, lineno)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._define_target(target, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._define_target(node.target, node.lineno)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._define_target(node.target, node.lineno)
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars:
                self._define_target(item.optional_vars, node.lineno)
        self.generic_visit(node)

    visit_AsyncWith = visit_With

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.scopes.append({"defined": {}, "used": set()})
        for gen in node.generators:
            self._define_target(gen.target, node.lineno)
        self.generic_visit(node)
        self.scopes.pop()

    visit_SetComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.scopes.append({"defined": {}, "used": set()})
        for gen in node.generators:
            self._define_target(gen.target, node.lineno)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._use(node.id)
            # Track load vs defined/built-in for undefined variable checks
            import builtins
            is_builtin = hasattr(builtins, node.id) or node.id in ("__name__", "__file__", "__doc__")
            is_defined = False
            for s in reversed(self.scopes):
                if node.id in s["defined"]:
                    is_defined = True
                    break
            if not is_defined and not is_builtin and node.id not in self.imports and node.id not in self.functions:
                # Undefined variable reference
                self.issues.append(SemanticIssue(
                    line=node.lineno,
                    issue_type="UndefinedVariable",
                    message=f"Undefined variable or name '{node.id}' referenced.",
                    suggestion=f"Define '{node.id}' before referencing it or check for typos.",
                    severity="WARNING",
                    symbol=node.id,
                ))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imports[name] = node.lineno

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                return   # Wildcard import — skip
            name = alias.asname or alias.name
            self.imports[name] = node.lineno

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            self._use(node.value.id)
            self.used_imports.add(node.value.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.called_fns.add(node.func.id)
            self._use(node.func.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name and isinstance(node.name, str):
            self._define(node.name, node.lineno)
        if node.type is None:
            self.issues.append(SemanticIssue(
                line=node.lineno,
                issue_type="BareExcept",
                message="Bare 'except:' catches ALL exceptions including KeyboardInterrupt and SystemExit.",
                suggestion="Catch specific exceptions, e.g., 'except (ValueError, TypeError):'",
                severity="WARNING",
            ))
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self.issues.append(SemanticIssue(
                line=node.lineno,
                issue_type="BroadExcept",
                message="Catching broad 'Exception' may hide unexpected errors.",
                suggestion="Catch the most specific exception type possible.",
                severity="INFO",
            ))
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.generic_visit(node)

    # ── Post-visit checks ─────────────────────────────────────────────────

    def _check_unused_vars(self, fn_line: int) -> None:
        scope = self._current_scope()
        defined = scope.get("defined", {})
        used = scope.get("used", set())
        skip = {"self", "cls", "_"}
        for name, def_line in defined.items():
            if name.startswith("_") or name in skip:
                continue
            if name not in used:
                self.issues.append(SemanticIssue(
                    line=def_line,
                    issue_type="UnusedVariable",
                    message=f"Variable '{name}' is assigned but never used.",
                    suggestion=f"Remove the assignment or use '{name}' in your logic. Prefix with '_' to indicate intentional non-use.",
                    severity="WARNING",
                    symbol=name,
                ))

    def _check_mutable_default(self, node: ast.FunctionDef) -> None:
        for default in node.args.defaults + node.args.kw_defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append(SemanticIssue(
                    line=node.lineno,
                    issue_type="MutableDefault",
                    message=f"Function '{node.name}' uses a mutable default argument (list/dict/set).",
                    suggestion="Use None as default and assign the mutable value inside the function:\n"
                               "  def fn(items=None):\n      if items is None: items = []",
                    severity="WARNING",
                    symbol=node.name,
                ))

    def finalize(self) -> None:
        """Check unused imports and functions after full traversal."""
        global_used = self.scopes[0]["used"]
        for name, lineno in self.imports.items():
            if name not in global_used and name not in self.used_imports:
                self.issues.append(SemanticIssue(
                    line=lineno,
                    issue_type="UnusedImport",
                    message=f"'{name}' is imported but never used.",
                    suggestion=f"Remove 'import {name}' or use it in your code.",
                    severity="WARNING",
                    symbol=name,
                ))

        for fn_name, lineno in self.functions.items():
            if fn_name not in self.called_fns and not fn_name.startswith(("test_", "__")):
                self.issues.append(SemanticIssue(
                    line=lineno,
                    issue_type="UnusedFunction",
                    message=f"Function '{fn_name}' is defined but never called.",
                    suggestion=f"Remove '{fn_name}' if unused, or call it where needed.",
                    severity="INFO",
                    symbol=fn_name,
                ))


def _detect_unreachable_python(tree: ast.AST) -> List[SemanticIssue]:
    """
    Detect statements after return, raise, break, or continue in the same block using AST.
    Avoids false positives from multiline return expressions or nested scopes.
    """
    issues: List[SemanticIssue] = []

    def check_body(stmts: List[ast.stmt]) -> None:
        for idx, stmt in enumerate(stmts):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                if idx + 1 < len(stmts):
                    dead_stmt = stmts[idx + 1]
                    action = type(stmt).__name__.lower()
                    issues.append(SemanticIssue(
                        line=dead_stmt.lineno,
                        issue_type="UnreachableCode",
                        message=f"Statement on line {dead_stmt.lineno} is unreachable after '{action}' on line {stmt.lineno}.",
                        suggestion="Remove the unreachable statement or reorder your logic.",
                        severity="WARNING",
                    ))
                break

    for node in ast.walk(tree):
        for attr in ("body", "orelse", "finalbody"):
            body = getattr(node, attr, None)
            if isinstance(body, list):
                check_body(body)

    return issues


class SemanticAnalyzer:
    """Public interface for semantic analysis."""

    def analyze(self, code: str, language: str) -> Dict[str, Any]:
        if language == "python":
            return self._analyze_python(code)
        elif language in ("java", "cpp"):
            return self._analyze_generic(code, language)
        return {"issues": [], "summary": {}}

    def _analyze_python(self, code: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"issues": [], "summary": {"note": "Semantic analysis skipped due to syntax errors."}}

        visitor = PythonSemanticVisitor()
        visitor.visit(tree)
        visitor.finalize()

        unreachable = _detect_unreachable_python(tree)
        all_issues  = visitor.issues + unreachable

        return {
            "issues": [
                {
                    "line":        i.line,
                    "type":        i.issue_type,
                    "message":     i.message,
                    "suggestion":  i.suggestion,
                    "severity":    i.severity,
                    "symbol":      i.symbol,
                }
                for i in all_issues
            ],
            "summary": {
                "unused_variables": sum(1 for i in all_issues if i.issue_type == "UnusedVariable"),
                "unused_imports":   sum(1 for i in all_issues if i.issue_type == "UnusedImport"),
                "unused_functions": sum(1 for i in all_issues if i.issue_type == "UnusedFunction"),
                "unreachable_code": sum(1 for i in all_issues if i.issue_type == "UnreachableCode"),
                "mutable_defaults": sum(1 for i in all_issues if i.issue_type == "MutableDefault"),
                "broad_exceptions": sum(1 for i in all_issues if i.issue_type in ("BareExcept", "BroadExcept")),
                "total":            len(all_issues),
            },
        }

    def _analyze_generic(self, code: str, language: str) -> Dict[str, Any]:
        """Heuristic semantic checks for Java/C++."""
        issues: List[Dict] = []
        lines = code.splitlines()

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Null/nullptr dereference risk
            if language == "java" and re.search(r"\w+\s*=\s*null\s*;.*\.\w+\s*\(", stripped):
                issues.append({
                    "line": i, "type": "NullDereference",
                    "message": "Possible null dereference: variable assigned null then immediately accessed.",
                    "suggestion": "Add a null check before accessing this object.",
                    "severity": "WARNING", "symbol": "",
                })

            if language == "cpp" and re.search(r"\w+\s*=\s*(nullptr|NULL)\s*;.*\w+->\w+", stripped):
                issues.append({
                    "line": i, "type": "NullPointerDereference",
                    "message": "Possible nullptr dereference: pointer set to nullptr/NULL then dereferenced with '->'.",
                    "suggestion": "Add a nullptr check before dereferencing this pointer.",
                    "severity": "WARNING", "symbol": "",
                })

            # Empty catch block
            if re.search(r"catch\s*\([^)]+\)\s*\{\s*\}", stripped):
                issues.append({
                    "line": i, "type": "EmptyCatch",
                    "message": "Empty catch block silently swallows exceptions.",
                    "suggestion": "Log the exception or rethrow it.",
                    "severity": "WARNING", "symbol": "",
                })

            # System.out.println in enterprise Java
            if language == "java" and "System.out.print" in stripped:
                issues.append({
                    "line": i, "type": "SystemOutPrintln",
                    "message": "Use of System.out.print/println in production Java code.",
                    "suggestion": "Replace console printing with a structured logger (e.g. SLF4J / Logger).",
                    "severity": "INFO", "symbol": "",
                })

            # using namespace std in C++ header/file
            if language == "cpp" and re.search(r"using\s+namespace\s+std\s*;", stripped):
                issues.append({
                    "line": i, "type": "UsingNamespaceStd",
                    "message": "'using namespace std;' causes global namespace pollution.",
                    "suggestion": "Use explicit 'std::' prefixes (e.g., std::cout, std::string) instead of importing whole namespace.",
                    "severity": "INFO", "symbol": "",
                })

            # C-style cast in C++
            if language == "cpp" and re.search(r"\(\s*(int|float|double|char\*|void\*)\s*\)\s*\w+", stripped):
                issues.append({
                    "line": i, "type": "CStyleCast",
                    "message": "C-style cast used in C++ code.",
                    "suggestion": "Use explicit C++ casts (e.g., static_cast<int>(var) or reinterpret_cast).",
                    "severity": "INFO", "symbol": "",
                })

        return {
            "issues": issues,
            "summary": {"total": len(issues)},
        }