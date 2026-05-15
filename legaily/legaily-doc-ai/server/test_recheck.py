"""
Targeted re-test for the 7 queries that WARN/ERRORed in the 50-section run.
"""
import requests, re, time

API = "http://localhost:8000/api/chat/"

TESTS = [
    ("ipc 299",  "299",  "culpable",   False),
    ("ipc 300",  "300",  "murder",     False),
    ("ipc 364A", "364A", "ransom",     False),
    ("ipc 392",  "392",  "robbery",    False),
    ("ipc 471",  "471",  "forged",     False),
    ("ipc 193",  "193",  "false",      False),
    ("ipc 503",  "503",  "intimidat",  False),
]

CLASS_FIELDS = ["Cognizable:", "Bailable:", "Compoundable:", "Triable By:"]
PUNISHMENT_RE = re.compile(r'Punishment|None\. This is a legal justification', re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r'\[value not provided\]|\[not provided\]|\[data missing\]', re.IGNORECASE)

print(f"\n{'='*64}")
print(f"  Re-check: 7 previously failed sections  ({time.strftime('%H:%M:%S')})")
print(f"{'='*64}\n")

results = []
for query, expected_sec, keyword, is_exc in TESTS:
    try:
        r = requests.post(API, json={"message": query}, timeout=120)
        r.raise_for_status()
        data = r.json()
        content = data.get("reply", data.get("response", data.get("message", str(data))))
    except Exception as e:
        print(f"[ERROR] {query} → {e}\n")
        results.append(("ERROR", query))
        time.sleep(1)
        continue

    issues = []

    # 1. Correct section cited?
    mentioned = re.findall(r'[Ss]ection\s+(\d+[A-Z]?)\s+IPC', content)
    mentioned += re.findall(r'IPC\s+(\d+[A-Z]?)', content)
    mentioned_set = set(s.upper() for s in mentioned)
    exp = expected_sec.upper()
    if mentioned_set and exp not in mentioned_set:
        issues.append(f"WRONG SECTION: cited {mentioned_set} not {exp}")

    # 2. Keyword present?
    if keyword.lower() not in content.lower():
        issues.append(f"MISSING KEYWORD: '{keyword}'")

    # 3. Classification fields
    for field in CLASS_FIELDS:
        m = re.search(rf'{re.escape(field)}\s*([^\n]+)', content, re.IGNORECASE)
        if not m:
            issues.append(f"MISSING FIELD: {field}")
        elif not m.group(1).strip():
            issues.append(f"EMPTY FIELD: {field}")

    # 4. No placeholders
    if PLACEHOLDER_RE.search(content):
        issues.append("PLACEHOLDER TEXT")

    # 5. Punishment block
    if not PUNISHMENT_RE.search(content):
        issues.append("MISSING Punishment section")

    status = "PASS" if not issues else "WARN"
    snippet = content[:180].replace('\n', ' ')
    print(f"[{status}] {query:12s}  sec={exp}")
    for i in issues:
        print(f"         ⚠  {i}")
    print(f"         ↳ {snippet}…\n")
    results.append((status, query))
    time.sleep(1.2)

passed = sum(1 for s, _ in results if s == "PASS")
print(f"\n{'='*64}")
print(f"  Re-check: {passed}/{len(TESTS)} PASS")
print(f"{'='*64}\n")
