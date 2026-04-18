# KisanAlert alerts package
from src.alerts.alert_engine import generate_alert, classify_signal
from src.alerts.edge_handler import generate_safe_alert
from src.alerts.trust_badge import (
    log_prediction,
    verify_predictions,
    get_accuracy_stats,
    get_recent_predictions,
    format_trust_badge_marathi,
    format_trust_badge_english,
)
