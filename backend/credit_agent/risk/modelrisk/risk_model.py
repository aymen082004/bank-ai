import os
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "best_loan_model (1).pkl")
SHAP_PATH = os.path.join(BASE_DIR, "shap_explainer (1).pkl")

# Charger pipeline
best_pipeline = joblib.load(MODEL_PATH)

# Charger explainer SHAP
try:
    shap_explainer = joblib.load(SHAP_PATH)
except Exception:
    shap_explainer = None