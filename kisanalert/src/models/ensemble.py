# -*- coding: utf-8 -*-
"""
Ensemble Formula — v2 (dual-model, 4-signal)

Weights:
  crash_score = 0.60 × xgb_crash + 0.30 × lstm + 0.10 × rule_score
  rise_score  = 1.00 × xgb_rise  (LSTM only trained for crash)

Hard overrides (rule engine):
  If rule_engine fires RED → crash_score forced to 1.0

Models:
  Crash: xgb_v3_best.json    (AUC 0.76 — no leakage)
  Rise : xgb_blue_signal.json (AUC 0.70)
  LSTM : lstm_v1.h5 / lstm_soybean.keras

Graceful degradation:
  - LSTM unavailable (sentinel -1.0) → renormalise crash: 0.857×XGB + 0.143×rule
  - Rise model unavailable           → rise_score = None (BLUE disabled)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Maps Rule Engine override_level → numeric rule_score
_RULE_SCORE_MAP: dict = {
    "RED"  : 1.0,
    "AMBER": 0.5,
    "GREEN": 0.0,
    None   : 0.0,
}

# Default ensemble weights (v2 blueprint)
_DEFAULT_XGB_CRASH_WEIGHT  = 0.60
_DEFAULT_LSTM_WEIGHT        = 0.30
_DEFAULT_RULE_WEIGHT        = 0.10


def override_to_rule_score(override_level: Optional[str]) -> float:
    """Convert Rule Engine override level string to a numeric score [0, 1]."""
    return _RULE_SCORE_MAP.get(override_level, 0.0)


def ensemble_score(
    xgb_prob    : float,
    lstm_prob   : float,
    rule_score  : float = 0.0,
    xgb_weight  : Optional[float] = None,
    lstm_weight : Optional[float] = None,
    rule_weight : Optional[float] = None,
) -> tuple[float, str]:
    """
    Combine XGBoost crash prob, LSTM crash prob, and rule score into
    a single final crash_score.

    Blueprint:  crash_score = 0.60×XGB + 0.30×LSTM + 0.10×rule

    Args:
        xgb_prob   : XGBoost crash probability [0, 1].
        lstm_prob  : LSTM crash probability [0, 1], or -1.0 if unavailable.
        rule_score : Numeric rule score: 1.0=RED, 0.5=AMBER, 0.0=none.
        xgb_weight : Override α (default 0.60).
        lstm_weight: Override β (default 0.30).
        rule_weight: Override γ (default 0.10).

    Returns:
        (final_crash_score, method_used)
        method_used ∈ {"ensemble", "xgb_rule_only", "xgb_only"}
    """
    alpha = xgb_weight  if xgb_weight  is not None else _DEFAULT_XGB_CRASH_WEIGHT
    beta  = lstm_weight if lstm_weight is not None else _DEFAULT_LSTM_WEIGHT
    gamma = rule_weight if rule_weight is not None else _DEFAULT_RULE_WEIGHT

    # Clamp inputs
    xgb_prob   = float(min(max(xgb_prob,  0.0), 1.0))
    rule_score = float(min(max(rule_score, 0.0), 1.0))

    if lstm_prob < 0:
        # ── LSTM unavailable — renormalise α and γ only ─────────────────────
        total = alpha + gamma
        if total == 0:
            log.warning("Ensemble: all weights zero — defaulting to xgb_prob.")
            return xgb_prob, "xgb_only"

        alpha_n = alpha / total
        gamma_n = gamma / total
        final = alpha_n * xgb_prob + gamma_n * rule_score

        log.info(
            "Ensemble (xgb_rule_only): α=%.2f×xgb(%.4f) + γ=%.2f×rule(%.2f) = %.4f",
            alpha_n, xgb_prob, gamma_n, rule_score, final,
        )
        return final, "xgb_rule_only"

    # ── Full 3-component ensemble ─────────────────────────────────────────────
    lstm_prob_clamped = float(min(max(lstm_prob, 0.0), 1.0))

    total   = alpha + beta + gamma
    alpha_n = alpha / total
    beta_n  = beta  / total
    gamma_n = gamma / total

    final = alpha_n * xgb_prob + beta_n * lstm_prob_clamped + gamma_n * rule_score

    log.info(
        "Ensemble: α=%.2f×xgb(%.4f) + β=%.2f×lstm(%.4f) + γ=%.2f×rule(%.2f) = %.4f",
        alpha_n, xgb_prob, beta_n, lstm_prob_clamped, gamma_n, rule_score, final,
    )
    return final, "ensemble"


def compute_rise_score(features_row, rise_model_path: Optional[str] = None) -> Optional[float]:
    """
    Run the BLUE rise model to get rise probability.

    Args:
        features_row      : pd.DataFrame shape (1, n_features).
        rise_model_path   : Path to xgb_blue_signal.json. Defaults to config.

    Returns:
        rise_score ∈ [0, 1], or None if model unavailable.
    """
    try:
        import config
        path = Path(rise_model_path or (config.MODELS_DIR / "xgb_blue_signal.json"))
        if not path.exists():
            log.warning("Rise model not found at %s — BLUE signal disabled.", path)
            return None

        import xgboost as xgb
        m = xgb.XGBClassifier()
        m.load_model(str(path))
        score = float(m.predict_proba(features_row)[0, 1])
        log.info("Rise score: %.4f", score)
        return score
    except Exception as e:
        log.warning("Rise model inference failed: %s", e)
        return None


def predict(
    features_row,
    lstm_prob   : float = -1.0,
    rule_score  : float = 0.0,
    rule_reason : Optional[str] = None,
) -> dict:
    """
    Full dual-model ensemble prediction.

    Returns:
        {
            "crash_score"   : float,
            "rise_score"    : float | None,
            "rule_triggered": bool,
            "rule_reason"   : str | None,
            "method"        : str,
        }
    """
    import config
    import xgboost as xgb

    # ── Crash model ───────────────────────────────────────────────────────────
    crash_path = config.MODELS_DIR / "xgb_v3_best.json"
    if not crash_path.exists():
        raise FileNotFoundError(f"Crash model missing: {crash_path}. Run fix_auc_v2.py.")

    crash_model = xgb.XGBClassifier()
    crash_model.load_model(str(crash_path))
    xgb_crash = float(crash_model.predict_proba(features_row)[0, 1])

    # ── Rise model ────────────────────────────────────────────────────────────
    rise_score = compute_rise_score(features_row)

    # ── Rule override → hard ceiling ─────────────────────────────────────────
    rule_triggered = rule_score >= 1.0
    if rule_triggered:
        log.info("Rule engine fired — forcing crash_score = 1.0")
        return {
            "crash_score"   : 1.0,
            "rise_score"    : rise_score,
            "rule_triggered": True,
            "rule_reason"   : rule_reason,
            "method"        : "rule_override",
        }

    # ── Ensemble ──────────────────────────────────────────────────────────────
    crash_score, method = ensemble_score(
        xgb_prob   = xgb_crash,
        lstm_prob  = lstm_prob,
        rule_score = rule_score,
    )

    return {
        "crash_score"   : round(crash_score, 4),
        "rise_score"    : round(rise_score, 4) if rise_score is not None else None,
        "rule_triggered": False,
        "rule_reason"   : None,
        "method"        : method,
    }
