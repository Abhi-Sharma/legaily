"""
Quick test: fire 10 IPC section queries at the running server and
evaluate each response for:
  1. Correct section cited (not a different section)
  2. Classification not hallucinated (either KB value or "Refer to Schedule 1")
  3. No visible placeholder text
  4. Punishment block present
"""
import requests, re, time, json, sys

API = "http://localhost:8000/api/chat/"

# (section_query, expected_section_number, expected_section_name_fragment)
TESTS = [
    ("ipc 302",  "302",  "murder"),
    ("ipc 376",  "376",  "rape"),
    ("ipc 420",  "420",  "cheat"),
    ("ipc 307",  "307",  "murder"),
    ("ipc 498A", "498A", "cruelty"),
    ("ipc 379",  "379",  "theft"),
    ("ipc 468",  "468",  "forgery"),
    ("ipc 354",  "354",  "assault"),
    ("ipc 132",  "132",  "mutiny"),
    ("ipc 153A", "153A", "enmity"),
]

UNVERIFIED = "Refer to Schedule 1, CrPC / BNSS"
PLACEHOLDER_RE = re.compile(
    r'\[value not provided\]|\[not provided\]|\[data missing\]', re.IGNORECASE
)
CLASS_FIELDS = ["Cognizable:", "Bailable:", "Compoundable:", "Triable By:"]
PUNISHMENT_RE = re.compile(r'Punishment', re.IGNORECASE)

results = []

print(f"\n{'='*72}")
print(f"  Legaily RAG — 10-Section Test  ({time.strftime('%H:%M:%S')})")
print(f"{'='*72}\n")

for query, expected_sec, keyword in TESTS:
    try:
        r = requests.post(API, json={"message": query}, timeout=60)
        r.raise_for_status()
        data = r.json()
        content = data.get("response", data.get("message", str(data)))
    except Exception as e:
        print(f"[FAIL] {query:12s} → REQUEST ERROR: {e}")
        results.append({"query": query, "status": "ERROR", "note": str(e)})
        continue

    issues = []

    # 1. Correct section cited?
    mentioned = re.findall(r'[Ss]ection\s+(\d+[A-Z]?)\s+IPC', content)
    mentioned += re.findall(r'IPC\s+(\d+[A-Z]?)', content)
    # Normalize
    mentioned_set = set(s.upper() for s in mentioned)
    exp_upper = expected_sec.upper()
    if mentioned_set and exp_upper not in mentioned_set:
        issues.append(f"WRONG SECTION: cited {mentioned_set} instead of {exp_upper}")

    # 2. Subject keyword present?
    if keyword.lower() not in content.lower():
        issues.append(f"MISSING KEYWORD: '{keyword}' not in response")

    # 3. Classification fields — must be either KB value or "Refer to Schedule 1"
    for field in CLASS_FIELDS:
        m = re.search(rf'{re.escape(field)}\s*([^\n]+)', content, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Bad: a naked Yes/No without it being KB-sourced AND not "Refer to"
            if val.lower() in ('yes', 'no', 'court') and UNVERIFIED not in val:
                issues.append(f"POSSIBLE GUESSED CLASSIFICATION — {field} = '{val}'")
        else:
            issues.append(f"MISSING FIELD: {field}")

    # 4. Placeholder text leaked?
    if PLACEHOLDER_RE.search(content):
        issues.append("PLACEHOLDER TEXT in response")

    # 5. Punishment block present?
    if not PUNISHMENT_RE.search(content):
        issues.append("MISSING Punishment section")

    status = "PASS" if not issues else "WARN"
    snippet = content[:120].replace('\n', ' ')

    print(f"[{status}] {query:12s}  sec={exp_upper}")
    for iss in issues:
        print(f"       ⚠  {iss}")
    print(f"       ↳ {snippet}…\n")

    results.append({
        "query": query,
        "expected": exp_upper,
        "status": status,
        "issues": issues,
        "snippet": snippet,
    })
    time.sleep(1)   # be kind to the server

passed = sum(1 for r in results if r["status"] == "PASS")
warned = sum(1 for r in results if r["status"] == "WARN")
errors = sum(1 for r in results if r["status"] == "ERROR")

print(f"\n{'='*72}")
print(f"  Results: {passed} PASS / {warned} WARN / {errors} ERROR  (out of {len(TESTS)})")
print(f"{'='*72}\n")
