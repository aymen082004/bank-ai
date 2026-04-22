# card_tool.py
from db.mongo import card_collection
import pandas as pd
import importlib
import logging

import services.prediction_service
from services.prediction_service import predict_card_service

importlib.reload(services.prediction_service)
import services.logger
logger = logging.getLogger(__name__)

def card_tool(
    client_id=None,
    compte_id=None,
    carte_id=None,
    year=None,
    date=None,
    label=None,
    is_large=None,
    cod_banq_par=None,
    cod_banq_acq=None,
    typ_trans=None,
    merchant_seen=None,
    mnt_min=None,
    mnt_max=None
):
    # =========================
    # BUILD QUERY
    # =========================
    query = {}

    if client_id:
        query["client"] = {"$regex": f"^{client_id.strip()}\\s*$"}
    if compte_id:
        query["compte"] = {"$regex": f"^{compte_id.strip()}\\s*$"}
    if carte_id:
        query["carte"] = {"$regex": f"^{carte_id.strip()}\\s*$"}

    # =========================
    # LOAD DATA
    # =========================
    df = pd.DataFrame(list(card_collection.find(query)))
    if df.empty:
        return {"error": "No card data"}

    # =========================
    # CLEAN STRINGS
    # =========================
    for col in ['client', 'compte', 'carte']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # =========================
    # PREDICTION
    # =========================
    df_result = predict_card_service(df)

    # =========================
    # FILTER BY YEAR
    # =========================
    if year is not None and 'datetime' in df_result.columns:
        df_result = df_result[df_result['datetime'].dt.year == int(year)]

    # =========================
    # FILTER BY DATE
    # =========================
    if date is not None and 'datetime' in df_result.columns:
        date = pd.to_datetime(date)
        df_result = df_result[df_result['datetime'].dt.date == date.date()]

    # =========================
    # FILTER BY LABEL
    # =========================
    if label is not None and 'final_label' in df_result.columns:
        df_result = df_result[df_result['final_label'] == label]

    # =========================
    # EXTRA FILTERS
    # =========================
    if 'mnt_autorise' in df_result.columns:
        df_result['mnt_autorise'] = df_result['mnt_autorise'].astype(float)

    if 'typ_trans' in df_result.columns:
        df_result['typ_trans'] = df_result['typ_trans'].astype(str).str.strip()

    if is_large is not None and 'is_large' in df_result.columns:
        df_result = df_result[df_result['is_large'].astype(bool) == bool(is_large)]

    if cod_banq_par is not None and 'cod_banq_par' in df_result.columns:
        df_result = df_result[df_result['cod_banq_par'] == int(cod_banq_par)]

    if cod_banq_acq is not None and 'cod_banq_acq' in df_result.columns:
        df_result = df_result[df_result['cod_banq_acq'] == int(cod_banq_acq)]

    if typ_trans is not None and 'typ_trans' in df_result.columns:
        df_result = df_result[df_result['typ_trans'] == str(typ_trans).strip()]

    if merchant_seen is not None and 'merchant_seen' in df_result.columns:
        df_result = df_result[df_result['merchant_seen'] == int(merchant_seen)]

    if mnt_min is not None and 'mnt_autorise' in df_result.columns:
        df_result = df_result[df_result['mnt_autorise'] >= float(mnt_min)]

    if mnt_max is not None and 'mnt_autorise' in df_result.columns:
        df_result = df_result[df_result['mnt_autorise'] <= float(mnt_max)]

    # =========================
    # DEBUG OUTPUT
    # =========================
    if 'final_label' in df_result.columns:
        logger.info("card label distribution:\n%s", df_result['final_label'].value_counts())

    # =========================
    # RETURN RESULTS
    # =========================
    return df_result.to_dict(orient="records")