# Banteay Digital AI Service

This is the FastAPI foundation for Banteay Digital's future AI workflow:

```text
Express backend → AI service → Gemini and Qdrant
```

The health endpoint and the first retrieval foundation are implemented. The foundation can create/check the configured Qdrant collection and run a one-text embedding, insert, and search smoke test. LLM explanation, bulk ingestion, and scan integration are intentionally not implemented yet.

## Structure

| Path | Purpose |
| --- | --- |
| `app/main.py` | FastAPI application entry point. |
| `app/config.py` | Pydantic environment settings and production validation. |
| `app/api/health.py` | Health-check route. |
| `app/api/retrieval.py` | Knowledge-base retrieval route. |
| `app/api/router.py` | Combines API route modules. |
| `app/schemas/` | Pydantic request and response models. |
| `app/services/embedding_service.py` | Generates one Gemini embedding with dimension validation. |
| `app/repositories/qdrant_store.py` | Creates/checks the Qdrant collection, upserts, and searches vectors. |
| `app/repositories/scam_case_repository.py` | Reads one backend `ScamCase` from MySQL. |
| `scripts/verify_retrieval.py` | One-vector Gemini → Qdrant insert/search smoke test. |
| `tests/` | Automated service tests. |

## Run locally (PowerShell)

From the repository root:

```powershell
cd ai-service
$python = "C:\Users\U-ser\AppData\Local\Python\bin\python.exe"
& $python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Copy `.env.example` to `.env` before setting real secrets or changing defaults. The service runs with safe development defaults while no `.env` file exists.

Verify the service:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Open interactive API documentation at `http://localhost:8000/docs`.

Run tests in a separate PowerShell terminal:

```powershell
cd ai-service
.\.venv\Scripts\Activate.ps1
pytest
```

## Configuration

Never commit `.env` or provider keys. `PORT` must be between 1 and 65535. `AI_SERVICE_API_KEY` is required if `ENVIRONMENT=production`. When it is set, retrieval requests must send it in the `X-AI-Service-Key` header. Set the same value in `backend/.env` so the backend can call this service. The Qdrant and Gemini variables are not used by the health endpoint, but are required by the retrieval smoke test.

## Retrieval smoke test

Set a valid `GEMINI_API_KEY` in `.env`, make sure Qdrant is running at `QDRANT_URL`, then run:

```powershell
cd ai-service
.\.venv\Scripts\Activate.ps1
python -m scripts.verify_retrieval
```

The script creates or validates `scam_knowledge_v1`, embeds one sample scam text, upserts it with a stable ID, and confirms the same point is returned by a vector search.

## Index one backend scam case

Set `DATABASE_URL` in `ai-service/.env` to the same local MySQL URL used by `backend/.env`. Then index one case:

```powershell
cd ai-service
.\.venv\Scripts\Activate.ps1
python -m scripts.index_scam_case 1
```

This is a local development step only. It indexes one selected case, not the full catalogue.

## Retrieval API

Start the service, then submit text to `POST /api/v1/retrieve`:

```powershell
$headers = @{ "X-AI-Service-Key" = "your-AI_SERVICE_API_KEY" }
Invoke-RestMethod http://localhost:8000/api/v1/retrieve -Method Post -ContentType 'application/json' -Headers $headers -Body '{"type":"TEXT","value":"Urgent: send your OTP now","limit":3}'
```

The request shape matches the backend scan API, so the backend can call it without translating `type` and `value`. The endpoint returns matching Qdrant points with their similarity scores and payloads. A new backend scan includes these as `aiMatches`; deterministic scan results continue to work if retrieval is unavailable. It does not generate an LLM explanation or persist AI matches yet.
