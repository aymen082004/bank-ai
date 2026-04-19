import json
import re
import numpy as np
import pandas as pd
import shap
from risk.modelrisk.risk_model import best_pipeline, shap_explainer
from bson import ObjectId
from bson.errors import InvalidId
from typing import Optional
import functools
import os
from supervisor.bd.mcp_server import mcp_handle
from langchain_core.tools import tool

_TOOL_DEBUG = os.environ.get("FASTFIN_DEBUG_TOOLS", "1").strip().lower() not in ("0", "false", "no")
_TOOL_DEBUG_MAX = int(os.environ.get("FASTFIN_DEBUG_TOOLS_MAXLEN", "6000"))

def _trace_tool(fn):
    """Afficher le nom de l’outil, les entrées et la sortie dans stderr (avec vidage forcé pour un débogage en temps réel)"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _TOOL_DEBUG:
            return fn(*args, **kwargs)
        name = getattr(fn, "__name__", repr(fn))
        print(f"\n{'=' * 72}", flush=True)
        print(f"[TOOL IN]  {name}", flush=True)
        if args:
            print(f"  args:   {args!r}", flush=True)
        if kwargs:
            print(f"  kwargs: {kwargs!r}", flush=True)
        try:
            out = fn(*args, **kwargs)
        except Exception as e:
            print(f"[TOOL ERR] {name}: {type(e).__name__}: {e}", flush=True)
            print(f"{'=' * 72}\n", flush=True)
            raise
        s = str(out)
        if len(s) > _TOOL_DEBUG_MAX:
            s = s[:_TOOL_DEBUG_MAX] + f"\n... [truncated, total {len(str(out))} chars]"
        print(f"[TOOL OUT] {name}", flush=True)
        print(s, flush=True)
        print(f"{'=' * 72}\n", flush=True)
        return out

    return wrapper


def _json_default_bson(obj):
    """Fallback for BSON/JSON serialization"""
    try:
        return str(obj)
    except Exception:
        return None

@tool
@_trace_tool
def get_customer(numero_compte: str) -> str:
    """
    Récupérer les infos essentielles du client depuis MongoDB sous format JSON string.
    Renvoie uniquement : personal_info, employment, credit_profile.
    """
    if not numero_compte:
        return "{}"

    oid_str = str(numero_compte).strip()
    if not re.fullmatch(r"[a-fA-F0-9]{24}", oid_str):
        return json.dumps({
            "error": "numero_compte_invalide",
            "message": "L'identifiant doit être exactement le champ 'numero_compte' de l'extrait OCR (24 caractères hex).",
            "reçu": oid_str
        }, ensure_ascii=False)

    or_clauses = [{"_id": oid_str}]
    try:
        or_clauses.insert(0, {"_id": ObjectId(oid_str)})
    except InvalidId:
        pass

    req = {
        "action": "fetch",
        "collection": "customers",
        "filter": {"$or": or_clauses},
    }
    resp = mcp_handle(req)
    rows = resp.get("data") if resp and resp.get("status") == "success" else None
    if rows and len(rows) > 0:
        raw = dict(rows[0])
        data = {
            "_id": str(raw["_id"]),
            "personal_info": raw.get("personal_info", {}),
            "employment": raw.get("employment", {}),
            "credit_profile": raw.get("credit_profile", {})
        }
        return json.dumps(data, ensure_ascii=False, default=_json_default_bson)
    return "{}"


@tool
@_trace_tool


def predict_risk(input_data_json: str) -> str:
    """
    Prédit le risque de défaut pour un client et identifie les features qui ont le plus d'impact.

    Arguments :
    - input_data_json : str JSON représentant les données client pour le modèle, ex:
      {"age": [23], "annual_income": [14939.69], ...}

    Retour :
    - JSON string de dict avec :
        * default_probability : probabilité de défaut (float)
        * risk_level : LOW / MEDIUM / HIGH
        * top_features : liste des 5 features les plus impactantes avec impact moyen
    """
    try:
        data = json.loads(input_data_json)
        input_data_df = pd.DataFrame(data)
    except Exception as e:
        return json.dumps({"error": f"Invalid input JSON: {str(e)}"}, ensure_ascii=False)

    try:
        # Transformer les nouvelles données avec le pipeline
        input_transformed = best_pipeline.named_steps["preprocessor"].transform(input_data_df)
        
        # Si sparse -> dense
        if hasattr(input_transformed, "toarray"):
            input_transformed = input_transformed.toarray()
        
        # Prédiction proba et classe (défaut = target 0)
        proba_default = best_pipeline.named_steps["model"].predict_proba(input_transformed)[0][0]
        predicted_class = int(best_pipeline.named_steps["model"].predict(input_transformed)[0])
        
        # Définir le niveau de risque
        if proba_default < 0.2:
            risk = "LOW"
        elif proba_default < 0.5:
            risk = "MEDIUM"
        else:
            risk = "HIGH"
        
        # SHAP explainer pour expliquer la prédiction
        if 'shap_explainer' in globals() and shap_explainer is not None:
            explainer = shap_explainer
        else:
            explainer = shap.TreeExplainer(best_pipeline.named_steps["model"])
            
        shap_values = explainer.shap_values(input_transformed)
        
        # Cas classification binaire (shap_values peut être une liste [val_0, val_1])
        if isinstance(shap_values, list):
            shap_values = shap_values[0] # Focus sur classe 0 (défaut)
        
        # Récupérer les noms des features après preprocessing
        feature_names = best_pipeline.named_steps["preprocessor"].get_feature_names_out()
        
        # Calculer l'impact moyen absolu de chaque feature
        shap_values_mean = np.abs(shap_values).mean(axis=0)
        if shap_values_mean.ndim > 1:
            shap_values_mean = shap_values_mean.mean(axis=0)
        
        # Top 5 features
        top_idx = np.argsort(shap_values_mean)[-5:]
        top_features = [(feature_names[i], float(shap_values_mean[i])) for i in reversed(top_idx)]

        print('Pred Class', predicted_class)
        
        out = {
            "default_probability": float(proba_default),
            "risk_level": risk,
            "top_features": top_features
        }
        return json.dumps(out, ensure_ascii=False)
        
    except Exception as e:
        import traceback
        return json.dumps({"error": f"Erreur de prédiction: {str(e)}", "trace": traceback.format_exc()}, ensure_ascii=False)

@tool
@_trace_tool
def submit_risk_report(
    risk_level: str,
    default_probability: float,
    grade_subgrade: str,
    top_features_json: str,
    risk_analysis: str
) -> str:
    """
    Soumet le rapport final de risque client.

    Args:
        risk_level (str): Niveau de risque global (LOW, MEDIUM, HIGH)
        default_probability (float): Probabilité de défaut (0 → 1)
        grade_subgrade (str): Grade attribué (ex: A1, B3, C5…)
        top_features_json (str): JSON list des 5 variables les plus impactantes
        risk_analysis (str): Analyse narrative détaillée du risque

    Returns:
        str: JSON string du rapport validé
    """

    # Sécurisation des inputs
    try:
        features = json.loads(top_features_json) if top_features_json else []
    except Exception:
        features = []

    report = {
        "risk_level": risk_level,
        "default_probability": float(default_probability),
        "grade_subgrade": grade_subgrade,
        "top_risk_drivers": features,
        "risk_analysis": risk_analysis
    }

    return json.dumps(report, ensure_ascii=False, indent=2)