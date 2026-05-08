# Bank AI System - BH Bank

## Overview

A comprehensive banking management system with AI agents for customer service, complaint handling, credit analysis, and fraud detection. Built with Django REST API and React, this platform provides a complete solution for Tunisian banking operations with intelligent automation and real-time data processing.

The system leverages cutting-edge AI technologies including LangChain, LangGraph, and local LLM inference via Ollama to deliver personalized customer experiences while maintaining strict security and compliance standards required for banking operations.

## Features

### Authentication & Security
- Email + CIN based login (passwordless authentication)
- Google OAuth integration for seamless access
- JWT token-based authentication with refresh tokens
- Role-based access control (Customer, Chef d'Agence, Admin)
- Session management with automatic token refresh

### Custom MongoDB Admin Interface
- Real-time dashboard with bank statistics and KPIs
- Full CRUD operations on MongoDB collections
- Advanced search and filtering capabilities
- Role-based data visibility (customers see only their data)
- Dark/Light theme support with responsive design
- Export functionality for reports

### AI Agents System

#### Complaint Agent (`/complaint-agent`)
- ReAct pattern agent with tool calling
- RAG-based policy lookup using Law 2016-48 (Tunisian consumer protection)
- Google Calendar integration for appointment booking
- Automatic complaint categorization and prioritization
- Resolution tracking with SLA monitoring
- Email notifications via Resend

#### Reception Agent (`/bank-agent`)
- General banking inquiries handling
- Account information queries
- Transaction history lookup
- Product recommendations
- Multi-turn conversation with memory

#### Credit Agent (`/credit-agent`)
- Loan application analysis
- Risk assessment scoring
- Document processing (PDF, Excel)
- Credit limit calculations
- Approval workflow automation

#### Dashboard Agent
- Automated report generation
- Financial analytics
- Custom query handling
- Chart and visualization creation

#### Fraud Detection Agent
- Real-time transaction monitoring
- Anomaly detection using Autoencoder + LSTM models
- Neo4j graph-based fraud signals
- Alert generation and escalation
- LLM-based explanation generation

### Data Collections
- `customers` - Customer profiles and personal information
- `accounts` - Bank accounts (checking, savings, deposits)
- `bank_transactions` - Complete transaction history
- `cheques` - Cheque management and tracking
- `reclamations` - Customer complaints and resolution tracking
- `bookings` - Appointment scheduling
- `recovery_loans` - Loan recovery management
- `users` - System users and roles
- `bank_params` - Bank configuration parameters

## Tech Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **Styling**: TailwindCSS for responsive, modern UI
- **State Management**: React Context API
- **Routing**: React Router v6
- **HTTP Client**: Axios with interceptors
- **Charts**: Recharts for data visualization
- **Icons**: Lucide React

### Backend
- **Framework**: Django 4.2 with Python 3.11
- **API**: Django REST Framework
- **Database**: MongoDB via PyMongo (primary data store)
- **Authentication**: JWT (PyJWT) + Google OAuth
- **AI/ML**: LangChain, LangGraph, OpenAI, Ollama
- **Task Queue**: Celery (for async processing)
- **Email**: Resend API
- **Web Scraping**: Playwright + Requests

### Other Tools
- **LLM Runtime**: Ollama (local inference)
- **Embeddings**: mxbai-embed-large
- **Vector Store**: Chroma (for RAG)
- **Graph Database**: Neo4j (fraud detection)
- **Calendar**: Google Calendar API
- **Browser Automation**: Playwright

## Directory Structure

```
project/
├── backend/
│   ├── backend/                    # Django project settings
│   │   ├── settings.py             # Main configuration
│   │   ├── urls.py                 # URL routing
│   │   └── wsgi.py                 # WSGI entry point
│   │
│   ├── api/                        # REST API endpoints
│   │   ├── views.py                # API views
│   │   ├── urls.py                 # URL patterns
│   │   ├── agent_views.py          # AI agent endpoints
│   │   ├── mongodb.py             # MongoDB connection
│   │   └── custom_admin.py        # MongoDB admin interface
│   │
│   ├── complaint-agent/            # Complaint handling agent
│   │   ├── agents/
│   │   │   ├── react_agent.py     # ReAct agent implementation
│   │   │   └── tools.py            # Tool definitions
│   │   └── db/
│   │       ├── rag_utils.py       # RAG utilities
│   │       └── vector_store.py    # Chroma vector store
│   │
│   ├── reception-agent/            # Reception/chat agent
│   │   ├── agents/
│   │   │   └── react_agent.py      # Main agent
│   │   └── bank_tools.py          # Banking tools
│   │
│   ├── credit_agent/               # Credit analysis agent
│   │   ├── agents/
│   │   └── services/
│   │
│   ├── dashboard_agent/            # Dashboard generation agent
│   │   └── code/
│   │       └── agent.py            # Agent implementation
│   │
│   ├── fraud_agent/                # Fraud detection agent
│   │   ├── agent/                  # ReAct agent
│   │   ├── model/                  # ML models
│   │   ├── db/                     # MongoDB
│   │   ├── graph/                  # Neo4j
│   │   └── services/               # Decision logic
│   │
│   ├── pi_integration/
│   │   └── pi_agents/
│   │       └── scraper.py          # Car/house scraping
│   │
│   ├── requirements.txt            # Python dependencies
│   └── .env                        # Environment variables
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx           # Login page
│   │   │   ├── Dashboard.tsx       # Main dashboard
│   │   │   ├── Admin.tsx           # MongoDB admin
│   │   │   ├── ComplaintChat.tsx  # Complaint agent UI
│   │   │   ├── BankAgent.tsx      # Reception agent UI
│   │   │   └── ...
│   │   │
│   │   ├── components/
│   │   │   ├── Navbar.tsx         # Navigation
│   │   │   ├── Sidebar.tsx        # Side menu
│   │   │   ├── ChatBox.tsx        # Chat interface
│   │   │   ├── DataTable.tsx      # Data display
│   │   │   └── ...
│   │   │
│   │   ├── context/
│   │   │   └── AuthContext.tsx    # Auth state
│   │   │
│   │   ├── services/
│   │   │   └── api.ts             # API client
│   │   │
│   │   └── App.tsx                # Main app
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── docs/                           # Documentation
│   └── COMPLAINT_AGENT.md         # Agent architecture
│
└── README.md                       # This file
```

## Getting Started

### Prerequisites

- Python 3.9+ (recommended 3.11)
- Node.js 18+
- MongoDB (Atlas or local)
- Ollama (optional, for local LLM)

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Or (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (see configuration section)
copy .env.example .env

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Configuration (.env)

```env
# MongoDB
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DB=bh_bank

# JWT
JWT_SECRET=your_super_secret_jwt_key

# Ollama (Local LLM)
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=mxbai-embed-large:latest

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Google Calendar
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REFRESH_TOKEN=...

# Email (Resend)
RESEND_API_KEY=re_xxxxx
```

### Running the Application

1. **MongoDB**: Ensure MongoDB is running (local or Atlas)
2. **Ollama** (optional): `ollama serve` to start local LLM
3. **Backend**: `python manage.py runserver 8000`
4. **Frontend**: `npm run dev` (runs on http://localhost:5173)

### Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin/

## Troubleshooting

### MongoDB Connection
- Verify URI in `.env`
- Check network/firewall settings
- For local: ensure MongoDB service is running

### Frontend-Backend Connection
- CORS is configured in Django settings
- Verify VITE_API_URL in frontend

### AI Agent Issues
- Verify Ollama is running: `ollama list`
- Check server logs for errors
- Ensure API keys are configured

## Acknowledgments

Developed for BH Bank Tunisia - Banking AI Project