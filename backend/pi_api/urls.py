from django.urls import path
from .views import (
    ChatAPIView, StockSearchAPIView, StockDetailAPIView,
    DashboardAPIView, YahooFinanceAPIView,
    StockStrategyAPIView, StockAggregatesAPIView, TrendingTickersAPIView,
    TransactionsAPIView, LSTMPredictionAPIView
)

urlpatterns = [
    path('dashboard/<str:user_id>/', DashboardAPIView.as_view(), name='dashboard-data'),
    path('transactions/<str:user_id>/', TransactionsAPIView.as_view(), name='user-transactions'),
    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('stocks/trending/', TrendingTickersAPIView.as_view(), name='stock-trending'),
    path('stocks/search/', StockSearchAPIView.as_view(), name='stock-search'),
    path('stocks/<str:ticker>/', StockDetailAPIView.as_view(), name='stock-detail'),
    path('stocks/<str:ticker>/aggregates/', StockAggregatesAPIView.as_view(), name='stock-aggregates'),
    path('stocks/<str:ticker>/yahoo/', YahooFinanceAPIView.as_view(), name='stock-yahoo'),
    path('stocks/<str:ticker>/strategy/', StockStrategyAPIView.as_view(), name='stock-strategy'),
    path('stocks/<str:ticker>/predict/', LSTMPredictionAPIView.as_view(), name='stock-predict'),
]
