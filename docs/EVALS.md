# Evaluations

This document records how the core logic of the Alumnx Sales Inbox is evaluated and verified.

## 1. Deal Value Extraction (`extract_deal_value`)

The function is responsible for parsing currency amounts from email text, with special support for **Indian number grouping** (last 3 digits grouped, then groups of 2).

### Test cases

| Input string                 | Expected output | Notes                       |
| ---------------------------- | --------------- | --------------------------- |
| `"deal worth 10,00,000 INR"` | `1000000`       | Indian format (10 lakh)     |
| `"quoted 1,50,000"`          | `150000`        | Indian format (1.5 lakh)    |
| `"budget of 25,000"`         | `25000`         | Standard 3-digit group      |
| `"value 12000"`              | `12000`         | Plain number, no separators |
| `"cost 1,000,000"`           | `1000000`       | Standard grouping           |
| `"no amount mentioned"`      | `None`          | No match                    |
| `"2024 budget"`              | `None`          | Year-like numbers excluded  |

### Acceptance criteria

- [x] `10,00,000` parses to `1000000`.
- [x] Standard formats (`1,000,000`, `25,000`) still parse correctly.
- [x] Plain numbers without separators parse correctly.
- [x] Non-amount values (e.g. years, dates) are excluded.

## 2. Database Connectivity

The application must connect to its PostgreSQL database and report health.

### Acceptance criteria

- [x] `/health/database` returns `{"status": "healthy", "database": "connected"}`.
- [x] Tables are auto-created on startup (`Base.metadata.create_all`).
- [x] Server starts without database connection errors.

## 3. Server Startup

- [x] `uvicorn app.main:app --reload` completes "Application startup complete."
- [x] `/health` returns `{"status": "healthy"}`.
- [x] `/` returns the API root message.

## 4. Routing Classification

Routing is driven by Google Gemini and returns a category, assignee, priority, and confidence. Validation of the full Gemini pipeline is performed manually against sample emails and is not part of the automated test set due to the external API dependency.
