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
| `app/api/ocr.py` | Image-to-text endpoint for scan screenshots. |
| `app/api/router.py` | Combines API route modules. |
| `app/schemas/` | Pydantic request and response models. |
| `app/services/embedding_service.py` | Generates one Gemini embedding with dimension validation. |
| `app/services/scam_case_indexer.py` | Converts backend scam cases into Qdrant documents. |
| `app/repositories/qdrant_store.py` | Creates/checks the Qdrant collection, upserts, and searches vectors. |
| `app/repositories/scam_case_repository.py` | Reads one backend `ScamCase` from MySQL. |
| `scripts/index_scam_cases.py` | Batch-indexes backend scam cases. |
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

## OCR image-to-text

The service uses the local Tesseract executable for screenshot/photo text extraction.
Set `TESSERACT_CMD`, `OCR_LANGUAGES` (for example `khm+eng`), and the optional
size/timeout limits in `.env`. Use `OCR_TESSDATA_DIR=.tessdata` to keep extra
language data local to this service. The configured executable must have every
requested language installed in its `tessdata` directory. On Windows verify the
machine-wide languages with:

```powershell
& $env:TESSERACT_CMD --list-langs
```

`OCR_TESSDATA_DIR` should be a relative directory without spaces on Windows;
for another location, configure Tesseract's `TESSDATA_PREFIX` environment variable.
To add Khmer language data to the local directory (which is intentionally ignored
by Git), run from `ai-service`:

```powershell
New-Item -ItemType Directory -Path .tessdata -Force
Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_fast/raw/main/khm.traineddata -OutFile .tessdata\khm.traineddata
Copy-Item "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" .tessdata\eng.traineddata
```

Send a multipart image to `POST /api/v1/ocr`. The image is processed in memory
only and is not stored by the AI service:

```powershell
$headers = @{ "X-AI-Service-Key" = "your-AI_SERVICE_API_KEY" }
Invoke-RestMethod http://localhost:8000/api/v1/ocr -Method Post -Headers $headers -Form @{ image = Get-Item .\scan.png }
```

The response includes `text`, the languages used, and `character_count`. The caller
can submit `text` to the existing text scan endpoint after extraction.

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

## Batch-index scam cases

For production knowledge, index only records marked `verified=true` in the backend database:

```powershell
cd ai-service
.\.venv\Scripts\Activate.ps1
python -m scripts.index_scam_cases
```

The script is safe to re-run: each database case has a stable Qdrant point ID and is replaced rather than duplicated. The current local synthetic catalogue is unverified, so it requires this explicit development-only command:

```powershell
python -m scripts.index_scam_cases --include-unverified
```

## Retrieval API

Start the service, then submit text to `POST /api/v1/retrieve`:

```powershell
$headers = @{ "X-AI-Service-Key" = "your-AI_SERVICE_API_KEY" }
Invoke-RestMethod http://localhost:8000/api/v1/retrieve -Method Post -ContentType 'application/json' -Headers $headers -Body '{"type":"TEXT","value":"Urgent: send your OTP now","limit":3}'
```

The request shape matches the backend scan API, so the backend can call it without translating `type` and `value`. The endpoint embeds labelled queries (`TEXT` or `URL`) and returns only `scam_case` records above `RETRIEVAL_MIN_SCORE` (default `0.70`). In production, it defaults to verified cases only. A new backend scan includes these as `aiMatches`; deterministic scan results continue to work if retrieval is unavailable.

## Simple AI analysis response (testing)

`POST /api/v1/analyze` deliberately returns a small community-facing response while the integration is being tested:

```json
{
  "assessment": "SUSPICIOUS",
  "summary": "This message asks for a one-time password, which can put your account at risk.",
  "recommendedActions": [
    "Do not share the code.",
    "Contact your bank using its official app or number."
  ]
}
```

Retrieved cases and deterministic findings are accepted as context, but the model is not required to cite them in this phase. The backend maps this minimal response to its existing stored fields.

## Text-analysis safeguards

Before the LLM is called, the backend checks submitted text for transparent
signals in English and Khmer: requests for OTP/verification codes, passwords
or PINs, urgency or account threats, and payment requests. It also applies the
same structural checks to up to three links embedded in a message. These are
warning signals, not proof of a scam, and are provided to the LLM as context.

## Text benchmark

The bilingual starter benchmark is at `../backend/data/text_benchmark.json`.
It contains labelled synthetic cases only; replace or expand it with
moderator-verified community messages before using its metrics for a release
decision. From `backend`, run:

```powershell
npm.cmd run benchmark:text
```

The report shows true positives, false positives, missed scams, precision,
recall, specificity, and accuracy for the deterministic text layer. Add
`-- --strict` to make the command fail if precision or recall is below 80%.

With Qdrant, Gemini, and the AI service running, use the same cases to verify
retrieval and the LLM response contract:

```powershell
cd ai-service
python -m scripts.benchmark_text_service
```

This live runner reports retrieved-match counts and validates the minimal AI
response for every case. It is an integration check, not an LLM-accuracy score;
review its output against moderator labels before changing production settings.
