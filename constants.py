"""
CodeSense - Constants
All application-wide constants in one place.
"""

# ─── Application ────────────────────────────────────────────────────────────
APP_NAME = "CodeSense"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "AI-Powered Code Quality Analyzer"

# ─── Supported Languages ────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = ["python", "java", "cpp"]
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
}

# ─── Score Thresholds ────────────────────────────────────────────────────────
GRADE_THRESHOLDS = {
    "A+": 95,
    "A":  90,
    "A-": 85,
    "B+": 80,
    "B":  75,
    "B-": 70,
    "C+": 65,
    "C":  60,
    "C-": 55,
    "D":  50,
    "F":   0,
}

SCORE_LABELS = {
    (90, 100): "Excellent",
    (75, 90):  "Good",
    (60, 75):  "Average",
    (40, 60):  "Below Average",
    (0,  40):  "Poor",
}

# ─── Complexity Thresholds ───────────────────────────────────────────────────
COMPLEXITY_THRESHOLDS = {
    "low":    5,
    "medium": 10,
    "high":   20,
}

MAX_LINE_LENGTH        = 120
MAX_FUNCTION_LENGTH    = 50
MAX_NESTING_DEPTH      = 4
MAX_PARAMETERS         = 7
MIN_COMMENT_RATIO      = 0.10   # 10%

# ─── Security Severity ──────────────────────────────────────────────────────
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH     = "HIGH"
SEVERITY_MEDIUM   = "MEDIUM"
SEVERITY_LOW      = "LOW"
SEVERITY_INFO     = "INFO"

SEVERITY_SCORES = {
    SEVERITY_CRITICAL: 10,
    SEVERITY_HIGH:      7,
    SEVERITY_MEDIUM:    4,
    SEVERITY_LOW:       2,
    SEVERITY_INFO:      1,
}

# ─── ML Model ────────────────────────────────────────────────────────────────
NUM_FEATURES          = 33
MODEL_FILENAME        = "models/codesense_model.pkl"
SCALER_FILENAME       = "models/codesense_scaler.pkl"
FEATURE_NAMES_FILE    = "models/feature_names.json"
MIN_SAMPLES_TRAIN     = 5000
TARGET_R2             = 0.90
CROSS_VAL_FOLDS       = 10
MAX_SCORE_ADJUSTMENT  = 5.0    # Maximum ±adjustment to ML score

# ─── UI Colors ───────────────────────────────────────────────────────────────
COLOR_PRIMARY   = "#1E88E5"
COLOR_SUCCESS   = "#43A047"
COLOR_WARNING   = "#FDD835"
COLOR_ERROR     = "#E53935"
COLOR_INFO      = "#00ACC1"
COLOR_NEUTRAL   = "#757575"
COLOR_DARK_BG   = "#0E1117"
COLOR_CARD_BG   = "#1E1E2E"
COLOR_BORDER    = "#2D2D3F"

# ─── Database ────────────────────────────────────────────────────────────────
DB_PATH               = "codesense.db"
DB_POOL_SIZE          = 5
MAX_ANALYSIS_HISTORY  = 100     # per user

# ─── Cache ───────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS     = 3600    # 1 hour
CACHE_MAX_SIZE        = 500
CACHE_DIR             = "cache"

# ─── Auth ────────────────────────────────────────────────────────────────────
OTP_EXPIRY_MINUTES    = 10
OTP_LENGTH            = 6
SESSION_TIMEOUT_HOURS = 24
MAX_LOGIN_ATTEMPTS    = 5
BCRYPT_ROUNDS         = 12

# ─── File Limits ─────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB      = 5
MAX_CODE_LINES        = 5000
MIN_CODE_LINES        = 3

# ─── Performance ─────────────────────────────────────────────────────────────
ANALYSIS_TIMEOUT_SEC  = 30
MAX_CONCURRENT_TASKS  = 4

# ─── Feature Names ───────────────────────────────────────────────────────────
FEATURE_NAMES = [
    # Basic metrics (1–8)
    "lines_of_code",
    "blank_lines",
    "comment_lines",
    "comment_ratio",
    "avg_line_length",
    "max_line_length",
    "num_functions",
    "num_classes",
    # Complexity (9–14)
    "avg_cyclomatic_complexity",
    "max_cyclomatic_complexity",
    "avg_cognitive_complexity",
    "max_nesting_depth",
    "avg_function_length",
    "max_function_length",
    # Style (15–19)
    "naming_consistency_score",
    "long_line_ratio",
    "magic_number_count",
    "docstring_ratio",
    "avg_parameters",
    # Security (20–23)
    "security_issue_count",
    "critical_security_count",
    "high_security_count",
    "has_input_validation",
    # DSA (24–26)
    "dsa_complexity_score",
    "algorithm_count",
    "data_structure_count",
    # NEW contextual features (27–33)
    "code_duplication_score",
    "exception_handling_coverage",
    "test_coverage_estimate",
    "code_reusability_score",
    "design_pattern_usage",
    "code_smell_count",
    "technical_debt_minutes",
]

assert len(FEATURE_NAMES) == NUM_FEATURES, \
    f"Feature count mismatch: {len(FEATURE_NAMES)} != {NUM_FEATURES}"

# ─── Algorithms ──────────────────────────────────────────────────────────────
ALGORITHM_COMPLEXITIES = {
    # Sorting
    "bubble_sort":          {"best": "O(n)", "avg": "O(n²)", "worst": "O(n²)", "space": "O(1)"},
    "selection_sort":       {"best": "O(n²)", "avg": "O(n²)", "worst": "O(n²)", "space": "O(1)"},
    "insertion_sort":       {"best": "O(n)", "avg": "O(n²)", "worst": "O(n²)", "space": "O(1)"},
    "merge_sort":           {"best": "O(n log n)", "avg": "O(n log n)", "worst": "O(n log n)", "space": "O(n)"},
    "quick_sort":           {"best": "O(n log n)", "avg": "O(n log n)", "worst": "O(n²)", "space": "O(log n)"},
    "heap_sort":            {"best": "O(n log n)", "avg": "O(n log n)", "worst": "O(n log n)", "space": "O(1)"},
    "counting_sort":        {"best": "O(n+k)", "avg": "O(n+k)", "worst": "O(n+k)", "space": "O(k)"},
    "radix_sort":           {"best": "O(nk)", "avg": "O(nk)", "worst": "O(nk)", "space": "O(n+k)"},
    "bucket_sort":          {"best": "O(n+k)", "avg": "O(n+k)", "worst": "O(n²)", "space": "O(n)"},
    "shell_sort":           {"best": "O(n log n)", "avg": "O(n log² n)", "worst": "O(n²)", "space": "O(1)"},
    # Searching
    "linear_search":        {"best": "O(1)", "avg": "O(n)", "worst": "O(n)", "space": "O(1)"},
    "binary_search":        {"best": "O(1)", "avg": "O(log n)", "worst": "O(log n)", "space": "O(1)"},
    "jump_search":          {"best": "O(1)", "avg": "O(√n)", "worst": "O(√n)", "space": "O(1)"},
    "interpolation_search": {"best": "O(1)", "avg": "O(log log n)", "worst": "O(n)", "space": "O(1)"},
    "exponential_search":   {"best": "O(1)", "avg": "O(log n)", "worst": "O(log n)", "space": "O(1)"},
    "ternary_search":       {"best": "O(1)", "avg": "O(log₃ n)", "worst": "O(log₃ n)", "space": "O(1)"},
    "dfs":                  {"best": "O(V+E)", "avg": "O(V+E)", "worst": "O(V+E)", "space": "O(V)"},
    "bfs":                  {"best": "O(V+E)", "avg": "O(V+E)", "worst": "O(V+E)", "space": "O(V)"},
    # Graph
    "dijkstra":             {"best": "O(E log V)", "avg": "O(E log V)", "worst": "O(E log V)", "space": "O(V)"},
    "bellman_ford":         {"best": "O(E)", "avg": "O(VE)", "worst": "O(VE)", "space": "O(V)"},
    "floyd_warshall":       {"best": "O(V³)", "avg": "O(V³)", "worst": "O(V³)", "space": "O(V²)"},
    "kruskal":              {"best": "O(E log E)", "avg": "O(E log E)", "worst": "O(E log E)", "space": "O(V)"},
    "prim":                 {"best": "O(E log V)", "avg": "O(E log V)", "worst": "O(E log V)", "space": "O(V)"},
    "topological_sort":     {"best": "O(V+E)", "avg": "O(V+E)", "worst": "O(V+E)", "space": "O(V)"},
    "tarjan_scc":           {"best": "O(V+E)", "avg": "O(V+E)", "worst": "O(V+E)", "space": "O(V)"},
    "a_star":               {"best": "O(E)", "avg": "O(E log V)", "worst": "O(V²)", "space": "O(V)"},
    # DP
    "fibonacci_dp":         {"best": "O(n)", "avg": "O(n)", "worst": "O(n)", "space": "O(n)"},
    "lcs":                  {"best": "O(mn)", "avg": "O(mn)", "worst": "O(mn)", "space": "O(mn)"},
    "knapsack":             {"best": "O(nW)", "avg": "O(nW)", "worst": "O(nW)", "space": "O(nW)"},
    "matrix_chain":         {"best": "O(n³)", "avg": "O(n³)", "worst": "O(n³)", "space": "O(n²)"},
    "edit_distance":        {"best": "O(mn)", "avg": "O(mn)", "worst": "O(mn)", "space": "O(mn)"},
    # String
    "kmp":                  {"best": "O(n)", "avg": "O(n+m)", "worst": "O(n+m)", "space": "O(m)"},
    "rabin_karp":           {"best": "O(n+m)", "avg": "O(n+m)", "worst": "O(nm)", "space": "O(1)"},
    "boyer_moore":          {"best": "O(n/m)", "avg": "O(n/m)", "worst": "O(nm)", "space": "O(m)"},
    "trie_search":          {"best": "O(m)", "avg": "O(m)", "worst": "O(m)", "space": "O(ALPHABET*n)"},
    # Advanced
    "backtracking":         {"best": "O(n!)", "avg": "O(bᵈ)", "worst": "O(bᵈ)", "space": "O(d)"},
    "greedy":               {"best": "O(n log n)", "avg": "O(n log n)", "worst": "O(n log n)", "space": "O(1)"},
    "divide_and_conquer":   {"best": "O(n log n)", "avg": "O(n log n)", "worst": "O(n log n)", "space": "O(log n)"},
    "two_pointer":          {"best": "O(n)", "avg": "O(n)", "worst": "O(n)", "space": "O(1)"},
    "sliding_window":       {"best": "O(n)", "avg": "O(n)", "worst": "O(n)", "space": "O(1)"},
}