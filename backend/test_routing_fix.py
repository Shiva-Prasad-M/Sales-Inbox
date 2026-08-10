from app.routing import classify_deterministic

cases = [
    ("marketing", "We are organizing a tech conference and would like a sponsorship and co-marketing partnership.",
     "Sponsorship Opportunity", "u_meera"),
    ("channel", "We would like a reseller and channel partnership to integrate your API and co-sell.",
     "Channel Partnership", "u_karan"),
    ("rfp", "We request proposals for company-wide deployment. Deal value Rs 2,50,00,000.",
     "RFP", "u_aarti"),
]

ok = True
for name, body, subject, expected in cases:
    d = classify_deterministic(body, subject)
    status = "PASS" if d["assignee_id"] == expected else "FAIL"
    if d["assignee_id"] != expected:
        ok = False
    print(f"{status} {name}: got {d['assignee_id']} expected {expected} cat={d['category']}")

print("ALL_OK" if ok else "SOME_FAILED")
