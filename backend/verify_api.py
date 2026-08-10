import json
import os
import urllib.request
import urllib.error

BASE = os.getenv("VERIFY_BASE_URL", "http://127.0.0.1:8000")
HEADERS = {"Content-Type": "application/json"}

emails = [
    {
        "email_id": "e-rfp-1",
        "thread_id": "t1",
        "from_name": "Gov User",
        "from_email": "gov@example.com",
        "subject": "RFP for public sector deployment",
        "body": "Please share proposal for government tender. Budget 10,00,000 INR.",
        "received_at": "2026-08-10T10:00:00Z",
        "is_reply": False,
    },
    {
        "email_id": "e-smb-1",
        "thread_id": "t2",
        "from_name": "SMB User",
        "from_email": "smb@example.com",
        "subject": "Product demo request",
        "body": "We need a demo and pricing for 4 licenses.",
        "received_at": "2026-08-10T11:00:00Z",
        "is_reply": False,
    },
    {
        "email_id": "e-mkt-1",
        "thread_id": "t3",
        "from_name": "Marketer",
        "from_email": "mkt@example.com",
        "subject": "Sponsorship for webinar",
        "body": "Interested in co-marketing and sponsorship for our conference.",
        "received_at": "2026-08-10T12:00:00Z",
        "is_reply": False,
    },
    {
        "email_id": "e-fin-1",
        "thread_id": "t4",
        "from_name": "Finance",
        "from_email": "finance@example.com",
        "subject": "Invoice payment due",
        "body": "Invoice 12345 for 2,50,000 INR is due. Please process.",
        "received_at": "2026-08-10T13:00:00Z",
        "is_reply": False,
    },
    {
        "email_id": "e-ooo-1",
        "thread_id": "t5",
        "from_name": "Auto Reply",
        "from_email": "ooo@example.com",
        "subject": "Out of office",
        "body": "I am currently out of office until next week.",
        "received_at": "2026-08-10T14:00:00Z",
        "is_reply": False,
    },
    {
        "email_id": "e-reply-1",
        "thread_id": "t2",
        "from_name": "SMB User",
        "from_email": "smb@example.com",
        "subject": "Re: Product demo request",
        "body": "Following up on a reply to the demo request.",
        "received_at": "2026-08-10T15:00:00Z",
        "is_reply": True,
    },
]


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        content = r.read().decode("utf-8")
        try:
            return r.status, json.loads(content)
        except json.JSONDecodeError:
            return r.status, content


if __name__ == "__main__":
    print("POST /ingest")
    try:
        status, body = post("/ingest", {"candidate_id": "medashivaprasad123@gmail.com", "emails": emails})
        print(status, body)
    except urllib.error.HTTPError as e:
        print("ERROR", e.code, e.read().decode())

    for path in ["/api/tasks", "/api/stats", "/users", "/api/users"]:
        print(f"GET {path}")
        try:
            status, body = get(path)
            print(status, body)
        except urllib.error.HTTPError as e:
            print("ERROR", e.code, e.read().decode())

    print("POST /api/chat")
    try:
        status, body = post("/api/chat", {"question": "How many enterprise RFPs?"})
        print(status, body)
    except urllib.error.HTTPError as e:
        print("ERROR", e.code, e.read().decode())
