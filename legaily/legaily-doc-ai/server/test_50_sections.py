"""
Legaily RAG — 50 Random IPC Section Test
=========================================
Tests the full pipeline across:
  • KB-verified sections (expect PASS)
  • Unknown/sparse sections (expect "Refer to Schedule 1" fallback)
  • General Exceptions (expect N/A classification)
  • Alphanumeric sections (304A, 498A, etc.)
  • Edge-case / easily-confused sections

Checks per response:
  1. Correct section cited in body (not a different section)
  2. Subject keyword present
  3. Classification fields populated (either KB value OR "Refer to Schedule 1")
  4. No [value not provided] / [data missing] placeholders
  5. Punishment block present in response
"""

import requests, re, time, json, sys

API = "http://localhost:8000/api/chat/"

# ─────────────────────────────────────────────────────────────────────────────
# (query, expected_section, keyword_fragment, is_general_exception)
#   is_general_exception = True  → classification "N/A" is correct, not a WARN
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── Homicide / Murder ────────────────────────────────────────────────────
    ("ipc 299",  "299",  "culpable",   False),
    ("ipc 300",  "300",  "murder",     False),
    ("ipc 301",  "301",  "malice",     False),
    ("ipc 302",  "302",  "murder",     False),
    ("ipc 303",  "303",  "murder",     False),
    ("ipc 304",  "304",  "culpable",   False),
    ("ipc 304A", "304A", "negligent",  False),
    ("ipc 304B", "304B", "dowry",      False),
    ("ipc 306",  "306",  "suicide",    False),
    ("ipc 307",  "307",  "murder",     False),
    ("ipc 308",  "308",  "culpable",   False),
    ("ipc 309",  "309",  "suicide",    False),
    # ── Assault / Hurt ───────────────────────────────────────────────────────
    ("ipc 323",  "323",  "hurt",       False),
    ("ipc 324",  "324",  "hurt",       False),
    ("ipc 325",  "325",  "grievous",   False),
    ("ipc 326",  "326",  "grievous",   False),
    ("ipc 326A", "326A", "acid",       False),
    ("ipc 354",  "354",  "modesty",    False),
    ("ipc 354A", "354A", "harassment", False),
    ("ipc 354D", "354D", "stalking",   False),
    # ── Sexual Offences ──────────────────────────────────────────────────────
    ("ipc 375",  "375",  "rape",       False),
    ("ipc 376",  "376",  "rape",       False),
    ("ipc 377",  "377",  "unnatural",  False),
    # ── Kidnapping / Abduction ───────────────────────────────────────────────
    ("ipc 363",  "363",  "kidnapping", False),
    ("ipc 364A", "364A", "ransom",     False),
    ("ipc 366",  "366",  "abduction",  False),
    # ── Theft / Robbery / Dacoity ────────────────────────────────────────────
    ("ipc 379",  "379",  "theft",      False),
    ("ipc 380",  "380",  "theft",      False),
    ("ipc 392",  "392",  "robbery",    False),
    ("ipc 395",  "395",  "dacoity",    False),
    ("ipc 411",  "411",  "stolen",     False),
    # ── Cheating / Forgery ───────────────────────────────────────────────────
    ("ipc 420",  "420",  "cheat",      False),
    ("ipc 467",  "467",  "forgery",    False),
    ("ipc 468",  "468",  "forgery",    False),
    ("ipc 471",  "471",  "forgery",    False),
    # ── Domestic / Matrimonial ───────────────────────────────────────────────
    ("ipc 498A", "498A", "cruelty",    False),
    # ── Public Order / State ─────────────────────────────────────────────────
    ("ipc 124A", "124A", "sedition",   False),
    ("ipc 153A", "153A", "enmity",     False),
    ("ipc 147",  "147",  "riot",       False),
    ("ipc 149",  "149",  "assembly",   False),
    # ── Perjury / False Evidence ─────────────────────────────────────────────
    ("ipc 193",  "193",  "false",      False),
    # ── Armed Forces ─────────────────────────────────────────────────────────
    ("ipc 132",  "132",  "mutiny",     False),
    # ── General Exceptions (Defense — N/A classification is CORRECT) ─────────
    ("ipc 76",   "76",   "bound",      True),
    ("ipc 79",   "79",   "justified",  True),
    ("ipc 80",   "80",  "accident",   True),
    ("ipc 96",   "96",   "defence",    True),
    ("ipc 100",  "100",  "death",      True),
    # ── Sections NOT in KB → must say "Refer to Schedule 1" ──────────────────
    ("ipc 141",  "141",  "unlawful",   False),  # sparse in KB
    ("ipc 503",  "503",  "intimidat",  False),
    ("ipc 506",  "506",  "intimidat",  False),
]

UNVERIFIED_MARKER = "Refer to Schedule 1"
PLACEHOLDER_RE = re.compile(
    r'\[value not provided\]|\[not provided\]|\[data missing\]|\[N/A\]',
    re.IGNORECASE,
)
CLASS_FIELDS = ["Cognizable:", "Bailable:", "Compoundable:", "Triable By:"]
PUNISHMENT_RE = re.compile(r'Punishment|None\. This is a legal justification', re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────────────
results = []
failures = []

print(f"\n{'='*76}")
print(f"  Legaily RAG — 50-Section Stress Test  ({time.strftime('%H:%M:%S')})")
print(f"{'='*76}\n")

for idx, (query, expected_sec, keyword, is_exception) in enumerate(TESTS, 1):
    try:
        r = requests.post(API, json={"message": query}, timeout=90)
        r.raise_for_status()
        data = r.json()
        content = data.get("reply", data.get("response", data.get("message", str(data))))
    except Exception as e:
        label = f"[{idx:02d}/50] {query:12s}"
        print(f"[FAIL] {label} → REQUEST ERROR: {e}")
        results.append({"query": query, "status": "ERROR", "note": str(e)})
        failures.append(query)
        time.sleep(1)
        continue

    issues = []

    # ── Check 1: Correct section cited? ──────────────────────────────────────
    mentioned = re.findall(r'[Ss]ection\s+(\d+[A-Z]?)\s+IPC', content)
    mentioned += re.findall(r'IPC\s+(\d+[A-Z]?)', content)
    mentioned += re.findall(r'IPC[Ss]ection\s*(\d+[A-Z]?)', content)
    mentioned_set = set(s.upper() for s in mentioned)
    exp_upper = expected_sec.upper()
    if mentioned_set and exp_upper not in mentioned_set:
        issues.append(f"WRONG SECTION: cited {mentioned_set} instead of {exp_upper}")

    # ── Check 2: Subject keyword ──────────────────────────────────────────────
    if keyword.lower() not in content.lower():
        issues.append(f"MISSING KEYWORD: '{keyword}' not found in response")

    # ── Check 3: Classification fields ───────────────────────────────────────
    for field in CLASS_FIELDS:
        m = re.search(rf'-?\s*{re.escape(field)}\s*([^\n]+)', content, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if is_exception:
                # For general exceptions N/A is expected — only flag if a naked Yes/No slips in
                if val.lower() in ('yes', 'no') and UNVERIFIED_MARKER not in val:
                    issues.append(f"EXCEPTION SECTION GOT CRIMINAL CLASS — {field} = '{val}'")
            else:
                # For normal offences: bare Yes/No is OK (KB-sourced); blank or missing is bad
                if not val:
                    issues.append(f"EMPTY VALUE: {field}")
        else:
            issues.append(f"MISSING FIELD: {field}")

    # ── Check 4: No placeholder text ─────────────────────────────────────────
    if PLACEHOLDER_RE.search(content):
        issues.append("PLACEHOLDER TEXT leaked into response")

    # ── Check 5: Punishment block ─────────────────────────────────────────────
    if not PUNISHMENT_RE.search(content):
        issues.append("MISSING ⛓️ Punishment section")

    status = "PASS" if not issues else "WARN"
    snippet = content[:150].replace('\n', ' ')
    label = f"[{idx:02d}/50] {query:12s}  sec={exp_upper}"

    print(f"[{status}] {label}")
    for iss in issues:
        print(f"         ⚠  {iss}")
    print(f"         ↳ {snippet}…\n")

    if status == "WARN":
        failures.append(query)

    results.append({
        "query": query,
        "expected": exp_upper,
        "status": status,
        "issues": issues,
        "snippet": snippet,
    })
    time.sleep(1.2)   # be kind to the server

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r["status"] == "PASS")
warned = sum(1 for r in results if r["status"] == "WARN")
errors = sum(1 for r in results if r["status"] == "ERROR")
total  = len(TESTS)

print(f"\n{'='*76}")
print(f"  RESULTS: {passed} PASS / {warned} WARN / {errors} ERROR  (out of {total})")
print(f"  PASS RATE: {passed/total*100:.1f}%")
print(f"{'='*76}")

if failures:
    print("\n  ⚠  Failing / Warned queries:")
    for q in failures:
        print(f"     • {q}")

# Save full JSON report
report_path = "test_50_report.json"
with open(report_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n  Full report saved → {report_path}\n")
