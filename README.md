# Banteay Digital AI Service

This is the FastAPI foundation for Banteay Digital's future AI workflow:

```text
Express backend → AI service → Gemini and Qdrant
```

Only the health endpoint and configuration validation are implemented. Gemini calls, embeddings, Qdrant retrieval, ingestion, and LLM analysis are intentionally not implemented yet.

## Structure

| Path | Purpose |
| --- | --- |
| `app/main.py` | FastAPI application entry point. |
| `app/config.py` | Pydantic environment settings and production validation. |
| `app/api/` | HTTP route modules. |
| `app/schemas/` | Pydantic request and response models. |
| `app/services/` | Reserved for Gemini, embedding, RAG, and ingestion logic. |
| `app/repositories/` | Reserved for Qdrant and other external adapters. |
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

Never commit `.env` or provider keys. `PORT` must be between 1 and 65535. `AI_SERVICE_API_KEY` is required if `ENVIRONMENT=production`. The Qdrant and Gemini variables are placeholders for the next implementation phase and are not used by the current health endpoint.
