# Bank AI System - BH Bank

A comprehensive banking management system with AI agents for customer service, complaint handling, credit analysis, and more.

## Overview

This project is a full-stack banking application built with Django REST API and React. It features multiple AI agents powered by LangChain and LangGraph to handle various banking operations including customer complaints, account inquiries, credit analysis, and fraud detection.

## Project Structure

```
project/
├── backend/                 # Django REST API
│   ├── backend/            # Django settings & configuration
│   ├── api/               # API endpoints & views
│   │   ├── views.py       # Authentication & user endpoints
│   │   ├── custom_admin.py # MongoDB admin interface
│   │   ├── agent_views.py  # AI agent endpoints
│   │   └── mongodb.py     # MongoDB connection
│   ├── complaint-agent/    # Complaint handling AI agent
│   │   ├── agents/       # ReAct agent & tools
│   │   └── db/           # RAG & vector storage
│   ├── reception-agent/   # Reception/chat AI agent
│   ├── credit_agent/     # Credit analysis AI agent
│   ├── dashboard_agent/   # Dashboard generation agent
│   └── requirements.txt
│
├── frontend/               # React + TypeScript + Vite
│   ├── src/
│   │   ├── pages/        # React pages
│   │   ├── components/   # Reusable components
│   │   └── context/      # Auth context
│   └── package.json
│
└── README.md
```

## Features

### 1. Authentication & Authorization
- Email + CIN based login (no password required)
- Google OAuth integration
- JWT token-based authentication
- Role-based access control (Customer, Chef d'Agence)

### 2. Custom MongoDB Admin Interface
- Dashboard with bank statistics
- View, search, filter, edit, delete MongoDB collections
- Role-based access:
  - **Customers**: See only their accounts, transactions, bookings, reclamations
  - **Chefs/Admins**: Full access to all collections
- Dark/Light theme support

### 3. AI Agents

#### Complaint Agent (`/complaint-agent`)
- Processes customer complaints using ReAct pattern
- RAG-based policy lookup (Law 2016-48)
- Google Calendar integration for appointments
- Multiple sub-agents for specialized tasks

#### Reception Agent (`/bank-agent`)
- General banking inquiries
- Account information
- Transaction history

#### Credit Agent (`/credit-agent`)
- Loan application analysis
- Risk assessment
- Document processing (PDF, Excel)

#### Fraud Detection Agent
- Transaction monitoring
- Anomaly detection

### 4. MongoDB Collections

| Collection | Description |
|------------|-------------|
| `customers` | Customer profiles with personal info |
| `accounts` | Bank accounts (checking, savings) |
| `bank_transactions` | All transaction records |
| `cheques` | Cheque management |
| `reclamations` | Customer complaints |
| `bookings` | Appointments |
| `recovery_loans` | Loan recovery tracking |
| `users` | System users |
| `bank_params` | Bank parameters |

## Prerequisites

- **Python**: 3.9+ (recommended 3.11)
- **Node.js**: 18+
- **MongoDB**: Atlas or local instance
- **Ollama**: For local LLM embeddings (optional)

## Environment Variables

Create `.env` file in `backend/`:

```env
# MongoDB Connection
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
JWT_SECRET=your_super_secret_jwt_key

# AI/LLM Configuration
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1

# Or use Ollama (local)
# OPENAI_MODEL=qwen3.5:4b
# OPENAI_BASE_URL=http://localhost:1234/v1
# OPENAI_API_KEY=lm-studio

# Ollama Embeddings
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_EMBED_MODEL=mxbai-embed-large:latest

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Google Calendar (optional - for booking sync)
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REFRESH_TOKEN=...
```

## Installation

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Or (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (for Django admin)
python manage.py migrate

# Start server
python manage.py runserver
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Running the Application

### 1. Start MongoDB
Ensure your MongoDB instance is running locally or use MongoDB Atlas.

### 2. Start Backend
```bash
cd backend
python manage.py runserver 8000
```

### 3. Start Frontend
```bash
cd frontend
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register/` | POST | Register new user |
| `/api/auth/login/` | POST | Login (email + CIN) |
| `/api/auth/google/` | POST | Google OAuth login |

### AI Agents
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/complaint/` | POST | Complaint agent chat |
| `/api/agents/bank/` | POST | Reception agent chat |
| `/api/agents/bank/memory/` | GET | Get chat memory |
| `/api/agents/bank/new-session/` | POST | Start new session |
| `/api/agents/bank/clear-memory/` | POST | Clear chat memory |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/` | GET | Dashboard stats |
| `/admin/<collection>/` | GET | List documents |
| `/admin/<collection>/<id>/` | GET/POST | View/Edit document |
| `/admin/<collection>/<id>/delete/` | POST | Delete document |

### Account
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/accounts/login/` | POST | Browser-based login |
| `/accounts/logout/` | GET | Logout |
| `/accounts/dashboard/` | GET | User dashboard |

## Tech Stack

### Backend
- **Framework**: Django 4.2
- **API**: Django REST Framework
- **Database**: MongoDB (via PyMongo)
- **Authentication**: JWT, Google OAuth
- **AI**: LangChain, LangGraph, OpenAI/Ollama

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **Routing**: React Router
- **HTTP Client**: Axios

### Database
- **Primary**: MongoDB (banking data)
- **Secondary**: SQLite (Django sessions)

## User Roles

### Customer
- View own accounts, transactions, bookings, reclamations
- Chat with AI agents
- Make complaints

### Chef d'Agence (Branch Manager)
- Full access to all MongoDB collections
- View all customer data
- Manage complaints
- Access admin panel

## Screenshots

The application features:
- Login page with email + CIN authentication
- Dashboard with role-based navigation
- Custom MongoDB admin interface
- AI chat interfaces for different agents
- Dark/Light theme toggle

## Troubleshooting

### MongoDB Connection Issues
- Verify MongoDB URI in `.env`
- Check network/firewall settings
- For local MongoDB: ensure service is running

### Frontend-Backend Connection
- CORS is configured in Django settings
- Check that frontend calls correct API URL

### AI Agent Not Responding
- Verify OpenAI API key or Ollama is running
- Check server logs for errors

## License

Private - BH Bank Project
