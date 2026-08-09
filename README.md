# Alumnx Sales Inbox

An AI-powered sales inbox routing system. It ingests incoming sales emails, uses a semantic layer (Google Gemini) to classify and route each email into a prioritized task, and stores the resulting tasks in PostgreSQL (Supabase).

## Features

- **Email ingestion** – accept a batch of incoming emails per candidate.
- **AI routing** – classify each email into a category, assignee, priority, and confidence using Gemini.
- **Deal value extraction** – parse Indian-format currency amounts (e.g. `10,00,000` → `1000000`).
- **Task storage** – persist routed tasks in PostgreSQL via SQLAlchemy.
- **Health endpoints** – `/health` and `/health/database` for operational checks.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, psycopg2, Pydantic
- **AI:** Google Gemini (`google-genai`)
- **Database:** PostgreSQL (Supabase)
- **Server:** Uvicorn

## Project Structure

```
alumnx-sales-inbox/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings (reads env vars)
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── main.py          # FastAPI app + routes
│   │   ├── models.py        # ORM models
│   │   ├── routing.py       # AI routing + deal value extraction
│   │   └── schemas.py       # Pydantic schemas
│   ├── .env.example         # Template for environment variables
│   └── requirements.txt
├── docs/
├── frontend/
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL (or a Supabase project)

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your real values:

| Variable         | Description                             |
| ---------------- | --------------------------------------- |
| `DATABASE_URL`   | PostgreSQL / Supabase connection string |
| `GEMINI_API_KEY` | Google Gemini API key                   |
| `CANDIDATE_ID`   | The candidate that owns this inbox      |
| `FRONTEND_URL`   | Frontend origin for CORS                |

> **Never commit your `.env` file.** It is ignored by `.gitignore`.

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

Then open:

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Database health: http://127.0.0.1:8000/health/database
- Interactive docs (Swagger): http://127.0.0.1:8000/docs

## Supabase / Database Notes

- Use the **Transaction Pooler** connection string (port `6543`) from the Supabase dashboard for stable connections.
- The pooler host looks like `aws-0-<region>.pooler.supabase.com`.
- The app auto-creates tables on startup via `Base.metadata.create_all`.

## License

Private project.
