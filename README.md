# GrabScore AI - Backend Architecture

GrabScore is an AI-powered Buy Now, Pay Later (BNPL) eligibility engine. It leverages transaction data to perform behavioral credit scoring using LLMs (Google Gemini) and integrates with payment providers for EMI processing.

## 🚀 Key Features

- **Behavioral Credit Scoring**: Uses Google Gemini to evaluate user behavior across 5 key dimensions:
  1. Purchase Frequency
  2. Deal Redemption Rate
  3. Category Diversification
  4. GMV Trajectory
  5. Return Behaviour
- **MCP Compliance**: Implements a Microservice Communication Protocol (MCP) server for robust transaction data retrieval and fraud velocity checks.
- **PayU Integration**: Fetches real-time EMI offers and handles payment initiation via PayU LazyPay.
- **FastAPI Framework**: High-performance, asynchronous Python backend with automated Swagger documentation.
- **Caching**: Redis-ready (configurable) with local cache fallback for optimized performance.

## 🛠️ Tech Stack

- **Core**: Python 3.11+, FastAPI
- **AI**: Google Generative AI (Gemini 2.0 Flash)
- **Database**: SQLAlchemy (SQLite for development)
- **Networking**: HTTPX, MCP SDK
- **Task Runner**: Uvicorn

## 📋 Prerequisites

- Python 3.11 or higher
- A Google AI Studio API Key (for Gemini)
- [Optional] Redis server for production caching

## ⚙️ Setup Instructions

1. **Clone the repository** and navigate to the backend folder.
2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment Variables**:
   Create a `.env` file in the root directory (refer to `.env.example` if available):
   ```env
   # Database
   DATABASE_URL=sqlite:///./grabcredit.db

   # Gemini Configuration
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL="gemini-flash-latest"
   USE_GEMINI=true

   # Security
   API_KEY=grabcredit-dev-key
   ```
5. **Start the Server**:
   ```bash
   uvicorn app.main:app --reload
   ```
   The backend will be available at `http://localhost:8000`.

## 📡 API Endpoints

### Credit Assessment
- `POST /api/v1/credit/assess`: Evaluates user eligibility.
  - **Input**: `user_id`, `requested_amount`
  - **Output**: Credit score, breakdown, limit, EMI offers, and AI narrative.

### Payments
- `POST /api/v1/credit/payu/initiate`: Generates PayU payment parameters for a selected EMI plan.

### Data & Discovery
- `GET /api/v1/docs`: Interactive Swagger documentation.
- `GET /api/v1/health`: Service health check.

## 🧪 Testing

Run the test suite using `pytest`:
```bash
pytest tests/
```

## 🏗️ Project Structure

```text
grabscore-backend/
├── app/
│   ├── api/          # API Route handlers
│   ├── core/         # Configuration & Database setup
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic validation schemas
│   └── services/     # Business logic & AI integrations
├── mcp_server.py     # MCP Tool implementation
├── requirements.txt  # Project dependencies
└── .env              # Environment configuration
```

## 📄 License
Internal Development - GrabScore AI Project.
