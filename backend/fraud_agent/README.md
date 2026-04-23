# Fraud Detection Agent

Quick start and deployment notes for the Fraud Detection Agent repository.

## Overview

This project provides a LangChain ReAct agent that analyzes account and card transactions
using pre-trained anomaly detection models (Autoencoder + LSTM) and Neo4j graph signals.
The agent exposes a notebook-based Gradio UI for quick experimentation.

## Setup

1. Create and activate a Python 3.10+ virtual environment.

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables (recommended):

- `MONGO_URI` (e.g., mongodb+srv://...)
- `MONGO_DB` (default: `fraud_db`)
- `NEO4J_URI` (e.g., neo4j+s://...)
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `OPENROUTER_KEY` (if using OpenRouter / Mistral)
- `JUDGE_MODEL` (optional LLM model name)

You can create a `.env` file and load it in your environment for development.

## Running (notebook)

Open `test00.ipynb` and run the Gradio cell. The notebook will attempt to find a free local port
and launch an interface where you can type queries such as `Check fraud for client181`.

## Important notes

- Sensitive credentials should be stored as environment variables. The code will fall back to
  existing values if env vars are not provided, but this is not recommended for production.
- Models are loaded and cached in memory to reduce latency; ensure sufficient RAM when using
  large models.
- The LLM should be used for explanation; decision logic is implemented in `services/decision_service.py`.

## Deployment

For production, containerize the app and ensure secret management (e.g., Hashicorp Vault, cloud secret store).
Add monitoring and structured logging in your deployment environment.

## Files to inspect first

- `agent/langchain_fraud_agent.py` — main agent loop
- `model/account_model.py` — model loading & inference (cached)
- `db/mongo.py` — MongoDB connection
- `graph/neo4j_connection.py` — Neo4j connectivity
- `test00.ipynb` — quick experiment UI
