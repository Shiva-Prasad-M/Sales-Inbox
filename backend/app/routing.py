"""
Hybrid routing engine: deterministic business rules first, Gemini as a
semantic enrichment layer with a robust deterministic fallback.

The system must never drop an email solely because Gemini failed.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ASSIGNEES = {
    "u_aarti": "Aarti (Enterprise RFP / PSU / Government)",
    "u_rohit": "Rohit (SMB enquiries / demos)",
    "u_meera": "Meera (Marketing / PR / Events)",
    "u_karan": "Karan (Channel / Alliances)",
    "u_divya": "Divya (Finance / Billing)",
    "u_triage": "Triage (Ambiguous)",
}

CATEGORY_LABELS = {
    "enterprise_rfp": "Enterprise RFP",
    "smb_enquiry": "SMB Enquiry",
    "marketing": "Marketing",
    "alliances": "Alliances",
    "finance": "Finance",
    "triage": "Triage",
}

SKIP_REASONS = [
    "ooo",
    "auto_reply",
    "newsletter",
    "vendor_spam",
    "unsolicited",
]

# Deadlines within 72h -> high priority
DEADLINE_WINDOW_HOURS = 72


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def _norm(text: Optional[str]) -> str:
    return (text or "").lower().strip()


def _strip_quote(email: Dict[str, Any], body: str) -> str:
    """Remove quoted original content from a reply."""
    if not body:
        return ""
    # Common reply markers
    lines = body.splitlines()
    clean: List[str] = []
    for line in lines:
        low = line.lower()
        if re.match(r"^\s*(on .* wrote:|\w+,?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{1,2},?\s*\d{4}.*wrote:)",
                    low):
            break
        if low.startswith(">"):
            break
        clean.append(line)
    return "\n".join(clean).strip()


# ---------------------------------------------------------------------------
# Currency extraction (Indian formats)
# ---------------------------------------------------------------------------
def extract_deal_value(text: str) -> Optional[int]:
    if not text:
        return None
    t = text.lower()

    # Pattern: [₹|rs|inr] [number] (lakh|lakhs|lac|lacs|cr|crore|crores|million|k|thousand)
    pattern = re.compile(
        r"(?:₹|rs\.?|inr|rs)\s*"
        r"([\d,]+\.?\d*)\s*"
        r"(lakh|lakhs|lac|lacs|cr|crore|crores|million|mn|billion|bn|thousand|k)?",
        re.IGNORECASE,
    )

    match = pattern.search(t)
    if not match:
        # e.g. "1.2 cr" without currency symbol
        alt = re.search(r"([\d,]+\.?\d*)\s*(cr|crore|crores|lakh|lakhs|lac)", t)
        if alt:
            match = alt

    if not match:
        # Bare Indian number format e.g. "10,00,000" or "1000000" (implied rupees)
        # Require a non-digit before the number so we don't match a suffix chunk.
        bare = re.search(r"(?<![\d,])(\d{1,2}(?:,\d{2})*,\d{3}|\d{1,2},\d{3}|\d{6,7})(?!\d)", t)
        if bare:
            return int(bare.group(1).replace(",", ""))

    if not match:
        return None

    num_str = match.group(1).replace(",", "")
    try:
        value = float(num_str)
    except ValueError:
        return None

    unit = (match.group(2) or "").lower()
    if unit in ("cr", "crore", "crores"):
        value = int(value * 10_000_000)
    elif unit in ("lakh", "lakhs", "lac", "lacs"):
        value = int(value * 100_000)
    elif unit in ("million", "mn"):
        value = int(value * 1_000_000)
    elif unit in ("billion", "bn"):
        value = int(value * 1_000_000_000)
    elif unit in ("thousand", "k"):
        value = int(value * 1000)
    else:
        value = int(value)

    return value


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(day: int, month: int, year: Optional[int], base: datetime) -> str:
    year = year or base.year
    try:
        d = datetime(year, month, day)
        if d < base - timedelta(days=1):
            d = datetime(year + 1, month, day)
        return d.strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_due_date(text: str, received_at: Optional[datetime] = None) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    base = received_at or datetime.now()

    # Absolute date: 12th August 2026 / 11 August / 03-08-2026 / 03/08/2026
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})\s+(\d{4})", t)
    if m:
        day = int(m.group(1))
        month = _parse_month(m.group(2))
        if month:
            return _parse_date(day, month, int(m.group(3)), base)

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})\b", t)
    if m:
        day = int(m.group(1))
        month = _parse_month(m.group(2))
        if month:
            return _parse_date(day, month, None, base)

    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})", t)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        if year < 100:
            year += 2000
        return _parse_date(day, month, year, base)

    # Relative: tomorrow / within 48 hours / within 72 hours / friday / monday
    m = re.search(r"tomorrow", t)
    if m:
        return (base + timedelta(days=1)).strftime("%Y-%m-%d")

    m = re.search(r"within\s+(\d+)\s*(?:hours|hrs)", t)
    if m:
        hours = int(m.group(1))
        return (base + timedelta(hours=hours)).date().strftime("%Y-%m-%d")

    m = re.search(r"in\s+(\d+)\s*days", t)
    if m:
        return (base + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    for day_name, offset in [("monday", 0), ("tuesday", 1), ("wednesday", 2),
                             ("thursday", 3), ("friday", 4), ("saturday", 5),
                             ("sunday", 6)]:
        if re.search(rf"\b{day_name}\b", t):
            days_ahead = (offset - base.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (base + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return None


def _parse_month(name: str) -> Optional[int]:
    name = name[:3].lower()
    return _MONTHS.get(name)


# ---------------------------------------------------------------------------
# Spam / OOO / newsletter detection
# ---------------------------------------------------------------------------
def _is_ooo(text: str, subject: str) -> bool:
    t = _norm(text) + " " + _norm(subject)
    ooo_markers = [
        "out of office", "on leave", "will be back", "currently out of the office",
        "auto reply", "auto-reply", "automatic reply", "away from", "on vacation",
        "on annual leave", "returning to work",
    ]
    return any(m in t for m in ooo_markers)


def _is_newsletter(text: str, subject: str) -> bool:
    t = _norm(text) + " " + _norm(subject)
    markers = [
        "newsletter", "unsubscribe", "you're receiving this because you subscribed",
        "weekly digest", "monthly digest", "subscribe to our", "view this email in your browser",
        "was sent to you because", "email preferences",
    ]
    return any(m in t for m in markers)


def detect_spam(text: str, subject: str) -> Optional[str]:
    """Return skip_reason if this email should be skipped, else None."""
    if _is_ooo(text, subject):
        return "ooo"
    if _is_newsletter(text, subject):
        return "newsletter"

    t = _norm(text) + " " + _norm(subject)
    vendor_spam = [
        "improve your seo", "boost your rankings", "seo services", "backlinks",
        "increase your web traffic", "digital marketing services", "we can improve",
        "guest post", "link building", "buy followers", "rank your website",
        "content writing services", "ppc services", "cold outreach",
    ]
    if any(m in t for m in vendor_spam):
        return "vendor_spam"

    return None


# ---------------------------------------------------------------------------
# Deterministic routing rules
# ---------------------------------------------------------------------------
def classify_deterministic(text: str, subject: str, thread_has_task: bool = False) -> Dict[str, Any]:
    """Return a routing decision dict (may be a skip). Pure deterministic."""
    t = _norm(text)
    s = _norm(subject)
    combined = t + " " + s

    # ---- Skip cases ----
    skip = detect_spam(text, subject)
    if skip:
        return {"decision": "skip", "skip_reason": skip, "category": None,
                "priority": None, "assignee_id": None, "confidence": 0.99,
                "reason": f"Detected {skip}"}

    # ---- Government / PSU tender ----
    is_gov = any(k in combined for k in [
        "government", "tender", "psu", "public sector", "ministry", "department of",
        "govt", "bharat electronic", "defence", "nucle", "railway", "municipal",
    ])
    if is_gov:
        return {"decision": "task", "category": "enterprise_rfp",
                "assignee_id": "u_aarti", "priority": "high",
                "confidence": 1.0, "reason": "Government/PSU tender -> Aarti"}

    # ---- RFP / RFI / tender ----
    is_rfp = any(k in combined for k in [
        "rfp", "request for proposal", "rfi", "request for information",
        "expression of interest", "eoi", "tender", "proposal", "bid",
    ])

    # ---- Deal value ----
    deal_value = extract_deal_value(combined)

    # ---- Marketing / PR / events ----
    is_marketing = any(k in combined for k in [
        "sponsorship", "webinar", "conference", "event", "content collaboration",
        "pr", "media", "press release", "brand partnership", "co-marketing",
        "podcast", "thought leadership", "exhibit", "booth",
    ])

    # ---- Alliances / channel ----
    is_alliance = any(k in combined for k in [
        "reseller", "channel partner", "technology integration", "integrate your",
        "api integration", "partnership", "alliance", "marketplace", "joint go-to-market",
        "gtm partnership", "co-selling", "system integrator",
    ])

    # ---- Finance ----
    is_finance = any(k in combined for k in [
        "invoice", "po ", "purchase order", "payment reminder", "gst", "vendor billing",
        "payment due", "overdue", "receipt", "billing", "vendor payment", "tax invoice",
    ])

    # ---- Enterprise above threshold ----
    if is_rfp and deal_value and deal_value > 1_000_000:
        return {"decision": "task", "category": "enterprise_rfp",
                "assignee_id": "u_aarti", "priority": "high",
                "confidence": 0.95, "reason": "Enterprise RFP above Rs 10L -> Aarti",
                "deal_value_inr": deal_value}

    # ---- SMB / demo below or at threshold ----
    is_smb = any(k in combined for k in [
        "demo", "product enquiry", "pricing", "trial", "subscription", "sign up",
        "buy", "purchase", "quote", "smb", "small business", "licenses",
    ])
    if is_smb and deal_value and deal_value <= 1_000_000:
        return {"decision": "task", "category": "smb_enquiry",
                "assignee_id": "u_rohit", "priority": "medium",
                "confidence": 0.9, "reason": "SMB demo/enquiry <= Rs 10L -> Rohit",
                "deal_value_inr": deal_value}

    if is_smb:
        return {"decision": "task", "category": "smb_enquiry",
                "assignee_id": "u_rohit", "priority": "medium",
                "confidence": 0.85, "reason": "SMB demo/enquiry -> Rohit",
                "deal_value_inr": deal_value}

    if is_marketing:
        return {"decision": "task", "category": "marketing",
                "assignee_id": "u_meera", "priority": "low",
                "confidence": 0.9, "reason": "Marketing/webinar/PR -> Meera"}

    if is_alliance:
        return {"decision": "task", "category": "alliances",
                "assignee_id": "u_karan", "priority": "medium",
                "confidence": 0.9, "reason": "Channel/alliance -> Karan"}

    if is_finance:
        return {"decision": "task", "category": "finance",
                "assignee_id": "u_divya", "priority": "medium",
                "confidence": 0.9, "reason": "Finance/invoice -> Divya"}

    if is_rfp:
        return {"decision": "task", "category": "enterprise_rfp",
                "assignee_id": "u_aarti", "priority": "medium",
                "confidence": 0.8, "reason": "RFP/tender -> Aarti",
                "deal_value_inr": deal_value}

    # ---- Triage (ambiguous) ----
    return {"decision": "task", "category": "triage",
            "assignee_id": "u_triage", "priority": "medium",
            "confidence": 0.5, "reason": "Ambiguous -> Triage",
            "deal_value_inr": deal_value}


# ---------------------------------------------------------------------------
# Gemini integration (with fallback)
# ---------------------------------------------------------------------------
class GeminiClient:
    """Thin wrapper around Gemini with timeout, retries and safe parsing."""

    def __init__(self):
        self._client = None
        self._key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self._configured = bool(self._key) and self._key != "your_gemini_api_key" and len(self._key) > 20

    @property
    def available(self) -> bool:
        return self._configured

    def _get_client(self):
        if self._client is None and self.available:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._key)
            except Exception:
                self._client = None
        return self._client

    def classify(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        client = self._get_client()
        if client is None:
            return None

        prompt = (
            "You are a sales email router. Classify this email.\n"
            "Return STRICT JSON only with keys: "
            "category(enterprise_rfp|smb_enquiry|marketing|alliances|finance|triage), "
            "assignee_id(u_aarti|u_rohit|u_meera|u_karan|u_divya|u_triage), "
            "priority(high|medium|low), confidence(0-1 float), "
            "deal_value_inr(int|null), due_date(YYYY-MM-DD|null), company_name(string|null), "
            "skip(bool), skip_reason(null|ooo|auto_reply|newsletter|vendor_spam|unsolicited), "
            "reason(string).\n"
            "If it is OOO/auto-reply/newsletter/vendor spam, set skip=true.\n"
            f"Email: {json.dumps(email)}"
        )

        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config={"temperature": 0.0},
                )
                text = resp.text or ""
                text = text.strip().strip("```json").strip("```").strip()
                data = json.loads(text)
                return self._validate(data)
            except Exception:
                delay = 2 ** attempt
                time.sleep(delay)
        return None

    def phrase_answer(self, question: str, data: Dict[str, Any]) -> Optional[str]:
        if not self.available:
            return None
        client = self._get_client()
        if client is None:
            return None
        prompt = (
            "You are an assistant answering from provided structured data. "
            "Do NOT invent numbers. Use ONLY the data. Answer in 1-2 sentences.\n"
            f"Question: {question}\nData: {json.dumps(data, default=str)}"
        )
        try:
            resp = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config={"temperature": 0.0},
            )
            return (resp.text or "").strip()
        except Exception:
            return None

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return None
        cat = data.get("category")
        if cat not in CATEGORY_LABELS:
            return None
        assignee = data.get("assignee_id")
        if assignee not in ASSIGNEES:
            if cat == "enterprise_rfp":
                assignee = "u_aarti"
            elif cat == "smb_enquiry":
                assignee = "u_rohit"
            elif cat == "marketing":
                assignee = "u_meera"
            elif cat == "alliances":
                assignee = "u_karan"
            elif cat == "finance":
                assignee = "u_divya"
            else:
                assignee = "u_triage"
        prio = data.get("priority")
        if prio not in ("high", "medium", "low"):
            prio = "medium"
        try:
            conf = float(data.get("confidence", 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        return {
            "decision": "skip" if data.get("skip") else "task",
            "category": cat,
            "assignee_id": assignee,
            "priority": prio,
            "confidence": min(max(conf, 0), 1),
            "deal_value_inr": data.get("deal_value_inr"),
            "due_date": data.get("due_date"),
            "company_name": data.get("company_name"),
            "skip_reason": data.get("skip_reason"),
            "reason": data.get("reason", "Gemini classification"),
        }


gemini = GeminiClient()


def route_email(email: Dict[str, Any]) -> Dict[str, Any]:
    """Route a single email. Returns a decision dict."""
    body = email.get("body") or ""
    subject = email.get("subject") or ""
    thread_has_task = email.get("_thread_has_task", False)

    # For replies, strip quoted content
    if email.get("is_reply"):
        body = _strip_quote(email, body)

    # Deterministic first (guardrails)
    det = classify_deterministic(body, subject)

    # Gemini enrichment only if deterministic says it's a task (not skip)
    if det["decision"] == "task":
        g = gemini.classify(email)
        if g and g["decision"] == "task":
            # Merge: prefer Gemini category but keep deterministic for
            # government RFP (always Aarti/high) and skip spurious.
            if det.get("category") == "enterprise_rfp" and det.get("assignee_id") == "u_aarti":
                merged = dict(det)
                # keep deterministic government override
                merged["confidence"] = max(det.get("confidence", 0), g.get("confidence", 0))
                merged["reason"] = f"{det.get('reason')} (Gemini: {g.get('reason')})"
                return merged
            return det if g.get("confidence", 0) < det.get("confidence", 0) else g

    return det


def build_task_fields(email: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    """Build fields used to create/update a Task, with extraction."""
    body = email.get("body") or ""
    subject = email.get("subject") or ""
    if email.get("is_reply"):
        body = _strip_quote(email, body)

    combined = body + " " + subject

    due_date = decision.get("due_date")
    if not due_date:
        received_at = None
        if email.get("received_at"):
            try:
                received_at = datetime.fromisoformat(str(email["received_at"]).replace("Z", "+00:00"))
            except ValueError:
                received_at = None
        due_date = extract_due_date(combined, received_at)

    deal_value = decision.get("deal_value_inr")
    if deal_value is None:
        deal_value = extract_deal_value(combined)

    company_name = decision.get("company_name")
    if not company_name:
        # Only extract company when clearly stated (e.g., "on behalf of X" or "from Y")
        m = re.search(r"(?:on behalf of|representing)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\.|,|\n|$)", combined)
        if m:
            company_name = m.group(1).strip()[:200]

    title = subject or "Untitled"
    if not title:
        title = "New enquiry"

    return {
        "title": title,
        "description": body[:5000],
        "assignee_id": decision.get("assignee_id"),
        "category": decision.get("category"),
        "priority": decision.get("priority", "medium"),
        "due_date": due_date,
        "deal_value_inr": deal_value,
        "company_name": company_name,
        "confidence": decision.get("confidence", 0.5),
        "reason": decision.get("reason"),
        "skip_reason": decision.get("skip_reason"),
    }
