import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import models
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routing import (ASSIGNEES, CATEGORY_LABELS, build_task_fields,
                         route_email)
from app.schemas import (ASSIGNEE_IDS, CATEGORIES, PRIORITIES, ApiTaskOut,
                         ChatRequest, ChatResponse, IngestRequest,
                         IngestResponse, TaskCreate, TaskOut, TaskUpdate)
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text
from sqlalchemy.orm import Session

app = FastAPI(
    title="Alumnx Sales Inbox",
    description="AI-powered sales inbox routing system",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        # Do not crash if DB is temporarily down
        print(f"[startup] DB tables not ensured: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize_candidate(candidate_id: str) -> str:
    return (candidate_id or "").strip().lower()


def _gen_task_id() -> str:
    return f"T-{uuid.uuid4().hex[:8].upper()}"


def _make_run_id() -> str:
    return f"RUN-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:4].upper()}"


# ---------------------------------------------------------------------------
# Root / health
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Alumnx Sales Inbox API is running", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as error:
        return {"status": "unhealthy", "database": "disconnected", "error": str(error)}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@app.get("/users")
def get_users():
    users = []
    for uid, label in ASSIGNEES.items():
        users.append({"user_id": uid, "name": label.split(" (")[0], "label": label})
    return {"users": users}


# ---------------------------------------------------------------------------
# Tasks CRUD
# ---------------------------------------------------------------------------
def _validate_task_fields(assignee_id: Optional[str], category: Optional[str],
                          priority: Optional[str], db: Session, field_errors: Dict):
    if assignee_id is not None and assignee_id not in ASSIGNEE_IDS:
        field_errors["assignee_id"] = assignee_id
    if category is not None and category not in CATEGORIES:
        field_errors["category"] = category
    if priority is not None and priority not in PRIORITIES:
        field_errors["priority"] = priority


@app.post("/tasks")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    candidate_id = _normalize_candidate(payload.candidate_id)

    # Validate enums -> HTTP 400 with specific structure
    err = {}
    if payload.assignee_id not in ASSIGNEE_IDS:
        err["field"] = "assignee_id"; err["received"] = payload.assignee_id; err["allowed"] = ASSIGNEE_IDS
    elif payload.category not in CATEGORIES:
        err["field"] = "category"; err["received"] = payload.category; err["allowed"] = CATEGORIES
    elif payload.priority not in PRIORITIES:
        err["field"] = "priority"; err["received"] = payload.priority; err["allowed"] = PRIORITIES

    if err:
        raise HTTPException(status_code=400, detail={
            "error": "invalid_enum_value",
            "field": err["field"],
            "received": err["received"],
            "allowed": err["allowed"],
        })

    # Idempotency: same candidate + source_email_id
    existing = db.query(models.Task).filter(
        models.Task.candidate_id == candidate_id,
        models.Task.source_email_id == payload.source_email_id,
    ).first()
    if existing:
        return _task_out(existing)

    task = models.Task(
        task_id=_gen_task_id(),
        candidate_id=candidate_id,
        source_email_id=payload.source_email_id,
        thread_id=payload.thread_id,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        category=payload.category,
        priority=payload.priority,
        due_date=payload.due_date,
        deal_value_inr=payload.deal_value_inr,
        company_name=payload.company_name,
        confidence=payload.confidence,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_out(task)


@app.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return _task_out(task)


@app.get("/tasks")
def list_tasks(candidate_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Task)
    if candidate_id:
        q = q.filter(models.Task.candidate_id == _normalize_candidate(candidate_id))
    tasks = q.order_by(models.Task.created_at.desc()).all()
    return [_task_out(t) for t in tasks]


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"status": "deleted", "task_id": task_id}


def _task_out(task: models.Task) -> Dict[str, Any]:
    return {
        "task_id": task.task_id,
        "candidate_id": task.candidate_id,
        "source_email_id": task.source_email_id,
        "thread_id": task.thread_id,
        "title": task.title,
        "description": task.description,
        "assignee_id": task.assignee_id,
        "category": task.category,
        "priority": task.priority,
        "due_date": task.due_date,
        "deal_value_inr": task.deal_value_inr,
        "company_name": task.company_name,
        "confidence": task.confidence,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------
@app.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest, db: Session = Depends(get_db)):
    candidate_id = _normalize_candidate(payload.candidate_id)
    emails = payload.emails
    if not emails:
        raise HTTPException(status_code=422, detail="No emails provided")

    run_id = _make_run_id()
    run = models.Run(run_id=run_id, candidate_id=candidate_id, emails_received=len(emails))
    db.add(run)
    db.add(models.ProcessedEmail(
        candidate_id=candidate_id, email_id="__run_marker__", thread_id="__run_marker__",
        run_id=run_id, decision="created", confidence=0, reason="run marker",
    ))
    db.commit()

    created = 0
    updated = 0
    skipped = 0
    errors: List[str] = []

    for email in emails:
        try:
            # Pre-check idempotency by source_email_id
            existing_by_email = db.query(models.Task).filter(
                models.Task.candidate_id == candidate_id,
                models.Task.source_email_id == email.email_id,
            ).first()

            # Thread reconciliation
            thread_has_task = False
            existing_thread_task = None
            if email.thread_id:
                existing_thread_task = db.query(models.Task).filter(
                    models.Task.candidate_id == candidate_id,
                    models.Task.thread_id == email.thread_id,
                ).first()
                thread_has_task = existing_thread_task is not None

            email_dict = {
                "email_id": email.email_id,
                "thread_id": email.thread_id,
                "from_name": email.from_name,
                "from_email": email.from_email,
                "subject": email.subject,
                "body": email.body,
                "received_at": email.received_at,
                "is_reply": email.is_reply,
                "_thread_has_task": thread_has_task,
            }

            decision = route_email(email_dict)
            fields = build_task_fields(email_dict, decision) if decision["decision"] == "task" else None

            # ---- Skip ----
            if decision["decision"] == "skip":
                db.add(models.ProcessedEmail(
                    candidate_id=candidate_id, email_id=email.email_id, thread_id=email.thread_id,
                    run_id=run_id, decision="skipped",
                    skip_reason=decision.get("skip_reason"),
                    confidence=decision.get("confidence"),
                    reason=decision.get("reason"),
                    spurious=True,
                    from_name=email.from_name, from_email=email.from_email,
                    subject=email.subject, received_at=_parse_dt(email.received_at),
                ))
                skipped += 1
                continue

            # ---- Reply on existing thread -> PATCH ----
            if email.is_reply and existing_thread_task:
                before = _task_out(existing_thread_task)
                changed = []
                for field in ["title", "description", "assignee_id", "category", "priority",
                              "due_date", "deal_value_inr", "company_name", "confidence"]:
                    new_val = fields.get(field) if field != "confidence" else fields.get("confidence")
                    old_val = before.get(field)
                    if new_val is not None and new_val != old_val:
                        setattr(existing_thread_task, field, new_val)
                        changed.append(field)
                if changed:
                    existing_thread_task.updated_at = datetime.now(timezone.utc)
                    db.add(models.ThreadUpdate(
                        candidate_id=candidate_id, task_id=existing_thread_task.task_id,
                        thread_id=email.thread_id, email_id=email.email_id, run_id=run_id,
                        fields_changed=",".join(changed),
                        new_deal_value_inr=existing_thread_task.deal_value_inr,
                        new_due_date=existing_thread_task.due_date,
                        new_priority=existing_thread_task.priority,
                    ))
                    updated += 1
                db.add(models.ProcessedEmail(
                    candidate_id=candidate_id, email_id=email.email_id, thread_id=email.thread_id,
                    run_id=run_id, decision="updated", category=existing_thread_task.category,
                    assignee_id=existing_thread_task.assignee_id, priority=existing_thread_task.priority,
                    confidence=existing_thread_task.confidence, reason="Thread reply -> PATCH",
                    task_id=existing_thread_task.task_id, is_reply=True,
                    from_name=email.from_name, from_email=email.from_email,
                    subject=email.subject, received_at=_parse_dt(email.received_at),
                ))
                db.commit()
                continue

            # ---- Duplicate by email_id ----
            if existing_by_email:
                db.add(models.ProcessedEmail(
                    candidate_id=candidate_id, email_id=email.email_id, thread_id=email.thread_id,
                    run_id=run_id, decision="skipped",
                    skip_reason="duplicate", confidence=1.0,
                    reason="Idempotency: already processed",
                    spurious=False,
                    from_name=email.from_name, from_email=email.from_email,
                    subject=email.subject, received_at=_parse_dt(email.received_at),
                ))
                skipped += 1
                continue

            # ---- Create new task ----
            task = models.Task(
                task_id=_gen_task_id(),
                candidate_id=candidate_id,
                source_email_id=email.email_id,
                thread_id=email.thread_id,
                title=fields["title"],
                description=fields["description"],
                assignee_id=fields["assignee_id"],
                category=fields["category"],
                priority=fields["priority"],
                due_date=fields["due_date"],
                deal_value_inr=fields["deal_value_inr"],
                company_name=fields["company_name"],
                confidence=fields["confidence"],
                run_id=run_id,
            )
            db.add(task)
            db.flush()
            db.add(models.ProcessedEmail(
                candidate_id=candidate_id, email_id=email.email_id, thread_id=email.thread_id,
                run_id=run_id, decision="created", category=task.category,
                assignee_id=task.assignee_id, priority=task.priority,
                confidence=task.confidence, reason=fields.get("reason"),
                task_id=task.task_id, title=task.title,
                deal_value_inr=task.deal_value_inr, due_date=task.due_date,
                company_name=task.company_name, is_reply=bool(email.is_reply),
                from_name=email.from_name, from_email=email.from_email,
                subject=email.subject, received_at=_parse_dt(email.received_at),
            ))
            created += 1
        except Exception as exc:
            errors.append(f"{email.email_id}: {exc}")

    db.commit()

    run.tasks_created = created
    run.tasks_updated = updated
    run.skipped = skipped
    run.errors = len(errors)
    db.commit()

    return IngestResponse(
        processed=len(emails),
        tasks_created=created,
        tasks_updated=updated,
        skipped=skipped,
        errors=errors,
    )


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# API tasks (read-only for frontend)
# ---------------------------------------------------------------------------
@app.get("/api/tasks")
def api_tasks(candidate_id: Optional[str] = Query(None),
              category: Optional[str] = Query(None),
              assignee_id: Optional[str] = Query(None),
              priority: Optional[str] = Query(None),
              thread_id: Optional[str] = Query(None),
              confidence: Optional[float] = Query(None),
              db: Session = Depends(get_db)):
    q = db.query(models.Task)
    if candidate_id:
        q = q.filter(models.Task.candidate_id == _normalize_candidate(candidate_id))
    if category:
        q = q.filter(models.Task.category == category)
    if assignee_id:
        q = q.filter(models.Task.assignee_id == assignee_id)
    if priority:
        q = q.filter(models.Task.priority == priority)
    if thread_id:
        q = q.filter(models.Task.thread_id == thread_id)
    if confidence is not None:
        q = q.filter(models.Task.confidence <= confidence)

    tasks = q.order_by(models.Task.created_at.desc()).all()

    # Attach reason from processed email if available
    results = []
    for t in tasks:
        item = _task_out(t)
        pe = db.query(models.ProcessedEmail).filter(
            models.ProcessedEmail.task_id == t.task_id
        ).order_by(models.ProcessedEmail.id.desc()).first()
        if pe:
            item["reason"] = pe.reason
        results.append(item)
    return {"tasks": results, "count": len(results)}


# ---------------------------------------------------------------------------
# API stats
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def api_stats(candidate_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    cand = _normalize_candidate(candidate_id) if candidate_id else None

    def q(model):
        qq = db.query(model)
        if cand:
            qq = qq.filter(model.candidate_id == cand)
        return qq

    # Processed emails aggregate
    processed_total = q(models.ProcessedEmail).filter(
        models.ProcessedEmail.email_id != "__run_marker__"
    ).count()

    created = q(models.ProcessedEmail).filter(
        models.ProcessedEmail.decision == "created"
    ).filter(models.ProcessedEmail.email_id != "__run_marker__").count()

    updated = q(models.ProcessedEmail).filter(
        models.ProcessedEmail.decision == "updated"
    ).filter(models.ProcessedEmail.email_id != "__run_marker__").count()

    skipped = q(models.ProcessedEmail).filter(
        models.ProcessedEmail.decision == "skipped"
    ).filter(models.ProcessedEmail.email_id != "__run_marker__").count()

    spurious = q(models.ProcessedEmail).filter(
        models.ProcessedEmail.spurious == True  # noqa: E712
    ).filter(models.ProcessedEmail.email_id != "__run_marker__").count()

    # Counts by category (from tasks)
    cat_rows = q(models.Task).with_entities(models.Task.category, func.count(models.Task.id)) \
        .group_by(models.Task.category).all()
    by_category = {c: n for c, n in cat_rows}
    for c in CATEGORIES:
        by_category.setdefault(c, 0)

    # Counts by assignee
    assign_rows = q(models.Task).with_entities(models.Task.assignee_id, func.count(models.Task.id)) \
        .group_by(models.Task.assignee_id).all()
    by_assignee = {a: n for a, n in assign_rows}
    for a in ASSIGNEE_IDS:
        by_assignee.setdefault(a, 0)

    # Counts by priority
    prio_rows = q(models.Task).with_entities(models.Task.priority, func.count(models.Task.id)) \
        .group_by(models.Task.priority).all()
    by_priority = {p: n for p, n in prio_rows}
    for p in PRIORITIES:
        by_priority.setdefault(p, 0)

    # Counts by run
    run_rows = q(models.ProcessedEmail).with_entities(
        models.ProcessedEmail.run_id, func.count(models.ProcessedEmail.id)
    ).filter(models.ProcessedEmail.email_id != "__run_marker__") \
        .group_by(models.ProcessedEmail.run_id).all()
    by_run = {r or "unknown": n for r, n in run_rows}

    # Confidence stats
    conf_rows = q(models.Task).with_entities(func.min(models.Task.confidence),
                                             func.max(models.Task.confidence),
                                             func.avg(models.Task.confidence),
                                             func.count(models.Task.id)).one()
    confidence_stats = {
        "min": round(conf_rows[0], 2) if conf_rows[0] is not None else None,
        "max": round(conf_rows[1], 2) if conf_rows[1] is not None else None,
        "avg": round(conf_rows[2], 2) if conf_rows[2] is not None else None,
        "count": conf_rows[3] or 0,
    }

    # Skipped categories/reasons
    skip_reason_rows = q(models.ProcessedEmail).with_entities(
        models.ProcessedEmail.skip_reason, func.count(models.ProcessedEmail.id)
    ).filter(models.ProcessedEmail.decision == "skipped") \
        .filter(models.ProcessedEmail.email_id != "__run_marker__") \
        .group_by(models.ProcessedEmail.skip_reason).all()
    by_skip_reason = {r[0] or "unknown": r[1] for r in skip_reason_rows}

    # Thread update statistics
    update_rows = q(models.ProcessedEmail).with_entities(
        models.ProcessedEmail.thread_id, func.count(models.ProcessedEmail.id)
    ).filter(models.ProcessedEmail.decision == "updated") \
        .filter(models.ProcessedEmail.email_id != "__run_marker__") \
        .group_by(models.ProcessedEmail.thread_id).all()
    threads_updated_more_than_once = sum(1 for t, n in update_rows if n > 1)

    # Total deal value of open (non-finished) RFPs
    total_open_rfp_value = q(models.Task).filter(
        models.Task.category == "enterprise_rfp",
        models.Task.deal_value_inr.isnot(None),
    ).with_entities(func.sum(models.Task.deal_value_inr)).scalar() or 0

    return {
        "processed": processed_total,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "spurious": spurious,
        "by_category": by_category,
        "by_assignee": by_assignee,
        "by_priority": by_priority,
        "by_run": by_run,
        "confidence": confidence_stats,
        "by_skip_reason": by_skip_reason,
        "threads_updated_more_than_once": threads_updated_more_than_once,
        "total_open_rfp_value": total_open_rfp_value,
    }


# ---------------------------------------------------------------------------
# API chat (grounded)
# ---------------------------------------------------------------------------
def _query_for_question(question: str, db: Session, cand: Optional[str]):
    """Parse a question into a structured DB query. Returns (summary, data)."""
    q_text = question.lower()

    def q(model):
        qq = db.query(model)
        if cand:
            qq = qq.filter(model.candidate_id == cand)
        return qq

    # --- Category counts ---
    cat_match = None
    for key, label in list(CATEGORY_LABELS.items()):
        if key in q_text or label.lower() in q_text:
            cat_match = key

    # --- Assignee counts ---
    assignee_map = {
        "aarti": "u_aarti", "rohit": "u_rohit", "meera": "u_meera",
        "karan": "u_karan", "divya": "u_divya", "triage": "u_triage",
    }
    assignee_match = None
    for name, uid in assignee_map.items():
        if name in q_text:
            assignee_match = uid

    # --- Priority ---
    priority_match = None
    for p in PRIORITIES:
        if p in q_text:
            priority_match = p

    # --- Number of emails / count ----
    if "how many" in q_text or "count" in q_text or "total" in q_text:
        if cat_match:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == cat_match,
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} email(s) were categorized as {CATEGORY_LABELS[cat_match]}.", {"category": cat_match, "count": n}
        if assignee_match:
            n = q(models.Task).filter(models.Task.assignee_id == assignee_match).count()
            return f"{n} task(s) are assigned to {assignee_match}.", {"assignee": assignee_match, "count": n}
        if "triage" in q_text:
            n = q(models.Task).filter(models.Task.assignee_id == "u_triage").count()
            return f"{n} item(s) are in triage.", {"assignee": "u_triage", "count": n}
        if "spurious" in q_text or "spam" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.decision == "skipped",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            total = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.email_id != "__run_marker__"
            ).count()
            rate = round(n / total * 100, 1) if total else 0
            return f"{n} email(s) were skipped (spurious rate {rate}%).", {"skipped": n, "total": total, "rate": rate}
        if "marketing" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == "marketing",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} marketing email(s) were processed.", {"category": "marketing", "count": n}
        if "alliances" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == "alliances",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} alliances email(s) were processed.", {"category": "alliances", "count": n}
        if "finance" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == "finance",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} finance email(s) were processed.", {"category": "finance", "count": n}
        if "enterprise" in q_text or "rfp" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == "enterprise_rfp",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} enterprise RFP email(s) were processed.", {"category": "enterprise_rfp", "count": n}
        if "smb" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == "smb_enquiry",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} SMB enquiry email(s) were processed.", {"category": "smb_enquiry", "count": n}
        if "webinar" in q_text:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == "marketing",
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            return f"{n} marketing/webinar email(s) were processed.", {"category": "marketing", "count": n}

    # --- Show everything in triage and why ---
    if "show everything in triage" in q_text or ("triage" in q_text and "why" in q_text):
        rows = q(models.Task).filter(models.Task.assignee_id == "u_triage").all()
        items = [{"task_id": t.task_id, "title": t.title, "category": t.category,
                  "confidence": t.confidence} for t in rows]
        return f"{len(items)} item(s) are in triage.", {"triage_items": items}

    # --- High priority + low confidence ---
    if "high priority" in q_text and "low confidence" in q_text:
        rows = q(models.Task).filter(
            models.Task.priority == "high", models.Task.confidence < 0.6
        ).all()
        items = [{"task_id": t.task_id, "title": t.title, "confidence": t.confidence} for t in rows]
        return f"{len(items)} task(s) are high priority with low confidence.", {"high_priority_low_confidence": items}

    if "high priority" in q_text:
        n = q(models.Task).filter(models.Task.priority == "high").count()
        return f"{n} task(s) have high priority.", {"priority": "high", "count": n}

    # --- Total deal value of open RFPs ---
    if "total deal value" in q_text and "rfp" in q_text:
        total = q(models.Task).filter(
            models.Task.category == "enterprise_rfp",
            models.Task.deal_value_inr.isnot(None),
        ).with_entities(func.sum(models.Task.deal_value_inr)).scalar() or 0
        n = q(models.Task).filter(models.Task.category == "enterprise_rfp").count()
        return f"Total deal value of open RFPs is Rs {total:,} across {n} RFP task(s).", {"total_rfp_value": total, "rfp_count": n}

    # --- Threads updated more than once ---
    if "thread" in q_text and "updated more than once" in q_text:
        n = q(models.ThreadUpdate).group_by(models.ThreadUpdate.thread_id) \
            .having(func.count(models.ThreadUpdate.id) > 1).count()
        return f"{n} thread(s) were updated more than once.", {"threads_updated_more_than_once": n}

    # --- Outlook / actionable -------------------------------------------------
    if "send " in q_text and ("email" in q_text):
        return ("This interface is read-only and cannot send emails. "
                "Please use your email client to send it manually.", {"action": "unsupported"})

    # --- Zero-count categories ---
    if "zero" in q_text or "no emails" in q_text or "no tasks" in q_text:
        zero_cats = []
        for c in CATEGORIES:
            n = q(models.ProcessedEmail).filter(
                models.ProcessedEmail.category == c,
                models.ProcessedEmail.email_id != "__run_marker__",
            ).count()
            if n == 0:
                zero_cats.append(CATEGORY_LABELS[c])
        if zero_cats:
            return f"These categories had zero emails: {', '.join(zero_cats)}.", {"zero_categories": zero_cats}
        return "No categories had zero emails.", {"zero_categories": []}

    # --- Unsupported subcategory ---
    return None, {}


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is required")

    cand = settings.CANDIDATE_ID or None

    summary, data = _query_for_question(question, db, cand)

    if summary is None:
        # Unsupported / out of scope
        return ChatResponse(
            answer="I can't help with that. The stored data does not contain that breakdown, "
                    "and this interface is read-only.",
            supporting_data={"matched": False},
        )

    # Try Gemini phrasing (never invents numbers - only rephrases)
    phrased = None
    try:
        from app.routing import gemini
        phrased = gemini.phrase_answer(question, {"summary": summary, **data})
    except Exception:
        phrased = None

    final_answer = phrased if phrased else summary

    return ChatResponse(answer=final_answer, supporting_data=data)


# ---------------------------------------------------------------------------
# Root count of users convenience
# ---------------------------------------------------------------------------
@app.get("/api/users")
def api_users(db: Session = Depends(get_db)):
    return get_users()
