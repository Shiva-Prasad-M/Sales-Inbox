# Sales Inbox

A small full-stack sales inbox that helps organize incoming emails into tasks and route them to the right person.

Instead of someone manually going through every email and deciding what needs to happen, the application handles the classification and keeps the important information in one place.

## Live Demo

**Frontend:**
https://alumnx-sales-inbox.vercel.app/

**Backend API:**
https://sales-inbox-ueax.onrender.com

**GitHub:**
https://github.com/Shiva-Prasad-M/Sales-Inbox

## What it does

The basic idea is simple:

**Incoming email → classify it → create/organize a task → assign it → show it in the inbox**

The frontend provides the interface for viewing and working with the tasks, while the FastAPI backend handles the application logic and database communication.

The project also supports Gemini-based classification when a valid Gemini API key is available. If Gemini isn't available, the application has a deterministic rule-based fallback so that email processing doesn't simply stop.

## Tech Stack

### Frontend

* React
* Vite
* JavaScript
* CSS

### Backend

* Python
* FastAPI
* SQLAlchemy
* Uvicorn

### Database

* PostgreSQL
* Supabase

### AI

* Google Gemini API
* Rule-based fallback classification

### Deployment

* Vercel — frontend
* Render — backend
* Supabase — PostgreSQL database

## Project Structure

```text
Sales-Inbox/
├── frontend/          # React + Vite application
├── backend/           # FastAPI application
│   ├── app/
│   ├── tests/
│   └── requirements.txt
└── README.md
```

## How the application works

1. The frontend sends requests to the FastAPI backend.
2. The backend processes the request and communicates with PostgreSQL.
3. Email information can be classified and converted into tasks.
4. Tasks are assigned to the appropriate person.
5. The frontend retrieves the data through the API and displays it in the inbox.

The frontend and backend are deployed separately:

```text
                    ┌─────────────────────┐
                    │      Vercel         │
                    │   React + Vite UI   │
                    └──────────┬──────────┘
                               │
                               │ API requests
                               ▼
                    ┌─────────────────────┐
                    │       Render        │
                    │   FastAPI Backend   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Supabase       │
                    │  PostgreSQL Database│
                    └─────────────────────┘
```

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs locally through Vite.

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend requires environment variables for the database and optional Gemini integration.

## Environment Variables

### Backend

```env
DATABASE_URL=your_database_url
GEMINI_API_KEY=your_gemini_api_key
CANDIDATE_ID=your_candidate_id
FRONTEND_URL=http://localhost:5173
```

### Frontend

```env
VITE_API_URL=http://127.0.0.1:8000
```

For production, `VITE_API_URL` should point to the deployed Render backend.

**Secrets and `.env` files should never be committed to GitHub.**

## API Health Checks

The backend exposes health endpoints that were used during deployment verification:

```text
GET /
GET /health
GET /health/database
GET /api/tasks
GET /api/stats
```

The production backend was verified to:

* Start successfully with Uvicorn
* Connect to the PostgreSQL database
* Return healthy status
* Return tasks successfully
* Return statistics successfully

## Testing

The project was tested from the backend through the frontend rather than only checking whether individual files compile.

The final smoke test verified:

* Backend startup
* Database connectivity
* API endpoints
* Frontend startup
* Frontend rendering
* Frontend → backend communication
* Task loading
* Production Vite build
* No `localhost` or `127.0.0.1` references in the production bundle

## A Problem I Had to Fix

One of the more interesting issues was with the `/api/tasks` endpoint.

The endpoint was making repeated database queries while processing tasks. This created an **N+1 query problem**, which could make the endpoint slow or even appear to hang when working with the database.

I changed it so the required processed-email information is fetched in a bulk query instead of querying the database separately for every task.

I also added an index to `ProcessedEmail.task_id` to make those lookups more efficient.

After the change, `/api/tasks` returned successfully during the backend smoke test.

## AI Fallback

Gemini isn't required for the basic application to remain functional.

When `GEMINI_API_KEY` isn't available, the routing system can fall back to deterministic rule-based classification.

That was intentional because an email shouldn't disappear just because an external AI service is unavailable.

## Deployment

The application is deployed as two services:

**Frontend — Vercel**

https://alumnx-sales-inbox.vercel.app/

**Backend — Render**

https://sales-inbox-ueax.onrender.com

**Database — Supabase**

PostgreSQL database used by the backend.

## What I Learned

The biggest lesson from this project wasn't just building the UI.

It was getting all the pieces to work together reliably.

A project can work perfectly on localhost and still fail after deployment because of things like:

* Incorrect environment variables
* CORS configuration
* Hardcoded localhost URLs
* Database connection problems
* Different cloud ports
* Frontend production builds
* API performance problems

Making the application work across the frontend, backend, database, and deployment environment was the most challenging part of the project.

## Links

* **Live Application:** https://alumnx-sales-inbox.vercel.app/
* **Backend API:** https://sales-inbox-ueax.onrender.com
* **GitHub Repository:** https://github.com/Shiva-Prasad-M/Sales-Inbox

---

Built as a full-stack project to explore email routing, task management, API development, database integration, and production deployment.
