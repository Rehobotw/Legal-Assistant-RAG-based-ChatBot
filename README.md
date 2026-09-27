# RAG Chatbot

A FastAPI backend and React frontend for document ingestion, retrieval-augmented generation, and streaming chat.

## Project layout

- `backend/`: FastAPI API, ingestion pipeline, RAG services, and tests.
- `frontend/`: Vite React client.
- `docker-compose.yml`: Local service orchestration for the application, Redis, and Qdrant.

Environment templates are provided in `backend/.env.example` and `frontend/.env.example`.

## Cassation precedent retrieval

The backend indexes the cleaned Amharic Federal Supreme Court reports in
`backend/data/raw/` with LangChain, OpenAI `text-embedding-3-small`, and a local
Chroma collection. Gemini creates a short, source-constrained holding summary for
each returned case; the API does not combine holdings into an uncited legal
conclusion.

Configure `OPENAI_API_KEY` and `GOOGLE_API_KEY` in `backend/.env`, then create or
refresh the local index:

```bash
cd backend
python scripts/ingest.py --recreate
```

The generated Chroma data is intentionally ignored by Git. Query `POST
/api/v1/chat` with `language: "am"` for Amharic retrieval. Results are ranked and
include the cassation file number, date, court, report location, and holding.
