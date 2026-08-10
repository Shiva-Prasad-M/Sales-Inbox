from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, String,
                        Text, UniqueConstraint)


class Task(Base):
    """A routed task created from an email."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, nullable=False, index=True)
    candidate_id = Column(String(255), nullable=False, index=True)
    source_email_id = Column(String(100), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    due_date = Column(String(10), nullable=True)
    deal_value_inr = Column(Integer, nullable=True)
    company_name = Column(String(500), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    run_id = Column(String(50), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "source_email_id",
            name="uq_candidate_source_email"
        ),
        UniqueConstraint(
            "candidate_id",
            "thread_id",
            name="uq_candidate_thread"
        ),
    )


class ProcessedEmail(Base):
    """Audit record for every processed email."""

    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(255), nullable=False, index=True)
    email_id = Column(String(100), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    run_id = Column(String(50), nullable=True, index=True)
    decision = Column(String(20), nullable=False)  # created | updated | skipped
    category = Column(String(50), nullable=True)
    assignee_id = Column(String(50), nullable=True)
    priority = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    skip_reason = Column(String(50), nullable=True)
    spurious = Column(Boolean, default=False, nullable=False)
    task_id = Column(String(50), nullable=True, index=True)
    title = Column(String(500), nullable=True)
    deal_value_inr = Column(Integer, nullable=True)
    due_date = Column(String(10), nullable=True)
    company_name = Column(String(500), nullable=True)
    is_reply = Column(Boolean, default=False, nullable=False)
    from_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "email_id",
            "run_id",
            name="uq_processed_email_run"
        ),
    )


class ThreadUpdate(Base):
    """History of thread reconciliations / updates."""

    __tablename__ = "thread_updates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(255), nullable=False, index=True)
    task_id = Column(String(50), nullable=False, index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    email_id = Column(String(100), nullable=False)
    run_id = Column(String(50), nullable=True, index=True)
    fields_changed = Column(String(500), nullable=True)
    new_deal_value_inr = Column(Integer, nullable=True)
    new_due_date = Column(String(10), nullable=True)
    new_priority = Column(String(20), nullable=True)
    create_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "task_id",
            "email_id",
            name="uq_thread_update",
        ),
    )


class Run(Base):
    """Ingest run record."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), unique=True, nullable=False, index=True)
    candidate_id = Column(String(255), nullable=False, index=True)
    emails_received = Column(Integer, default=0, nullable=False)
    tasks_created = Column(Integer, default=0, nullable=False)
    tasks_updated = Column(Integer, default=0, nullable=False)
    skipped = Column(Integer, default=0, nullable=False)
    errors = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
