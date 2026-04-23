#prediction_service001.py
import importlib
import os
import model.account_model
import model.card_model

importlib.reload(model.account_model)
importlib.reload(model.card_model)

from model.account_model import load_models, predict_account
from model.card_model import predict as predict_card

# Get absolute path to saved_models relative to this file
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_MODELS_PATH = os.path.join(SERVICE_DIR, "..", "saved_models")

# Load models ONCE (singleton style)
account_models = load_models(SAVED_MODELS_PATH)


# =========================
# ACCOUNT PREDICTION
# =========================
def predict_account_service(account_df):
    return predict_account(account_df, account_models)


    
# =========================
# CARD PREDICTION
# =========================
def predict_card_service(card_df):
    return predict_card(card_df)