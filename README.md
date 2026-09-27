# ⚖️ Legal Assistant RAG-based ChatBot

A production-ready, bilingual (Arabic/English) legal assistant chatbot powered by **Retrieval-Augmented Generation (RAG)**. Built to assist users in navigating Armenian labor law and pension regulations using AI-driven document retrieval and natural language generation.

---

## 🚀 Features

- 🔍 **RAG Pipeline** — Retrieves relevant legal documents from a vector store before generating answers
- 🌐 **Bilingual Support** — Handles queries in both Arabic and English
- 💬 **Chat Session Management** — Full session history with creation, retrieval, and deletion
- 🤖 **Multi-model AI** — Integrates OpenAI (embeddings + generation) and Google Gemini
- ⚡ **Fast & Scalable** — FastAPI backend with Redis caching and Chroma vector store
- 🐳 **Docker-ready** — Fully containerized with `docker-compose`

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                   │
│                     Vite · CSS · i18n                   │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST
┌───────────────────────▼─────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Auth / JWT  │  │  Chat API    │  │   RAG Service │ │
│  └──────────────┘  └──────────────┘  └───────┬───────┘ │
│                                               │         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────▼───────┐ │
│  │  SQLite DB   │  │  Redis Cache │  │ Chroma Vector │ │
│  └──────────────┘  └──────────────┘  │     Store     │ │
│                                       └───────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite |
| **Backend** | FastAPI, Python 3.11+ |
| **AI / LLM** | OpenAI GPT, Google Gemini 2.5 Flash |
| **Embeddings** | OpenAI `text-embedding-3-small` |
| **Vector Store** | ChromaDB |
| **Caching** | Redis |
| **Database** | SQLite (via SQLAlchemy) |
| **Auth** | JWT (python-jose) |
| **Infra** | Docker, Docker Compose |

---

## 📦 Project Structure

```
legal-assistant-rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/
│   │       └── rag/      # RAG pipeline, retriever
│   ├── data/             # Legal documents (raw + vector store)
│   ├── scripts/          # Ingestion / setup scripts
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── context/      # Language context
│   │   └── App.jsx
│   ├── .env.example
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Getting Started

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- Google Gemini API key

### 1. Clone the repository

```bash
git clone https://github.com/Rehobotw/legal-assistant-rag-chatbot.git
cd legal-assistant-rag-chatbot
```

### 2. Configure environment variables

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env and fill in your API keys

# Frontend
cp frontend/.env.example frontend/.env
```

**Required variables in `backend/.env`:**

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GOOGLE_API_KEY` | Your Google Gemini API key |
| `JWT_SECRET_KEY` | A secure random string for JWT signing |

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Ingest legal documents

Place your PDF documents in `backend/data/raw/`, then run the ingestion script:

```bash
docker-compose exec backend python scripts/ingest.py
```

---

## 🔧 Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

---

## 🧪 Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👤 Author

**Rehobotw** — [rehobotwgy@gmail.com](mailto:rehobotwgy@gmail.com)
