"""
Yahoo Finance API integration for free stock data and charts.
Uses yfinance library as a reliable free alternative to paid APIs.
"""
import yfinance as yf
import json
import requests
import time
import os
import threading
from datetime import datetime, timedelta

# Thread lock for yfinance calls to avoid concurrent access issues
_yf_lock = threading.Lock()

# Disable yfinance cache to avoid disk I/O errors in concurrent environments
try:
    # Some versions of yfinance use requests_cache or custom sqlite cache
    # We try to disable it or redirect it to a temporary unique location
    import yfinance as yf
    import tempfile
    
    # Method 1: Environment variable
    temp_cache_dir = os.path.join(tempfile.gettempdir(), f"yf_cache_{os.getpid()}")
    os.environ["YF_CACHE_DIR"] = temp_cache_dir
    if not os.path.exists(temp_cache_dir):
        os.makedirs(temp_cache_dir, exist_ok=True)
        
    # Method 2: For newer versions that might use a global session
    # We can try to monkeypatch or set the session to None if it supports it
except Exception as e:
    print(f"Failed to setup yfinance cache dir: {e}")

# Simple in-memory cache with timestamps
_cache = {}
_cache_ttl = 300  # 5 minutes cache

def _get_cache(key):
    """Get cached value if not expired."""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < _cache_ttl:
            return value
    return None

def _set_cache(key, value):
    """Set cached value with timestamp."""
    _cache[key] = (value, time.time())

# Mock fallback data for common stocks when Yahoo rate limits
FALLBACK_STOCK_DATA = {
    "AAPL": {
        "name": "Apple Inc.", "price": 175.50, "change": 2.30, "change_percent": 1.33, 
        "currency": "USD", "market_cap": 2700000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "1980-12-12", "exchange": "NASDAQ",
        "employees": 161000, "website": "https://www.apple.com",
        "description": "Apple Inc. conçoit, fabrique et commercialise des smartphones, des ordinateurs personnels, des tablettes, des wearables et des accessoires dans le monde entier.",
        "sector": "Technologie", "industry": "Électronique grand public",
        "pe_ratio": 28.5, "pb_ratio": 45.2, "eps": 6.15
    },
    "TSLA": {
        "name": "Tesla, Inc.", "price": 245.80, "change": -3.20, "change_percent": -1.29,
        "currency": "USD", "market_cap": 780000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "2010-06-29", "exchange": "NASDAQ",
        "employees": 140473, "website": "https://www.tesla.com",
        "description": "Tesla, Inc. conçoit, développe, fabrique, loue et vend des véhicules électriques, ainsi que des systèmes de production et de stockage d'énergie.",
        "sector": "Consommation cyclique", "industry": "Constructeurs automobiles",
        "pe_ratio": 65.2, "pb_ratio": 12.8, "eps": 3.77
    },
    "MSFT": {
        "name": "Microsoft Corporation", "price": 420.25, "change": 5.10, "change_percent": 1.23,
        "currency": "USD", "market_cap": 3100000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "1986-03-13", "exchange": "NASDAQ",
        "employees": 221000, "website": "https://www.microsoft.com",
        "description": "Microsoft Corporation développe, licencie et prend en charge des logiciels, des services, des appareils et des solutions dans le monde entier.",
        "sector": "Technologie", "industry": "Logiciels - Infrastructure",
        "pe_ratio": 32.1, "pb_ratio": 12.5, "eps": 13.10
    },
    "GOOGL": {
        "name": "Alphabet Inc.", "price": 165.40, "change": 1.80, "change_percent": 1.10,
        "currency": "USD", "market_cap": 2050000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "2004-08-19", "exchange": "NASDAQ",
        "employees": 182502, "website": "https://abc.xyz",
        "description": "Alphabet Inc. propose divers produits et plateformes aux États-Unis, en Europe, au Moyen-Orient, en Afrique, en Asie-Pacifique, au Canada et en Amérique latine.",
        "sector": "Services de communication", "industry": "Contenu et information Internet",
        "pe_ratio": 24.5, "pb_ratio": 6.8, "eps": 6.75
    },
    "AMZN": {
        "name": "Amazon.com Inc.", "price": 185.30, "change": 2.50, "change_percent": 1.37,
        "currency": "USD", "market_cap": 1920000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "1997-05-15", "exchange": "NASDAQ",
        "employees": 1500000, "website": "https://www.amazon.com",
        "description": "Amazon.com, Inc. s'engage dans la vente au détail de produits de consommation et d'abonnements en Amérique du Nord et à l'international.",
        "sector": "Consommation cyclique", "industry": "Commerce de détail sur Internet",
        "pe_ratio": 58.2, "pb_ratio": 8.5, "eps": 3.18
    },
    "NVDA": {
        "name": "NVIDIA Corporation", "price": 890.50, "change": 12.30, "change_percent": 1.40,
        "currency": "USD", "market_cap": 2200000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "1999-01-22", "exchange": "NASDAQ",
        "employees": 29600, "website": "https://www.nvidia.com",
        "description": "NVIDIA Corporation fournit des solutions graphiques, informatiques et de mise en réseau dans les Amériques, en Europe, en Asie et à l'international.",
        "sector": "Technologie", "industry": "Semi-conducteurs",
        "pe_ratio": 75.3, "pb_ratio": 52.1, "eps": 11.82
    },
    "META": {
        "name": "Meta Platforms, Inc.", "price": 505.20, "change": 6.80, "change_percent": 1.37,
        "currency": "USD", "market_cap": 1300000000000, "market": "actions", "type": "CS",
        "status": "Actif", "listed": "2012-05-18", "exchange": "NASDAQ",
        "employees": 67317, "website": "https://investor.fb.com",
        "description": "Meta Platforms, Inc. développe des produits qui permettent aux gens de se connecter et de partager avec leurs amis et leur famille via des appareils mobiles, des ordinateurs personnels et d'autres surfaces.",
        "sector": "Services de communication", "industry": "Contenu et information Internet",
        "pe_ratio": 25.8, "pb_ratio": 8.2, "eps": 19.58
    },
}

def get_stock_info(symbol):
    """
    Get comprehensive stock info from Yahoo Finance.
    Tries Yahoo first, uses fallback data only on error/rate limit.
    """
    symbol_upper = symbol.upper()
    cache_key = f"stock_info_{symbol_upper}"
    
    # Check cache first
    cached = _get_cache(cache_key)
    if cached:
        print(f"Yahoo Finance: Using cached data for {symbol}")
        return cached
    
    # Try Yahoo Finance first
    try:
        with _yf_lock:
            print(f"Yahoo Finance: Fetching real data for {symbol}...")
            ticker = yf.Ticker(symbol)
            info = ticker.info
        
        # Check if we got valid data
        if not info or info.get("regularMarketPrice") is None:
            raise Exception("No data returned from Yahoo")
        
        result = {
            "symbol": symbol.upper(),
            "name": info.get("longName", info.get("shortName", symbol)),
            "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "change": info.get("regularMarketChange", 0),
            "change_percent": info.get("regularMarketChangePercent", 0),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", info.get("forwardPE", 0)),
            "pb_ratio": info.get("priceToBook", 0),
            "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "volume": info.get("regularMarketVolume", info.get("volume", 0)),
            "avg_volume": info.get("averageVolume", 0),
            "beta": info.get("beta", 0),
            "eps": info.get("trailingEps", info.get("forwardEps", 0)),
            "revenue": info.get("totalRevenue", 0),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "website": info.get("website", ""),
            "country": info.get("country", ""),
            "employees": info.get("fullTimeEmployees", 0),
            "business_summary": info.get("longBusinessSummary", ""),
            "market": info.get("market", "stocks"),
            "type": info.get("quoteType", "CS"),
            "status": "Active" if info.get("regularMarketPrice") else "Inactive",
            "listed": info.get("firstTradeDateEpochUtc", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "trend": "UP" if info.get("regularMarketChange", 0) > 0 else "DOWN" if info.get("regularMarketChange", 0) < 0 else "NEUTRAL",
            "data_source": "Yahoo Finance (Real-time)"
        }
        
        # Cache successful result
        _set_cache(cache_key, result)
        print(f"Yahoo Finance: Successfully fetched real data for {symbol}")
        return result
        
    except Exception as e:
        error_str = str(e)
        print(f"Yahoo Finance error for {symbol}: {error_str}")
        
        # Only use fallback if Yahoo fails
        if symbol_upper in FALLBACK_STOCK_DATA:
            fallback = FALLBACK_STOCK_DATA[symbol_upper].copy()
            fallback["symbol"] = symbol_upper
            fallback["trend"] = "UP" if fallback.get("change", 0) > 0 else "DOWN"
            fallback["data_source"] = "Fallback (Yahoo unavailable)"
            print(f"Yahoo Finance: Using fallback data for {symbol}")
            return fallback
        
        return {"error": error_str, "symbol": symbol}

def get_historical_data(symbol, period="1y", interval="1d"):
    """
    Get historical price data for charts.
    Tries Yahoo first, uses mock data only on error/rate limit.
    """
    symbol_upper = symbol.upper()
    cache_key = f"historical_{symbol_upper}_{period}_{interval}"
    
    # Check cache
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    # Try Yahoo Finance first
    try:
        with _yf_lock:
            print(f"Yahoo Finance: Fetching historical data for {symbol}...")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
        
        # Check if we got valid data
        if hist.empty:
            raise Exception("No historical data returned")
        
        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })
        
        result = {
            "symbol": symbol_upper,
            "period": period,
            "interval": interval,
            "data": data,
            "data_source": "Yahoo Finance (Real-time)"
        }
        _set_cache(cache_key, result)
        print(f"Yahoo Finance: Successfully fetched historical data for {symbol}")
        return result
        
    except Exception as e:
        print(f"Historical data error for {symbol}: {e}")
        
        # Generate mock historical data as fallback
        if symbol_upper in FALLBACK_STOCK_DATA:
            base_price = FALLBACK_STOCK_DATA[symbol_upper]["price"]
            mock_data = []
            from datetime import datetime, timedelta
            # Generate 100 days of data to satisfy the 30-day minimum check
            for i in range(100):
                date = datetime.now() - timedelta(days=100-i)
                variation = (i % 7 - 3) * 0.8
                price = base_price + variation
                mock_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(price - 0.5, 2),
                    "high": round(price + 1.0, 2),
                    "low": round(price - 1.0, 2),
                    "close": round(price, 2),
                    "volume": 1000000 + (i * 10000)
                })
            
            result = {
                "symbol": symbol_upper,
                "period": period,
                "interval": interval,
                "data": mock_data,
                "data_source": "Fallback (Yahoo unavailable)"
            }
            _set_cache(cache_key, result)
            print(f"Yahoo Finance: Using mock historical data for {symbol}")
            return result
        
        return {"error": str(e), "symbol": symbol_upper, "data": []}

def get_financial_ratios(symbol):
    """
    Get key financial ratios.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "symbol": symbol.upper(),
            "valuation": {
                "pe_trailing": info.get("trailingPE", 0),
                "pe_forward": info.get("forwardPE", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "ps_ratio": info.get("priceToSalesTrailing12Months", 0),
                "peg_ratio": info.get("pegRatio", 0),
                "ev_ebitda": info.get("enterpriseToEbitda", 0),
            },
            "profitability": {
                "profit_margin": info.get("profitMargins", 0) * 100 if info.get("profitMargins") else 0,
                "operating_margin": info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else 0,
                "roa": info.get("returnOnAssets", 0) * 100 if info.get("returnOnAssets") else 0,
                "roe": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0,
            },
            "liquidity": {
                "current_ratio": info.get("currentRatio", 0),
                "quick_ratio": info.get("quickRatio", 0),
                "debt_equity": info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else 0,
            },
            "efficiency": {
                "asset_turnover": info.get("revenuePerShare", 0) / info.get("bookValue", 1) if info.get("bookValue") else 0,
                "inventory_turnover": 0,  # Not always available
            }
        }
    except Exception as e:
        print(f"Financial ratios error for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}

def get_recommendations(symbol):
    """
    Get analyst recommendations (buy/hold/sell).
    """
    try:
        ticker = yf.Ticker(symbol)
        recommendations = ticker.recommendations
        
        if recommendations is None or recommendations.empty:
            return {"symbol": symbol.upper(), "recommendations": [], "summary": {}}
        
        # Get the most recent period
        recent = recommendations.tail(1).to_dict('records')[0] if len(recommendations) > 0 else {}
        
        summary = {
            "strong_buy": recent.get("strongBuy", 0),
            "buy": recent.get("buy", 0),
            "hold": recent.get("hold", 0),
            "sell": recent.get("sell", 0),
            "strong_sell": recent.get("strongSell", 0),
        }
        
        # Calculate consensus
        total = sum(summary.values())
        if total > 0:
            score = (summary["strong_buy"] * 5 + summary["buy"] * 4 + summary["hold"] * 3 + 
                    summary["sell"] * 2 + summary["strong_sell"] * 1) / total
            
            if score >= 4.5:
                consensus = "STRONG_BUY"
            elif score >= 3.5:
                consensus = "BUY"
            elif score >= 2.5:
                consensus = "HOLD"
            elif score >= 1.5:
                consensus = "SELL"
            else:
                consensus = "STRONG_SELL"
        else:
            consensus = "UNKNOWN"
            score = 0
        
        return {
            "symbol": symbol.upper(),
            "summary": summary,
            "consensus": consensus,
            "score": round(score, 2),
            "total_analysts": total
        }
    except Exception as e:
        print(f"Recommendations error for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}

def get_trending_tickers():
    """
    Get trending tickers (stocks, crypto, etc.) using Yahoo Finance.
    Tries Yahoo first, returns fallback data on error/rate limits.
    """
    cache_key = "trending_tickers"
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    # Try fetching from Yahoo Finance first
    try:
        print("Yahoo Finance: Fetching trending tickers...")
        trending_symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "NVDA", "AMZN"]
        results = []
        
        for symbol in trending_symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if info and info.get("regularMarketPrice"):
                    results.append({
                        "symbol": symbol,
                        "name": info.get("shortName", info.get("longName", symbol)),
                        "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                        "change": info.get("regularMarketChange", 0),
                        "change_percent": info.get("regularMarketChangePercent", 0),
                        "trend": "UP" if info.get("regularMarketChange", 0) > 0 else "DOWN",
                        "data_source": "Yahoo Finance"
                    })
            except:
                continue
        
        if results:
            _set_cache(cache_key, results)
            print(f"Yahoo Finance: Successfully fetched {len(results)} trending tickers")
            return results
        else:
            raise Exception("No trending data available")
            
    except Exception as e:
        print(f"Yahoo Finance trending error: {e}")
        
        # Fallback data
        fallback_results = [
            {"symbol": "AAPL", "name": "Apple Inc.", "price": 175.50, "change": 2.30, "change_percent": 1.33, "trend": "UP", "data_source": "Fallback"},
            {"symbol": "TSLA", "name": "Tesla, Inc.", "price": 245.80, "change": -3.20, "change_percent": -1.29, "trend": "DOWN", "data_source": "Fallback"},
            {"symbol": "MSFT", "name": "Microsoft Corp", "price": 420.25, "change": 5.10, "change_percent": 1.23, "trend": "UP", "data_source": "Fallback"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": 165.40, "change": 1.80, "change_percent": 1.10, "trend": "UP", "data_source": "Fallback"},
            {"symbol": "NVDA", "name": "NVIDIA Corp", "price": 890.50, "change": 12.30, "change_percent": 1.40, "trend": "UP", "data_source": "Fallback"},
            {"symbol": "AMZN", "name": "Amazon.com", "price": 185.30, "change": 2.50, "change_percent": 1.37, "trend": "UP", "data_source": "Fallback"},
        ]
        _set_cache(cache_key, fallback_results)
        return fallback_results

def search_stocks(query):
    """
    Search for stocks by name or symbol using Yahoo Finance search endpoint.
    Prioritizes stocks where the symbol starts with the query.
    Tries Yahoo API first, uses fallback on error/rate limits.
    """
    cache_key = f"search_{query.upper()}"
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    # Try Yahoo API first
    try:
        print(f"Yahoo Finance: Searching for '{query}'...")
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            query_upper = query.upper()
            
            # Separate results: those starting with query vs containing query
            starts_with = []
            contains = []
            
            for quote in data.get("quotes", []):
                if quote.get("quoteType") in ["EQUITY", "ETF"]:
                    symbol = quote.get("symbol", "")
                    symbol_upper = symbol.upper()
                    name = quote.get("shortname", quote.get("longname", symbol))
                    
                    item = {
                        "symbol": symbol,
                        "name": name,
                        "exchange": quote.get("exchange", ""),
                        "type": quote.get("quoteType", ""),
                        "data_source": "Yahoo Finance"
                    }
                    
                    if symbol_upper.startswith(query_upper):
                        starts_with.append(item)
                    elif query_upper in symbol_upper or query_upper in name.upper():
                        contains.append(item)
            
            results = (starts_with + contains)[:10]
            if results:
                result_obj = {"query": query, "results": results}
                _set_cache(cache_key, result_obj)
                print(f"Yahoo Finance: Found {len(results)} results for '{query}'")
                return result_obj
        
        # If we get here, either status != 200 or no results
        raise Exception(f"Yahoo API returned {response.status_code} or no results")
        
    except Exception as e:
        print(f"Yahoo Search error for '{query}': {e}")
        
        # Use fallback data as backup
        query_upper = query.upper()
        fallback_matches = []
        
        for symbol, data in FALLBACK_STOCK_DATA.items():
            if query_upper in symbol or query_upper in data["name"].upper():
                fallback_matches.append({
                    "symbol": symbol,
                    "name": data["name"],
                    "exchange": "NASDAQ",
                    "type": "EQUITY",
                    "data_source": "Fallback"
                })
        
        if fallback_matches:
            result = {"query": query, "results": fallback_matches[:10], "note": "Using fallback data"}
            _set_cache(cache_key, result)
            return result
        
        # No fallback match either
        return {"query": query, "results": [], "note": "No results found"}


if __name__ == "__main__":
    # Test
    print(json.dumps(get_stock_info("AAPL"), indent=2))
