# ALUMNX Sales Inbox — Implementation Checklist

## Phase 1 — Backend hardening

- [ ] Update Gemini model to current version (gemini-2.0-flash)
- [ ] Add `/tasks` optional filters (thread_id, source_email_id, assignee_id)
- [ ] Harden chat for all 10 required query types
- [ ] Improve deadline/INR parsing edge cases
- [ ] Add processing-history detail endpoint for chat
- [ ] Validate deal_value vs invoice distinction

## Phase 2 — Sample data generator

- [ ] Build 250-email generator covering all routing paths

## Phase 3 — Frontend (React + Vite)

- [ ] Scaffold Vite React app
- [ ] JSON input + validation
- [ ] Raw email table
- [ ] 250-email generator integration
- [ ] Ingest + results
- [ ] Chat panel
- [ ] Live backend integration, no hardcoded data

## Phase 4 — Automated tests (pytest)

- [ ] Task API tests
- [ ] Routing tests
- [ ] Ingest tests
- [ ] Chat tests

## Phase 5 — Docs & verification

- [ ] README.md (candidate_id, URLs, setup)
- [ ] EVALS.md (50+ hand-labelled, failure cases)
- [ ] DECISIONS.md (5+ tradeoffs)
- [ ] .gitignore add \*.log
- [ ] Run full test suite
- [ ] End-to-end verification against running backend + frontend
- [ ] Security audit
