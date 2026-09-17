# Banteay Digital AI Service

## URL scan evidence

The backend URL scanner sends a typed `urlEvidence` object to the existing
`POST /api/v1/analyze` endpoint alongside `type: "URL"` and `value`.
It includes VirusTotal status, analysis date, engine statistics, flagged engine
labels, source (`report` or `analysis`), and an optional final URL. Completed
evidence requires nonempty valid statistics. Existing text requests continue
to work without this field. The Gemini prompt treats provider data as untrusted
context and explains that undetected verdicts and zero detections do not prove
safety. The backend enforces risk floors and supplies fallback guidance.

`VIRUSTOTAL_API_KEY` belongs in the Express backend configuration. No VirusTotal
key is needed in this AI service. See `Backend/URL_SCAN.md` for job endpoints,
frontend polling, rate limits, and operational constraints.

Run tests without reading any `.env` file:
`python scripts/test_without_env.py -q`.

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
python -m pip install -r requirements-dev.txt
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

Never commit environment files or provider keys. `PORT` must be between 1 and 65535. In production, `AI_SERVICE_API_KEY`, `QDRANT_API_KEY`, and `GEMINI_API_KEY` must each be at least 32 characters. Requests from the backend send `AI_SERVICE_API_KEY` in `X-AI-Service-Key`; configure the same value in both services. Configure `QDRANT_URL` and `QDRANT_API_KEY` together. Set `ALLOWED_HOSTS` to the comma-separated internal DNS names and public hostnames that may reach the service, such as `banteay-ai,ai.example.com,127.0.0.1`.

Production also supports `QDRANT_TIMEOUT_SECONDS`, `GEMINI_TIMEOUT_MS`, `AI_MAX_CONCURRENCY`, `OCR_MAX_CONCURRENCY`, `OCR_MAX_IMAGE_BYTES`, `OCR_MAX_IMAGE_PIXELS`, and `MAX_REQUEST_BYTES`. Interactive FastAPI documentation and the OpenAPI route are disabled automatically when `ENVIRONMENT=production`.

If direct scam-case indexing uses an external MySQL server, append `sslaccept=strict` to `DATABASE_URL`; add a URL-encoded `sslcert` path when the server CA is not in the system trust store.

## Container deployment

Build from this directory and inject secrets only at runtime:

```powershell
docker build -t banteay-ai .
docker run --rm -p 8000:8000 `
  -e ENVIRONMENT=production `
  -e ALLOWED_HOSTS=localhost,127.0.0.1 `
  -e AI_SERVICE_API_KEY=<32-plus-character-shared-key> `
  -e GEMINI_API_KEY=<gemini-key> `
  -e QDRANT_URL=https://qdrant.example.com:6333 `
  -e QDRANT_API_KEY=<qdrant-key> `
  banteay-ai
```

The image runs as a non-root user and includes English and Khmer Tesseract data. Put the service and Qdrant on a private network; for self-hosted Qdrant, configure the same value as `QDRANT__SERVICE__API_KEY` and enable TLS before exposing it outside that network.

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

## Structured AI analysis response

`POST /api/v1/analyze` deliberately returns a small community-facing response while the integration is being tested:

```json
{
  "riskLevel": "HIGH",
  "confidenceScore": 0.96,
  "assessment": "SUSPICIOUS",
  "evidenceSufficiency": "SUFFICIENT",
  "riskSignals": [
    {
      "category": "CREDENTIAL_THEFT",
      "severity": "CRITICAL",
      "evidence": "send the code",
      "message": "The message asks for a private verification code."
    }
  ],
  "summary": "This message asks for a one-time password, which can put your account at risk.",
  "recommendedActions": [
    "Do not share the code.",
    "Contact your bank using its official app or number."
  ]
}
```

The model assesses submitted content independently before using retrieval as
supporting context. Every model-generated risk signal must quote the submitted
input. The backend rejects ungrounded signal quotes and enforces an assessment
floor from valid signals, deterministic findings, and URL-reputation evidence.
Text and OCR scans containing Khmer script receive Khmer explanations and
recommendations; English and unsupported-language text receive English output.
URL-only scans use the supported English/Khmer interface preference because a
URL may not contain enough natural-language content to detect.
When retrieval returns no usable match or is unavailable, the model still
returns an independent risk level, confidence score, explanation, and practical
actions. The backend accepts that independent classification at 70% confidence
or higher while retaining deterministic and URL-reputation safety floors. A
missing match is treated as missing context, never as evidence of safety.

Scam-case retrieval includes the moderated case description, sample text, and
indicators in the LLM context. Re-run `python -m scripts.index_scam_cases` after
deploying this version so existing Qdrant payloads receive those fields.

## Text-analysis safeguards

Before the LLM is called, the backend checks submitted text for transparent
signals in English and Khmer: requests for OTP/verification codes, passwords
or PINs, urgency or account threats, and payment requests. It also applies the
same structural checks to up to three links embedded in a message. These are
warning signals, not proof of a scam, and are provided to the LLM as context.

## Text benchmark

The bilingual deterministic starter benchmark is at
`../BanteayDigital-Backend/data/text_benchmark.csv`.
It contains labelled synthetic cases only; replace or expand it with
moderator-verified community messages before using its metrics for a release
decision. From `backend`, run:

```powershell
npm.cmd run benchmark:text
```

The report shows true positives, false positives, missed scams, precision,
recall, specificity, and accuracy for the deterministic text layer. Add
`-- --strict` to make the command fail if precision or recall is below 80%.

With Qdrant, Gemini, and the AI service running, use the separate novelty suite
to measure the LLM on scam wording outside the seed catalogue:

```powershell
cd BanteayDigital-AI
python -m scripts.benchmark_text_service --strict
```

This live runner reports retrieval coverage, assessments, grounded signal
counts, and pass/fail results against minimum expected assessments. The cases
remain synthetic; expand them with moderator-verified, privacy-reviewed examples
before using the pass rate as a release gate.
