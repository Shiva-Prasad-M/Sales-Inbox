from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ---------- Enum values ----------
ASSIGNEE_IDS = [
    "u_aarti",
    "u_rohit",
    "u_meera",
    "u_karan",
    "u_divya",
    "u_triage",
]

CATEGORIES = [
    "enterprise_rfp",
    "smb_enquiry",
    "marketing",
    "alliances",
    "finance",
    "triage",
]

PRIORITIES = ["high", "medium", "low"]


# ---------- Ingest ----------
class IncomingEmail(BaseModel):
    email_id: str
    thread_id: str
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    received_at: Optional[str] = None
    is_reply: Optional[bool] = False


class IngestRequest(BaseModel):
    candidate_id: str
    emails: List[IncomingEmail] = Field(default_factory=list)


class IngestResponse(BaseModel):
    processed: int
    tasks_created: int
    tasks_updated: int
    skipped: int
    errors: List[str] = Field(default_factory=list)


# ---------- Tasks ----------
class TaskCreate(BaseModel):
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: Optional[str] = None
    assignee_id: str
    category: str
    priority: str
    due_date: Optional[str] = None
    deal_value_inr: Optional[float] = None
    company_name: Optional[str] = None
    confidence: float = 0.0


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    deal_value_inr: Optional[float] = None
    company_name: Optional[str] = None
    confidence: Optional[float] = None


class TaskOut(BaseModel):
    task_id: str
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: Optional[str] = None
    assignee_id: str
    category: str
    priority: str
    due_date: Optional[str] = None
    deal_value_inr: Optional[float] = None
    company_name: Optional[str] = None
    confidence: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------- API tasks ----------
class ApiTaskOut(BaseModel):
    task_id: str
    title: str
    category: str
    assignee_id: str
    priority: str
    confidence: float
    due_date: Optional[str] = None
    deal_value_inr: Optional[float] = None
    company_name: Optional[str] = None
    thread_id: str
    source_email_id: str
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------- API chat ----------
class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    supporting_data: Dict[str, Any] = Field(default_factory=dict)
