#account_tool.py#new version with improved query building, better error handling, and more flexible filtering options
from db.mongo import account_collection
import pandas as pd
import logging
import importlib
import services.prediction_service
from services.prediction_service import predict_account_service

importlib.reload(services.prediction_service)
import services.logger
logger = logging.getLogger(__name__)


def account_tool(
    client_id=None,
    compte_id=None,
    carte_id=None,
    year=None,
    date=None,
    label=None
):
    try:
        # =========================
        # 1. BUILD QUERY
        # =========================
        query = {}

        if client_id:
            query["client"] = {"$regex": f"^{client_id.strip()}\\s*$"}

        if compte_id:
            query["compte"] = {"$regex": f"^{compte_id.strip()}\\s*$"}

        if carte_id:
            query["carte"] = {"$regex": f"^{carte_id.strip()}\\s*$"}

        # =========================
        # 2. LOAD DATA FROM MONGO
        # =========================
        data = list(account_collection.find(query))

        if not data:
            return {"error": "No data found"}

        df = pd.DataFrame(data)

        # =========================
        # 3. PREDICTION (NEW MODEL)
        # =========================
        df_result = predict_account_service(df)

        # =========================
        # 4. FILTER BY YEAR
        # =========================
        if year is not None:
            df_result = df_result[
                df_result['datetime'].dt.year == int(year)
            ]

        # =========================
        # 5. FILTER BY DATE
        # =========================
        if date is not None:
            date = pd.to_datetime(date)
            df_result = df_result[
                df_result['datetime'].dt.date == date.date()
            ]

        # =========================
        # 6. FILTER BY LABEL
        # =========================
        if label is not None:
            df_result = df_result[
                df_result['final_label'] == label
            ]

        # =========================
        # 7. DEBUG (OPTIONAL)
        # =========================
        if not df_result.empty:
            logger.info("account label distribution:\n%s", df_result['final_label'].value_counts())
        else:
            logger.info("No results after filtering")

        # =========================
        # 8. RETURN RESULT
        # =========================
        return df_result.to_dict(orient="records")

    except Exception as e:
        return {"error": str(e)}