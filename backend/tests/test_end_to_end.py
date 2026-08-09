"""
End-to-end test suite for the Alumnx Sales Inbox backend.

Run with the backend running:
    uvicorn app.main:app --port 8000

Then from the backend directory:
    python tests/test_end_to_end.py
"""
import os
import sys
import time
import uuid
from datetime import datetime

import requests

BASE = os.getenv("TEST_BASE", "http://127.0.0.1:8000")
CANDIDATE = "medashivaprasad123@gmail.com"

PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  FAIL  {name}  {extra}")


def uid(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def ingest(emails, candidate=CANDIDATE):
    r = requests.post(f"{BASE}/ingest", json={"candidate_id": candidate, "emails": emails})
    return r.status_code, r.json()


def get_tasks(candidate=CANDIDATE):
    r = requests.get(f"{BASE}/api/tasks", params={"candidate_id": candidate})
    return r.json()


def make_email(subject, body, thread_id=None, email_id=None, is_reply=False, from_name="Test User", from_email="t@t.com"):
    return {
        "email_id": email_id or uid("e"),
        "thread_id": thread_id or uid("th"),
        "from_name": from_name,
        "from_email": from_email,
        "subject": subject,
        "body": body,
        "received_at": datetime.utcnow().isoformat(),
        "is_reply": is_reply,
    }


def main():
    global PASS, FAIL
    print("=" * 60)
    print("Alumnx Sales Inbox - End to End Test Matrix")
    print("=" * 60)

    # ---- Health ----
    print("\n[1] Health checks")
    r = requests.get(f"{BASE}/health")
    check("GET /health -> 200", r.status_code == 200, str(r.status_code))
    r = requests.get(f"{BASE}/health/database")
    check("GET /health/database healthy", r.json().get("status") == "healthy", str(r.json()))

    # ---- 1. Enterprise RFP -> u_aarti ----
    print("\n[2] Enterprise RFP -> u_aarti")
    eid = uid("e")
    em = make_email(
        "Request for Proposal - Enterprise License",
        "We request proposals for a company-wide deployment. Deal value is Rs 2,50,00,000. Deadline within 72 hours.",
        email_id=eid,
    )
    st, resp = ingest([em])
    check("ingest 201/200", st in (200, 201), str(st))
    check("1 task created", resp.get("tasks_created") == 1, str(resp))
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["source_email_id"] == eid), None)
    check("enterprise RFP exists", t is not None)
    if t:
        check("assignee u_aarti", t["assignee_id"] == "u_aarti", t["assignee_id"])
        check("category enterprise_rfp", t["category"] == "enterprise_rfp", t["category"])
        check("priority high (72h)", t["priority"] == "high", t["priority"])
        check("deal value parsed", t["deal_value_inr"] == 25000000, str(t["deal_value_inr"]))

    # ---- 2. SMB demo -> u_rohit ----
    print("\n[3] SMB demo -> u_rohit")
    eid = uid("e")
    em = make_email("Product Demo Request", "We are a small business interested in a demo. Budget around 3,00,000.")
    st, resp = ingest([em])
    check("SMB ingest 200", st in (200, 201))
    check("SMB task created", resp.get("tasks_created") == 1, str(resp))
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["title"] == "Product Demo Request"), None)
    check("SMB assignee u_rohit", t and t["assignee_id"] == "u_rohit", str(t and t["assignee_id"]))
    check("SMB category smb_enquiry", t and t["category"] == "smb_enquiry")

    # ---- 3. PSU/government tender below Rs 10L -> u_aarti ----
    print("\n[4] PSU/government tender below Rs 10L -> u_aarti")
    eid = uid("e")
    em = make_email("Government Tender - EOI", "Expression of interest for a government ministry tender. Estimated value Rs 5,00,000. Please submit bid.")
    st, resp = ingest([em])
    check("gov ingest 200", st in (200, 201))
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["title"] == "Government Tender - EOI"), None)
    check("gov tender -> u_aarti", t and t["assignee_id"] == "u_aarti", str(t and t["assignee_id"]))
    check("gov tender category enterprise_rfp", t and t["category"] == "enterprise_rfp")

    # ---- 4. Marketing sponsorship -> u_meera ----
    print("\n[5] Marketing sponsorship -> u_meera")
    eid = uid("e")
    em = make_email("Sponsorship Opportunity", "We are organizing a tech conference and would like a sponsorship and co-marketing partnership.")
    st, resp = ingest([em])
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["title"] == "Sponsorship Opportunity"), None)
    check("marketing -> u_meera", t and t["assignee_id"] == "u_meera", str(t and t["assignee_id"]))
    check("marketing category", t and t["category"] == "marketing")

    # ---- 5. Invoice/GST/payment -> u_divya ----
    print("\n[6] Invoice/GST -> u_divya")
    eid = uid("e")
    em = make_email("Invoice #1234 - Payment Due", "Please find attached invoice for services. This is a payment reminder. GST details included.")
    st, resp = ingest([em])
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if "Invoice #1234" in x["title"]), None)
    check("finance -> u_divya", t and t["assignee_id"] == "u_divya", str(t and t["assignee_id"]))
    check("finance category", t and t["category"] == "finance")

    # ---- 6. Reseller/channel/integration -> u_karan ----
    print("\n[7] Reseller/channel -> u_karan")
    eid = uid("e")
    em = make_email("Channel Partnership Proposal", "We would like a reseller and channel partnership. We are interested in integrating your API and co-selling.")
    st, resp = ingest([em])
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["title"] == "Channel Partnership Proposal"), None)
    check("alliance -> u_karan", t and t["assignee_id"] == "u_karan", str(t and t["assignee_id"]))

    # ---- 7. OOO -> no task ----
    print("\n[8] OOO -> no task")
    before = len(get_tasks()["tasks"])
    eid = uid("e")
    em = make_email("Out of Office - Auto", "I am out of the office and will be back next Monday. This is an automated reply.")
    st, resp = ingest([em])
    check("OOO skipped", resp.get("skipped") == 1 and resp.get("tasks_created") == 0, str(resp))
    after = len(get_tasks()["tasks"])
    check("OOO no task created", after == before, f"{before}->{after}")

    # ---- 8. Newsletter -> no task ----
    print("\n[9] Newsletter -> no task")
    eid = uid("e")
    em = make_email("Your Weekly Newsletter", "Here is this week's digest. To unsubscribe, click here. You're receiving this because you subscribed.")
    st, resp = ingest([em])
    check("newsletter skipped", resp.get("skipped") == 1 and resp.get("tasks_created") == 0, str(resp))

    # ---- 9. Vendor SEO/marketing spam -> no task ----
    print("\n[10] Vendor SEO spam -> no task")
    eid = uid("e")
    em = make_email("Improve Your SEO Rankings", "We can help improve your website rankings with our SEO and backlink building services. Boost your web traffic.")
    st, resp = ingest([em])
    check("spam skipped", resp.get("skipped") == 1 and resp.get("tasks_created") == 0, str(resp))

    # ---- 10. Ambiguous multi-intent -> u_triage low confidence ----
    print("\n[11] Ambiguous -> u_triage")
    eid = uid("e")
    em = make_email("General Business Inquiry", "Hello, I have a general inquiry about your company and would like to know what you offer.")
    st, resp = ingest([em])
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["title"] == "General Business Inquiry"), None)
    check("triage -> u_triage", t and t["assignee_id"] == "u_triage", str(t and t["assignee_id"]))
    check("triage low confidence", t and t["confidence"] <= 0.6, str(t and t["confidence"]))

    # ---- 11. Hinglish and crore/lakh ----
    print("\n[12] Hinglish & crore/lakh")
    eid = uid("e")
    em = make_email("Product ke baare mein jaankari", "Namaste, hum aapke product mein ruchi rakh rahe hain. Budget around 3 lakh. Demo dein.")
    st, resp = ingest([em])
    check("hinglish ingest 200", st in (200, 201))
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if "Product ke baare" in x["title"]), None)
    check("hinglish deal 3 lakh", t and t["deal_value_inr"] == 300000, str(t and t["deal_value_inr"]))

    # ---- 12. Deadline within 72h -> high priority ----
    print("\n[13] Deadline 72h -> high priority")
    eid = uid("e")
    em = make_email("URGENT - Tender response", "Request for proposal. We need a response within 48 hours. Deal value Rs 1.5 crore.")
    st, resp = ingest([em])
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if "URGENT" in x["title"]), None)
    check("urgent high priority", t and t["priority"] == "high", str(t and t["priority"]))

    # ---- 13. Thread reply -> PATCH existing task, no duplicate ----
    print("\n[14] Thread reply -> PATCH existing task")
    thread = uid("th")
    eid1 = uid("e")
    em1 = make_email("Initial RFP", "We request a proposal for deployment. Value Rs 2 crore.", thread_id=thread)
    st, resp = ingest([em1])
    check("initial create", resp.get("tasks_created") == 1, str(resp))
    tasks = get_tasks()
    t0 = next((x for x in tasks["tasks"] if x["thread_id"] == thread), None)
    check("initial task exists", t0 is not None)
    orig_confidence = t0["confidence"]

    eid2 = uid("e")
    em2 = make_email("Re: Initial RFP", "We confirm the budget has increased to Rs 3 crore. Please proceed. Deadline is Friday.",
                     thread_id=thread, is_reply=True)
    st, resp = ingest([em2])
    check("reply no new task", resp.get("tasks_created") == 0, str(resp))
    check("reply updated", resp.get("tasks_updated") == 1, str(resp))
    tasks = get_tasks()
    t1 = next((x for x in tasks["tasks"] if x["thread_id"] == thread), None)
    check("same task (no duplicate)", t1 and t1["task_id"] == t0["task_id"], f"{t0['task_id']} vs {t1 and t1['task_id']}")
    check("deal value updated", t1 and t1["deal_value_inr"] == 30000000, str(t1 and t1["deal_value_inr"]))

    # ---- 14. Same batch twice -> no increase ----
    print("\n[15] Idempotency - same batch twice")
    batch = [make_email(f"Batch {i}", f"Body {i}") for i in range(5)]
    st1, resp1 = ingest(batch)
    c1 = resp1.get("tasks_created")
    st2, resp2 = ingest(batch)
    c2 = resp2.get("tasks_created")
    check("second ingest creates 0", c2 == 0, f"{c1}->{c2}")

    # ---- 15. Invalid enum -> HTTP 400 exact ----
    print("\n[16] Invalid enum -> HTTP 400")
    r = requests.post(f"{BASE}/tasks", json={
        "candidate_id": CANDIDATE, "source_email_id": uid("e"), "thread_id": uid("th"),
        "title": "x", "assignee_id": "u_bad", "category": "enterprise_rfp",
        "priority": "high", "confidence": 0.9,
    })
    check("invalid enum 400", r.status_code == 400, str(r.status_code))
    body = r.json()
    check("400 has invalid_enum_value", body.get("detail", {}).get("error") == "invalid_enum_value", str(body))

    # ---- 16. Null due_date/deal_value/company_name ----
    print("\n[17] Null fields when not stated")
    eid = uid("e")
    em = make_email("Simple Enquiry", "Hello, we would like general information about your product.")
    st, resp = ingest([em])
    tasks = get_tasks()
    t = next((x for x in tasks["tasks"] if x["title"] == "Simple Enquiry"), None)
    check("null due_date", t and t["due_date"] is None, str(t and t["due_date"]))
    check("null deal_value", (t and t["deal_value_inr"] in (None, 0)), str(t and t["deal_value_inr"]))

    # ---- 17. Chat zero-count -> zero, no hallucination ----
    print("\n[18] Chat zero-count -> zero")
    r = requests.post(f"{BASE}/api/chat", json={"question": "How many emails are in a category with zero emails?"})
    check("chat zero 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("chat has supporting_data", "supporting_data" in body, str(body))
    check("chat zero answer present", bool(body.get("answer")), str(body.get("answer")))

    # ---- 18. Chat out-of-scope -> refuse ----
    print("\n[19] Chat out-of-scope refuses")
    r = requests.post(f"{BASE}/api/chat", json={"question": "Please send an email to aarti"})
    body = r.json()
    check("chat refuses send", "read-only" in body.get("answer", "").lower() or "cannot" in body.get("answer", "").lower(), str(body.get("answer")))

    # ---- 19. Chat from structured DB query ----
    print("\n[20] Chat structured DB query")
    r = requests.post(f"{BASE}/api/chat", json={"question": "How many enterprise RFP emails were processed?"})
    body = r.json()
    check("chat structured has supporting_data", "supporting_data" in body and body.get("supporting_data"), str(body.get("supporting_data")))

    # ---- 20. Browser no API key ----
    print("\n[21] No API key exposed")
    # The backend never returns GEMINI_API_KEY. Verify no route leaks it.
    for path in ["/", "/api/stats", "/api/tasks", "/api/chat"]:
        if path == "/api/chat":
            r = requests.post(f"{BASE}/api/chat", json={"question": "how many tasks"})
        else:
            r = requests.get(f"{BASE}{path}")
        check(f"no key in {path}", "GEMINI_API_KEY" not in r.text and "AIza" not in r.text, "")

    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("FAILURES:")
        for f in FAILURES:
            print("  - " + f)
        sys.exit(1)
    print("ALL TESTS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
