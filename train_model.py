"""
CodeSense - ML Model Training
Production-grade RandomForest model with R² ≥ 0.90, cross-validation, and versioning.
The ML model score IS the primary quality score — no hardcoded overrides.
"""

import json
import math
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold, cross_val_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import RobustScaler
    _HAS_SKLEARN = True
except ImportError:
    RandomForestRegressor = None
    Pipeline = None
    _HAS_SKLEARN = False

from constants import (
    FEATURE_NAMES, MODEL_FILENAME, NUM_FEATURES,
    TARGET_R2, CROSS_VAL_FOLDS, MIN_SAMPLES_TRAIN,
)
from logger import get_logger

logger = get_logger(__name__)


# ─── Synthetic Data Generation ────────────────────────────────────────────────

def _generate_sample(rng: np.random.Generator) -> Tuple[np.ndarray, float]:
    """
    Generate one realistic (features, score) training sample.
    The score is derived entirely from feature values — no arbitrary labels.
    """
    # Feature sampling with realistic distributions
    loc = float(rng.integers(10, 500))
    blank = float(rng.integers(0, int(loc * 0.2) + 1))
    comment = float(rng.integers(0, int(loc * 0.4) + 1))
    comment_ratio = round(comment / max(1, loc), 3)
    avg_ll = float(rng.uniform(20, 100))
    max_ll = float(avg_ll + rng.uniform(0, 80))
    num_fns = float(rng.integers(0, 30))
    num_cls = float(rng.integers(0, 5))

    avg_cc = float(rng.uniform(1, 15))
    max_cc = float(avg_cc + rng.uniform(0, 20))
    avg_cog = float(avg_cc * rng.uniform(0.8, 2.5))
    max_nest = float(rng.integers(0, 8))
    avg_fn_len = float(rng.uniform(5, 80))
    max_fn_len = float(avg_fn_len + rng.uniform(0, 100))

    naming = float(rng.uniform(0.3, 1.0))
    ll_ratio = float(rng.uniform(0, 0.3))
    magic_n = float(rng.integers(0, 20))
    doc_ratio = float(rng.uniform(0, 1.0))
    avg_params = float(rng.uniform(0, 8))

    sec_count = float(rng.integers(0, 10))
    crit_sec = float(rng.integers(0, min(3, int(sec_count) + 1)))
    high_sec = float(rng.integers(0, min(5, int(sec_count) + 1)))
    has_validation = float(rng.choice([0, 1], p=[0.4, 0.6]))

    dsa_score = float(rng.uniform(0, 1))
    algo_cnt = float(rng.integers(0, 5))
    ds_cnt = float(rng.integers(0, 5))

    dup_score = float(rng.uniform(0, 0.5))
    exc_cov = float(rng.uniform(0, 1))
    test_cov = float(rng.uniform(0, 1))
    reuse = float(rng.uniform(0.2, 1.0))
    dp_usage = float(rng.uniform(0, 1))
    smell_cnt = float(rng.integers(0, 15))
    # Tech debt calculation matching features.py
    tech_debt = float(crit_sec * 60 + high_sec * 30 + (max(0, max_cc - 10) * 5) + (magic_n * 5) + (0 if doc_ratio >= 0.2 else (0.2 - doc_ratio) * 100))

    features = np.array([
        loc, blank, comment, comment_ratio, avg_ll, max_ll, num_fns, num_cls,
        avg_cc, max_cc, avg_cog, max_nest, avg_fn_len, max_fn_len,
        naming, ll_ratio, magic_n, doc_ratio, avg_params,
        sec_count, crit_sec, high_sec, has_validation,
        dsa_score, algo_cnt, ds_cnt,
        dup_score, exc_cov, test_cov, reuse, dp_usage, smell_cnt, tech_debt,
    ], dtype=np.float32)

    # ── Score formula (ground-truth labels) ──────────────────────────────────
    #   Each component scored 0–100 then weighted.
    fn_len_penalty = max(0.0, max_fn_len - 40.0) * 0.4
    score_complexity  = max(0.0, 100.0 - (max(0.0, avg_cc - 2.0) * 4.0) - (max(0.0, max_nest - 1.0) * 5.0) - fn_len_penalty)
    score_security    = max(0.0, 100.0 - crit_sec * 20.0 - high_sec * 10.0 - (sec_count - crit_sec - high_sec) * 3.0)
    score_style       = (naming * 30.0) + (max(0.0, 1.0 - ll_ratio) * 20.0) + \
                        (max(0.0, 1.0 - magic_n / 20.0) * 15.0) + (doc_ratio * 35.0)
    score_maintainability = (reuse * 35.0) + (exc_cov * 25.0) + (dp_usage * 30.0) + (test_cov * 10.0)
    # DSA: Baseline is 95.0 (standard optimal built-in data structures/primitives), with bonus up to 100 for advanced algorithms
    score_dsa = 95.0 + (dsa_score * 5.0)

    final = (
        score_complexity      * 0.30 +
        score_security        * 0.25 +
        score_style           * 0.25 +
        score_maintainability * 0.15 +
        score_dsa             * 0.05
    )
    final += float(rng.normal(0, 1.0))   # Realistic subtle variance
    final = float(np.clip(final, 0, 100))

    return features, final


def generate_training_data(n: int = 10000, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """Generate n (features, score) training samples."""
    rng = np.random.default_rng(seed)
    X, y = [], []
    for _ in range(n):
        feat, score = _generate_sample(rng)
        X.append(feat)
        y.append(score)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ─── Model Training ──────────────────────────────────────────────────────────

def train(n_samples: int = 10000, save: bool = True) -> Dict:
    """
    Train the pure RandomForest model and save to disk.

    Returns:
        Training metrics dictionary.
    """
    logger.info("Generating %d training samples...", n_samples)
    X, y = generate_training_data(n=n_samples)

    # ── Pure Random Forest Model ─────────────────────────────────────────────
    # Optimized tree depth and sample leaf counts to maximize generalization
    # while drastically reducing uncompressed model weight.
    rf = RandomForestRegressor(
        n_estimators=150,
        max_depth=16,
        min_samples_split=4,
        min_samples_leaf=3,
        max_features="sqrt",
        bootstrap=True,
        oob_score=True,
        n_jobs=-1,
        random_state=42,
    )

    pipeline = Pipeline([
        ("scaler", RobustScaler()),
        ("model",  rf),
    ])

    # ── Cross-validation ─────────────────────────────────────────────────────
    logger.info("Running %d-fold cross-validation...", CROSS_VAL_FOLDS)
    kf     = KFold(n_splits=CROSS_VAL_FOLDS, shuffle=True, random_state=42)
    cv_r2  = cross_val_score(pipeline, X, y, cv=kf, scoring="r2", n_jobs=-1)
    cv_mae = cross_val_score(pipeline, X, y, cv=kf, scoring="neg_mean_absolute_error", n_jobs=-1)

    logger.info("CV R²: %.4f ± %.4f", cv_r2.mean(), cv_r2.std())
    logger.info("CV MAE: %.4f ± %.4f", -cv_mae.mean(), cv_mae.std())

    # ── Final fit on all data ─────────────────────────────────────────────────
    t0 = time.time()
    pipeline.fit(X, y)
    train_time = time.time() - t0

    y_pred = pipeline.predict(X)
    r2  = r2_score(y, y_pred)
    mae = mean_absolute_error(y, y_pred)
    rmse = math.sqrt(mean_squared_error(y, y_pred))
    oob = getattr(rf, "oob_score_", None)

    logger.info("Train R²=%.4f  MAE=%.2f  RMSE=%.2f  OOB=%.4f  time=%.1fs",
                r2, mae, rmse, oob or 0.0, train_time)

    if r2 < TARGET_R2:
        logger.warning("R² %.4f below target %.2f — consider more samples or tuning.", r2, TARGET_R2)

    # Feature importance dictionary
    importances = {
        name: round(float(imp), 4)
        for name, imp in zip(FEATURE_NAMES, rf.feature_importances_)
    }
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    metrics = {
        "model_type":   "RandomForestRegressor",
        "r2":           round(float(r2), 4),
        "mae":          round(float(mae), 4),
        "rmse":         round(float(rmse), 4),
        "oob_score":    round(float(oob), 4) if oob else None,
        "cv_r2_mean":   round(float(cv_r2.mean()), 4),
        "cv_r2_std":    round(float(cv_r2.std()), 4),
        "cv_mae_mean":  round(float(-cv_mae.mean()), 4),
        "n_samples":    n_samples,
        "n_features":   NUM_FEATURES,
        "trained_at":   datetime.utcnow().isoformat(),
        "target_r2":    TARGET_R2,
        "passed":       r2 >= TARGET_R2,
        "top_features": sorted_importances,
    }

    if save:
        _save_model(pipeline, metrics)

    return metrics


def _save_model(pipeline: Pipeline, metrics: Dict) -> None:
    Path(MODEL_FILENAME).parent.mkdir(parents=True, exist_ok=True)
    try:
        import joblib
        joblib.dump(pipeline, MODEL_FILENAME, compress=("zlib", 3))
    except Exception:
        with open(MODEL_FILENAME, "wb") as f:
            pickle.dump(pipeline, f, protocol=5)
    # Save feature names for reference
    feat_path = MODEL_FILENAME.replace(".pkl", "_features.json")
    with open(feat_path, "w") as f:
        json.dump(FEATURE_NAMES, f, indent=2)
    # Save metrics and importance
    meta_path = MODEL_FILENAME.replace(".pkl", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Compressed Random Forest model saved to %s", MODEL_FILENAME)


# ─── Inference ───────────────────────────────────────────────────────────────


class QualityPredictor:
    """
    Loads the trained model and predicts code quality scores.
    The ML score IS the primary quality score.
    Max contextual adjustment is ±MAX_SCORE_ADJUSTMENT points.
    """

    from constants import MAX_SCORE_ADJUSTMENT

    def __init__(self, model_path: str = MODEL_FILENAME) -> None:
        self.pipeline: Optional[Pipeline] = None
        self.model_path = model_path
        self._load()

    def _load(self) -> None:
        if Path(self.model_path).exists():
            try:
                import joblib
                self.pipeline = joblib.load(self.model_path)
                logger.info("Model loaded from %s via joblib", self.model_path)
            except Exception:
                try:
                    with open(self.model_path, "rb") as f:
                        self.pipeline = pickle.load(f)
                    logger.info("Model loaded from %s via pickle", self.model_path)
                except Exception as exc:
                    logger.warning("Failed to load model: %s — will train on first use.", exc)
        else:
            logger.info("No trained model found at %s", self.model_path)

    def ensure_model(self) -> None:
        """Train and save model if it doesn't exist."""
        if self.pipeline is None:
            logger.info("Training model (first-time setup)...")
            train(n_samples=MIN_SAMPLES_TRAIN)
            self._load()

    def predict(
        self,
        feature_array: np.ndarray,
        contextual_adjustments: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Predict quality score.

        Args:
            feature_array:           1D array of NUM_FEATURES features.
            contextual_adjustments:  Optional ±MAX_SCORE_ADJUSTMENT adjustment.

        Returns:
            (final_score, confidence_interval_half_width)
        """
        self.ensure_model()

        X = feature_array.reshape(1, -1)

        if self.pipeline is not None:
            # PRIMARY score from ML model
            ml_score = float(self.pipeline.predict(X)[0])
            confidence = self._estimate_confidence(X)
        else:
            # Fallback heuristic calculation if scikit-learn pipeline is unavailable
            ml_score = self._heuristic_score(feature_array)
            confidence = 3.0

        # Bounded contextual adjustment
        adj = float(np.clip(contextual_adjustments,
                            -self.MAX_SCORE_ADJUSTMENT,
                            +self.MAX_SCORE_ADJUSTMENT))
        final = float(np.clip(ml_score + adj, 0, 100))

        return round(final, 1), round(confidence, 1)

    def _heuristic_score(self, f: np.ndarray) -> float:
        avg_cc = f[8]
        max_nest = f[11]
        max_fn_len = f[13]
        naming = f[14]
        ll_ratio = f[15]
        magic_n = f[16]
        doc_ratio = f[17]
        sec_count = f[19]
        crit_sec = f[20]
        high_sec = f[21]
        dsa_score = f[23]
        dup_score = f[26]
        exc_cov = f[27]
        test_cov = f[28]
        reuse = f[29]
        smell_cnt = f[31]

        score_complexity = max(0.0, 100.0 - avg_cc * 4 - max_nest * 5 - max_fn_len * 0.3)
        score_security = max(0.0, 100.0 - crit_sec * 20 - high_sec * 10 - (sec_count - crit_sec - high_sec) * 3)
        score_style = (naming * 40) + (max(0.0, 1.0 - ll_ratio) * 20) + (max(0.0, 1.0 - magic_n / 20) * 20) + (doc_ratio * 20)
        score_maintainability = (reuse * 30) + (exc_cov * 20) + (test_cov * 30) + (max(0.0, 1.0 - smell_cnt / 15) * 20)
        score_dsa = dsa_score * 100
        return float(score_complexity * 0.30 + score_security * 0.25 + score_style * 0.20 + score_maintainability * 0.15 + score_dsa * 0.10)

    def _estimate_confidence(self, X: np.ndarray) -> float:
        """
        Estimate ± confidence interval using individual tree predictions
        directly from the Random Forest regressor.
        """
        try:
            model_step = self.pipeline.named_steps["model"]
            rf = model_step if hasattr(model_step, "estimators_") else dict(model_step.estimators_)["rf"]
            X_scaled = self.pipeline.named_steps["scaler"].transform(X)
            preds = np.array([tree.predict(X_scaled)[0] for tree in rf.estimators_])
            return float(np.std(preds))
        except Exception as exc:
            logger.debug("Confidence estimation error: %s", exc)
            return 3.0   # Default ±3 confidence

    def get_model_meta(self) -> Dict:
        meta_path = self.model_path.replace(".pkl", "_meta.json")
        if Path(meta_path).exists():
            with open(meta_path) as f:
                return json.load(f)
        return {}


_GLOBAL_PREDICTOR: Optional[QualityPredictor] = None


def get_predictor(model_path: str = MODEL_FILENAME) -> QualityPredictor:
    """Return a cached singleton QualityPredictor instance."""
    global _GLOBAL_PREDICTOR
    if _GLOBAL_PREDICTOR is None:
        _GLOBAL_PREDICTOR = QualityPredictor(model_path)
    return _GLOBAL_PREDICTOR


# ─── Contextual Adjustments ──────────────────────────────────────────────────

def calculate_contextual_adjustments(
    analysis: Dict,
    dsa: Dict,
    language: str,
) -> float:
    """
    Compute a ±MAX_SCORE_ADJUSTMENT contextual bonus/penalty.
    This is the ONLY source of adjustment on top of the ML score.
    """
    from constants import MAX_SCORE_ADJUSTMENT
    adj = 0.0

    # Bonus: high-complexity algorithm detected with good complexity
    dsa_summary = dsa.get("summary", {})
    if dsa_summary.get("complexity_score", 0) > 70:
        adj += 1.0

    # Penalty: critical or high security issues
    sec = analysis.get("security", {})
    adj -= min(3.0, sec.get("counts", {}).get("CRITICAL", 0) * 1.5)
    adj -= min(2.0, sec.get("counts", {}).get("HIGH", 0) * 0.8)

    # Bonus: zero security vulnerabilities
    if sec.get("total_issues", 0) == 0:
        adj += 1.0

    # Bonus: clean control flow & short script / snippet
    cx = analysis.get("complexity", {})
    metrics = analysis.get("metrics", {})
    if metrics.get("code_lines", 100) < 15 and sec.get("total_issues", 0) == 0 and cx.get("avg_complexity", 10) <= 2.0:
        adj += 2.5
    elif cx.get("avg_complexity", 10) <= 4.0:
        adj += 1.0

    # Bonus: well-documented code (docstrings)
    doc = analysis.get("documentation", {})
    ratio = doc.get("docstring_ratio", doc.get("comment_ratio", 0))
    if ratio >= 0.8:
        adj += 1.5
    elif ratio >= 0.5:
        adj += 0.8

    return float(np.clip(adj, -MAX_SCORE_ADJUSTMENT, MAX_SCORE_ADJUSTMENT))


# ─── Grade Calculation ────────────────────────────────────────────────────────

def score_to_grade(score: float) -> str:
    from constants import GRADE_THRESHOLDS
    for grade, threshold in sorted(GRADE_THRESHOLDS.items(),
                                   key=lambda x: x[1], reverse=True):
        if score >= threshold:
            return grade
    return "F"


def score_to_label(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Average"
    if score >= 40:
        return "Below Average"
    return "Poor"


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train CodeSense ML model")
    parser.add_argument("--samples", type=int, default=10000,
                        help="Number of training samples (default: 10000)")
    parser.add_argument("--no-save", action="store_true", help="Don't save model")
    args = parser.parse_args()

    metrics = train(n_samples=args.samples, save=not args.no_save)
    print("\n--- Training Results ----------------------------------")
    for k, v in metrics.items():
        print(f"  {k:<20} {v}")
    status = "PASSED (R2 >= TARGET)" if metrics["passed"] else "BELOW TARGET"
    print(f"\n  Target R2 >= {TARGET_R2}   ->  {status}")