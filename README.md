# Bank Complaint AI System

A banking complaint management system with an AI agent that handles customer complaints, bookings, and provides policy information using RAG.

## Project Structure

```
project/
├── backend/                 # Django REST API
│   ├── backend/            # Django settings
│   ├── api/                # API endpoints
│   ├── complaint-agent/    # AI Agent
│   │   ├── agents/         # ReAct agent & tools
│   │   ├── db/             # MongoDB handler
│   │   ├── graph/          # LangGraph pipeline (optional)
│   │   └── ressources/     # ChromaDB, PDFs
│   └── requirements.txt
└── frontend/               # React + TypeScript + Vite
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- MongoDB (Atlas or local)
- Ollama (for local LLM embeddings)

## Environment Variables

Create `.env` file in `backend/`:

```env
# MongoDB
APP_MONGO_URI=mongodb+srv://...
APP_MONGO_DB_NAME=bank_ai
GOOGLE_AUTH_MONGO_URI=mongodb+srv://...
GOOGLE_AUTH_MONGO_DB_NAME=google_auth

# JWT
JWT_SECRET=your_secret_key

# LLM (OpenAI or Ollama)
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Ollama (for embeddings)
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_EMBED_MODEL=mxbai-embed-large:latest

# Google Calendar (OAuth)
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REFRESH_TOKEN=...
```

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Running the Application

### 1. Start MongoDB

Ensure your MongoDB instance is running.

### 2. Start Ollama (for embeddings)

```bash
ollama serve
ollama pull mxbai-embed-large:latest
ollama pull qwen3.5:4b
```

### 3. Start Backend

```bash
cd backend
pip install -r ./requirements.txt
python manage.py runserver 8000
```

### 4. Start Frontend

```bash
cd frontend
npm run dev
```

### 5. Access the App

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

## Features

### AI Agent
- **ReAct Agent**: Processes complaints using reasoning + tools
- **RAG**: Uses ChromaDB to query banking regulations (Law 2016-48)
- **Memory**: In-memory storage for user context
- **Google Calendar**: Syncs bookings to user's calendar

### Available Tools
- `fetch_customer_context`: Get customer data from MongoDB
- `extract_complaint_details`: Parse complaint and identify tasks
- `record_complaint`: Save complaint to database
- `query_rag_policies`: Search bank regulations
- `book_appointment`: Create booking + sync to Google Calendar
- `suggest_booking_slots`: Get available time slots
- `generate_client_message`: Create professional response
- `call_subagent`: Delegate to specialist agents (reception, credit, etc.)

### MongoDB Collections
- `customers` - Customer profiles
- `accounts` - Bank accounts
- `bank_transactions` - Transaction history
- `cheques` - Cheque information
- `reclamations` - Complaint records
- `bookings` - Appointment records + Google Calendar sync

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register/` | POST | Register user |
| `/api/auth/login/` | POST | Login |
| `/api/auth/google/` | POST | Google OAuth |
| `/api/agents/complaint/` | POST | AI agent chat |

## Tech Stack

- **Backend**: Django, Django REST Framework, PyMongo
- **Frontend**: React, TypeScript, Vite, TailwindCSS
- **AI**: LangChain, LangGraph, Ollama
- **Vector DB**: ChromaDB
- **Database**: MongoDB