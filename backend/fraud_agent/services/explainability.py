"""
🔍 Model Explainability Module
Integrates SHAP insights and feature importance into fraud explanations
Based on Account_Operations_Fraud_Model_explainability.ipynb
"""

import numpy as np
import pandas as pd
import torch
from typing import Dict, List, Any, Tuple
import joblib
import logging
import services.logger

logger = logging.getLogger(__name__)


# =========================
# FEATURE IMPORTANCE CALCULATOR
# =========================

class ModelExplainer:
    """
    Explains fraud detection by showing which features contributed most to the risk score.
    Uses reconstruction error and feature analysis.
    """
    
    def __init__(self, model_dir: str = "saved_models", model_card_dir: str = "models_card"):
        """Initialize explainer with saved model information"""
        self.model_dir = model_dir
        self.model_card_dir = model_card_dir
        
        # Load feature names and thresholds
        import json
        import os
        
        try:
            with open(os.path.join(model_dir, "config.json")) as f:
                self.account_config = json.load(f)
            self.account_features = self.account_config.get("features", [])
        except:
            self.account_features = [
                'montant_mvt', 'sens_mvt', 'lib_mvt', 'hour', 'day', 
                'time_diff', 'amount_ratio', 'tx_count'
            ]
        
        try:
            with open(os.path.join(model_card_dir, "features.json")) as f:
                self.card_features = json.load(f)
        except:
            self.card_features = []

    def _normalize_score(self, value: float) -> float:
        """Normalize raw model numeric scores to a bounded range for LLM context.

        - Keeps small magnitudes unchanged (up to 1k).
        - Compresses very large values using a log + tanh transform to map them
          into approximately a 0-10 range so the LLM sees reasonable magnitudes.
        """
        try:
            v = float(value)
        except Exception:
            return value

        # Keep small values as-is for interpretability
        if abs(v) <= 1000:
            return round(v, 4)

        # Compress large magnitudes: log10 -> scaled via tanh into ~0-10 range
        try:
            mag = np.log10(abs(v)) if abs(v) > 0 else 0.0
            scaled = np.tanh(mag / 6.0) * 10.0
            return round(scaled if v >= 0 else -scaled, 4)
        except Exception:
            return round(v, 4)
    
    def explain_account_score(self, 
                              df: pd.DataFrame, 
                              ae_score: float,
                              lstm_score: float = None,
                              final_score: float = None) -> Dict[str, Any]:
        """
        Explain account fraud score by identifying key contributing features
        
        Args:
            df: DataFrame with transaction data
            ae_score: Autoencoder reconstruction error
            lstm_score: LSTM sequence anomaly score
            final_score: Combined final score
            
        Returns:
            Dict with explanation details
        """
        
        explanation = {
            "model_components": [],
            "key_features": [],
            "anomaly_patterns": [],
            "risk_factors": []
        }
        
        # =========================
        # 1. ANALYZE FEATURES
        # =========================
        
        # High amounts
        if 'montant_mvt' in df.columns:
            amounts = pd.to_numeric(df['montant_mvt'], errors='coerce')
            high_amounts = (amounts > amounts.mean() * 2).sum()
            if high_amounts > 0:
                explanation["key_features"].append({
                    "name": "Transaction Amount",
                    "impact": "HIGH",
                    "reason": f"Unusual high amounts detected ({high_amounts} transactions > 2x average)",
                    "value": f"Max: {amounts.max():.2f}, Avg: {amounts.mean():.2f}"
                })
        
        # Time anomalies
        if 'time_diff' in df.columns:
            time_diffs = pd.to_numeric(df['time_diff'], errors='coerce')
            unusual_gaps = (time_diffs < 60).sum()  # Less than 1 minute between tx
            if unusual_gaps > 0:
                explanation["key_features"].append({
                    "name": "Transaction Timing",
                    "impact": "MEDIUM",
                    "reason": f"Rapid consecutive transactions detected ({unusual_gaps} within 1 minute)",
                    "value": f"Min gap: {time_diffs.min():.0f}s, Avg gap: {time_diffs.mean():.0f}s"
                })
        
        # Unusual hours
        if 'hour' in df.columns:
            night_hours = ((df['hour'] < 6) | (df['hour'] > 23)).sum()
            if night_hours / len(df) > 0.3:  # More than 30% night transactions
                explanation["key_features"].append({
                    "name": "Transaction Time",
                    "impact": "MEDIUM",
                    "reason": f"Unusual transaction hours ({night_hours} at night/early morning)",
                    "value": f"{night_hours/len(df)*100:.1f}% night transactions"
                })
        
        # Amount ratio (compared to client average)
        if 'amount_ratio' in df.columns:
            ratios = pd.to_numeric(df['amount_ratio'], errors='coerce')
            high_ratio = (ratios > 1.5).sum()  # 50% above average
            if high_ratio > 0:
                explanation["key_features"].append({
                    "name": "Amount Deviation",
                    "impact": "HIGH",
                    "reason": f"Transactions much higher than client average",
                    "value": f"{high_ratio} transactions >1.5x client average"
                })
        
        # =========================
        # 2. MODEL COMPONENTS
        # =========================
        
        if ae_score is not None:
            norm_ae = self._normalize_score(ae_score)
            explanation["model_components"].append({
                "model": "Autoencoder",
                "type": "Reconstruction-based",
                "score": norm_ae,
                "raw_score": round(float(ae_score), 4),
                "explanation": "Detects point anomalies by analyzing individual transactions"
            })
        
        if lstm_score is not None:
            norm_lstm = self._normalize_score(lstm_score)
            explanation["model_components"].append({
                "model": "LSTM Autoencoder",
                "type": "Sequence-based",
                "score": norm_lstm,
                "raw_score": round(float(lstm_score), 4),
                "explanation": "Detects sequence anomalies across 10-transaction windows"
            })
        
        # =========================
        # 3. ANOMALY PATTERNS
        # =========================
        
        if len(df) > 1:
            explanation["anomaly_patterns"] = self._identify_patterns(df)
        
        # =========================
        # 4. RISK FACTORS SUMMARY
        # =========================
        
        risk_level = "LOW"
        if final_score is not None:
            if final_score >= 8:
                risk_level = "CRITICAL"
            elif final_score >= 6:
                risk_level = "HIGH"
            elif final_score >= 4:
                risk_level = "MEDIUM"
            elif final_score >= 2:
                risk_level = "LOW-MEDIUM"
        
        explanation["risk_level"] = risk_level
        
        return explanation
    
    def explain_card_score(self, 
                          df: pd.DataFrame,
                          ae_score: float = None,
                          lstm_score: float = None,
                          final_score: float = None) -> Dict[str, Any]:
        """
        Explain card fraud score with card-specific features
        """
        
        explanation = {
            "model_components": [],
            "key_features": [],
            "anomaly_patterns": [],
            "risk_factors": []
        }
        
        # Card-specific features
        
        # High transaction amounts
        if 'mnt_autorise' in df.columns:
            amounts = pd.to_numeric(df['mnt_autorise'], errors='coerce')
            high_amounts = (amounts > amounts.mean() * 3).sum()
            if high_amounts > 0:
                explanation["key_features"].append({
                    "name": "Authorized Amount",
                    "impact": "HIGH",
                    "reason": f"Very high transaction amounts",
                    "value": f"Max: {amounts.max():.2f}, {high_amounts} > 3x avg"
                })
        
        # Merchant anomalies
        if 'merchant_seen' in df.columns:
            new_merchants = (df['merchant_seen'] == 0).sum()
            if new_merchants / len(df) > 0.5:  # More than 50% new merchants
                explanation["key_features"].append({
                    "name": "Merchant Pattern",
                    "impact": "HIGH",
                    "reason": f"Transactions with new/unfamiliar merchants",
                    "value": f"{new_merchants} out of {len(df)} transactions ({new_merchants/len(df)*100:.0f}%)"
                })
        
        # Geographic anomalies (if available)
        if 'cod_banq_acq' in df.columns:
            unique_acquirers = df['cod_banq_acq'].nunique()
            if unique_acquirers > 3:
                explanation["key_features"].append({
                    "name": "Geographic Spread",
                    "impact": "MEDIUM",
                    "reason": f"Transactions across multiple geographic regions",
                    "value": f"{unique_acquirers} different acquirer banks"
                })
        
        # Model components
        if ae_score is not None:
            norm_ae = self._normalize_score(ae_score)
            explanation["model_components"].append({
                "model": "Autoencoder",
                "score": norm_ae,
                "raw_score": round(float(ae_score), 4),
                "explanation": "Detects card transaction anomalies"
            })
        
        if lstm_score is not None:
            norm_lstm = self._normalize_score(lstm_score)
            explanation["model_components"].append({
                "model": "LSTM Autoencoder",
                "score": norm_lstm,
                "raw_score": round(float(lstm_score), 4),
                "explanation": "Detects sequential card fraud patterns"
            })
        
        explanation["anomaly_patterns"] = self._identify_patterns(df)
        
        return explanation
    
    def _identify_patterns(self, df: pd.DataFrame) -> List[str]:
        """Identify specific fraud patterns in the data"""
        patterns = []
        
        # Rapid transactions
        if 'time_diff' in df.columns:
            time_diffs = pd.to_numeric(df['time_diff'], errors='coerce')
            if time_diffs.min() < 60:
                patterns.append("⚡ Rapid-fire transactions (within 60 seconds)")
        
        # Late night activity
        if 'hour' in df.columns:
            night_count = ((df['hour'] < 6) | (df['hour'] > 23)).sum()
            if night_count / len(df) > 0.3:
                patterns.append("🌙 Unusual nighttime activity (>30%)")
        
        # Consistency breaks
        if 'amount_ratio' in df.columns:
            ratios = pd.to_numeric(df['amount_ratio'], errors='coerce')
            if ratios.max() > 2.0:
                patterns.append(f"📈 Sudden amount spike (up to {ratios.max():.1f}x normal)")
        
        # Weekend vs weekday (if multiple days)
        if 'day' in df.columns and len(df['day'].unique()) > 1:
            patterns.append("📅 Activity across multiple days detected")
        
        return patterns
    
    def generate_llm_context(self, 
                            account_explanation: Dict[str, Any],
                            card_explanation: Dict[str, Any] = None) -> str:
        """
        Generate context string for LLM to use in explanations
        This can be passed to the LLM service for better context-aware explanations
        """
        
        context = "FRAUD DETECTION EXPLAINABILITY CONTEXT:\n\n"
        
        # Account analysis context
        context += "=== ACCOUNT ANALYSIS ===\n"
        for feature in account_explanation.get("key_features", []):
            context += f"• {feature['name']} ({feature['impact']}): {feature['reason']}\n"
        
        for pattern in account_explanation.get("anomaly_patterns", []):
            context += f"• Pattern: {pattern}\n"
        
        # Card analysis context
        if card_explanation:
            context += "\n=== CARD ANALYSIS ===\n"
            for feature in card_explanation.get("key_features", []):
                context += f"• {feature['name']} ({feature['impact']}): {feature['reason']}\n"
            
            for pattern in card_explanation.get("anomaly_patterns", []):
                context += f"• Pattern: {pattern}\n"
        
        context += "\n=== MODEL SCORES ===\n"
        for component in account_explanation.get("model_components", []):
            context += f"• {component['model']}: {component['score']}\n"
        
        if card_explanation:
            for component in card_explanation.get("model_components", []):
                context += f"• {component['model']} (Card): {component['score']}\n"
        
        return context


# =========================
# GENERATE INTERPRETABLE EXPLANATIONS
# =========================

def create_detailed_explanation(client_id: str,
                               account_data: pd.DataFrame,
                               card_data: pd.DataFrame = None,
                               account_scores: Dict = None,
                               card_scores: Dict = None) -> Dict[str, Any]:
    """
    Create detailed explanation combining model insights and feature analysis
    
    Args:
        client_id: The client being analyzed
        account_data: DataFrame with account transactions
        card_data: DataFrame with card transactions (optional)
        account_scores: Dict with ae_score, lstm_score, final_score
        card_scores: Dict with card model scores
        
    Returns:
        Dict with comprehensive explainability information
    """
    
    explainer = ModelExplainer()
    
    # Explain account
    account_exp = explainer.explain_account_score(
        account_data,
        ae_score=account_scores.get('ae_score') if account_scores else None,
        lstm_score=account_scores.get('lstm_score') if account_scores else None,
        final_score=account_scores.get('risk_score') if account_scores else None
    )
    
    # Explain card (if available)
    card_exp = None
    if card_data is not None and len(card_data) > 0:
        card_exp = explainer.explain_card_score(
            card_data,
            ae_score=card_scores.get('ae_score') if card_scores else None,
            lstm_score=card_scores.get('lstm_score') if card_scores else None,
            final_score=card_scores.get('risk_score') if card_scores else None
        )
    
    # Generate LLM context
    llm_context = explainer.generate_llm_context(account_exp, card_exp)
    
    return {
        "client_id": client_id,
        "account_explanation": account_exp,
        "card_explanation": card_exp,
        "llm_context": llm_context,
        "explainability_ready": True
    }


if __name__ == "__main__":
    # Example usage
    logger.info("Explainability module loaded")
    logger.info("Use: from services.explainability import ModelExplainer, create_detailed_explanation")
