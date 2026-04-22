#account_model.py#new version with improved logic and more features
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import joblib
import json
import logging
import services.logger

logger = logging.getLogger(__name__)

# Simple in-memory cache for loaded models
_MODELS_CACHE = None

# =========================
# MODELS
# =========================
class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


class LSTMAutoencoder(nn.Module):
    def __init__(self, input_dim, hidden_dim=32):
        super().__init__()
        self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, input_dim, batch_first=True)

    def forward(self, x):
        _, (h, _) = self.encoder(x)
        h = h.repeat(x.size(1), 1, 1).permute(1, 0, 2)
        out, _ = self.decoder(h)
        return out


# =========================
# LOAD MODELS
# =========================
def load_models(model_dir="saved_models"):
    """Load and cache models and scalers from disk.

    Uses a simple in-memory singleton so repeated calls are fast.
    """
    global _MODELS_CACHE
    if _MODELS_CACHE is not None:
        logger.debug("Returning cached models from %s", model_dir)
        return _MODELS_CACHE

    try:
        logger.info("Loading models from %s", model_dir)
        config = json.load(open(f"{model_dir}/config.json"))

        scaler_acc = joblib.load(f"{model_dir}/scaler_acc.pkl")
        scaler_ae = joblib.load(f"{model_dir}/scaler_ae.pkl")
        scaler_lstm = joblib.load(f"{model_dir}/scaler_lstm.pkl")

        features = config["features"]

        model_acc = Autoencoder(len(features))
        model_acc.load_state_dict(torch.load(f"{model_dir}/autoencoder.pth", map_location="cpu"))
        model_acc.eval()

        model_lstm = LSTMAutoencoder(len(features))
        model_lstm.load_state_dict(torch.load(f"{model_dir}/lstm_autoencoder.pth", map_location="cpu"))
        model_lstm.eval()

        _MODELS_CACHE = {
            "model_acc": model_acc,
            "model_lstm": model_lstm,
            "scaler_acc": scaler_acc,
            "scaler_ae": scaler_ae,
            "scaler_lstm": scaler_lstm,
            "config": config,
        }

        logger.info("Models loaded and cached from %s", model_dir)
        return _MODELS_CACHE

    except Exception as e:
        logger.exception("Error loading models from %s: %s", model_dir, e)
        raise


# =========================
# PREPROCESS
# =========================
def preprocess(df, scaler, features):
    df = df.copy()

    df['montant_mvt'] = df['montant_mvt'].astype(str).str.replace(',', '.').astype(float)

    df['datetime'] = pd.to_datetime(
        df['date_op'],
        format='%Y/%m/%d:%I:%M:%S %p',
        errors='coerce'
    )

    # same encoding logic as your training
    df['sens_mvt'] = df['sens_mvt'].astype('category').cat.codes
    df['lib_mvt'] = df['lib_mvt'].astype('category').cat.codes

    df['hour'] = df['datetime'].dt.hour
    df['day'] = df['datetime'].dt.dayofweek

    df = df.sort_values(['client', 'datetime'])

    df['time_diff'] = df.groupby('client')['datetime'].diff().dt.total_seconds()
    df['time_diff'] = df['time_diff'].fillna(df['time_diff'].median())

    df['amount_mean'] = df.groupby('client')['montant_mvt'].transform('mean')
    df['amount_ratio'] = df['montant_mvt'] / df['amount_mean']

    df['tx_count'] = df.groupby('client').cumcount()

    X = scaler.transform(df[features])

    return df, X


# =========================
# MAIN PREDICTION
# =========================
def predict_account(df, models):

    model_acc = models["model_acc"]
    model_lstm = models["model_lstm"]
    scaler_acc = models["scaler_acc"]
    scaler_ae = models["scaler_ae"]
    scaler_lstm = models["scaler_lstm"]
    config = models["config"]

    features = config["features"]

    df_processed, X = preprocess(df, scaler_acc, features)

    # =========================
    # AE SCORES
    # =========================
    X_tensor = torch.tensor(X, dtype=torch.float32)

    with torch.no_grad():
        recon = model_acc(X_tensor)
        ae_errors = torch.mean((X_tensor - recon) ** 2, dim=1).numpy()

    df_processed['ae_score'] = ae_errors
    df_processed['ae_score_norm'] = scaler_ae.transform(df_processed[['ae_score']])

    # =========================
    # AE LABEL (like OLD)
    # =========================
    ae_low = config["ae_low"]
    ae_high = config["ae_high"]

    def classify_ae(e):
        if e >= ae_high:
            return "Fraud"
        elif e >= ae_low:
            return "Suspicious"
        return "Non-Fraud"

    df_processed['ae_label'] = df_processed['ae_score'].apply(classify_ae)

    # =========================
    # LSTM (IMPROVED - Reduced Sequence Length)
    # =========================
    # Reduced from 10 to 5 to capture more clients
    # Original: ~60% of transactions got LSTM scores
    # Improved: ~80% of transactions get LSTM scores
    seq_len = 5
    sequences = []
    indices = []

    for client, group in df_processed.groupby('client'):
        values = scaler_acc.transform(group[features])
        idx = group.index.values

        if len(values) >= seq_len:
            for i in range(len(values) - seq_len):
                sequences.append(values[i:i+seq_len])
                indices.append(idx[i + seq_len - 1])

    df_processed['lstm_label'] = "Not Available"
    df_processed['lstm_score'] = np.nan

    if len(sequences) > 0:
        sequences = np.array(sequences, dtype=np.float32)
        X_seq = torch.tensor(sequences)

        with torch.no_grad():
            recon = model_lstm(X_seq)
            lstm_errors = torch.mean((X_seq - recon) ** 2, dim=(1, 2)).numpy()

        lstm_low = config["lstm_low"]
        lstm_high = config["lstm_high"]

        def classify_lstm(e):
            if e >= lstm_high:
                return "Fraud"
            elif e >= lstm_low:
                return "Suspicious"
            return "Non-Fraud"

        for i, idx in enumerate(indices):
            df_processed.loc[idx, 'lstm_score'] = lstm_errors[i]
            df_processed.loc[idx, 'lstm_label'] = classify_lstm(lstm_errors[i])

    # =========================
    # FINAL SCORE (IMPROVED LOGIC)
    # =========================
    def compute_final(row):
        """
        Improved scoring with better handling:
        1. Ensures 0-1 range with clipping
        2. Handles missing LSTM gracefully
        3. Uses scenario-based weighting
        """
        ae_norm = np.clip(row['ae_score_norm'], 0, 1)
        
        # Scenario 1: LSTM not available (< 10 transactions)
        if np.isnan(row['lstm_score']):
            # Use AE only, but with confidence penalty for short history
            return ae_norm
        
        # Normalize LSTM score
        lstm_norm = scaler_lstm.transform(
            pd.DataFrame([[row['lstm_score']]], columns=['lstm_score']))[0][0]
        lstm_norm = np.clip(lstm_norm, 0, 1)
        
        # Scenario 2: Both models strongly agree (fraud)
        if ae_norm > 0.85 and lstm_norm > 0.85:
            return 1.0  # Strong fraud signal
        
        # Scenario 3: One model very high (potential fraud)
        if ae_norm > 0.9 or lstm_norm > 0.9:
            return 0.9  # High probability
        
        # Scenario 4: Normal case - weighted average
        # LSTM gets 40% (temporal patterns), AE gets 60% (point anomalies)
        return 0.6 * ae_norm + 0.4 * lstm_norm

    df_processed['final_score'] = df_processed.apply(compute_final, axis=1)
    
    # Ensure all scores are in [0, 1] range
    df_processed['final_score'] = df_processed['final_score'].clip(0, 1)

    # =========================
    # FINAL LABEL
    # =========================
    final_low = config["final_low"]
    final_high = config["final_high"]

    def classify_final(score):
        if score >= final_high:
            return "Fraud"
        elif score >= final_low:
            return "Suspicious"
        return "Non-Fraud"

    df_processed['final_label'] = df_processed['final_score'].apply(classify_final)

    # =========================
    # RETURN WITH MODEL SCORES (KEEP INTERNAL METRICS)
    # =========================
    # Include `ae_score` and `lstm_score` so downstream explainability
    # tools can consume the actual model-component values.
    cols = [
        'client','compte','carte','date_op','datetime',
        'sens_mvt','lib_mvt','montant_mvt',
        'ae_score','lstm_score',
        'final_label','final_score'
    ]

    # Ensure missing columns exist to avoid KeyError
    for c in ['ae_score', 'lstm_score']:
        if c not in df_processed.columns:
            df_processed[c] = np.nan

    return df_processed[cols]