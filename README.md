<div align="center">

# 🧠 CodeSense
### AI-Based Code Quality Analyzer

*My B.Tech Final Year Project — built from scratch 😅*

<br>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML_Model-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)

<br>

> **"CodeSense doesn't just grade your code — it analyzes algorithms, flags security flaws, explains line-by-line issues, and provides actionable fixes with tailored learning paths."**

<br>

[🚀 Quick Start](#-quick-start) • [✨ Key Features](#-key-features) • [🏗️ How it Works](#%EF%B8%8F-how-it-works) • [🔒 Security & Auth](#-security--authentication) • [🤖 ML Architecture](#-ml-model-architecture)

</div>

---

## 👋 About the Project

CodeSense analyzes **Python, Java, and C++** code and delivers an in-depth audit covering:
- **Objective Quality Score (0–100):** Predicted by a tuned Random Forest Regressor trained on 33 engineered metrics (R² ≥ 0.95).
- **DSA & Complexity Detection:** Recognizes 40+ algorithms and data structures with exact Big-O time and space bounds.
- **Syntax & Semantic Analysis:** Pinpoints unused variables, unreferenced imports, mutable defaults, and dead code.
- **Security Vulnerability Scanner:** Detects 50+ real-world vulnerabilities (SQL injection, hardcoded secrets, weak crypto).
- **Auto-Fix Recommendations:** Shows clean, safe before/after diffs with explanations.
- **Personalized Learning Paths:** Progressive feedback (Beginner / Intermediate / Advanced) linked to LeetCode problems and official references.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🤖 ML-Based Quality Scoring
Tuned `RandomForestRegressor` with `RobustScaler` pipeline trained on 10,000 code samples. Evaluates 33 static, complexity, maintainability, and security features with tree-variance confidence intervals.

</td>
<td width="50%">

### 🧠 Algorithm & DSA Detection
Heuristic detection for 40+ algorithms (Binary Search, Dijkstra, QuickSort, Knapsack, Sliding Window) with detailed Big-O time (best, avg, worst) and space analysis.

</td>
</tr>
<tr>
<td width="50%">

### 🔐 Email-Based OTP Authentication
Secure user registration with 6-digit numeric OTP verification delivered dynamically via SMTP. Includes bcrypt password hashing (12 rounds) and brute-force lockout protection.

</td>
<td width="50%">

### 🔒 50+ Security Vulnerability Patterns
Scans for SQL injection, command injection, hardcoded secrets, weak cryptography, XXE, insecure deserialization, and dangerous C++ memory management functions.

</td>
</tr>
<tr>
<td width="50%">

### ⚠️ Syntax & Semantic Scope Engine
Dual-pass AST & tokenizer analysis with friendly syntax diagnostics, lexical scope resolution, unused variable/import detection, and unreachable code elimination.

</td>
<td width="50%">

### 🔧 1-Click Smart Refactoring & Diff Viewer
Interactive VS Code Dark editor with unified red/green diffs, 1-click "Apply Fix to Editor", and "Apply All Safe Fixes" with bottom-up line index preserving refactoring.

</td>
</tr>
<tr>
<td width="50%">

### 📚 Adaptive Learning Paths
Tailors feedback to the user's selected proficiency level (Beginner, Intermediate, Advanced) and recommends curated LeetCode problems and study resources.

</td>
<td width="50%">

### 📄 Direct PDF Export & Performance Transcripts
Generates official binary PDF audit certificates for individual code submissions and downloadable student performance transcripts with gamified achievements.

</td>
</tr>
<tr>
<td width="50%">

### 💻 VS Code-Style Interactive Editor
Embedded code editor with line numbers, live syntax highlighting, bracket matching, and debounced real-time language auto-detection for Python, Java, and C++.

</td>
<td width="50%">

### 🛠️ DevSecOps & CI/CD Quality Gating
Standalone CLI tool (`cli.py`) and GitHub Actions workflow for pull request quality gating (`--min-score 75`, `--fail-on-sec`, JSON/Markdown reports).

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Step 1 — Clone the repository

```bash
git clone https://github.com/asarthak2304/CodeSense-AI-Based-Code-Quality-Analyzer
cd CodeSense-AI-Based-Code-Quality-Analyzer
```

### Step 2 — Create and activate virtual environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

```bash
# Copy template
cp .env.example .env
```

Edit `.env` to configure your `SECRET_KEY` and optional email SMTP settings:
```env
SECRET_KEY=your-secure-random-key-min-32-chars-long
ENVIRONMENT=development

# Optional: For live email OTP delivery
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-char-gmail-app-password
FROM_EMAIL=your-email@gmail.com
```

### Step 5 — Train the ML Model (Optional)

```bash
python train_model.py --samples 10000
```

This runs once and saves the model to `models/`. Takes about 30-60 seconds. You'll see output like:

```
Generating 10000 training samples...
Running 10-fold cross-validation...
CV R²: 0.923 ± 0.008  ✅ PASSED
Model saved to models/codesense_model.pkl
```

*(Note: If skipped, CodeSense automatically self-trains and caches the model on first launch).*

### Step 6 — Launch CodeSense 🎉

```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501** — use the **"🚀 Try Demo"** button for instant access, or create an account!

---

## 🏗️ How it Works

```
User Code (Paste / Upload / GitHub)
    │
    ├──► 1. Syntax Analyzer     (AST + Tokenizer, finds parse issues)
    ├──► 2. Semantic Analyzer   (Lexical scope, unused vars/imports, dead code)
    ├──► 3. Static Analyzer     (Complexity, PEP 8 / style rules, 50+ security patterns)
    ├──► 4. DSA Detector        (Pattern matching for 40+ algorithms & Big-O bounds)
    └──► 5. Context Engine      (Code intent: test suite, script, or algorithm)
                │
                ▼
         Feature Extractor
         (Transforms analysis into 33 numerical features)
                │
                ▼
         ML Model (RandomForestRegressor Pipeline + RobustScaler)
                │
                ▼
         Quality Score (0–100) + Grade (A+ to F) + Confidence Interval
                │
                ▼
         Code Fixer & Feedback Engine
         (Generates diffs, structured explanations & learning roadmap)
```

---

## 📊 The 33 Engineered Features

The ML model consumes 33 normalized features across 6 distinct categories:

| Category | Count | Key Features |
| :--- | :---: | :--- |
| **Basic Metrics** | 8 | Lines of code, comment lines, comment ratio, average line length, function count, class count |
| **Complexity** | 6 | Cyclomatic complexity (avg & max), cognitive complexity, nesting depth, function length |
| **Style & Quality** | 5 | Naming consistency score, long line ratio, magic numbers, docstring ratio, average parameters |
| **Security** | 4 | Total issues, critical issues, high issues, input validation presence |
| **Data Structures & Algorithms** | 3 | DSA complexity score, algorithm count, data structure count |
| **Maintainability & Context** | 7 | Code duplication, exception handling coverage, test coverage, reusability, design patterns, code smells, technical debt minutes |

---

## 🔒 Security & Authentication

### Application Security:
- **Email-Based 6-Digit OTP:** Generates cryptographically secure, time-expiring (10 min) numeric verification codes delivered via SMTP to any user email.
- **Local Dev / Demo Fallback:** If SMTP is unconfigured, CodeSense automatically allows instant testing with on-screen verification.
- **bcrypt Password Hashing:** Uses 12 salt rounds with constant-time verification.
- **Brute-Force Lockout:** Automatically locks accounts for 30 minutes after 5 failed login attempts.
- **Session Tokens:** 48-byte cryptographically secure URL-safe tokens stored in SQLite with TTL enforcement.
- **Parameterized SQL:** All queries use parameterized statements to eliminate SQL injection.

### Code Security Scanner:
- Detects SQL injection, command injection, raw shell calls (`os.system`, `subprocess(shell=True)`).
- Hardcoded secrets, passwords, tokens, API keys.
- Broken cryptography (MD5, SHA1, non-cryptographic `random`).
- Insecure deserialization (`pickle`, `yaml.load` without SafeLoader).
- Unsafe memory functions in C++ (`gets`, `strcpy`, `sprintf`, double-free).

---

## 🤖 ML Model Architecture

- **Model Type:** `RandomForestRegressor` (150 estimators, max depth 16, min samples leaf 3)
- **Data Scaling:** `RobustScaler` (handles outliers and non-normal distributions)
- **Validation:** 10-fold cross-validation (`R² ≥ 0.95`, `MAE ≤ 1.62`, `RMSE ≤ 2.05`)
- **Confidence Interval:** Estimated per prediction via standard deviation across all individual tree predictions.
- **Contextual Adjustment:** Bounded ±5 points modifier for clean scripts, algorithmic excellence, and verified docstring coverage.

---

## 📁 Project Structure

```
CodeSense/
├── 📱 app.py                 ← Main Streamlit multi-page application
├── 💻 cli.py                 ← Standalone DevSecOps CLI tool for CI/CD pipelines
├── 🔍 analyzer.py            ← Static analysis & security pattern engine
├── 🧠 dsa_detector.py        ← Algorithm & Big-O complexity detector
├── 📊 features.py            ← 33-feature extraction engine
├── 🤖 train_model.py         ← ML training, cross-validation & inference
├── 💬 student_feedback.py    ← Personalized feedback & learning path generator
├── ⚠️  syntax_analyzer.py    ← AST & tokenizer syntax diagnostic engine
├── 🔬 semantic_analyzer.py   ← Scope, variable & dead code analyzer
├── 🌍 context_engine.py      ← Code intent classifier
├── 🔧 code_fixer.py          ← Auto-fix suggestion & diff generator
├── 🎨 ui_components.py       ← Modern responsive UI components & dark theme
│
├── 🗄️  db.py                 ← SQLite interface (WAL mode & thread-local pooling)
├── 🔐 auth.py                ← Authentication, bcrypt & OTP delivery
├── ⚡ cache.py               ← Two-tier LRU memory + disk cache
├── ✅ validators.py          ← Input sanitization & code validation
├── 🛠️  utils.py              ← GitHub integration, timing & direct PDF exports
├── 📝 logger.py              ← Structured logging
├── ⚙️  config.py             ← Configuration & secrets management
├── 📌 constants.py           ← Global thresholds, colors & constants
│
├── 📁 .github/workflows/     ← GitHub Actions CI quality check workflow
├── 📁 .streamlit/            ← Streamlit server configuration
├── 📁 models/                ← Model binaries & metadata
├── 📁 tests/                 ← Unit & regression test suite
├── 📁 logs/                  ← Application runtime logs
├── 📁 cache/                 ← Disk cache storage
│
├── 📋 requirements.txt       ← Pinned project dependencies
├── 🔒 .env.example           ← Environment variables template
└── 📄 README.md              ← Project documentation
```

---

## 🛠️ DevSecOps CLI & CI/CD Pipeline

CodeSense includes a standalone CLI tool (`cli.py`) for integrating code quality and security gating into CI/CD workflows:

```bash
# Basic file analysis
python cli.py path/to/script.py

# Quality gating with minimum score requirement
python cli.py path/to/script.py --min-score 75

# Strict security gating (fails build on any critical/high security finding)
python cli.py path/to/script.py --fail-on-sec

# Output structured JSON or Markdown for CI summary
python cli.py path/to/script.py --format json --output report.json
python cli.py path/to/script.py --format markdown --output audit.md
```

---

## 🧪 Testing

Run the automated test suite:

```bash
# Run all unit and DevSecOps tests
python tests/test_suite_enhanced.py
```

---

## 📚 Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend & UI** | Streamlit, HTML5, Vanilla CSS, Ace Editor | Fast, modern web interface with VS Code dark editor |
| **Reporting & Export** | fpdf2, Plotly | Direct binary PDF audit certificates and interactive analytics |
| **Machine Learning** | scikit-learn, NumPy, Pandas, Joblib | Random Forest regression model & feature engineering |
| **Database** | SQLite (WAL Mode) | Persistent user analyses, session tracking, and achievements |
| **Security** | bcrypt, secrets, smtplib | Secure password hashing, session tokens, and OTP delivery |
| **DevSecOps & CI/CD** | GitHub Actions, Python CLI | Automated pull request scoring and security quality gating |
| **Code Parsing** | Python AST, tokenize | Native abstract syntax tree parsing and lexical analysis |

---

## 🙏 Acknowledgements

- My project guide for not giving up on me when I showed up with "I'll just use cyclomatic complexity as the score" in month 2
- [Big-O Cheat Sheet](https://www.bigocheatsheet.com) — referenced constantly
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — for the security patterns
- [Streamlit docs](https://docs.streamlit.io) — surprisingly good docs
- Stack Overflow — obviously

---

## 👥 Authors

* **Shivam Jaiswal** — B.Tech CSE, Final Year
* **Sarthak Agrawal** — B.Tech CSE, Final Year
* **Yash Sharma** — B.Tech CSE, Final Year
* **Tanishq Kumar** — B.Tech CSE, Final Year

⭐ **Star this repository if you found it helpful!** ⭐