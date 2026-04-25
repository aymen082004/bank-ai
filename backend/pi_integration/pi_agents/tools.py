"""
LangChain Tools for Digital Bank Agent System.
These tools wrap existing utility functions for use by LangChain agents.
"""

from langchain.tools import tool
from typing import Dict, List, Optional, Any
import json

# Import existing utilities
from ..pi_utils.db_mongo import mcp_handle
from ..pi_utils.db_neo4j import neo4j_handler
from ..pi_utils.stock_api import search_tickers, get_ticker_details, get_snapshot_ticker, get_related_companies
from ..pi_utils.yahoo_finance import get_stock_info, get_historical_data, get_financial_ratios, get_recommendations
from ..pi_utils.llm import call_llm
from .scraper import scrape_automobile_tn, scrape_tecnocasa_tn


@tool
def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch user profile and financial data from MongoDB.
    Use this to get user information, budget, and transaction history.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        Dictionary containing user profile, budget, and financial data
    """
    try:
        res = mcp_handle({
            "action": "fetch",
            "collection": "accounts",
            "filter": {"user_id": user_id}
        })
        
        if res.get("status") != "success" or not res.get("data"):
            return {"error": f"User {user_id} not found", "profile": {}}
        
        user_data = res.get("data")[0]
        return {
            "user_id": user_id,
            "profile": user_data,
            "budget": user_data.get("total_liquidity", 0),  # Default large purchase budget
            "monthly_budget": user_data.get("monthly_budget", 0),
            "current_balance": user_data.get("total_liquidity", 0),
            "income": user_data.get("income", 0),
            "goal": user_data.get("goal", ""),
            "name": user_data.get("name", "Unknown")
        }
    except Exception as e:
        return {"error": str(e), "profile": {}}


@tool
def get_user_transactions(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve user transaction history from MongoDB.
    Use this to analyze spending patterns and financial behavior.
    
    Args:
        user_id: The unique identifier for the user
        limit: Maximum number of transactions to retrieve (default 50)
        
    Returns:
        List of transaction records
    """
    try:
        res = mcp_handle({
            "action": "fetch",
            "collection": "transactions",
            "filter": {"user_id": user_id}
        })
        if res.get("status") == "success":
            transactions = res.get("data", [])
            # Limit to 20 transactions for context optimization
            return transactions[:20] if transactions else []
        return []
    except Exception as e:
        return [{"error": str(e)}]


@tool
def query_neo4j_graph(user_id: str) -> Dict[str, Any]:
    """
    Query Neo4j graph database for user relationships and context.
    Use this to get GraphRAG insights about user connections and behavior patterns.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        Dictionary containing graph context and insights
    """
    try:
        graph_context = neo4j_handler.get_user_graph_context(user_id)
        return {
            "user_id": user_id,
            "graph_context": graph_context,
            "insights": graph_context if graph_context else "No graph data available"
        }
    except Exception as e:
        return {"error": str(e), "graph_context": {}}


@tool
def scrape_car_listings(budget: float, brand: Optional[str] = None, persona: str = "neutral") -> Dict[str, Any]:
    """
    Scrape car listings exclusively from automobile.tn.
    
    Use this when the user is looking to buy a car within a specific budget.
    
    Args:
        budget: Maximum budget in TND (Tunisian Dinar)
        brand: Optional car brand filter (e.g., "BMW", "Toyota", "Mercedes")
        persona: User persona type (spender/keeper/neutral) for filtering
        
    Returns:
        Dictionary with listings and metadata
    """
    try:
        # Detect if brand is an origin name (English or French)
        country_names = {
            "german": "german", "allemande": "german", "allemand": "german",
            "french": "french", "française": "french", "français": "french",
            "japanese": "japanese", "japonaise": "japanese", "japonais": "japanese",
            "korean": "korean", "coréenne": "korean", "coréen": "korean",
            "american": "american", "américaine": "american", "américain": "american",
            "british": "british", "britannique": "british", "anglaise": "british",
            "italian": "italian", "italienne": "italian", "italien": "italian",
            "chinese": "chinese", "chinoise": "chinese", "chinois": "chinese",
            "spanish": "spanish", "espagnole": "spanish", "espagnol": "spanish",
            "indian": "indian", "indienne": "indian", "indien": "indian",
            "czech": "czech", "tchèque": "czech",
            "romanian": "romanian", "roumaine": "romanian", "roumain": "romanian",
            "swedish": "swedish", "suédoise": "swedish", "suédois": "swedish"
        }
        
        is_origin = False
        brand_clean = brand.lower().strip() if brand else ""
        origin_value = ""
        if brand_clean in country_names:
            is_origin = True
            origin_value = country_names[brand_clean]

        # Convert persona to preferences
        preferences = {
            "risk_tolerance": "low" if persona == "keeper" else "high" if persona == "spender" else "medium",
            "brand": brand if not is_origin else None,
            "brand_origin": origin_value if is_origin else ""
        }
        
        # Call the automobile.tn scraper function
        all_listings = []
        
        try:
            listings = scrape_automobile_tn(budget, persona, preferences)
            if listings:
                for item in listings:
                    item["source"] = "automobile.tn"
                all_listings.extend(listings)
        except Exception as e:
            print(f"Warning: automobile.tn scraping failed: {e}")
        
        # Filter by brand if specified (and if it's not an origin)
        if brand and not is_origin:
            brand_lower = brand.lower()
            all_listings = [
                item for item in all_listings 
                if brand_lower in item.get("title", "").lower()
            ]
        
        # Sort by price (closest to budget first, then under budget)
        all_listings.sort(key=lambda x: abs(x.get("price", 0) - budget * 0.8))
        
        return {
            "listings": all_listings[:20],  # Limit to top 20
            "total_found": len(all_listings),
            "budget": budget,
            "brand_filter": brand,
            "sources_checked": 1
        }
    except Exception as e:
        return {"error": str(e), "listings": []}


@tool
def scrape_real_estate_listings(budget: float, location: Optional[str] = None, property_type: str = "house") -> Dict[str, Any]:
    """
    Scrape real estate listings exclusively from Tecnocasa.tn.
    
    Use this when the user is looking to buy a house, apartment, or property.
    
    Args:
        budget: Maximum budget in TND
        location: Optional location filter (e.g., "Tunis", "Sfax")
        property_type: Type of property (house, apartment, villa)
        
    Returns:
        Dictionary with property listings
    """
    try:
        # Tecnocasa scraper for real estate
        listings = scrape_tecnocasa_tn(budget, location)
        
        # Filter by property type if specified - make it more inclusive for Tunisian listings
        if property_type:
            type_keywords = {
                "house": ["maison", "villa", "dar", "house", "s+1", "s+2", "s+3", "s+4", "vente"],
                "apartment": ["appartement", "apartment", "flat", "studio", "s+1", "s+2", "s+3"]
            }
            keywords = type_keywords.get(property_type.lower(), [])
            if keywords:
                # Only filter if the title actually contains some identifying keywords
                # Otherwise keep it to avoid filtering out all Tunisian "S+X" style titles
                filtered_listings = [
                    item for item in listings
                    if any(kw in item.get("title", "").lower() for kw in keywords)
                ]
                # If filtering would remove everything, keep the original list
                if filtered_listings:
                    listings = filtered_listings
        
        return {
            "listings": listings[:15],
            "total_found": len(listings),
            "budget": budget,
            "location": location,
            "property_type": property_type
        }
    except Exception as e:
        return {"error": str(e), "listings": []}


@tool
def search_stock_tickers(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Search for stock tickers/symbols by company name or symbol.
    Use this when the user mentions investing, stocks, or specific companies.
    
    Args:
        query: Company name or ticker symbol (e.g., "Apple", "AAPL", "Tesla")
        limit: Maximum number of results (default 5)
        
    Returns:
        Dictionary with matching stock symbols and basic info
    """
    try:
        results = search_tickers(query, limit=limit)
        stocks_data = []
        
        for res in results:
            ticker = res.get("ticker")
            details = get_ticker_details(ticker)
            snapshot = get_snapshot_ticker(ticker)
            
            # Calculate price from available data
            price = 0
            if snapshot.get("lastTrade"):
                price = snapshot.get("lastTrade", {}).get("p", 0)
            elif snapshot.get("day"):
                price = snapshot.get("day", {}).get("c", 0)
            
            stocks_data.append({
                "symbol": ticker,
                "name": res.get("name") or details.get("name", ticker),
                "price": price,
                "change": snapshot.get("todaysChange", 0),
                "change_percent": snapshot.get("todaysChangePerc", 0),
                "description": details.get("description", "")[:300] + "..." if details.get("description") and len(details.get("description", "")) > 300 else details.get("description", ""),
                "trend": "UP" if snapshot.get("todaysChange", 0) > 0 else "DOWN"
            })
        
        return {
            "query": query,
            "results": stocks_data,
            "count": len(stocks_data)
        }
    except Exception as e:
        return {"error": str(e), "results": []}


@tool
def get_stock_yahoo_data(ticker: str, data_type: str = "full") -> Dict[str, Any]:
    """
    Get comprehensive stock data from Yahoo Finance.
    Use this for detailed stock analysis, charts, and financial ratios.
    
    Args:
        ticker: Stock symbol (e.g., "AAPL", "MSFT", "TSLA")
        data_type: Type of data to retrieve (info, chart, financials, recommendations, or full)
        
    Returns:
        Dictionary with stock information, historical data, and financial ratios
    """
    try:
        if data_type == "info":
            return get_stock_info(ticker)
        elif data_type == "chart":
            return get_historical_data(ticker)
        elif data_type == "financials":
            return get_financial_ratios(ticker)
        elif data_type == "recommendations":
            return get_recommendations(ticker)
        else:  # full
            info = get_stock_info(ticker)
            chart = get_historical_data(ticker)
            
            # Optimization: Limit data for LLM context to prevent token overflow
            # 1. Limit chart to last 5 days
            if isinstance(chart, dict) and "data" in chart:
                chart["data"] = chart["data"][-5:]
                chart["note"] = "Data limited for context optimization"
                
            # 2. Truncate long descriptions
            if info and "business_summary" in info:
                summary = info["business_summary"]
                if len(summary) > 500:
                    info["business_summary"] = summary[:500] + "..."
            
            return {
                "info": info,
                "chart": chart,
                "financials": get_financial_ratios(ticker),
                "recommendations": get_recommendations(ticker)
            }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@tool
def analyze_financial_behavior(transactions: List[Dict[str, Any]], income: float, balance: float) -> Dict[str, Any]:
    """
    Analyze user's financial behavior and classify their persona.
    Use this to determine if the user is a spender, keeper, or neutral.
    
    Args:
        transactions: List of transaction records
        income: User's monthly or total income
        balance: Current account balance
        
    Returns:
        Dictionary with persona classification and insights
    """
    try:
        # Calculate spending metrics
        expenses = sum([t.get("amount", 0) for t in transactions if t.get("category") != "Income"])
        essential_spending = sum([t.get("amount", 0) for t in transactions if t.get("category") in ["Rent", "Utilities", "Groceries"]])
        non_essential_spending = expenses - essential_spending
        
        savings_rate = (income - expenses) / income if income > 0 else 0
        
        # Classify persona
        if savings_rate > 0.3:
            persona = "keeper"
            insight = "Taux d'épargne élevé, habitudes de dépenses conservatrices"
        elif savings_rate < 0.1:
            persona = "spender"
            insight = "Faible taux d'épargne, dépenses discrétionnaires plus élevées"
        else:
            persona = "neutral"
            insight = "Comportement financier équilibré"
        
        # Determine purchasing power
        if balance > income * 3:
            purchasing_power = "premium"
        elif balance > income:
            purchasing_power = "mid-range"
        else:
            purchasing_power = "budget"
        
        return {
            "persona": persona,
            "purchasing_power": purchasing_power,
            "insight": insight,
            "savings_rate": round(savings_rate * 100, 1),
            "income": income,
            "balance": balance,
            "total_expenses": expenses,
            "essential_spending": essential_spending,
            "non_essential_spending": non_essential_spending
        }
    except Exception as e:
        return {"error": str(e), "persona": "neutral", "purchasing_power": "mid-range"}


@tool
def generate_recommendation_decision(
    asset_type: str,
    assets: List[Dict[str, Any]],
    persona: str,
    budget: float,
    graph_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Generate BUY/HOLD/SELL recommendations for assets.
    Use this to make investment or purchase recommendations based on user profile.
    
    Args:
        asset_type: Type of asset (car, house, stock, investment)
        assets: List of asset data to evaluate
        persona: User persona (spender/keeper/neutral)
        budget: User's available budget
        graph_context: Optional Neo4j graph context for GraphRAG
        
    Returns:
        Dictionary with recommendations and explanations
    """
    try:
        recommendations = []
        
        if asset_type == "STOCK":
            for asset in assets:
                symbol = asset.get("symbol", "Inconnu")
                price = asset.get("price", 0)
                change = asset.get("change_percent", 0)
                
                # Simple logic for stock decision
                if change > 2:
                    decision = "ACHETER"
                    reason = f"Forte dynamique haussière ({change:.2f}%). L'action montre une tendance positive robuste."
                elif change > 0:
                    decision = "CONSERVER"
                    reason = f"Performance stable ({change:.2f}%). Potentiel de croissance modéré à court terme."
                elif change > -2:
                    decision = "CONSERVER"
                    reason = f"Légère correction ({change:.2f}%). Fondamentaux solides, surveillez les points d'entrée."
                else:
                    decision = "ATTENDRE"
                    reason = f"Tendance baissière ({change:.2f}%). Risque élevé à court terme, attendez une stabilisation."
                    
                recommendations.append({
                    "asset": symbol,
                    "decision": decision,
                    "reason": reason,
                    "investment_return": 12.5 # Rendement standard demandé
                })
        else:
            # For general investments
            for asset in assets:
                name = asset.get("name", asset.get("symbol", "Actif"))
                price = asset.get("price", 0)
                
                if price <= budget and budget > 0:
                    decision = "ACHETER"
                    reason = f"Le prix ({price} TND) correspond parfaitement à votre budget."
                elif price <= budget * 1.2:
                    decision = "SURVEILLER"
                    reason = f"Le prix ({price} TND) est légèrement supérieur à votre budget."
                else:
                    decision = "ATTENDRE"
                    reason = f"Le prix ({price} TND) dépasse significativement votre allocation actuelle."
                    
                recommendations.append({
                    "asset": name,
                    "decision": decision,
                    "reason": reason,
                    "investment_return": 12.5
                })
        
        return {
            "recommendations": recommendations,
            "asset_type": asset_type,
            "persona": persona,
            "budget": budget,
            "graph_context_used": graph_context is not None
        }
    except Exception as e:
        return {"error": str(e), "recommendations": []}


# Tool list for easy import
TOOLS = [
    get_user_profile,
    get_user_transactions,
    query_neo4j_graph,
    scrape_car_listings,
    scrape_real_estate_listings,
    search_stock_tickers,
    get_stock_yahoo_data,
    analyze_financial_behavior,
    generate_recommendation_decision,
]
