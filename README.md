# RAG Chatbot

A FastAPI backend and React frontend for document ingestion, retrieval-augmented generation, and streaming chat.

## Project layout

- `backend/`: FastAPI API, ingestion pipeline, RAG services, and tests.
- `frontend/`: Vite React client.
- `docker-compose.yml`: Local service orchestration for the application, Redis, and Qdrant.

Environment templates are provided in `backend/.env.example` and `frontend/.env.example`.
