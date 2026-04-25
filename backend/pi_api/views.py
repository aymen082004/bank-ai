from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from asgiref.sync import async_to_sync
import json
import os
import tempfile
from pi_integration.main import create_graph
from pi_integration.pi_utils.stock_api import search_tickers, get_ticker_details, get_snapshot_ticker, get_related_companies, get_stock_details
from pi_integration.pi_utils.yahoo_finance import get_stock_info, get_historical_data, get_financial_ratios, get_recommendations
from pi_integration.pi_utils.db_mongo import mcp_handle
from pi_integration.pi_utils.voice import transcribe_tunisian, normalize_intent

# Initialize LangGraph app once
app = create_graph()

class DashboardAPIView(APIView):
    """
    Endpoint for fetching dashboard data (liquidity, budget, etc.) from MongoDB.
    """
    def get(self, request, user_id):
        try:
            # Fetch user profile/account data
            res = mcp_handle({
                "action": "fetch",
                "collection": "accounts",
                "filter": {"user_id": user_id}
            })
            
            if res.get("status") == "success" and res.get("data"):
                account_data = res.get("data")[0]
            else:
                # User not found in MongoDB - return error
                return Response({"error": "User not found", "user_id": user_id}, status=status.HTTP_404_NOT_FOUND)

            # Sync to Neo4j for graph analysis
            try:
                from pi_integration.pi_utils.db_neo4j import neo4j_handler
                neo4j_handler.sync_user_from_mongodb(account_data)
                # Also sync transactions if available
                txn_result = mcp_handle({
                    "action": "fetch",
                    "collection": "transactions",
                    "filter": {"user_id": user_id}
                })
                if txn_result.get("status") == "success" and txn_result.get("data"):
                    neo4j_handler.sync_transactions_to_neo4j(user_id, txn_result["data"])
            except Exception as neo_err:
                print(f"⚠️ Neo4j sync warning (non-critical): {neo_err}")
            
            return Response(account_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatAPIView(APIView):
    """
    Endpoint for handling chat (text/voice transcribed text).
    """
    def post(self, request):
        user_input = request.data.get("message", "")
        user_id = request.data.get("user_id", "default_user")
        
        if not user_input:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        initial_state = {
            "user_id": user_id,
            "user_input": user_input,
            "profile": {},
            "persona": "neutral",
            "listings": [],
            "stocks": [],
            "recommendations": [],
            "explanation": "",
            "executed": False
        }
        
        try:
            print(f"🤖 Processing message for {user_id}: {user_input}")
            # Use async_to_sync to call the async graph
            final_state = async_to_sync(app.ainvoke)(initial_state)
            
            print(f"✅ State after processing:")
            print(f"   - Profile: {final_state.get('profile')}")
            print(f"   - Persona: {final_state.get('persona')}")
            print(f"   - Listings count: {len(final_state.get('listings', []))}")
            
            return Response({
                "response": final_state.get("explanation"),
                "recommendations": final_state.get("recommendations"),
                "stocks": final_state.get("stocks"),
                "listings": final_state.get("listings"),
                "profile": final_state.get("profile"),
                "persona": final_state.get("persona")
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VoiceAPIView(APIView):
    """
    Endpoint for receiving audio and returning transcription.
    """
    parser_classes = [MultiPartParser]

    def post(self, request):
        if 'audio' not in request.FILES:
            return Response({"error": "Audio file is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        audio_file = request.FILES['audio']
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            for chunk in audio_file.chunks():
                temp_audio.write(chunk)
            temp_path = temp_audio.name

        try:
            # Transcribe using Whisper
            transcription = transcribe_tunisian(temp_path)
            
            # Clean up
            os.remove(temp_path)
            
            return Response({"transcription": transcription})
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockSearchAPIView(APIView):
    """
    Endpoint for searching stocks directly.
    Uses Yahoo Finance autocomplete for high-performance propositions.
    """
    def get(self, request):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        from pi_integration.pi_utils.yahoo_finance import search_stocks
        try:
            # 1. Get rapid autocomplete propositions from Yahoo
            search_data = search_stocks(query)
            results = search_data.get("results", [])
            
            # 2. Enrich with basic snapshot data for the propositions
            stocks_data = []
            for res in results[:8]: # Limit for speed
                symbol = res.get("symbol")
                stocks_data.append({
                    "symbol": symbol,
                    "name": res.get("name"),
                    "exchange": res.get("exchange"),
                    "type": res.get("type"),
                    "price": 0, # Frontend will handle price if needed
                    "change": 0,
                    "change_percent": 0,
                    "trend": "UP"
                })
            return Response(stocks_data)
        except Exception as e:
            print(f"Search view error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockDetailAPIView(APIView):
    """
    Endpoint for getting stock detail information using Massive API with Yahoo fallback.
    """
    def get(self, request, ticker):
        try:
            # 1. Try Massive API for institutional details
            data = get_stock_details(ticker)
            
            # 2. If Massive API fails or returns zero price, fallback to Yahoo Finance
            if not data or data.get("price") == 0 or "error" in data:
                print(f"⚠️ Massive API fallback for {ticker}...")
                yahoo_info = get_stock_info(ticker)
                
                if not yahoo_info.get("error"):
                    # Merge or use Yahoo data
                    if not data or "error" in data:
                        data = {
                            "symbol": ticker.upper(),
                            "name": yahoo_info.get("name"),
                            "price": yahoo_info.get("price"),
                            "change": yahoo_info.get("change"),
                            "change_percent": yahoo_info.get("change_percent"),
                            "market": "stocks",
                            "type": "CS",
                            "currency": yahoo_info.get("currency"),
                            "status": "Active",
                            "listed": "N/A",
                            "exchange": yahoo_info.get("exchange", "N/A"),
                            "employees": yahoo_info.get("employees", 0),
                            "website": yahoo_info.get("website", "N/A"),
                            "description": yahoo_info.get("business_summary", "Aucune description disponible."),
                            "related_companies": get_related_companies(ticker)
                        }
                    else:
                        # Just update the price/change if Massive details were OK but price was 0
                        data["price"] = yahoo_info.get("price")
                        data["change"] = yahoo_info.get("change")
                        data["change_percent"] = yahoo_info.get("change_percent")
                        if data.get("description") == "Aucune description disponible.":
                            data["description"] = yahoo_info.get("business_summary")

            if not data or ("error" in data and not yahoo_info):
                return Response({"error": "Stock not found"}, status=status.HTTP_404_NOT_FOUND)
                
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockAggregatesAPIView(APIView):
    """
    Endpoint for getting aggregate stock data (for candlestick charts).
    Uses Yahoo Finance historical data as a reliable free source.
    """
    def get(self, request, ticker):
        from pi_integration.pi_utils.yahoo_finance import get_historical_data
        
        period = request.query_params.get("period", "3mo")
        interval = request.query_params.get("interval", "1d")
        
        try:
            # Get historical data from Yahoo Finance
            hist_data = get_historical_data(ticker, period=period, interval=interval)
            
            if hist_data.get("error"):
                return Response({"error": hist_data.get("error")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Format for Lightweight Charts Candlestick Series
            # Expected: { time: 'YYYY-MM-DD', open: 75.16, high: 82.84, low: 36.16, close: 45.72 }
            chart_data = []
            for r in hist_data.get("data", []):
                chart_data.append({
                    "time": r['date'],
                    "open": r['open'],
                    "high": r['high'],
                    "low": r['low'],
                    "close": r['close']
                })
            
            return Response(chart_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class YahooFinanceAPIView(APIView):
    """
    Endpoint for getting Yahoo Finance data (free alternative for charts and financials).
    """
    def get(self, request, ticker):
        data_type = request.query_params.get("type", "full")
        
        try:
            if data_type == "info":
                data = get_stock_info(ticker)
            elif data_type == "chart":
                period = request.query_params.get("period", "1y")
                interval = request.query_params.get("interval", "1d")
                data = get_historical_data(ticker, period=period, interval=interval)
            elif data_type == "financials":
                data = get_financial_ratios(ticker)
            elif data_type == "recommendations":
                data = get_recommendations(ticker)
            else:  # full
                info = get_stock_info(ticker)
                chart = get_historical_data(ticker)
                financials = get_financial_ratios(ticker)
                recommendations = get_recommendations(ticker)
                data = {
                    "info": info,
                    "chart": chart,
                    "financials": financials,
                    "recommendations": recommendations
                }
            
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockStrategyAPIView(APIView):
    """
    Endpoint for getting personalized strategy recommendations using LLM.
    Analyzes stock data against user profiling (liquidity, persona, goals).
    """
    def get(self, request, ticker):
        user_id = request.query_params.get("user_id", "default_user")
        
        try:
            # 1. Fetch User Data for profiling
            user_res = mcp_handle({
                "action": "fetch",
                "collection": "accounts",
                "filter": {"user_id": user_id}
            })
            user_profile = user_res.get("data", [{}])[0] if user_res.get("data") else {}
            
            # 2. Get Stock Data
            info = get_stock_info(ticker)
            recommendations = get_recommendations(ticker)
            
            if info.get("error"):
                return Response({"error": info.get("error")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 3. Use LLM for Personalized Strategy & Explainability
            prompt = f"""
            Analysez l'action {ticker} pour l'utilisateur {user_id}.
            
            PROFIL UTILISATEUR:
            - Persona: {user_profile.get('persona', 'Neutre')}
            - Liquidité Totale: {user_profile.get('total_liquidity', 0)} TND
            - Budget Mensuel: {user_profile.get('monthly_budget', 0)} TND
            - Appétence au Risque: {user_profile.get('risk_appetite', 'Moyen')}
            
            DONNÉES BOURSIÈRES ({ticker}):
            - Prix: {info.get('price')} $
            - Ratio P/E: {info.get('pe_ratio')}
            - Bêta: {info.get('beta')}
            - Rendement Dividende: {info.get('dividend_yield')}%
            - Consensus Analystes: {recommendations.get('consensus')}
            
            TÂCHE:
            1. Fournissez une stratégie d'investissement personnalisée (ACHETER, CONSERVER ou VENDRE).
            2. Rédigez une explication COURTE et professionnelle (max 3 phrases) en FRANÇAIS expliquant POURQUOI cela correspond ou non au profil spécifique de l'utilisateur.
            3. Déterminez un niveau de risque (BAS, MOYEN, ÉLEVÉ) pour cet utilisateur.
            4. Suggérez une période de détention.
            
            Retournez UNIQUEMENT un objet JSON :
            {{
                "decision": "ACHETER/CONSERVER/VENDRE",
                "explanation": "...",
                "risk_level": "BAS/MOYEN/ÉLEVÉ",
                "holding_period": "...",
                "confidence_score": 0-100
            }}
            """
            
            from pi_integration.pi_utils.llm import call_llm
            messages = [{"role": "user", "content": prompt}]
            llm_response = call_llm(messages)
            
            # Parse LLM JSON
            import json
            import re
            match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if match:
                strategy_data = json.loads(match.group())
            else:
                raise ValueError("Failed to parse LLM response")

            # 4. Construct Final Response
            data = {
                "symbol": ticker,
                "strategy": {
                    "type": strategy_data["decision"],
                    "description": strategy_data["explanation"],
                    "risk_level": strategy_data["risk_level"],
                    "holding_period": strategy_data["holding_period"],
                    "confidence": strategy_data["confidence_score"]
                },
                "analyst_consensus": recommendations,
                "key_metrics": {
                    "pe_ratio": info.get("pe_ratio"),
                    "pb_ratio": info.get("pb_ratio"),
                    "dividend_yield": info.get("dividend_yield"),
                    "beta": info.get("beta")
                }
            }
            
            return Response(data)
        except Exception as e:
            print(f"Error in personalized strategy: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrendingTickersAPIView(APIView):
    """
    Endpoint for fetching trending tickers (stocks/crypto) for the dashboard.
    """
    def get(self, request):
        from pi_integration.pi_utils.yahoo_finance import get_trending_tickers
        try:
            trending_data = get_trending_tickers()
            return Response(trending_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransactionsAPIView(APIView):
    """
    Endpoint for fetching user transactions from MongoDB.
    Returns expenses, incomes, and transaction history.
    """
    def get(self, request, user_id):
        try:
            # Fetch transactions from MongoDB
            txn_result = mcp_handle({
                "action": "fetch",
                "collection": "transactions",
                "filter": {"user_id": user_id}
            })

            if txn_result.get("status") != "success":
                return Response({"error": "Failed to fetch transactions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            transactions = txn_result.get("data", [])

            # Calculate totals
            expenses = [t for t in transactions if t.get("amount", 0) > 0]
            total_expenses = sum(t.get("amount", 0) for t in expenses)

            # Group expenses by category
            categories = {}
            for t in expenses:
                cat = t.get("category", "Other")
                if cat not in categories:
                    categories[cat] = {"total": 0, "count": 0, "transactions": []}
                categories[cat]["total"] += t.get("amount", 0)
                categories[cat]["count"] += 1
                categories[cat]["transactions"].append(t)

            # Sort by amount descending
            sorted_categories = sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True)

            # Format recent transactions (last 10)
            recent_transactions = sorted(transactions, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]

            # Format for response
            formatted_transactions = []
            for t in recent_transactions:
                formatted_transactions.append({
                    "id": str(t.get("_id", "")),
                    "amount": t.get("amount", 0),
                    "category": t.get("category", "Other"),
                    "description": t.get("description", ""),
                    "type": t.get("type", "expense"),
                    "timestamp": t.get("timestamp", ""),
                    "date": t.get("timestamp", "")[:10] if t.get("timestamp") else ""
                })

            return Response({
                "transactions": formatted_transactions,
                "total_expenses": total_expenses,
                "expense_count": len(expenses),
                "categories": [
                    {
                        "name": cat[0],
                        "total": cat[1]["total"],
                        "count": cat[1]["count"],
                        "percentage": round((cat[1]["total"] / total_expenses * 100), 1) if total_expenses > 0 else 0
                    }
                    for cat in sorted_categories
                ],
                "user_id": user_id
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LSTMPredictionAPIView(APIView):
    """
    Endpoint for LSTM-based stock price predictions.
    Uses Hugging Face model: jengyang/lstm-stock-prediction-model
    """
    def get(self, request, ticker):
        from pi_integration.pi_utils.lstm_predictor import predict_stock_prices
        from pi_integration.pi_utils.yahoo_finance import get_historical_data
        
        days = int(request.query_params.get("days", 90))
        
        try:
            print(f"DEBUG: LSTM Prediction requested for {ticker}")
            # Fetch historical data from Yahoo Finance
            hist_data = get_historical_data(ticker, period="1y", interval="1d")
            
            if hist_data.get("error"):
                print(f"DEBUG: Historical data error for {ticker}: {hist_data.get('error')}")
                return Response({
                    "error": f"Market data error: {hist_data.get('error')}",
                    "symbol": ticker.upper()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            historical_prices = hist_data.get("data", [])
            print(f"DEBUG: Found {len(historical_prices)} historical prices for {ticker}")
            
            if not historical_prices or len(historical_prices) < 10:
                print(f"DEBUG: Insufficient data for {ticker}: {len(historical_prices)} days")
                return Response({
                    "error": f"Insufficient historical data (found {len(historical_prices)} days, need at least 10)",
                    "symbol": ticker.upper()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate LSTM predictions
            print(f"DEBUG: Calling predict_stock_prices for {ticker}")
            predictions = predict_stock_prices(ticker, historical_prices, days=days)
            
            if predictions.get("error"):
                print(f"DEBUG: Predictor error for {ticker}: {predictions.get('error')}")
                return Response(predictions, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            print(f"DEBUG: Prediction successful for {ticker}")
            return Response(predictions)
            
        except Exception as e:
            print(f"LSTM Prediction API error for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": str(e),
                "symbol": ticker.upper()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
