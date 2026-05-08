# Fraud Detection Agent

## Overview

The Fraud Detection Agent is a sophisticated AI system designed to identify and analyze potentially fraudulent transactions in real-time. Built using LangChain's ReAct pattern, it combines machine learning models (Autoencoder + LSTM) with graph-based analytics from Neo4j to provide comprehensive fraud detection capabilities.

The agent processes both account and card transactions, leveraging multiple signal sources to detect anomalies and generate human-readable explanations for each flagged transaction. A notebook-based Gradio UI allows for quick experimentation and testing.

## Features

### Core Capabilities
- **Real-time Transaction Analysis**: Monitors incoming transactions and evaluates fraud risk
- **Anomaly Detection**: Uses Autoencoder and LSTM models for pattern recognition
- **Graph Analytics**: Neo4j-based relationship analysis for detecting complex fraud schemes
- **LLM Explanation**: Generates human-readable explanations for flagged transactions
- **Alert Management**: Automated alert generation and escalation workflows

### Technical Features
- ReAct agent pattern with tool calling
- Pre-trained ML model caching for low latency
- MongoDB for transaction storage
- Neo4j for graph-based fraud signals
- Gradio UI for testing and demonstration

## Tech Stack

### Backend
- **Language**: Python 3.10+
- **AI Framework**: LangChain + LangGraph
- **ML Models**: TensorFlow/Keras (Autoencoder, LSTM)
- **Database**: MongoDB (PyMongo)
- **Graph Database**: Neo4j
- **UI**: Gradio

### Dependencies
```
langchain
langgraph
pymongo
neo4j
gradio
tensorflow
numpy
pandas
python-dotenv
```

## Directory Structure

```
fraud_agent/
├── agent/
│   ├── langchain_fraud_agent.py   # Main ReAct agent loop
│   └── tools.py                    # Tool definitions
│
├── model/
│   ├── account_model.py           # Model loading & inference
│   ├── autoencoder.py             # Autoencoder model
│   └── lstm.py                     # LSTM model
│
├── db/
│   ├── mongo.py                   # MongoDB connection
│   └── fraud_repository.py        # Data access layer
│
├── graph/
│   ├── neo4j_connection.py        # Neo4j connectivity
│   └── fraud_graph.py            # Graph queries
│
├── services/
│   ├── decision_service.py        # Fraud decision logic
│   └── alerting_service.py        # Alert generation
│
├── test00.ipynb                   # Gradio UI for testing
├── requirements.txt
└── README.md
```

## Getting Started

### Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file with the following variables:

```env
# MongoDB
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DB=fraud_db

# Neo4j
NEO4J_URI=neo4j+s://your-neo4j-uri
NEO4J_USER=neo4j_user
NEO4J_PASSWORD=neo4j_password

# LLM (optional - for explanations)
OPENROUTER_KEY=your_openrouter_key
JUDGE_MODEL=mistralai/mistral-7b-instruct
```

### Running

```bash
# Start Jupyter notebook
jupyter notebook test00.ipynb

# Run the Gradio cell to launch UI
# Access at http://localhost:7860

# Test queries:
# "Check fraud for client181"
# "Analyze transaction TXN-12345"
# "Get fraud score for account ACC-98765"
```

## Model Details

### Autoencoder Model
- Architecture: Input → 128 → 64 → 32 → 64 → 128 → Output
- Trained on normal transaction patterns
- Reconstruction error threshold determines anomaly score

### LSTM Model
- Sequential pattern detection for time-series data
- Captures temporal dependencies in transaction sequences
- Combined with autoencoder for hybrid detection

### Graph Features
- Account relationship analysis
- Transaction network topology
- Velocity patterns (rapid successive transactions)
- Device/IP correlation analysis

## Important Notes

### Security
- Sensitive credentials should be stored as environment variables
- Do not commit `.env` files to version control
- Use secret management in production (Hashicorp Vault, cloud secrets)

### Performance
- Models are loaded and cached in memory to reduce latency
- Ensure sufficient RAM when using large models
- Consider GPU acceleration for production workloads

### LLM Usage
- The LLM is used for explanation generation only
- Decision logic is implemented in `services/decision_service.py`
- This ensures deterministic, auditable fraud decisions

## Deployment

### Production Requirements
1. Containerize using Docker
2. Implement secret management
3. Add monitoring and logging
4. Set up health checks
5. Configure auto-scaling

### Docker Example
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "agent/langchain_fraud_agent.py"]
```

## Files to Inspect

- `agent/langchain_fraud_agent.py` — Main agent loop
- `model/account_model.py` — Model loading & inference
- `db/mongo.py` — MongoDB connection
- `graph/neo4j_connection.py` — Neo4j connectivity
- `services/decision_service.py` — Fraud decision logic
- `test00.ipynb` — Quick experiment UI

## Acknowledgments

BH Bank Fraud Detection Project - AI Banking Security