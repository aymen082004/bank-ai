import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MASSIVE_STOCK_API_KEY")
BASE_URL = "https://api.massive.com"

def get_ticker_details(ticker):
    """
    GET /v3/reference/tickers/{ticker}
    Retrieve detailed information about a ticker.
    """
    url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
    params = {"apiKey": API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("results", {})
    return {}

def search_tickers(search_query, limit=10):
    """
    GET /v3/reference/tickers
    Search for ticker symbols or company names.
    """
    url = f"{BASE_URL}/v3/reference/tickers"
    params = {
        "search": search_query,
        "market": "stocks",
        "active": "true",
        "limit": limit,
        "apiKey": API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def get_stock_aggregates(ticker, multiplier=1, timespan="day", from_date="2023-01-01", to_date="2024-04-11"):
    """
    GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
    Get aggregate bars for a ticker over a given date range.
    """
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
    params = {"apiKey": API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def get_snapshot_ticker(ticker):
    """
    GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}
    Get the most recent snapshot for a single ticker.
    """
    url = f"{BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
    params = {"apiKey": API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("ticker", {})
    return {}

def get_related_companies(ticker):
    """
    Simulate related companies based on ticker industry if endpoint not available.
    """
    tech_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
    if ticker in tech_stocks:
        return [s for s in tech_stocks if s != ticker]
    return ["SPY", "QQQ"]

def get_stock_details(ticker):
    """
    Combines ticker details, snapshot, and related companies into one object.
    """
    details = get_ticker_details(ticker)
    snapshot = get_snapshot_ticker(ticker)
    related = get_related_companies(ticker)
    
    # Enhanced price detection
    price = 0
    if snapshot.get("lastTrade"):
        price = snapshot.get("lastTrade", {}).get("p", 0)
    elif snapshot.get("day"):
        price = snapshot.get("day", {}).get("c", 0)

    return {
        "symbol": ticker,
        "name": details.get("name") if details.get("name") else ticker,
        "price": price,
        "change": snapshot.get("todaysChange", 0),
        "change_percent": snapshot.get("todaysChangePerc", 0),
        "market": details.get("market", "stocks"),
        "type": details.get("type", "CS"),
        "currency": details.get("currency_name", "usd"),
        "status": "Active" if details.get("active") else "Inactive",
        "listed": details.get("list_date", "N/A"),
        "exchange": details.get("primary_exchange", "N/A"),
        "employees": details.get("total_employees", 0),
        "shares_outstanding": details.get("share_class_shares_outstanding", 0),
        "weighted_shares": details.get("weighted_shares_outstanding", 0),
        "round_lot": details.get("round_lot", 100),
        "website": details.get("homepage_url", "N/A"),
        "description": details.get("description", "Aucune description disponible."),
        "related_companies": related,
        "volume": snapshot.get("day", {}).get("v", 0),
    }
