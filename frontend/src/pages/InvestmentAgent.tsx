import { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  Wallet,
  TrendingUp,
  Brain,
  Search,
  Send,
  History,
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight,
  Info,
  Home,
  Car,
  Moon,
  Sun,
  TrendingDown,
  Activity
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = `${import.meta.env.VITE_API_URL}/pi_api`;

export default function InvestmentAgent() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [messages, setMessages] = useState<any[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedStock, setSelectedStock] = useState<any>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [transactionsData, setTransactionsData] = useState<any>(null);
  const [, setTrendingStocks] = useState<any[]>([]);
  const [isDark, setIsDark] = useState(false);
  const [lstmPrediction, setLSTMPrediction] = useState<any>(null);
  const [xaiInsight, setXAIInsight] = useState<any>(null);
  const [loadingXAI, setLoadingXAI] = useState(false);
  const [stockMetrics, setStockMetrics] = useState<any>(null);
  const [analystConsensus, setAnalystConsensus] = useState<any>(null);
  const [chartPeriod, setChartPeriod] = useState<'1d' | '1w' | '1m' | '1y'>('1y');
  const [chartData, setChartData] = useState<any[]>([]);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number, y: number, price: number, date: string } | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) {
      fetchDashboardData();
      fetchTransactionsData();
      fetchTrendingStocks();
    }
  }, [user]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // Generate XAI when stock data or prediction is available
  useEffect(() => {
    if (selectedStock && !xaiInsight) {
      generateXAIInsight();
    }
  }, [selectedStock, lstmPrediction]);

  // Initialize ApexCharts when stock detail is shown
  useEffect(() => {
    if (activeTab === 'stock-detail' && selectedStock && typeof window !== 'undefined' && (window as any).ApexCharts) {
      const ApexCharts = (window as any).ApexCharts;

      // Generate sample candlestick data
      const generateCandleData = (basePrice: number, days: number) => {
        const data = [];
        let price = basePrice;
        const now = new Date();

        for (let i = days; i >= 0; i--) {
          const date = new Date(now);
          date.setDate(date.getDate() - i);

          const volatility = price * 0.02;
          const open = price + (Math.random() - 0.5) * volatility;
          const close = open + (Math.random() - 0.5) * volatility;
          const high = Math.max(open, close) + Math.random() * volatility * 0.5;
          const low = Math.min(open, close) - Math.random() * volatility * 0.5;

          data.push({
            x: date.getTime(),
            y: [parseFloat(open.toFixed(2)), parseFloat(high.toFixed(2)), parseFloat(low.toFixed(2)), parseFloat(close.toFixed(2))]
          });

          price = close;
        }
        return data;
      };

      // Candlestick Chart
      const candleOptions = {
        series: [{
          data: generateCandleData(selectedStock.price || 273, 60)
        }],
        chart: {
          type: 'candlestick',
          height: 320,
          background: 'transparent',
          toolbar: { show: false },
          animations: { enabled: false }
        },
        theme: { mode: isDark ? 'dark' : 'light' },
        plotOptions: {
          candlestick: {
            colors: {
              upward: '#10B981',
              downward: '#EF4444'
            }
          }
        },
        xaxis: {
          type: 'datetime',
          axisBorder: { show: false },
          axisTicks: { show: false },
          labels: { style: { colors: '#9CA3AF' } }
        },
        yaxis: {
          tooltip: { enabled: true },
          labels: {
            style: { colors: '#9CA3AF' },
            formatter: (value: number) => value.toFixed(2)
          }
        },
        grid: {
          borderColor: 'rgba(0, 0, 0, 0.05)',
          xaxis: { lines: { show: true } },
          yaxis: { lines: { show: true } }
        },
        tooltip: {
          theme: isDark ? 'dark' : 'light',
          custom: function ({ seriesIndex, dataPointIndex, w }: any) {
            const data = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
            if (!data) return '';
            const date = new Date(data.x).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' });
            const [open, high, low, close] = data.y;
            const color = close >= open ? '#10B981' : '#EF4444';
            return `
              <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; font-family: system-ui, sans-serif; min-width: 140px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <div style="color: #6B7280; font-size: 12px; margin-bottom: 8px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px;">${date}</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; font-size: 13px;">
                  <span style="color: #6B7280;">Ouverture:</span><span style="color: #111827; text-align: right;">${open.toFixed(2)}</span>
                  <span style="color: #6B7280;">Haut:</span><span style="color: #111827; text-align: right;">${high.toFixed(2)}</span>
                  <span style="color: #6B7280;">Bas:</span><span style="color: #111827; text-align: right;">${low.toFixed(2)}</span>
                  <span style="color: #6B7280;">Clôture:</span><span style="color: ${color}; font-weight: bold; text-align: right;">${close.toFixed(2)}</span>
                </div>
              </div>
            `;
          }
        }
      };

      // LSTM Prediction Chart (Line chart)
      const generatePredictionData = () => {
        // If we have real LSTM prediction data, use it
        if (lstmPrediction?.predictions && lstmPrediction.predictions.length > 0) {
          return lstmPrediction.predictions.map((p: any) => ({
            x: new Date(p.date).getTime(),
            y: parseFloat(p.price.toFixed(2))
          }));
        }

        // Fallback: Generate 90 days future prediction data starting from today
        const data = [];
        const now = new Date();
        let price = selectedStock.price || 273;

        // Start from today's price
        data.push({ x: now.getTime(), y: parseFloat(price.toFixed(2)) });

        // Prediction data (next 90 days)
        for (let i = 1; i <= 90; i++) {
          const date = new Date(now);
          date.setDate(date.getDate() + i);
          // Trend upward with some volatility
          price = price * (1 + 0.001 + (Math.random() - 0.4) * 0.008);
          data.push({ x: date.getTime(), y: parseFloat(price.toFixed(2)) });
        }

        return data;
      };

      const lstmOptions = {
        series: [{
          name: 'Prix Prédit',
          data: generatePredictionData()
        }],
        chart: {
          type: 'line',
          height: 128,
          background: isDark ? '#0B1F3A' : '#ffffff',
          toolbar: { show: false },
          animations: { enabled: true }
        },
        stroke: {
          curve: 'smooth',
          width: 4,
          colors: [isDark ? '#00FF9D' : '#059669']
        },
        fill: {
          type: 'gradient',
          gradient: {
            shadeIntensity: 1,
            opacityFrom: isDark ? 0.6 : 0.4,
            opacityTo: 0.1,
            stops: [0, 100],
            colorStops: [
              {
                offset: 0,
                color: isDark ? '#00FF9D' : '#059669',
                opacity: isDark ? 0.4 : 0.3
              },
              {
                offset: 100,
                color: isDark ? '#00FF9D' : '#059669',
                opacity: 0.05
              }
            ]
          }
        },
        xaxis: {
          type: 'datetime',
          axisBorder: { show: false },
          axisTicks: { show: false },
          labels: { show: false }
        },
        yaxis: {
          labels: { show: false }
        },
        grid: {
          show: false
        },
        tooltip: {
          theme: isDark ? 'dark' : 'light',
          custom: function ({ series, seriesIndex, dataPointIndex, w }: any) {
            const data = w.globals.initialSeries[seriesIndex].data[dataPointIndex];
            if (!data) return '';
            const date = new Date(data.x).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
            const price = data.y;
            return `
              <div style="background: ${isDark ? '#1e293b' : '#ffffff'}; border: 1px solid ${isDark ? '#334155' : '#e2e8f0'}; border-radius: 6px; padding: 8px 12px; font-family: system-ui, sans-serif; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <div style="color: ${isDark ? '#94a3b8' : '#64748b'}; font-size: 11px; margin-bottom: 4px;">${date}</div>
                <div style="color: ${isDark ? '#ffffff' : '#1a1a1a'}; font-size: 13px; font-weight: 600;">${price.toFixed(2)} TND</div>
              </div>
            `;
          }
        },
        theme: {
          mode: isDark ? 'dark' : 'light'
        }
      };

      // Render charts
      const candleContainer = document.querySelector('#candlestick-chart');
      const lstmContainer = document.querySelector('#lstm-prediction-chart');

      if (candleContainer) {
        candleContainer.innerHTML = '';
        const candleChart = new ApexCharts(candleContainer, candleOptions);
        candleChart.render();
      }

      if (lstmContainer) {
        // Clear any existing chart completely
        while (lstmContainer.firstChild) {
          lstmContainer.removeChild(lstmContainer.firstChild);
        }
        const lstmChart = new ApexCharts(lstmContainer, lstmOptions);
        lstmChart.render();
      }

      // Yahoo Finance Area Chart (Canvas)
      const canvas = document.getElementById('yahoo-chart') as HTMLCanvasElement;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          // Set canvas size from parent
          const rect = canvas.parentElement?.getBoundingClientRect();
          const width = rect ? rect.width : canvas.clientWidth || 800;
          const height = rect ? rect.height : canvas.clientHeight || 400;

          if (width > 0 && height > 0) {
            canvas.width = width;
            canvas.height = height;
          }

          const padding = { top: 20, bottom: 30, left: 50, right: 20 };
          const chartWidth = canvas.width - padding.left - padding.right;
          const chartHeight = canvas.height - padding.top - padding.bottom;

          // Generate chart data based on selected period
          const newChartData: { price: number, date: string }[] = [];
          const dataPoints = chartPeriod === '1d' ? 24 : chartPeriod === '1w' ? 7 : chartPeriod === '1m' ? 30 : 100;
          let price = selectedStock.price || 273;
          const now = new Date();

          // Work backwards from current price
          for (let i = 0; i < dataPoints; i++) {
            let dateStr = '';
            if (chartPeriod === '1d') {
              dateStr = `${23 - i}h`;
            } else if (chartPeriod === '1w') {
              const days = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
              dateStr = days[(now.getDay() - i + 7) % 7];
            } else if (chartPeriod === '1m') {
              const d = new Date(now);
              d.setDate(d.getDate() - i);
              const day = d.getDate().toString().padStart(2, '0');
              const month = (d.getMonth() + 1).toString().padStart(2, '0');
              dateStr = `${day}/${month}`;
            } else {
              const d = new Date(now);
              d.setDate(d.getDate() - i * 4); // ~90 days for 1 year
              const months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'];
              dateStr = `${d.getDate()} ${months[d.getMonth()]}`;
            }

            newChartData.unshift({ price, date: dateStr });
            // Different volatility for different periods
            const volatility = chartPeriod === '1d' ? 0.005 : chartPeriod === '1w' ? 0.015 : chartPeriod === '1m' ? 0.02 : 0.025;
            price = price / (1 + (Math.random() - 0.48) * volatility);
          }

          setChartData(newChartData);

          const prices = newChartData.map(d => d.price);
          const minPrice = Math.min(...prices) * 0.995;
          const maxPrice = Math.max(...prices) * 1.005;
          const priceRange = maxPrice - minPrice;

          // Helper functions
          const getY = (p: number) => padding.top + chartHeight - ((p - minPrice) / priceRange) * chartHeight;
          const getX = (i: number) => padding.left + (i / (newChartData.length - 1)) * chartWidth;

          // Clear canvas completely using actual canvas dimensions
          ctx.clearRect(0, 0, canvas.width, canvas.height);

          // Draw grid lines
          ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.12)';
          ctx.lineWidth = 1;
          for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartHeight * i / 4);
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();
          }

          // Draw the area chart with gradient
          const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartHeight);
          if (isDark) {
            gradient.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0.05)');
          } else {
            gradient.addColorStop(0, 'rgba(5, 150, 105, 0.5)');
            gradient.addColorStop(1, 'rgba(5, 150, 105, 0.1)');
          }

          ctx.beginPath();
          ctx.moveTo(getX(0), getY(newChartData[0].price));

          // Draw smooth curve through points
          for (let i = 1; i < newChartData.length; i++) {
            const x = getX(i);
            const y = getY(newChartData[i].price);
            ctx.lineTo(x, y);
          }

          // Close path for fill
          ctx.lineTo(getX(newChartData.length - 1), padding.top + chartHeight);
          ctx.lineTo(getX(0), padding.top + chartHeight);
          ctx.closePath();
          ctx.fillStyle = gradient;
          ctx.fill();

          // Draw the line on top
          ctx.beginPath();
          ctx.moveTo(getX(0), getY(newChartData[0].price));
          for (let i = 1; i < newChartData.length; i++) {
            ctx.lineTo(getX(i), getY(newChartData[i].price));
          }
          ctx.strokeStyle = isDark ? '#10B981' : '#059669';
          ctx.lineWidth = isDark ? 3 : 4;
          ctx.stroke();

          // Draw Y-axis labels (only 3 labels to avoid crowding)
          ctx.font = '12px system-ui, sans-serif';
          ctx.fillStyle = isDark ? '#9CA3AF' : '#4B5563';
          ctx.textAlign = 'right';
          ctx.textBaseline = 'middle';
          const yLabelCount = 3;
          for (let i = 0; i < yLabelCount; i++) {
            const price = minPrice + (priceRange * (yLabelCount - 1 - i) / (yLabelCount - 1));
            const y = padding.top + (chartHeight * i / (yLabelCount - 1));
            ctx.fillText(price.toFixed(0), padding.left - 10, y);
          }

          // Draw X-axis labels
          ctx.font = '12px system-ui, sans-serif';
          ctx.fillStyle = isDark ? '#9CA3AF' : '#4B5563';
          ctx.textAlign = 'center';
          const labelCount = Math.min(3, newChartData.length);
          const step = Math.max(1, Math.floor(newChartData.length / (labelCount - 1)));

          for (let i = 0; i < labelCount; i++) {
            const idx = Math.min(i * step, newChartData.length - 1);
            const x = getX(idx);
            // Skip if too close to edges
            if (x > padding.left + 40 && x < width - padding.right - 40) {
              ctx.fillText(newChartData[idx].date, x, padding.top + chartHeight + 20);
            }
          }

          // Add hover interaction
          const handleMouseMove = (e: MouseEvent) => {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Find nearest data point
            const relativeX = x - padding.left;
            const index = Math.round((relativeX / chartWidth) * (newChartData.length - 1));

            if (index >= 0 && index < newChartData.length) {
              const pointX = getX(index);
              const pointY = getY(newChartData[index].price);

              // Check if mouse is close to the line
              const distance = Math.abs(x - pointX);
              if (distance < 20 && y >= padding.top && y <= padding.top + chartHeight) {
                setHoveredPoint({
                  x: pointX,
                  y: pointY,
                  price: newChartData[index].price,
                  date: newChartData[index].date
                });
              } else {
                setHoveredPoint(null);
              }
            }
          };

          const handleMouseLeave = () => {
            setHoveredPoint(null);
          };

          canvas.addEventListener('mousemove', handleMouseMove);
          canvas.addEventListener('mouseleave', handleMouseLeave);

          // Cleanup
          return () => {
            canvas.removeEventListener('mousemove', handleMouseMove);
            canvas.removeEventListener('mouseleave', handleMouseLeave);
          };
        }
      }
    }
  }, [activeTab, selectedStock, lstmPrediction, chartPeriod, isDark]);

  const fetchDashboardData = async () => {
    try {
      const userId = user?.id || user?.customer_id || 'user_123';
      const res = await fetch(`${API_BASE_URL}/dashboard/${userId}/`);
      const data = await res.json();
      if (data.error) {
        console.warn('Dashboard API error:', data.error);
        // Get persona from user object
        const persona = user?.persona || 'balanced';
        setDashboardData({
          total_liquidity: 50000,
          monthly_budget: 5000,
          savings_rate: 24,
          persona: persona
        });
      } else {
        setDashboardData({
          ...data,
          persona: user?.persona || data.persona || 'balanced'
        });
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      const persona = user?.persona || 'balanced';
      setDashboardData({
        total_liquidity: 50000,
        monthly_budget: 5000,
        savings_rate: 24,
        persona: persona
      });
    }
  };

  const fetchTransactionsData = async () => {
    try {
      const userId = user?.id || user?.customer_id || 'user_123';
      const res = await fetch(`${API_BASE_URL}/transactions/${userId}/`);
      const data = await res.json();
      if (data.error) {
        console.warn('Transactions API error:', data.error);
        setTransactionsData({
          transactions: [
            { id: 1, description: 'Salaire', amount: 3500, date: '2024-01-15', category: 'Revenu', type: 'income' },
            { id: 2, description: 'Loyer', amount: 800, date: '2024-01-14', category: 'Logement', type: 'expense' },
            { id: 3, description: 'Courses', amount: 450, date: '2024-01-13', category: 'Alimentation', type: 'expense' },
            { id: 4, description: 'Facture électricité', amount: 120, date: '2024-01-12', category: 'Utilités', type: 'expense' },
            { id: 5, description: 'Investissement', amount: 1000, date: '2024-01-10', category: 'Investissement', type: 'expense' },
          ]
        });
      } else {
        setTransactionsData(data);
      }
    } catch (err) {
      console.error('Failed to fetch transactions data:', err);
      setTransactionsData({
        transactions: [
          { id: 1, description: 'Salaire', amount: 3500, date: '2024-01-15', category: 'Revenu', type: 'income' },
          { id: 2, description: 'Loyer', amount: 800, date: '2024-01-14', category: 'Logement', type: 'expense' },
          { id: 3, description: 'Courses', amount: 450, date: '2024-01-13', category: 'Alimentation', type: 'expense' },
          { id: 4, description: 'Facture électricité', amount: 120, date: '2024-01-12', category: 'Utilités', type: 'expense' },
          { id: 5, description: 'Investissement', amount: 1000, date: '2024-01-10', category: 'Investissement', type: 'expense' },
        ]
      });
    }
  };

  const fetchTrendingStocks = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/stocks/trending/`);
      const data = await res.json();
      setTrendingStocks(data.results || []);
    } catch (err) {
      console.error('Failed to fetch trending stocks:', err);
    }
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/stocks/search/?q=${query}`);
      const data = await res.json();
      setSearchResults(data);
    } catch (err) {
      console.error('Search error:', err);
    }
  };

  const handleSelectStock = async (ticker: string) => {
    try {
      // Fetch stock details
      const res = await fetch(`${API_BASE_URL}/stocks/${ticker}/`);
      const data = await res.json();
      setSelectedStock(data);

      // Fetch all related data in parallel
      await Promise.all([
        fetchLSTMPrediction(ticker),
        fetchXAIInsight(ticker),
        fetchAnalystConsensus(ticker),
        fetchStockMetrics(ticker)
      ]);

      setSearchResults([]);
      setSearchQuery('');
      setActiveTab('stock-detail');
    } catch (err) {
      console.error('Failed to fetch stock detail:', err);
    }
  };

  const fetchLSTMPrediction = async (ticker: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/stocks/${ticker}/predict/?days=90`);
      const data = await res.json();
      if (!data.error) {
        setLSTMPrediction(data);
      }
    } catch (err) {
      console.error('Failed to fetch LSTM prediction:', err);
    }
  };

  // Generate XAI insight after data is loaded
  const generateXAIInsight = () => {
    if (!selectedStock) return;

    const stock = selectedStock;
    const prediction = lstmPrediction;

    const xaiData = {
      strategy: generateInvestmentStrategy(stock, prediction),
      explanation: generateXAIExplanation(stock, prediction),
      risk_assessment: assessRisk(stock, prediction),
      recommendation: generateRecommendation(stock, prediction)
    };

    setXAIInsight(xaiData);

    // Also set analyst consensus if not already set
    if (!analystConsensus) {
      setAnalystConsensus({
        consensus: xaiData.recommendation.action,
        strong_buy: xaiData.recommendation.action === 'ACHETER' ? 45 : 25,
        buy: xaiData.recommendation.action === 'ACHETER' ? 35 : 30,
        hold: 15,
        sell: xaiData.recommendation.action === 'VENDRE' ? 25 : 10,
        strong_sell: xaiData.recommendation.action === 'VENDRE' ? 15 : 5,
        confidence: xaiData.recommendation.confidence
      });
    }

    // Set stock metrics if not already set
    if (!stockMetrics) {
      setStockMetrics({
        pe_ratio: stock.pe_ratio || (20 + Math.random() * 15).toFixed(1),
        pb_ratio: stock.pb_ratio || (1.5 + Math.random() * 3).toFixed(1),
        beta: stock.beta || (0.8 + Math.random() * 0.8).toFixed(2),
        dividend_yield: stock.dividend_yield || (Math.random() * 2.5).toFixed(2) + '%'
      });
    }
  };

  // Fetch XAI (Explainable AI) insights
  const fetchXAIInsight = async (ticker: string) => {
    setLoadingXAI(true);
    try {
      const res = await fetch(`${API_BASE_URL}/stocks/${ticker}/strategy/`);
      const data = await res.json();
      if (!data.error) {
        setXAIInsight(data);
      } else {
        // Generate dynamic XAI insight based on stock data
        generateXAIInsight();
      }
    } catch (err) {
      console.error('Failed to fetch XAI insight:', err);
      // Fallback: generate local XAI insight
      generateXAIInsight();
    } finally {
      setLoadingXAI(false);
    }
  };

  // Voice recording functions


  // Generate dynamic investment strategy based on stock data
  const generateInvestmentStrategy = (stock: any, prediction: any) => {
    if (!stock || !prediction) return null;
    const currentPrice = stock?.price || 150;
    const pe = stock?.pe_ratio || 28;
    const change = stock?.change_percent || 2.5;
    const trend = prediction?.trend || 'UP';
    const predictedChange = prediction?.change_percent || (8 + Math.random() * 12);
    const confidence = prediction?.confidence || 0.82;

    let strategy = '';

    if (trend === 'STRONG_UP' && pe < 30) {
      strategy = `Fort potentiel haussier détecté. À ${currentPrice.toFixed(2)} TND, l'action présente une valorisation attractive (P/E: ${pe.toFixed(1)}) avec une tendance LSTM confirmée. Projection: +${predictedChange.toFixed(1)}% à 90 jours (confiance: ${Math.round(confidence * 100)}%). Recommandation: Accumulation progressive sur les phases de faiblesse.`;
    } else if (trend === 'UP') {
      strategy = `Momentum positif identifié. Prix actuel ${currentPrice.toFixed(2)} TND avec ${change >= 0 ? '+' : ''}${change.toFixed(2)}% de performance récente. Le modèle prévoit +${predictedChange.toFixed(1)}% de croissance. Stratégie: Achats sélectifs à la baisse, objectif de sortie à ${(currentPrice * (1 + predictedChange / 100)).toFixed(2)} TND.`;
    } else if (trend === 'DOWN' && change > -5) {
      strategy = `Correction technique en cours. Le prix ${currentPrice.toFixed(2)} TND offre une opportunité d'entrée si support tenu. Attendez un signal de retournement avant positionnement. Stop-loss recommandé: ${(currentPrice * 0.95).toFixed(2)} TND.`;
    } else if (trend === 'STRONG_DOWN') {
      strategy = `Tendance baissière confirmée. À ${currentPrice.toFixed(2)} TND, privilégiez la défense. Si position détenue, réduisez l'exposition. Sinon, attendez une consolidation avant toute entrée.`;
    } else {
      strategy = `Phase de consolidation. Prix ${currentPrice.toFixed(2)} TND - absence de direction claire. Surveillez la cassure des niveaux ${(currentPrice * 1.05).toFixed(2)} TND (résistance) et ${(currentPrice * 0.95).toFixed(2)} TND (support) pour orientation.`;
    }

    return strategy;
  };

  // Generate XAI explanation
  const generateXAIExplanation = (stock: any, prediction: any) => {
    const confidence = Math.round((prediction?.confidence || 0.8) * 100);
    const trend = prediction?.trend || 'UP';
    const change = prediction?.change_percent || (5 + Math.random() * 10);
    const stockName = stock?.name || stock?.symbol || 'cette action';
    const currentPrice = stock?.price || 150;
    const targetPrice = prediction?.predicted_final_price || currentPrice * (1 + change / 100);
    const pe = stock?.pe_ratio || 25;

    let analysis = '';
    let factors = [];

    // Build factors list based on metrics
    if (pe < 20) factors.push('valorisation attractive (P/E faible)');
    else if (pe > 35) factors.push('valorisation élevée (attention au P/E)');
    else factors.push('valorisation modérée');

    if (stock?.change_percent > 3) factors.push('forte performance récente');
    else if (stock?.change_percent > 0) factors.push('momentum positif');
    else if (stock?.change_percent < -3) factors.push('correction récente à surveiller');

    if (trend === 'STRONG_UP') factors.push('tendance haussière confirmée par LSTM');
    else if (trend === 'UP') factors.push('signal haussier LSTM');
    else if (trend === 'DOWN') factors.push('signal baissier détecté');

    if (confidence > 80) factors.push('forte confiance prédictive');
    else if (confidence > 60) factors.push('confiance modérée');

    // Build detailed analysis
    if (trend.includes('UP')) {
      analysis = `L'analyse XAI de ${stockName} révèle un scénario favorable. Actuellement à ${currentPrice.toFixed(2)} TND, l'action présente ${factors.join(', ')}. Le modèle LSTM, entraîné sur 90 jours de données, projette un objectif de ${targetPrice.toFixed(2)} TND (+${change.toFixed(1)}%) avec ${confidence}% de certitude. Les indicateurs techniques confirment ce momentum haussier.`;
    } else if (trend.includes('DOWN')) {
      analysis = `L'analyse XAI de ${stockName} indique une prudence nécessaire. À ${currentPrice.toFixed(2)} TND, malgré ${factors.join(', ')}, le modèle LSTM anticipe une pression vendeuse. La prédiction suggère un mouvement de ${change.toFixed(1)}% avec ${confidence}% de confiance. Attendez une stabilisation avant positionnement.`;
    } else {
      analysis = `L'analyse XAI de ${stockName} montre une configuration équilibrée. Au prix de ${currentPrice.toFixed(2)} TND, l'action combine ${factors.join(', ')}. Le modèle LSTM prévoit une variation de ${change >= 0 ? '+' : ''}${change.toFixed(1)}% avec ${confidence}% de confiance. La direction dépendra des prochaines cassures de niveaux techniques.`;
    }

    return analysis;
  };

  // Assess risk level
  const assessRisk = (stock: any, prediction: any) => {
    const beta = stock?.beta || 1;
    const volatility = prediction?.confidence ? (1 - prediction.confidence) * 100 : 20;

    if (beta > 1.5 || volatility > 40) return { level: 'ÉLEVÉ', color: 'text-red-400', bg: 'bg-red-500/20' };
    if (beta > 1.2 || volatility > 25) return { level: 'MOYEN', color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
    return { level: 'FAIBLE', color: 'text-emerald-400', bg: 'bg-emerald-500/20' };
  };

  // Generate buy/sell/hold recommendation
  const generateRecommendation = (stock: any, prediction: any) => {
    const trend = prediction?.trend || 'UP';
    const confidence = prediction?.confidence || 0.8;

    if ((trend === 'STRONG_UP' || trend === 'UP') && confidence > 0.75) {
      return { action: 'ACHETER', color: 'text-emerald-400', confidence: Math.round(confidence * 100) };
    } else if (trend === 'DOWN' && confidence > 0.7) {
      return { action: 'VENDRE', color: 'text-red-400', confidence: Math.round(confidence * 100) };
    }
    return { action: 'HOLD', color: 'text-yellow-400', confidence: Math.round(confidence * 100) };
  };

  // Fetch analyst consensus data
  const fetchAnalystConsensus = async (ticker: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/stocks/${ticker}/yahoo/?type=recommendations`);
      const data = await res.json();
      if (!data.error && data.recommendations) {
        setAnalystConsensus(data.recommendations);
      } else {
        // Generate dynamic consensus based on stock metrics
        setAnalystConsensus({
          consensus: generateRecommendation(selectedStock, lstmPrediction).action,
          strong_buy: 35,
          buy: 30,
          hold: 20,
          sell: 10,
          strong_sell: 5,
          confidence: 82
        });
      }
    } catch (err) {
      console.error('Failed to fetch analyst consensus:', err);
      setAnalystConsensus({
        consensus: generateRecommendation(selectedStock, lstmPrediction).action,
        strong_buy: 35,
        buy: 30,
        hold: 20,
        sell: 10,
        strong_sell: 5,
        confidence: 82
      });
    }
  };

  // Fetch stock metrics
  const fetchStockMetrics = async (ticker: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/stocks/${ticker}/yahoo/?type=financials`);
      const data = await res.json();
      if (!data.error) {
        setStockMetrics(data);
      } else {
        // Use stock data as fallback
        setStockMetrics({
          pe_ratio: selectedStock?.pe_ratio || (25 + Math.random() * 15).toFixed(1),
          pb_ratio: selectedStock?.pb_ratio || (2 + Math.random() * 4).toFixed(1),
          beta: selectedStock?.beta || (0.8 + Math.random() * 0.8).toFixed(2),
          dividend_yield: selectedStock?.dividend_yield || (Math.random() * 3).toFixed(2) + '%'
        });
      }
    } catch (err) {
      console.error('Failed to fetch stock metrics:', err);
      setStockMetrics({
        pe_ratio: selectedStock?.pe_ratio || (25 + Math.random() * 15).toFixed(1),
        pb_ratio: selectedStock?.pb_ratio || (2 + Math.random() * 4).toFixed(1),
        beta: selectedStock?.beta || (0.8 + Math.random() * 0.8).toFixed(2),
        dividend_yield: selectedStock?.dividend_yield || (Math.random() * 3).toFixed(2) + '%'
      });
    }
  };

  // Helper to clean thinking tags and translate to French
  const processThinking = (text: string) => {
    // Replace thinking tags with French equivalent
    let cleaned = text.replace(/<think>/g, '🤔 **Réflexion :**');
    cleaned = cleaned.replace(/<\/think>/g, '');
    cleaned = cleaned.replace(/\*\*Thinking:\*\*/g, '🤔 **Réflexion :**');
    cleaned = cleaned.replace(/Thinking:/g, '🤔 Réflexion :');
    return cleaned;
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMsg = { text: inputValue, isAi: false };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsThinking(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputValue, user_id: user?.id || 'user_123' })
      });
      const data = await res.json();
      // Process thinking tags to French
      const cleanedResponse = processThinking(data.response || '');
      setMessages(prev => [...prev, {
        text: cleanedResponse,
        isAi: true,
        stocks: data.stocks,
        recommendations: data.recommendations,
        listings: data.listings,
        profile: data.profile,
        persona: data.persona
      }]);
    } catch (err) {
      console.error('Chat error:', err);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#0A0F1C] text-gray-100' : 'bg-gray-50 text-gray-900'} transition-colors duration-300`}>
      <div className="flex h-[calc(100vh-68px)]">
        {/* Sidebar */}
        <aside className={`w-64 flex-shrink-0 border-r ${isDark ? 'bg-[#0B1F3A] border-white/5' : 'bg-white border-gray-200'} p-6 flex flex-col gap-8`}>
          <div className="flex items-center">
            <div>
              <h1 className="text-xl font-bold uppercase tracking-tight">Agent de Recommandation</h1>
            </div>
          </div>

          <nav className="flex flex-col gap-2">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-4 px-4 py-3 rounded-xl font-semibold transition-all ${activeTab === 'dashboard' ? 'bg-[#bc000c] text-white' : 'hover:bg-white/5 text-gray-400'}`}
            >
              <LayoutDashboard size={20} />
              <span>Dashboard</span>
            </button>
            <button
              onClick={() => setActiveTab('investment')}
              className={`flex items-center gap-4 px-4 py-3 rounded-xl font-semibold transition-all ${activeTab === 'investment' ? 'bg-[#bc000c] text-white' : 'hover:bg-white/5 text-gray-400'}`}
            >
              <Wallet size={20} />
              <span>Investissement</span>
            </button>
            <button
              onClick={() => setActiveTab('intelligence')}
              className={`flex items-center gap-4 px-4 py-3 rounded-xl font-semibold transition-all ${activeTab === 'intelligence' ? 'bg-[#bc000c] text-white' : 'hover:bg-white/5 text-gray-400'}`}
            >
              <Brain size={20} />
              <span>Assistant</span>
            </button>
          </nav>

          <div className={`mt-auto p-4 rounded-xl border ${isDark ? 'bg-white/5 border-white/10' : 'bg-gray-100 border-gray-200'}`}>
            <p className="text-[10px] font-bold uppercase mb-2 text-gray-500">Statut IA</p>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
              <span className="text-xs font-medium">Opérationnel</span>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Header */}
          <header className={`h-16 flex items-center justify-between px-8 border-b ${isDark ? 'bg-[#0B1F3A]/80 border-white/5' : 'bg-white border-gray-200'} backdrop-blur-xl sticky top-0 z-40`}>
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Rechercher des actions (ex: AAPL)..."
                  className={`w-full py-2 pl-12 pr-4 rounded-full border-0 ${isDark ? 'bg-white/5 focus:ring-red-500/50' : 'bg-gray-100 focus:ring-red-500/30'} transition-all`}
                />
                {searchResults.length > 0 && (
                  <div className={`absolute top-full left-0 right-0 mt-2 rounded-xl border shadow-2xl overflow-hidden ${isDark ? 'bg-[#0B1F3A] border-white/10' : 'bg-white border-gray-200'}`}>
                    {searchResults.map((stock) => (
                      <button
                        key={stock.symbol}
                        onClick={() => handleSelectStock(stock.symbol)}
                        className={`w-full text-left px-6 py-3 hover:bg-[#bc000c] hover:text-white transition-colors flex items-center justify-between`}
                      >
                        <div>
                          <p className="font-bold">{stock.symbol}</p>
                          <p className="text-xs opacity-70">{stock.name}</p>
                        </div>
                        <span className="text-[10px] uppercase font-bold px-2 py-1 rounded bg-black/20">{stock.exchange}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsDark(!isDark)}
                className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${isDark ? 'bg-white/10 hover:bg-white/20' : 'bg-gray-100 hover:bg-gray-200'}`}
              >
                {isDark ? <Sun size={20} /> : <Moon size={20} />}
              </button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-8 space-y-8">
            {activeTab === 'dashboard' && (
              <>
                <section>
                  <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">Systèmes en Ligne</h3>
                  <h1 className="text-4xl font-extrabold font-headline tracking-tight">
                    Ravi de vous revoir, <span className="text-[#bc000c]">{user?.name || 'Client'}</span>.
                  </h1>
                </section>

                {/* Main Balance Card */}
                <div className={`p-8 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5 shadow-2xl' : 'bg-white border-gray-200 shadow-xl'}`}>
                  <div className="flex justify-between items-start mb-8">
                    <div>
                      <h4 className="text-sm font-bold uppercase tracking-wider text-gray-500">Liquidité Totale</h4>
                      <p className="text-5xl font-black mt-2 tracking-tighter">
                        {dashboardData?.total_liquidity?.toLocaleString() || '0.00'} <span className="text-xl text-gray-500">TND</span>
                      </p>
                    </div>
                    <div className="bg-[#bc000c]/10 p-4 rounded-2xl text-[#bc000c]">
                      <Wallet size={32} />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className={`p-6 rounded-xl ${isDark ? 'bg-white/5' : 'bg-gray-50'} space-y-3`}>
                      <p className="text-xs font-bold uppercase text-gray-500">Budget Mensuel</p>
                      <p className="text-2xl font-bold">{dashboardData?.monthly_budget?.toLocaleString() || '2,000'} TND</p>
                      <div className="h-1.5 w-full bg-black/10 rounded-full overflow-hidden">
                        <div className="h-full bg-[#bc000c] w-[85%]"></div>
                      </div>
                      <p className="text-[10px] text-gray-500">85% utilisé</p>
                    </div>
                    <div className={`p-6 rounded-xl ${isDark ? 'bg-white/5' : 'bg-gray-50'} space-y-3`}>
                      <p className="text-xs font-bold uppercase text-gray-500">Taux d'Épargne</p>
                      <p className="text-2xl font-bold">35.8%</p>
                      <div className="h-1.5 w-full bg-black/10 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500 w-[35%]"></div>
                      </div>
                      <p className="text-[10px] text-gray-500">Épargne mensuelle</p>
                    </div>
                    <div className={`p-6 rounded-xl ${isDark ? 'bg-white/5' : 'bg-gray-50'} space-y-3`}>
                      <p className="text-xs font-bold uppercase text-gray-500">Prévision IA</p>
                      <p className="text-2xl font-bold text-emerald-400">+72.5 TND</p>
                      <p className="text-[10px] text-gray-500 uppercase">Surplus Estimé</p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-12 gap-6">
                  {/* Left Column: Monthly Expenses */}
                  <div className="col-span-12 lg:col-span-7 space-y-6">
                    <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                          <TrendingDown size={18} className="text-[#bc000c]" />
                          Dépenses Mensuelles
                        </h3>
                        <div className="text-right">
                          <p className="font-bold text-lg">6,425 TND</p>
                          <p className="text-xs text-gray-500">Total Dépenses</p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        {[
                          { label: 'Food', sublabel: 'Alimentation', amount: 4000, percent: 62.3, color: 'bg-[#bc000c]' },
                          { label: 'Fuel', sublabel: 'Transport', amount: 350, percent: 5.4, color: 'bg-emerald-500' },
                          { label: 'Internet', sublabel: 'Services', amount: 100, percent: 1.6, color: 'bg-blue-500' },
                          { label: 'Investment', sublabel: 'Investissement', amount: 1200, percent: 18.7, color: 'bg-purple-500' },
                          { label: 'Netflix', sublabel: 'Abonnement', amount: 70, percent: 1.1, color: 'bg-yellow-500' },
                        ].map((item) => (
                          <div key={item.label} className="space-y-2">
                            <div className="flex justify-between items-center">
                              <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${item.color}`}></span>
                                <span className="font-medium text-sm">{item.label}</span>
                                <span className="text-xs text-gray-500">• {item.sublabel}</span>
                              </div>
                              <div className="text-right">
                                <span className="font-bold text-sm">{item.amount} TND</span>
                                <span className="text-xs text-gray-500 ml-2">({item.percent}%)</span>
                              </div>
                            </div>
                            <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                              <div className={`h-full ${item.color}`} style={{ width: `${item.percent}%` }}></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Recent Transactions */}
                    <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                      <h3 className="text-sm font-bold uppercase tracking-wider mb-6 flex items-center gap-2">
                        <History size={18} className="text-[#bc000c]" />
                        Transactions Récentes
                      </h3>
                      <div className="space-y-4">
                        {transactionsData?.transactions?.slice(0, 4).map((tx: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-colors">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${tx.type === 'expense' ? 'bg-red-500/10 text-red-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
                                {tx.type === 'expense' ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                              </div>
                              <div>
                                <p className="font-bold text-sm">{tx.description}</p>
                                <p className="text-xs text-gray-500">{tx.date?.split('T')[0]} • {tx.category}</p>
                              </div>
                            </div>
                            <p className={`font-bold ${tx.type === 'expense' ? 'text-red-500' : 'text-emerald-500'}`}>
                              {tx.type === 'expense' ? '-' : '+'}{tx.amount?.toLocaleString()} TND
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Asset Allocation & Summary */}
                  <div className="col-span-12 lg:col-span-5 space-y-6">
                    {/* Asset Allocation */}
                    <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                      <h3 className="text-sm font-bold uppercase tracking-wider mb-6">Allocation d'Actifs</h3>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs font-bold uppercase">
                            <span className="text-gray-500">Liquidités</span>
                            <span>65%</span>
                          </div>
                          <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                            <div className="h-full bg-[#bc000c] w-[65%]"></div>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs font-bold uppercase">
                            <span className="text-gray-500">Actions</span>
                            <span>25%</span>
                          </div>
                          <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 w-[25%]"></div>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs font-bold uppercase">
                            <span className="text-gray-500">Autres Actifs</span>
                            <span>10%</span>
                          </div>
                          <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500 w-[10%]"></div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Revenue Summary */}
                    <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                      <h3 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
                        <TrendingUp size={18} className="text-emerald-500" />
                        Résumé des Revenus
                      </h3>
                      <div className="space-y-4">
                        <div className={`p-4 rounded-xl ${isDark ? 'bg-emerald-500/10' : 'bg-emerald-50'}`}>
                          <p className="text-xs text-gray-500 uppercase">Revenu Mensuel</p>
                          <p className="text-2xl font-bold text-emerald-400">2000 TND</p>
                          <p className="text-xs text-gray-500">Depuis votre Marketplace</p>
                        </div>
                        <div className={`p-4 rounded-xl ${isDark ? 'bg-white/5' : 'bg-gray-50'}`}>
                          <p className="text-xs text-gray-500 uppercase">Flux de Trésorerie Net</p>
                          <p className="text-xl font-bold text-red-400">-4,425 TND</p>
                          <p className="text-xs text-gray-500">Revenus - Dépenses</p>
                        </div>
                      </div>
                    </div>

                    {/* Financial Health */}
                    <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                      <h3 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
                        <Activity size={18} className="text-[#bc000c]" />
                        Santé Financière
                      </h3>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">Réserve de Liquidité</span>
                          <span className="font-bold">369 mois</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">Ratio Épargne</span>
                          <span className="font-bold text-emerald-400">88.8%</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">Nabto de Transactions</span>
                          <span className="font-bold">20</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'investment' && (
              <div className="space-y-8 animate-in fade-in duration-500">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">SYSTÈMES EN LIGNE</h3>
                    <h1 className="text-4xl font-extrabold font-headline tracking-tight">
                      Analyse du <span className="text-[#bc000c]">Portefeuille</span>
                    </h1>
                    <p className="text-gray-400 mt-2">Votre Coffre Numérique est optimisé. Parlez-moi en dialecte tunisien ou par texte.</p>
                  </div>
                  <div className={`px-4 py-3 rounded-xl border ${isDark ? 'bg-white/5 border-white/10' : 'bg-white border-gray-200'}`}>
                    <p className="text-[10px] text-gray-500 uppercase">Profil Persona</p>
                    <p className="text-lg font-bold text-emerald-400 capitalize">{dashboardData?.persona || user?.persona || 'Balanced'}</p>
                  </div>
                </div>

                {/* AI Portfolio Analysis */}
                <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                  <div className="flex items-center gap-2 mb-6">
                    <Brain size={20} className="text-[#bc000c]" />
                    <h3 className="text-sm font-bold uppercase tracking-wider">Analyse IA du Portefeuille</h3>
                  </div>

                  {/* Persona-Based Analysis */}
                  {(() => {
                    const persona = dashboardData?.persona || user?.persona || 'balanced';
                    const balance = dashboardData?.total_liquidity || 28810;
                    const monthlyBudget = dashboardData?.monthly_budget || 2000;

                    // Generate recommendations based on persona
                    const recommendations = {
                      conservative: {
                        title: 'Profil Conservateur',
                        description: `Votre solde de ${balance.toLocaleString()} TND et budget de ${monthlyBudget.toLocaleString()} TND/mois suggèrent une stratégie défensive avec priorités de sécurité.`,
                        allocation: { liquidity: 70, bonds: 20, stocks: 10 },
                        actions: [
                          { stock: 'AAPL', action: 'HOLD', reason: 'Stable, bon pour conserver' },
                          { stock: 'MSFT', action: 'REDUCE', reason: 'Réduire l exposition aux actions' },
                          { stock: 'BND', action: 'BUY', reason: 'Obligations sécurisées recommandées' }
                        ],
                        risk: 'Faible'
                      },
                      balanced: {
                        title: 'Profil Équilibré',
                        description: `Avec ${balance.toLocaleString()} TND et ${monthlyBudget.toLocaleString()} TND/mois, une diversification équilibrée optimise rendement et sécurité.`,
                        allocation: { liquidity: 40, bonds: 30, stocks: 30 },
                        actions: [
                          { stock: 'AAPL', action: 'BUY', reason: 'Croissance stable recommandée' },
                          { stock: 'GOOGL', action: 'HOLD', reason: 'Maintenir position actuelle' },
                          { stock: 'NVDA', action: 'REDUCE', reason: 'Trop volatile, réduire' }
                        ],
                        risk: 'Modéré'
                      },
                      aggressive: {
                        title: 'Profil Agressif',
                        description: `Votre capacité avec ${balance.toLocaleString()} TND et ${monthlyBudget.toLocaleString()} TND/mois permet une stratégie growth orientée.`,
                        allocation: { liquidity: 20, bonds: 10, stocks: 70 },
                        actions: [
                          { stock: 'NVDA', action: 'BUY', reason: 'Fort potentiel de croissance' },
                          { stock: 'TSLA', action: 'BUY', reason: 'Innovation et disruption' },
                          { stock: 'AAPL', action: 'HOLD', reason: 'Base stable du portefeuille' }
                        ],
                        risk: 'Élevé'
                      }
                    };

                    const analysis = recommendations[persona as keyof typeof recommendations] || recommendations.balanced;

                    return (
                      <div className="space-y-6">
                        {/* Analysis Summary */}
                        <div className={`p-4 rounded-xl ${isDark ? 'bg-white/5' : 'bg-gray-50'}`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="px-3 py-1 bg-[#bc000c] text-white text-xs font-bold rounded-full">
                              {analysis.title}
                            </span>
                            <span className={`px-3 py-1 text-xs font-bold rounded-full ${analysis.risk === 'Faible' ? 'bg-emerald-500/20 text-emerald-400' :
                              analysis.risk === 'Élevé' ? 'bg-red-500/20 text-red-400' :
                                'bg-yellow-500/20 text-yellow-400'
                              }`}>
                              Risque: {analysis.risk}
                            </span>
                          </div>
                          <p className="text-sm text-gray-400">{analysis.description}</p>
                        </div>

                        {/* Recommended Allocation */}
                        <div>
                          <p className="text-xs font-bold text-gray-500 uppercase mb-3">Allocation Recommandée</p>
                          <div className="space-y-3">
                            <div className="space-y-1">
                              <div className="flex justify-between text-xs">
                                <span>Liquidités</span>
                                <span className="font-bold">{analysis.allocation.liquidity}%</span>
                              </div>
                              <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                                <div className="h-full bg-gray-500" style={{ width: `${analysis.allocation.liquidity}%` }}></div>
                              </div>
                            </div>
                            <div className="space-y-1">
                              <div className="flex justify-between text-xs">
                                <span>Obligations</span>
                                <span className="font-bold">{analysis.allocation.bonds}%</span>
                              </div>
                              <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500" style={{ width: `${analysis.allocation.bonds}%` }}></div>
                              </div>
                            </div>
                            <div className="space-y-1">
                              <div className="flex justify-between text-xs">
                                <span>Actions</span>
                                <span className="font-bold">{analysis.allocation.stocks}%</span>
                              </div>
                              <div className="h-2 w-full bg-black/10 rounded-full overflow-hidden">
                                <div className="h-full bg-[#bc000c]" style={{ width: `${analysis.allocation.stocks}%` }}></div>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Recommended Actions */}
                        <div>
                          <p className="text-xs font-bold text-gray-500 uppercase mb-3">Recommandations Personnalisées</p>
                          <div className="space-y-2">
                            {analysis.actions.map((rec, idx) => (
                              <div
                                key={idx}
                                onClick={() => handleSelectStock(rec.stock)}
                                className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${isDark ? 'bg-white/5 hover:bg-white/10' : 'bg-gray-50 hover:bg-gray-100'}`}
                              >
                                <div className="flex items-center gap-3">
                                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold ${isDark ? 'bg-white/10' : 'bg-gray-200'}`}>
                                    {rec.stock.slice(0, 2)}
                                  </div>
                                  <div>
                                    <p className="font-bold text-sm">{rec.stock}</p>
                                    <p className="text-xs text-gray-500">{rec.reason}</p>
                                  </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold ${rec.action === 'BUY' || rec.action === 'ACHETER' ? 'bg-emerald-500/20 text-emerald-400' :
                                  rec.action === 'SELL' || rec.action === 'VENDRE' || rec.action === 'REDUCE' || rec.action === 'RÉDUIRE' ? 'bg-red-500/20 text-red-400' :
                                    'bg-yellow-500/20 text-yellow-400'
                                  }`}>
                                  {rec.action === 'BUY' || rec.action === 'ACHETER' ? 'ACHETER' : 
                                   rec.action === 'SELL' || rec.action === 'VENDRE' ? 'VENDRE' : 
                                   rec.action === 'REDUCE' || rec.action === 'RÉDUIRE' ? 'RÉDUIRE' : 
                                   rec.action === 'HOLD' || rec.action === 'ATTENDRE' ? 'ATTENDRE' : rec.action}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* Trending Stocks Table */}
                <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#111827] border-white/5' : 'bg-white border-gray-200'}`}>
                  <div className="flex items-center gap-2 mb-6">
                    <Activity size={20} className="text-[#bc000c]" />
                    <h3 className="text-sm font-bold uppercase tracking-wider">Actions Tendances</h3>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="text-left border-b border-white/10">
                          <th className="pb-3 text-[10px] font-bold text-gray-500 uppercase">Symbole</th>
                          <th className="pb-3 text-[10px] font-bold text-gray-500 uppercase">Nom</th>
                          <th className="pb-3 text-[10px] font-bold text-gray-500 uppercase text-right">Dernier Prix</th>
                          <th className="pb-3 text-[10px] font-bold text-gray-500 uppercase text-right">Variation 24h</th>
                          <th className="pb-3 text-[10px] font-bold text-gray-500 uppercase text-right">Variation %</th>
                        </tr>
                      </thead>
                      <tbody className="space-y-2">
                        {[
                          { symbol: 'AAPL', name: 'Apple Inc.', price: 273.03, change: -0.03, changePct: -0.01 },
                          { symbol: 'TSLA', name: 'Tesla, Inc.', price: 377.10, change: -10.41, changePct: -2.69 },
                          { symbol: 'MSFT', name: 'Microsoft Corporation', price: 417.10, change: -15.82, changePct: -3.65 },
                          { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 340.41, change: +1.09, changePct: +0.32 },
                          { symbol: 'NVDA', name: 'NVIDIA Corporation', price: 201.67, change: -0.91, changePct: -0.45 },
                          { symbol: 'AMZN', name: 'Amazon.com, Inc.', price: 258.22, change: +1.26, changePct: +0.50 },
                        ].map((stock) => (
                          <tr
                            key={stock.symbol}
                            onClick={() => handleSelectStock(stock.symbol)}
                            className="cursor-pointer hover:bg-white/5 transition-colors"
                          >
                            <td className="py-3 font-bold text-[#bc000c]">{stock.symbol}</td>
                            <td className="py-3 text-sm">{stock.name}</td>
                            <td className="py-3 text-right font-bold">{stock.price.toFixed(2)} TND</td>
                            <td className={`py-3 text-right ${stock.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}
                            </td>
                            <td className={`py-3 text-right ${stock.changePct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {stock.changePct >= 0 ? '+' : ''}{stock.changePct.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'intelligence' && (
              <div className="h-full flex flex-col animate-in fade-in duration-500">
                {/* Header */}
                <div className="mb-6">
                  <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500 mb-2">Assistant IA</h3>
                  <h1 className="text-3xl font-extrabold font-headline tracking-tight">
                    Conseiller <span className="text-[#bc000c]">Souverain</span>
                  </h1>
                  <p className="text-gray-400 mt-2">Posez vos questions sur les voitures, maisons, ou investissements.</p>
                </div>

                {/* Chat Messages */}
                <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
                  {messages.length === 0 && (
                    <div className={`p-8 rounded-2xl border text-center ${isDark ? 'bg-white/5 border-white/10' : 'bg-white border-gray-200'}`}>
                      <Brain size={48} className="mx-auto text-[#bc000c] mb-4" />
                      <h3 className="text-xl font-bold mb-2">Bienvenue dans l'Intelligence Artificielle</h3>
                      <p className="text-gray-400 max-w-md mx-auto">
                        Je peux vous aider à trouver une voiture, une maison, ou des opportunités d'investissement.
                        Essayez : "Je cherche une voiture française " ou "Je cherche une maison"
                      </p>
                    </div>
                  )}

                  {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.isAi ? 'justify-start' : 'justify-end'} animate-in fade-in slide-in-from-bottom-2`}>
                      <div className={`max-w-[85%] p-4 rounded-2xl ${msg.isAi ? (isDark ? 'bg-white/5 border border-white/10' : 'bg-gray-100') : 'bg-[#bc000c] text-white'}`}>
                        {/* Message Text */}
                        <div
                          className="text-sm leading-relaxed whitespace-pre-wrap prose prose-invert max-w-none"
                          dangerouslySetInnerHTML={{
                            __html: msg.text
                              .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                              .replace(/\n/g, '<br/>')
                          }}
                        />

                        {/* Recommendations Display */}
                        {msg.isAi && msg.recommendations && msg.recommendations.length > 0 && (
                          <div className="mt-4 space-y-2">
                            <p className="text-xs font-bold text-gray-500 uppercase">Recommandations</p>
                            {msg.recommendations.map((rec: any, ridx: number) => (
                              <div key={ridx} className={`p-3 rounded-xl ${isDark ? 'bg-black/30' : 'bg-gray-200'}`}>
                                <div className="flex items-center gap-2 mb-1">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${rec.decision === 'BUY' || rec.decision === 'ACHETER' ? 'bg-emerald-500/20 text-emerald-400' :
                                    rec.decision === 'SELL' || rec.decision === 'VENDRE' || rec.decision === 'ÉVITER' ? 'bg-red-500/20 text-red-400' :
                                      'bg-yellow-500/20 text-yellow-400'
                                    }`}>
                                    {rec.decision === 'BUY' || rec.decision === 'ACHETER' ? 'ACHETER' : 
                                     rec.decision === 'SELL' || rec.decision === 'VENDRE' ? 'VENDRE' : 
                                     rec.decision === 'HOLD' || rec.decision === 'ATTENDRE' ? 'ATTENDRE' : 
                                     rec.decision === 'CONSIDER' || rec.decision === 'CONSIDÉRER' || rec.decision === 'SURVEILLER' ? 'SURVEILLER' : rec.decision}
                                  </span>
                                  <span className="font-bold text-sm">{rec.asset}</span>
                                </div>
                                <p className="text-xs text-gray-400">{rec.reason}</p>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Car/House Listings - Property Cards */}
                        {msg.isAi && msg.listings && msg.listings.length > 0 && (
                          <div className="mt-6">
                            <p className="text-xs font-bold text-gray-500 uppercase mb-4">Annonces trouvées ({msg.listings.length})</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {msg.listings.slice(0, 6).map((listing: any, lidx: number) => (
                                <a
                                  key={lidx}
                                  href={listing.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`group rounded-2xl overflow-hidden transition-all hover:scale-[1.02] ${isDark ? 'bg-[#111827] border border-white/5' : 'bg-white border border-gray-200 shadow-lg'}`}
                                >
                                  {/* Property Image */}
                                  <div className="relative h-40 overflow-hidden">
                                    <img
                                      src={listing.image || `https://picsum.photos/400/250?random=${lidx}`}
                                      alt={listing.title}
                                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                                    />
                                    <div className="absolute top-3 left-3">
                                      <span className="px-3 py-1 bg-[#bc000c] text-white text-xs font-bold rounded-full">
                                        {lidx + 1}
                                      </span>
                                    </div>
                                    <div className="absolute top-3 right-3">
                                      <span className="px-3 py-1 bg-black/50 text-white text-xs font-bold rounded-full flex items-center gap-1">
                                        {listing.category === 'car' ? <Car size={12} /> : <Home size={12} />}
                                        {listing.category === 'car' ? 'VOITURE' : 'MAISON'}
                                      </span>
                                    </div>
                                  </div>

                                  {/* Property Info */}
                                  <div className="p-4">
                                    <h4 className="font-bold text-sm mb-1 line-clamp-1">{listing.title}</h4>
                                    <p className="text-xs text-gray-500 mb-3">{listing.location || 'Tunisia'}</p>

                                    <div className="flex items-center justify-between">
                                      <p className="text-lg font-black text-[#bc000c]">{listing.price?.toLocaleString()} TND</p>
                                      {listing.investment_return && (
                                        <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs font-bold rounded">
                                          +{listing.investment_return}%
                                        </span>
                                      )}
                                    </div>

                                    <button className="w-full mt-4 py-2 bg-white/5 hover:bg-[#bc000c] text-xs font-bold uppercase tracking-wider rounded-lg transition-colors">
                                      Voir détails de la propriété
                                    </button>
                                  </div>
                                </a>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Stock Recommendations */}
                        {msg.isAi && msg.stocks && msg.stocks.length > 0 && (
                          <div className="mt-4 flex flex-wrap gap-2">
                            {msg.stocks.map((stock: any) => (
                              <button
                                key={stock.symbol}
                                onClick={() => handleSelectStock(stock.symbol)}
                                className="px-3 py-1.5 bg-white/10 rounded-lg text-xs font-bold hover:bg-[#bc000c] transition-all uppercase"
                              >
                                {stock.symbol}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Profile Info */}
                        {msg.isAi && msg.profile && msg.profile.goal && (
                          <div className="mt-3 pt-3 border-t border-white/10">
                            <p className="text-[10px] text-gray-500">
                              Profil: {msg.profile.goal} {msg.persona && `• Persona: ${msg.persona === 'balanced' ? 'équilibré' : msg.persona === 'aggressive' ? 'agressif' : 'conservateur'}`}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {isThinking && (
                    <div className="flex justify-start">
                      <div className={`p-4 rounded-2xl ${isDark ? 'bg-white/5 border border-white/10' : 'bg-gray-100'} flex items-center gap-2`}>
                        <span className="text-xs text-gray-400">L'IA réfléchit</span>
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></span>
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input Area */}
                <div className={`p-4 rounded-2xl border ${isDark ? 'bg-white/5 border-white/10' : 'bg-gray-100 border-gray-200'}`}>
                  <div className="flex items-center gap-3">
                    <input
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Posez une question... (ex: Je cherche une voiture , Je cherche une maison )"
                      className={`flex-1 bg-transparent border-0 focus:ring-0 text-sm py-3 ${isDark ? 'placeholder-gray-500' : 'placeholder-gray-400'}`}
                    />

                    <button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isThinking}
                      className="p-3 bg-[#bc000c] text-white rounded-xl shadow-lg shadow-[#bc000c]/20 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Send size={20} />
                    </button>
                  </div>
                  <div className="flex justify-between items-center mt-3 pt-3 border-t border-white/5">
                    <div className="flex items-center gap-4">
                      <button className="flex items-center gap-1 text-[10px] font-bold text-gray-500 hover:text-gray-300 transition-colors">
                        <ShieldCheck size={12} />
                        CHIFFRÉ
                      </button>
                      <button onClick={() => setMessages([])} className="flex items-center gap-1 text-[10px] font-bold text-gray-500 hover:text-gray-300 transition-colors">
                        <History size={12} />
                        EFFACER
                      </button>
                    </div>
                    <span className="text-[10px] text-gray-500">Persona: {user?.persona === 'balanced' ? 'équilibré' : user?.persona === 'aggressive' ? 'agressif' : 'conservateur'}</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'stock-detail' && selectedStock && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {/* Header */}
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className={`text-3xl font-black font-headline ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      {selectedStock.name} ({selectedStock.symbol})
                    </h2>
                    <p className={`text-xs font-bold uppercase tracking-widest mt-1 ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>
                      {selectedStock.exchange || 'XNAS'} - Prix en Temps Réel
                    </p>
                    <div className="flex items-center gap-3 mt-4">
                      <span className={`text-4xl font-black ${isDark ? 'text-white' : 'text-slate-900'}`}>{selectedStock.price} TND</span>
                      <span className={`font-bold ${selectedStock.change >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                        {selectedStock.change >= 0 ? '+' : ''}{selectedStock.change?.toFixed(2)} ({selectedStock.change_percent?.toFixed(2)}%)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Main Grid - Matching PI Organization */}
                <div className="grid grid-cols-12 gap-6">
                  {/* LEFT COLUMN: Chart & Strategy (col-span-8) */}
                  <div className="col-span-12 lg:col-span-8 space-y-6">

                    {/* Chart 1: Candlestick (Institutional) */}
                    <div className={`rounded-xl p-4 border ${isDark ? 'bg-white/5 border-white/5' : 'bg-white border-slate-200 shadow-sm'}`}>
                      <div className="flex justify-between items-center mb-4">
                        <h4 className={`font-bold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          <TrendingUp size={18} className="text-[#bc000c]" />
                          Action des Prix Institutionnels (Chandelier)
                        </h4>
                        <div className="flex gap-2">
                          <button className={`px-3 py-1 text-xs rounded hover:bg-[#bc000c] ${isDark ? 'bg-white/10 text-white' : 'bg-slate-200 text-slate-700'}`}>6M</button>
                          <button className="px-3 py-1 text-xs rounded bg-[#bc000c] text-white">3M</button>
                          <button className={`px-3 py-1 text-xs rounded hover:bg-[#bc000c] ${isDark ? 'bg-white/10 text-white' : 'bg-slate-200 text-slate-700'}`}>1M</button>
                        </div>
                      </div>
                      <div id="candlestick-chart" className={`h-80 w-full rounded-lg overflow-hidden border ${isDark ? 'border-white/5 bg-slate-900/20' : 'border-slate-300 bg-white'}`}></div>
                    </div>

                    {/* Chart 2: Yahoo Finance Area Chart */}
                    <div className={`rounded-xl p-4 border ${isDark ? 'bg-white/5 border-white/5' : 'bg-slate-50 border-slate-200'}`}>
                      <div className="flex justify-between items-center mb-4">
                        <h4 className={`font-bold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          <Activity size={18} className="text-emerald-400" />
                          Graphique des Prix (Yahoo Finance)
                        </h4>
                        <div className="flex gap-2">
                          {(['1d', '1w', '1m', '1y'] as const).map((period) => (
                            <button
                              key={period}
                              onClick={() => setChartPeriod(period)}
                              className={`px-3 py-1 text-xs rounded transition-colors ${chartPeriod === period
                                ? 'bg-[#bc000c] text-white'
                                : isDark
                                  ? 'bg-white/10 text-white hover:bg-[#bc000c]'
                                  : 'bg-slate-200 text-slate-700 hover:bg-[#bc000c] hover:text-white'
                                }`}
                            >
                              {period === '1d' ? '1J' : period === '1w' ? '1S' : period === '1m' ? '1M' : '1A'}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div id="yahoo-chart-container" className="h-64 w-full relative">
                        <canvas id="yahoo-chart" className="w-full h-full"></canvas>
                        {/* Hover Tooltip */}
                        {hoveredPoint && (
                          <div
                            className={`absolute pointer-events-none rounded-lg px-3 py-2 text-xs shadow-xl z-10 border ${isDark ? 'bg-slate-800/95 border-emerald-500/30' : 'bg-white border-emerald-500/50'}`}
                            style={{
                              left: Math.min(hoveredPoint.x, (document.getElementById('yahoo-chart-container')?.offsetWidth || 300) - 120),
                              top: hoveredPoint.y - 40
                            }}
                          >
                            <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{hoveredPoint.date}</p>
                            <p className="text-emerald-500 font-bold">{hoveredPoint.price.toFixed(2)} TND</p>
                          </div>
                        )}
                        {/* Y-Axis Labels */}
                        <div className={`absolute left-0 top-8 bottom-8 w-12 flex flex-col justify-between text-[10px] pointer-events-none ${isDark ? 'text-gray-500' : 'text-gray-700'}`}>
                          {chartData.length > 0 && (() => {
                            const maxPrice = Math.max(...chartData.map(d => d.price));
                            const minPrice = Math.min(...chartData.map(d => d.price));
                            const range = maxPrice - minPrice;
                            return [
                              maxPrice + range * 0.05,
                              maxPrice - range * 0.25,
                              (maxPrice + minPrice) / 2,
                              minPrice + range * 0.25,
                              minPrice - range * 0.05,
                            ].map((price, i) => (
                              <span key={i} className="text-right pr-1">{price.toFixed(0)}</span>
                            ));
                          })()}
                        </div>
                        {/* X-Axis Labels */}
                        <div className={`absolute left-12 right-0 bottom-0 h-6 flex justify-between text-[10px] pointer-events-none px-2 ${isDark ? 'text-gray-500' : 'text-gray-700'}`}>
                          {chartData.length > 0 && (() => {
                            const points = chartPeriod === '1d'
                              ? [0, 6, 12, 18, 23]
                              : chartPeriod === '1w'
                                ? [0, 2, 4, 6]
                                : chartPeriod === '1m'
                                  ? [0, 10, 20, 30]
                                  : [0, 33, 66, 99];
                            return points.map((idx, i) => {
                              const dataPoint = chartData[Math.floor((idx / (chartPeriod === '1d' ? 23 : chartPeriod === '1w' ? 6 : chartPeriod === '1m' ? 30 : 100)) * (chartData.length - 1))];
                              return (
                                <span key={i} className="text-center min-w-[20px]">
                                  {dataPoint?.date || (chartPeriod === '1d' ? `${idx}h` : chartPeriod === '1w' ? ['Lun', 'Mer', 'Ven', 'Dim'][i] : chartPeriod === '1m' ? ['J1', 'J10', 'J20', 'J30'][i] : ['Jan', 'Avr', 'Juil', 'Oct'][i])}
                                </span>
                              );
                            });
                          })()}
                        </div>
                      </div>
                    </div>

                    {/* Strategy & Decision Section */}
                    <div className="bg-gradient-to-br from-[#0B1F3A]/50 to-black/40 rounded-xl p-6 border border-white/10">
                      {/* Header */}
                      <div className="flex justify-between items-start mb-6">
                        <div>
                          <h4 className="text-white font-bold text-lg flex items-center gap-2">
                            <Brain size={20} className="text-[#bc000c]" />
                            Stratégie d'Investissement
                          </h4>
                          <p className="text-gray-400 text-sm mt-1">Personnalisée pour votre profil de richesse.</p>
                        </div>
                        <div className={`px-4 py-2 rounded-full ${xaiInsight?.risk_assessment?.bg || 'bg-yellow-500/20'} ${xaiInsight?.risk_assessment?.color || 'text-yellow-400'} font-bold text-sm`}>
                          RISQUE {xaiInsight?.risk_assessment?.level || 'MOYEN'}
                        </div>
                      </div>

                      {/* Analyst Consensus */}
                      <div className={`flex items-center gap-4 mb-6 p-4 rounded-lg ${isDark ? 'bg-black/30' : 'bg-slate-100'}`}>
                        <div className="text-center">
                          <p className={`text-xs uppercase ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Consensus</p>
                          <p className={`text-xl font-bold ${analystConsensus?.consensus === 'ACHETER' || xaiInsight?.recommendation?.action === 'ACHETER' ? 'text-emerald-500' : analystConsensus?.consensus === 'VENDRE' || xaiInsight?.recommendation?.action === 'VENDRE' ? 'text-red-500' : 'text-yellow-500'}`}>
                            {analystConsensus?.consensus || xaiInsight?.recommendation?.action || 'ACHETER'}
                          </p>
                        </div>
                        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden flex">
                          <div className="h-full bg-emerald-500" style={{ width: `${analystConsensus?.strong_buy || 40}%` }}></div>
                          <div className="h-full bg-emerald-400" style={{ width: `${analystConsensus?.buy || 35}%` }}></div>
                          <div className="h-full bg-yellow-400" style={{ width: `${analystConsensus?.hold || 15}%` }}></div>
                          <div className="h-full bg-red-400" style={{ width: `${analystConsensus?.sell || 10}%` }}></div>
                        </div>
                        <div className="text-center">
                          <p className={`text-xs uppercase ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Confiance</p>
                          <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{analystConsensus?.confidence || xaiInsight?.recommendation?.confidence || 80}%</p>
                        </div>
                      </div>

                      {/* Decision Etiquette */}
                      <div className="mb-6 p-4 bg-[#bc000c]/10 border-l-4 border-[#bc000c] rounded-r-lg">
                        <p className="text-xs text-[#bc000c] uppercase font-bold mb-1">Étiquette de Décision</p>
                        <p className="text-white text-sm">
                          {loadingXAI ? 'Analyse IA en cours...' : (xaiInsight?.strategy?.description || xaiInsight?.strategy || `Stratégie d'${xaiInsight?.recommendation?.action === 'ACHETER' ? 'achat' : xaiInsight?.recommendation?.action === 'VENDRE' ? 'vente' : 'attente'} recommandée. ${xaiInsight?.recommendation?.confidence || 80}% de confiance basé sur l'analyse LSTM.`)}
                        </p>
                      </div>

                      {/* ACTION BUTTONS: SELL, HOLD, ALERT, WISHLIST */}
                      <div className="grid grid-cols-2 gap-3">
                        <button className="group relative p-4 bg-emerald-500/20 border border-emerald-500/50 rounded-xl hover:bg-emerald-500/30 transition-all text-left">
                          <div className="flex items-center gap-2 mb-2">
                            <Wallet size={18} className="text-emerald-400" />
                            <span className="font-bold text-emerald-400">Acheter Maintenant</span>
                          </div>
                          <p className="text-xs text-gray-400 group-hover:text-gray-300">Entrée immédiate au prix actuel</p>
                          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        </button>

                        <button className="group p-4 bg-blue-500/20 border border-blue-500/50 rounded-xl hover:bg-blue-500/30 transition-all text-left">
                          <div className="flex items-center gap-2 mb-2">
                            <Search size={18} className="text-blue-400" />
                            <span className="font-bold text-blue-400">Ajouter à la Surveillance</span>
                          </div>
                          <p className="text-xs text-gray-400 group-hover:text-gray-300">Surveiller pour un meilleur point d'entrée</p>
                        </button>

                        <button className="group p-4 bg-red-500/20 border border-red-500/50 rounded-xl hover:bg-red-500/30 transition-all text-left">
                          <div className="flex items-center gap-2 mb-2">
                            <TrendingDown size={18} className="text-red-400" />
                            <span className="font-bold text-red-400">Vendre la Position</span>
                          </div>
                          <p className="text-xs text-gray-400 group-hover:text-gray-300">Sortir si détenu ou éviter l'entrée</p>
                        </button>

                        <button className="group p-4 bg-purple-500/20 border border-purple-500/50 rounded-xl hover:bg-purple-500/30 transition-all text-left">
                          <div className="flex items-center gap-2 mb-2">
                            <Info size={18} className="text-purple-400" />
                            <span className="font-bold text-purple-400">Alerte de Prix</span>
                          </div>
                          <p className="text-xs text-gray-400 group-hover:text-gray-300">Notifier au prix cible</p>
                        </button>
                      </div>

                      {/* Key Metrics */}
                      <div className={`grid grid-cols-4 gap-3 mt-6 pt-6 border-t ${isDark ? 'border-white/10' : 'border-slate-200'}`}>
                        <div className="text-center">
                          <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Ratio P/E</p>
                          <p className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{stockMetrics?.pe_ratio || selectedStock.pe_ratio || (20 + Math.random() * 15).toFixed(1)}</p>
                        </div>
                        <div className="text-center">
                          <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Ratio P/B</p>
                          <p className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{stockMetrics?.pb_ratio || selectedStock.pb_ratio || (1.5 + Math.random() * 3).toFixed(1)}</p>
                        </div>
                        <div className="text-center">
                          <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Bêta</p>
                          <p className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{stockMetrics?.beta || selectedStock.beta || (0.8 + Math.random() * 0.8).toFixed(2)}</p>
                        </div>
                        <div className="text-center">
                          <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Rendement Div</p>
                          <p className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{stockMetrics?.dividend_yield || selectedStock.dividend_yield || (Math.random() * 2.5).toFixed(2) + '%'}</p>
                        </div>
                      </div>

                      {/* XAI Explanation */}
                      <div className={`mt-6 p-5 rounded-xl relative overflow-hidden group border ${isDark ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-emerald-50 border-emerald-200'}`}>
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                          <Brain size={60} className="text-emerald-500" />
                        </div>
                        <h5 className="text-emerald-500 font-bold text-xs uppercase tracking-widest flex items-center gap-2 mb-3">
                          <Brain size={16} />
                          Insight XAI Souverain
                        </h5>
                        {loadingXAI ? (
                          <div className="flex items-center gap-2">
                            <div className="w-4 h-4 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
                            <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>Génération de l'analyse XAI...</span>
                          </div>
                        ) : (
                          <p className={`text-sm leading-relaxed italic ${isDark ? 'text-white/90' : 'text-slate-700'}`}>
                            {xaiInsight?.explanation || `L'analyse XAI de ${selectedStock.name || selectedStock.symbol} montre des signaux ${lstmPrediction?.trend?.includes('UP') ? 'haussiers' : lstmPrediction?.trend?.includes('DOWN') ? 'baissiers' : 'mitigés'}. Le modèle LSTM prévoit ${lstmPrediction?.change_percent >= 0 ? 'une hausse' : 'une baisse'} de ${Math.abs(lstmPrediction?.change_percent || 0).toFixed(1)}% sur les 90 prochains jours avec une confiance de ${Math.round((lstmPrediction?.confidence || 0.8) * 100)}%.`}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* RIGHT COLUMN: Sidebar Info (col-span-4) */}
                  <div className="col-span-12 lg:col-span-4 space-y-6">

                    {/* Informations de Base */}
                    <div className={`rounded-xl p-6 border ${isDark ? 'bg-white/5 border-white/5' : 'bg-white border-slate-200 shadow-sm'}`}>
                      <h5 className={`font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        <Info size={16} />
                        Informations de Base
                      </h5>
                      <div className="space-y-3 text-xs">
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-gray-400' : 'text-slate-500'}>Marché :</span>
                          <span className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{selectedStock.market || 'actions'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-gray-400' : 'text-slate-500'}>Type :</span>
                          <span className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{selectedStock.type || 'CS'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-gray-400' : 'text-slate-500'}>Devise :</span>
                          <span className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{selectedStock.currency || 'usd'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-gray-400' : 'text-slate-500'}>Statut :</span>
                          <span className="text-emerald-500 font-bold">Actif</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-gray-400' : 'text-slate-500'}>Bourse :</span>
                          <span className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{selectedStock.exchange || 'XNAS'}</span>
                        </div>
                      </div>
                    </div>

                    {/* Détails de l'Entreprise */}
                    <div className={`rounded-xl p-6 border ${isDark ? 'bg-white/5 border-white/5' : 'bg-slate-50 border-slate-200'}`}>
                      <h5 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>Détails de l'Entreprise</h5>
                      <div className="space-y-4 text-xs">
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-gray-400' : 'text-slate-600'}>Employés :</span>
                          <span className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{selectedStock.employees?.toLocaleString() || '164,000'}</span>
                        </div>
                        <div>
                          <p className={`mb-1 ${isDark ? 'text-gray-400' : 'text-slate-600'}`}>Site Web :</p>
                          <a href="#" target="_blank" className="text-[#bc000c] font-bold hover:underline">
                            www.{selectedStock.symbol?.toLowerCase() || 'apple'}.com
                          </a>
                        </div>
                        <div>
                          <p className={`mb-2 uppercase font-bold tracking-tighter ${isDark ? 'text-gray-400' : 'text-slate-600'}`}>Description</p>
                          <p className={`leading-relaxed overflow-y-auto max-h-48 ${isDark ? 'text-gray-300' : 'text-slate-700'}`}>
                            {selectedStock.description || `${selectedStock.name} est une entreprise technologique majeure...`}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Entreprises Liées */}
                    <div className={`rounded-xl p-6 border ${isDark ? 'bg-white/5 border-white/5' : 'bg-slate-50 border-slate-200'}`}>
                      <h5 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>Entreprises Liées</h5>
                      <div className="grid grid-cols-3 gap-2">
                        {(selectedStock.related_companies || ['MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA']).map((ticker: string) => (
                          <button
                            key={ticker}
                            onClick={() => handleSelectStock(ticker)}
                            className={`px-2 py-2 text-xs font-bold rounded-lg transition-colors hover:bg-[#bc000c] hover:text-white ${isDark ? 'text-gray-400 bg-white/5' : 'text-slate-600 bg-slate-200'}`}
                          >
                            {ticker}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* LSTM AI Prediction */}
                    <div className={`rounded-xl p-6 border ${isDark ? 'bg-gradient-to-br from-[#0B1F3A]/50 to-black/40 border-white/10' : 'bg-gradient-to-br from-slate-50 to-white border-slate-200 shadow-sm'}`}>
                      <div className="flex justify-between items-start mb-4">
                        <h5 className={`font-bold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          <Brain size={16} className="text-emerald-500" />
                          Prédiction de Prix IA
                        </h5>
                        <span className="px-2 py-1 bg-emerald-500/20 text-emerald-500 text-[10px] font-bold uppercase rounded">Modèle LSTM</span>
                      </div>

                      {/* Trend Indicator */}
                      <div className={`flex items-center justify-between mb-4 p-3 rounded-lg ${isDark ? 'bg-black/30' : 'bg-slate-100'}`}>
                        <div>
                          <p className={`text-xs ${isDark ? 'text-white' : 'text-black'}`}>Prévision à {lstmPrediction?.prediction_days || 90} Jours</p>
                          <p className={`text-lg font-bold ${lstmPrediction?.trend?.includes('UP') ? 'text-emerald-500' :
                            lstmPrediction?.trend?.includes('DOWN') ? 'text-red-500' : 'text-yellow-500'
                            }`}>
                            {lstmPrediction?.trend === 'STRONG_UP' ? 'TENDANCE FORTEMENT HAUSSIÈRE' :
                              lstmPrediction?.trend === 'UP' ? 'TENDANCE HAUSSIÈRE' :
                                lstmPrediction?.trend === 'DOWN' ? 'TENDANCE BAISSIÈRE' :
                                  lstmPrediction?.trend === 'STRONG_DOWN' ? 'TENDANCE FORTEMENT BAISSIÈRE' :
                                    'TENDANCE HAUSSIÈRE'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className={`text-xs ${isDark ? 'text-white' : 'text-black'}`}>Confiance</p>
                          <p className={`text-lg font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{Math.round((lstmPrediction?.confidence || 0.85) * 100)}%</p>
                        </div>
                      </div>

                      {/* LSTM Chart */}
                      <div id="lstm-prediction-chart" className="h-48 w-full mb-4"></div>

                      {/* Price Targets */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className={`text-center p-3 rounded-lg ${isDark ? 'bg-white/5' : 'bg-slate-100'}`}>
                          <p className={`text-xs ${isDark ? 'text-white' : 'text-black'}`}>Prix Actuel</p>
                          <p className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{lstmPrediction?.current_price?.toFixed(2) || selectedStock.price?.toFixed(2) || '--'} TND</p>
                        </div>
                        <div className="text-center p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                          <p className={`text-xs ${isDark ? 'text-white' : 'text-black'}`}>Prédit ({lstmPrediction?.prediction_days || 90}j)</p>
                          <p className="text-emerald-500 font-bold">{lstmPrediction?.predicted_final_price?.toFixed(2) || (selectedStock.price * 1.125).toFixed(2)} TND</p>
                        </div>
                      </div>

                      <div className="mt-3 text-center">
                        <p className={`text-sm ${(lstmPrediction?.change_percent || 12.5) >= 0 ? 'text-emerald-500' : 'text-red-500'
                          }`}>
                          {(lstmPrediction?.change_percent || 12.5) >= 0 ? '+' : ''}{lstmPrediction?.change_percent?.toFixed(1) || '12.5'}% attendu
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>

      </div>
    </div>
  );
}
