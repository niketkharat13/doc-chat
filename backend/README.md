# Backend — DocChat

Quick setup and run instructions for the backend service.

## Environment

Copy the example and fill in real values (do NOT commit secrets):

```bash
cp .env-example .env
# then edit .env and fill values
```

Important vars:
- `DATABASE_URL` — Postgres connection string
- `GEMINI_API_KEY` — LLM/provider API key
- `GOOGLE_APPLICATION_CREDENTIALS` — path to Google service account JSON (if used)

The repository already ignores `.env` and `__pycache__` (see `.gitignore`).

## Install (recommended in a virtualenv)

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Run (development)

Start the app with uvicorn from the `backend/` folder:

```bash
uvicorn app.main:app --reload --port 8000
```

If you have trouble installing heavy PDF or native deps (e.g. `pymupdf`, `pdfplumber`, `camelot`), install them in your environment separately and consult the package docs for platform-specific steps.

## Notes
- Use `.env-example` as reference. Do not commit `.env` or secret files.
- The frontend files live in `../frontend/`.
