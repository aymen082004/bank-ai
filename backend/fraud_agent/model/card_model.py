# card_model.py
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import joblib
import json
import os
import logging
import services.logger

logger = logging.getLogger(__name__)

# =========================
# MODEL DEFINITIONS
# =========================
class LSTMAutoencoder(nn.Module):
    def __init__(self, input_dim, hidden_dim=32):
        super().__init__()
        self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, input_dim, batch_first=True)

    def forward(self, x):
        _, (hidden, _) = self.encoder(x)
        hidden = hidden.repeat(x.size(1), 1, 1).permute(1, 0, 2)
        output, _ = self.decoder(hidden)
        return output


class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


# =========================
# LOAD MODELS AND ARTIFACTS
# =========================
# Use proper path resolution instead of hardcoded paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models_card")

try:
    scaler_lstm = joblib.load(os.path.join(MODEL_DIR, "scaler_lstm.pkl"))
    scaler_ae = joblib.load(os.path.join(MODEL_DIR, "scaler_ae.pkl"))
    # Note: scaler_score.pkl is not used in prediction logic
    
    le_par = joblib.load(os.path.join(MODEL_DIR, "labelencoder_par.pkl"))
    le_acq = joblib.load(os.path.join(MODEL_DIR, "labelencoder_acq.pkl"))
    
    with open(os.path.join(MODEL_DIR, "features.json"), "r") as f:
        FEATURES = json.load(f)
    
    input_dim = len(FEATURES)
    
    model_lstm = LSTMAutoencoder(input_dim)
    model_lstm.load_state_dict(torch.load(os.path.join(MODEL_DIR, "lstm_autoencoder.pth"), map_location="cpu"))
    model_lstm.eval()
    
    model_ae = Autoencoder(input_dim)
    model_ae.load_state_dict(torch.load(os.path.join(MODEL_DIR, "autoencoder.pth"), map_location="cpu"))
    model_ae.eval()
    
    with open(os.path.join(MODEL_DIR, "thresholds.json"), "r") as f:
        THRESHOLDS = json.load(f)
    
    logger.info("Card models loaded from %s", MODEL_DIR)
    
except Exception as e:
    logger.exception("Error loading card models from %s: %s", MODEL_DIR, e)
    logger.debug("Working directory: %s", os.getcwd())
    raise


# =========================
# PREPROCESSING
# =========================
def preprocess(df):
    df = df.copy()
    df['mnt_autorise'] = df['mnt_autorise'].astype(str).str.replace(' ', '').str.replace(',', '.').astype(float)
    df['mnt_compense'] = df['mnt_compense'].astype(str).str.replace(' ', '').str.replace(',', '.').astype(float)

    df['datetime'] = pd.to_datetime(df['dat_trans'] + ' ' + df['time_trans'], dayfirst=True)
    df['hour'] = df['datetime'].dt.hour
    df['day'] = df['datetime'].dt.dayofweek
    df['is_large'] = df['mnt_autorise'] > df['mnt_autorise'].mean()

    df['time_diff'] = df.groupby('client')['datetime'].diff().dt.total_seconds()
    df['time_diff'] = df['time_diff'].fillna(df['time_diff'].median())

    df['amount_mean_client'] = df.groupby('client')['mnt_autorise'].transform('mean')
    df['amount_ratio'] = df['mnt_autorise'] / df['amount_mean_client']

    df['merchant_seen'] = df.groupby('client')['nom_term commercant'].transform(lambda x: x.duplicated()).astype(int)

    if df['cod_banq_par'].dtype == object:
        df['cod_banq_par'] = le_par.transform(df['cod_banq_par'])
    if df['cod_banq_acq'].dtype == object:
        df['cod_banq_acq'] = le_acq.transform(df['cod_banq_acq'])

    return df


# =========================
# PREDICTION
# =========================
def predict(df):
    df = preprocess(df)

    # Scale features
    X_lstm = scaler_lstm.transform(df[FEATURES])
    X_ae = scaler_ae.transform(df[FEATURES])

    # ---------- LSTM ----------
    sequence_length = 10
    sequences, indices = [], []

    for client in df['client'].unique():
        client_df = df[df['client'] == client].sort_values('datetime')
        values = client_df[FEATURES].values
        idx = client_df.index
        for i in range(len(values) - sequence_length):
            sequences.append(values[i:i+sequence_length])
            indices.append(idx[i + sequence_length - 1])

    df['lstm_label'] = "Not Available"
    df['lstm_score'] = np.nan

    if sequences:
        X_seq = torch.tensor(np.array(sequences, dtype=np.float32))
        with torch.no_grad():
            recon = model_lstm(X_seq)
            scores = torch.mean((X_seq - recon)**2, dim=(1,2)).numpy()

        low, high = THRESHOLDS['lstm_low'], THRESHOLDS['lstm_high']
        labels = ["Fraud" if s >= high else "Suspicious" if s >= low else "Non-Fraud" for s in scores]
        df.loc[indices, 'lstm_label'] = labels
        df.loc[indices, 'lstm_score'] = scores

    # ---------- Autoencoder ----------
    X_tensor = torch.tensor(X_ae, dtype=torch.float32)
    with torch.no_grad():
        recon = model_ae(X_tensor)
        ae_scores = torch.mean((X_tensor - recon)**2, dim=1).numpy()

    low, high = THRESHOLDS['ae_low'], THRESHOLDS['ae_high']
    df['ae_label'] = ["Fraud" if s >= high else "Suspicious" if s >= low else "Non-Fraud" for s in ae_scores]
    df['ae_score'] = ae_scores

    # ---------- FINAL SCORE ----------
    def safe_div(a, b):
        if b == 0 or pd.isna(a):
            return 0
        return a / b

    def compute_final_score(row):
        """
        Improved card scoring with better thresholds and handling.
        Ensures 0-1 normalized range.
        """
        ae = safe_div(row.get('ae_score', 0), THRESHOLDS['ae_high'])
        ae = np.clip(ae, 0, 1)  # Ensure 0-1 range
        
        lstm_score = row.get('lstm_score', np.nan)
        if pd.isna(lstm_score):
            lstm = 0
        else:
            lstm = safe_div(lstm_score, THRESHOLDS['lstm_high'])
        lstm = np.clip(lstm, 0, 1)  # Ensure 0-1 range
        
        # Scenario 1: Both models strongly agree (fraud)
        if ae > 0.85 and lstm > 0.85:
            return 1.0  # Strong fraud signal
        
        # Scenario 2: One model very high (potential fraud)
        if ae > 0.9 or lstm > 0.9:
            return 0.9  # High probability
        
        # Scenario 3: LSTM missing
        if pd.isna(lstm_score):
            return ae  # Use AE only
        
        # Scenario 4: Normal case - weighted average
        # AE=40% (card-specific point anomalies), LSTM=60% (temporal patterns)
        return 0.4 * ae + 0.6 * lstm

    df['final_score'] = df.apply(compute_final_score, axis=1)

    df['final_score'] = df['final_score'].fillna(0)
    # ---------- FINAL LABEL ----------
    low, high = THRESHOLDS['final_low'], THRESHOLDS['final_high']
    def classify_final(score):
        if score >= high:
            return "Fraud"
        elif score >= low:
            return "Suspicious"
        else:
            return "Non-Fraud"

    df['final_label'] = df['final_score'].apply(classify_final)
    # Return the main columns for consistency and include model scores
    # so explainability tools can compute feature contexts correctly.
    cols = ['client', 'dat_trans', 'time_trans', 'mnt_autorise', 'mnt_compense',
            'ae_score', 'lstm_score', 'final_score', 'final_label']

    for c in ['ae_score', 'lstm_score']:
        if c not in df.columns:
            df[c] = np.nan

    return df[cols]