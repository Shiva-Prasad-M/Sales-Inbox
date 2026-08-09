# Decisions

This document records key technical decisions and the rationale behind them.

## 1. Supabase Transaction Pooler for the Database

**Decision:** Use the Supabase **Transaction Pooler** connection string (port `6543`) instead of the direct database connection (port `5432`).

**Rationale:**

- The direct connection produced `password authentication failed for user "postgres"` errors.
- The Transaction Pooler provides a stable, connection-managed endpoint that works reliably with SQLAlchemy connection pooling.
- It is the recommended connection mode for applications using a connection pool.

**Alternative considered:** Direct port `5432` connection — abandoned due to authentication/connection failures.

## 2. Indian Number-Format Regex for Deal Values

**Decision:** Rewrite the `extract_deal_value` regex to support Indian grouping: `\d{1,2}(?:,\d{2})*,\d{3}`.

**Rationale:**

- The original regex (`\d{1,2},\d{3},\d{3}(?:,\d{3})*`) failed on Indian-format values like `10,00,000` because of greedy-backtracking behavior.
- Indian currency grouping uses the last 3 digits grouped, then groups of 2 (`10,00,000`).
- The new pattern handles both Indian and standard grouping.

**Trade-off:** More complex regex; mitigated with negative lookarounds to avoid matching parts of larger numbers or years.

## 3. SQLAlchemy ORM with `create_all` for schema management

**Decision:** Use SQLAlchemy ORM models and create tables on startup via `Base.metadata.create_all`.

**Rationale:**

- Keeps the schema definition in code and versioned with the repository.
- Avoids a separate migration tool for the initial deployment.
- Suitable for the current single-table schema.

**Trade-off:** No automatic migration history. For future schema changes, a migration tool (e.g., Alembic) should be introduced.

## 4. Environment variables via `.env` (python-dotenv)

**Decision:** Load configuration from a `.env` file using `python-dotenv`, with `.env` excluded from version control and `.env.example` committed as a template.

**Rationale:**

- Keeps secrets (DB credentials, Gemini API key) out of the repository.
- Provides a clear onboarding template via `.env.example`.

## 5. FastAPI + Uvicorn

**Decision:** Build the API with FastAPI and serve it with Uvicorn.

**Rationale:**

- FastAPI provides automatic OpenAPI docs, Pydantic validation, and async support.
- Uvicorn is the standard ASGI server and supports hot reload during development.
