"""Self-contained verification runner: starts server, runs E2E matrix, reports."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid as _uuid

BASE = "http://127.0.0.1:8011"
CANDIDATE = "medashivaprasad123@gmail.com"
RUN_SUFFIX = _uuid.uuid4().hex[:6]
LOG = []


def u(prefix):
    """Unique id per run so idempotency tests don't collide with prior runs."""
    return f"{prefix}_{RUN_SUFFIX}"


def log(msg):
    LOG.append(msg)
    print(msg, flush=True)


def req(method, path, data=None, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method)
    if body:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"raw": str(e)}
    except Exception as e:
        return 0, {"call_error": str(e)}


def start_server():
    env = dict(os.environ)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8011"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log("Waiting for server...")
    for _ in range(30):
        time.sleep(1)
        try:
            s, _ = req("GET", "/health")
            if s == 200:
                log("Server up.")
                return proc
        except Exception:
            pass
    log("SERVER FAILED TO START")
    proc.terminate()
    sys.exit(1)


AGENTS = {
    "u_aarti": "Aarti", "u_rohit": "Rohit", "u_meera": "Meera",
    "u_karan": "Karan", "u_divya": "Divya", "u_triage": "Triage",
}


def make_email(prefix, subject, body, thread=None, is_reply=False):
    eid = u(prefix)
    tid = u(thread or prefix + "_th")
    return {
        "email_id": eid, "thread_id": tid, "from_name": "X",
        "from_email": "x@y.com", "subject": subject, "body": body,
        "received_at": "2024-01-01T00:00:00Z", "is_reply": is_reply,
    }


def main():
    proc = start_server()
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        log(("  PASS  " if cond else "  FAIL  ") + name + ("  " + str(extra) if extra else ""))

    # Health
    s, h = req("GET", "/health")
    check("GET /health 200", s == 200)
    s, hd = req("GET", "/health/database")
    check("DB healthy", hd.get("status") == "healthy", hd)

    def ingest(emails):
        s, r = req("POST", "/ingest", {"candidate_id": CANDIDATE, "emails": emails})
        return s, r

    def find_task(eid):
        _, tasks = req("GET", "/api/tasks", params={"candidate_id": CANDIDATE})
        return next((x for x in tasks["tasks"] if x["source_email_id"] == eid), None)

    # 1. Enterprise RFP -> u_aarti
    e = make_email("eefp1", "Request for Proposal - Enterprise License",
                   "We request proposals for company-wide deployment. Deal value Rs 2,50,00,000. Deadline within 72 hours.")
    s, r = ingest([e])
    check("RFP ingest 200", s in (200, 201), s)
    check("RFP created", r.get("tasks_created") == 1, r)
    t = find_task(e["email_id"])
    check("RFP -> u_aarti", t and t["assignee_id"] == "u_aarti", t and t["assignee_id"])
    check("RFP category", t and t["category"] == "enterprise_rfp")
    check("RFP priority high", t and t["priority"] == "high")
    check("RFP deal 25000000", t and t["deal_value_inr"] == 25000000, t and t["deal_value_inr"])

    # 2. SMB -> u_rohit
    e = make_email("esmb1", "Product Demo Request",
                   "We are a small business interested in a demo. Budget around 3,00,000.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("SMB -> u_rohit", t and t["assignee_id"] == "u_rohit", t and t["assignee_id"])
    check("SMB category smb_enquiry", t and t["category"] == "smb_enquiry")

    # 3. Gov tender below 10L -> u_aarti
    e = make_email("egov1", "Government Tender - EOI",
                   "Expression of interest for a government ministry tender. Estimated value Rs 5,00,000.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Gov tender -> u_aarti", t and t["assignee_id"] == "u_aarti", t and t["assignee_id"])
    check("Gov tender category enterprise_rfp", t and t["category"] == "enterprise_rfp")

    # 4. Marketing -> u_meera
    e = make_email("emark1", "Sponsorship Opportunity",
                   "We are organizing a tech conference and would like a sponsorship and co-marketing partnership.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Marketing -> u_meera", t and t["assignee_id"] == "u_meera", t and t["assignee_id"])
    check("Marketing category", t and t["category"] == "marketing")

    # 5. Invoice -> u_divya
    e = make_email("efin1", "Invoice #1234 - Payment Due",
                   "Please find attached invoice for services. This is a payment reminder. GST details included.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Invoice -> u_divya", t and t["assignee_id"] == "u_divya", t and t["assignee_id"])
    check("Invoice category finance", t and t["category"] == "finance")

    # 6. Reseller/channel -> u_karan
    e = make_email("eall1", "Channel Partnership Proposal",
                   "We would like a reseller and channel partnership. We are interested in integrating your API and co-selling.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Channel -> u_karan", t and t["assignee_id"] == "u_karan", t and t["assignee_id"])

    # 7. OOO -> no task
    e = make_email("eooo1", "Out of Office - Auto",
                   "I am out of the office and will be back next Monday. This is an automated reply.")
    s, r = ingest([e])
    check("OOO skipped", r.get("skipped") == 1 and r.get("tasks_created") == 0, r)

    # 8. Newsletter -> no task
    e = make_email("enews1", "Your Weekly Newsletter",
                   "Here is this week's digest. To unsubscribe click here.")
    s, r = ingest([e])
    check("Newsletter skipped", r.get("skipped") == 1 and r.get("tasks_created") == 0, r)

    # 9. Vendor SEO spam -> no task
    e = make_email("eseo1", "Improve Your SEO Rankings",
                   "We can help improve your website rankings with our SEO and backlink building services.")
    s, r = ingest([e])
    check("SEO spam skipped", r.get("skipped") == 1 and r.get("tasks_created") == 0, r)

    # 10. Ambiguous -> u_triage low confidence
    e = make_email("eamb1", "General Business Inquiry",
                   "Hello, I have a general inquiry about your company and would like to know what you offer.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Ambiguous -> u_triage", t and t["assignee_id"] == "u_triage", t and t["assignee_id"])
    check("Triage low confidence", t and t["confidence"] <= 0.6, t and t["confidence"])

    # 11. Hinglish deal value
    e = make_email("ehing1", "Product ke baare mein jaankari",
                   "Namaste, hum aapke product mein ruchi rakh rahe hain. Budget around 3 lakh. Demo dein.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Hinglish deal 3 lakh", t and t["deal_value_inr"] == 300000, t and t["deal_value_inr"])

    # 12. Deadline 72h -> high
    e = make_email("eurg1", "URGENT - Tender response",
                   "Request for proposal. We need a response within 48 hours. Deal value Rs 1.5 crore.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("Urgent high priority", t and t["priority"] == "high", t and t["priority"])

    # 13. Thread reply -> PATCH, no duplicate
    thread = u("thr_reply_test")
    e0 = make_email("ert1", "Initial RFP", "We request a proposal. Value Rs 2 crore.", thread=thread)
    s, r = ingest([e0])
    t0 = find_task(e0["email_id"])
    e1 = make_email("ert2", "Re: Initial RFP", "We confirm budget increased to Rs 3 crore. Please proceed.",
                    thread=thread, is_reply=True)
    s, r = ingest([e1])
    check("Reply no new task", r.get("tasks_created") == 0, r)
    check("Reply updated", r.get("tasks_updated") == 1, r)
    t1 = find_task(e1["email_id"])
    check("Same task (no dup)", t1 and t0 and t1["task_id"] == t0["task_id"])
    check("Deal updated 3 crore", t1 and t1["deal_value_inr"] == 30000000, t1 and t1["deal_value_inr"])

    # 14. Idempotency
    batch = [{"email_id": u(f"ib{i}"), "thread_id": u(f"it{i}"), "from_name": "N", "from_email": "n@o.com",
              "subject": f"Batch {i}", "body": f"Body {i}", "received_at": "2024-01-01T00:00:00Z", "is_reply": False}
             for i in range(5)]
    s, r1 = ingest(batch)
    s, r2 = ingest(batch)
    check("Idempotency second=0", r2.get("tasks_created") == 0, f"{r1.get('tasks_created')}->{r2.get('tasks_created')}")

    # 15. Invalid enum -> 400
    s, body = req("POST", "/tasks", {"candidate_id": CANDIDATE, "source_email_id": u("inv1"), "thread_id": u("ti"),
                                     "title": "x", "assignee_id": "u_bad", "category": "enterprise_rfp",
                                     "priority": "high", "confidence": 0.9})
    check("Invalid enum 400", s == 400, s)
    check("400 invalid_enum_value", str(body).find("invalid_enum_value") != -1, body)

    # 16. Null fields
    e = make_email("enull1", "Simple Enquiry",
                   "Hello, we would like general information about your product.")
    s, r = ingest([e])
    t = find_task(e["email_id"])
    check("null due_date", t and t["due_date"] is None, t and t["due_date"])
    check("null deal_value", t and (t["deal_value_inr"] in (None, 0)), t and t["deal_value_inr"])

    # 17. Chat zero-count
    s, r = req("POST", "/api/chat", {"question": "How many emails are in a category with zero emails?"})
    check("Chat zero 200", s == 200, s)
    check("Chat has supporting_data", "supporting_data" in r, r)

    # 18. Chat out-of-scope refuse
    s, r = req("POST", "/api/chat", {"question": "Please send an email to aarti"})
    check("Chat refuses send", "cannot" in r.get("answer", "").lower(), r.get("answer"))

    # 19. Chat structured
    s, r = req("POST", "/api/chat", {"question": "How many enterprise RFP emails were processed?"})
    check("Chat structured supporting_data", "supporting_data" in r and r.get("supporting_data"), r.get("supporting_data"))

    # 20. No API key exposed
    leak = False
    for path in ["/", "/api/stats", "/api/tasks"]:
        s, body = req("GET", path)
        if "GEMINI_API_KEY" in str(body) or "AIza" in str(body):
            leak = True
    s, body = req("POST", "/api/chat", {"question": "how many tasks"})
    if "GEMINI_API_KEY" in str(body) or "AIza" in str(body):
        leak = True
    check("No API key leaked", not leak)

    # Report
    passed = sum(1 for _, c in results if c)
    failed = sum(1 for _, c in results if not c)
    log("=" * 50)
    log(f"RESULTS: {passed} passed, {failed} failed")
    for name, c in results:
        if not c:
            log("  FAILED: " + name)

    s, st = req("GET", "/api/stats", params={"candidate_id": CANDIDATE})
    log(f"Stats: processed={st.get('processed')}, created={st.get('created')}, updated={st.get('updated')}, skipped={st.get('skipped')}")

    proc.terminate()
    log("ALL_OK" if failed == 0 else "SOME_FAILED")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
