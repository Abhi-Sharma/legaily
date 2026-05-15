"""
Legaily RAG — 100 Unknown-Section Stress Test
==============================================
Tests 100 IPC sections that are NOT in LEGAL_KNOWLEDGE_BASE.

For each response we verify:
  1. Classification fields are ALL present
  2. NO bare 'Yes' / 'No' guesses — must say "Refer to Schedule 1" or similar
  3. No [value not provided] / placeholder text leaking through
  4. Punishment section is present (even as "refer to statute")
  5. Section number appears in the response (not a totally wrong section)
  6. No hallucinated scenario outside the illustrative-example block

The test tracks:
  PASS   → all checks green
  WARN   → content issues (wrong classification, placeholder, missing field)
  ERROR  → network/server failure
"""

import requests, re, time, json, sys

API = "http://localhost:8000/api/chat/"

# ── 100 IPC sections NOT present in the KB ───────────────────────────────────
# Spread across every chapter of the IPC (1–511) to give full coverage.
# (verified against LEGAL_KNOWLEDGE_BASE output: 135 entries above)
TESTS = [
    # Chapter IV — General Exceptions (not in KB)
    ("ipc 82",  "82",  "child"),
    ("ipc 83",  "83",  "child"),
    ("ipc 84",  "84",  "unsound mind"),
    ("ipc 85",  "85",  "intoxication"),
    ("ipc 86",  "86",  "intoxication"),
    ("ipc 87",  "87",  "consent"),
    ("ipc 88",  "88",  "consent"),
    ("ipc 89",  "89",  "guardian"),
    ("ipc 90",  "90",  "fear"),
    ("ipc 91",  "91",  "offence"),
    ("ipc 92",  "92",  "good faith"),
    ("ipc 93",  "93",  "communication"),
    ("ipc 94",  "94",  "threat"),
    ("ipc 95",  "95",  "harm"),
    ("ipc 98",  "98",  "private defence"),
    ("ipc 99",  "99",  "private defence"),
    # Chapter V — Abetment (not in KB)
    ("ipc 108", "108", "abettor"),
    ("ipc 109", "109", "abetment"),
    ("ipc 110", "110", "abetment"),
    ("ipc 111", "111", "abettor"),
    ("ipc 112", "112", "abettor"),
    ("ipc 113", "113", "abetment"),
    ("ipc 114", "114", "abettor"),
    ("ipc 115", "115", "abetment"),
    ("ipc 116", "116", "abetment"),
    ("ipc 117", "117", "abetment"),
    ("ipc 118", "118", "design"),
    ("ipc 119", "119", "design"),
    # Chapter VI — Offences Against the State
    ("ipc 121", "121", "war"),
    ("ipc 122", "122", "war"),
    ("ipc 123", "123", "design"),
    ("ipc 125", "125", "war"),
    ("ipc 126", "126", "depredation"),
    ("ipc 127", "127", "property"),
    ("ipc 128", "128", "prisoner"),
    ("ipc 129", "129", "prisoner"),
    ("ipc 130", "130", "prisoner"),
    # Chapter VII — Offences Relating to the Army, Navy, Air Force (not in KB)
    ("ipc 134", "134", "mutiny"),
    ("ipc 135", "135", "desertion"),
    ("ipc 136", "136", "deserter"),
    ("ipc 137", "137", "vessel"),
    ("ipc 138", "138", "insubordination"),
    ("ipc 140", "140", "token"),
    # Chapter VIII — Offences Against Public Tranquillity (not in KB)
    ("ipc 142", "142", "assembly"),
    ("ipc 143", "143", "assembly"),
    ("ipc 144", "144", "weapon"),
    ("ipc 145", "145", "assembly"),
    ("ipc 146", "146", "riot"),
    ("ipc 150", "150", "assembly"),
    ("ipc 151", "151", "assembly"),
    ("ipc 152", "152", "riot"),
    ("ipc 153", "153", "provocation"),
    ("ipc 158", "158", "riot"),
    ("ipc 160", "160", "affray"),
    # Chapter IX — Offences by/Relating to Public Servants (not in KB)
    ("ipc 166", "166", "public servant"),
    ("ipc 167", "167", "public servant"),
    ("ipc 170", "170", "personating"),
    ("ipc 171", "171", "token"),
    # Chapter X — Contempt of Lawful Authority
    ("ipc 172", "172", "summons"),
    ("ipc 173", "173", "summons"),
    ("ipc 174", "174", "order"),
    ("ipc 175", "175", "document"),
    ("ipc 176", "176", "notice"),
    ("ipc 177", "177", "information"),
    ("ipc 178", "178", "oath"),
    ("ipc 179", "179", "answer"),
    ("ipc 180", "180", "statement"),
    ("ipc 181", "181", "oath"),
    ("ipc 182", "182", "information"),
    ("ipc 183", "183", "property"),
    ("ipc 184", "184", "sale"),
    ("ipc 185", "185", "purchase"),
    ("ipc 187", "187", "assistance"),
    ("ipc 188", "188", "disobedience"),
    ("ipc 190", "190", "complaint"),
    ("ipc 192", "192", "evidence"),
    ("ipc 195", "195", "conviction"),
    ("ipc 196", "196", "evidence"),
    ("ipc 197", "197", "certificate"),
    ("ipc 198", "198", "certificate"),
    ("ipc 199", "199", "declaration"),
    ("ipc 200", "200", "declaration"),
    ("ipc 201", "201", "evidence"),
    ("ipc 202", "202", "information"),
    # Chapter XI — False Evidence & Offences Against Public Justice
    ("ipc 205", "205", "personation"),
    ("ipc 206", "206", "property"),
    ("ipc 207", "207", "property"),
    ("ipc 208", "208", "decree"),
    ("ipc 209", "209", "claim"),
    ("ipc 210", "210", "decree"),
    ("ipc 212", "212", "offender"),
    ("ipc 213", "213", "offender"),
    ("ipc 214", "214", "offender"),
    ("ipc 215", "215", "stolen"),
    # Chapter XVI — Hurt (sections not in KB)
    ("ipc 321", "321", "hurt"),
    ("ipc 322", "322", "grievous"),
    ("ipc 327", "327", "hurt"),
    ("ipc 328", "328", "poison"),
    ("ipc 329", "329", "hurt"),
    ("ipc 330", "330", "hurt"),
]

# Ensure exactly 100
assert len(TESTS) == 100, f"Got {len(TESTS)} test cases, expected 100"

# ── Validation constants ──────────────────────────────────────────────────────
UNVERIFIED_MARKER = re.compile(
    r'Refer to Schedule\s*1|Refer to Schedule\s*I|refer to schedule',
    re.IGNORECASE
)
# A bare Yes/No (not preceded by something like "N/A" or "Refer to")
BARE_CLASSIFICATION_RE = re.compile(
    r'(Cognizable|Bailable|Compoundable|Triable By)\s*:\s*(Yes|No|Court of Session|'
    r'Magistrate|Any Magistrate|Chief Judicial Magistrate)\b',
    re.IGNORECASE
)
PLACEHOLDER_RE = re.compile(
    r'\[value not provided\]|\[not provided\]|\[data missing\]|\[information unavailable\]',
    re.IGNORECASE
)
CLASS_FIELDS = ["Cognizable:", "Bailable:", "Compoundable:", "Triable By:"]
PUNISHMENT_RE = re.compile(
    r'Punishment|None\. This is a legal|Refer to the relevant punishment|'
    r'refer to statute|no standalone punishment|prescribed in',
    re.IGNORECASE
)

# ── Run tests ─────────────────────────────────────────────────────────────────
results = []
failures = []

print(f"\n{'='*78}")
print(f"  Legaily RAG — 100 Unknown-Section Fallback Test  ({time.strftime('%H:%M:%S')})")
print(f"  Goal: All 4 fields must say 'Refer to Schedule 1' — NO bare Yes/No guesses")
print(f"{'='*78}\n")

for idx, (query, expected_sec, keyword) in enumerate(TESTS, 1):
    try:
        r = requests.post(API, json={"message": query}, timeout=120)
        r.raise_for_status()
        data = r.json()
        # Routes return {"reply": "...", "type": "..."}
        content = data.get("reply", data.get("response", data.get("message", str(data))))
    except Exception as e:
        label = f"[{idx:03d}/100] {query:12s}"
        print(f"[ERROR] {label} → {e}")
        results.append({"query": query, "status": "ERROR", "issues": [str(e)]})
        failures.append((query, ["REQUEST_ERROR"]))
        time.sleep(1)
        continue

    issues = []

    # ── Check 1: Section number present in response ───────────────────────────
    mentioned = re.findall(r'[Ss]ection\s+(\d+[A-Z]?)\s*(?:IPC|BNS|of the)', content)
    mentioned += re.findall(r'IPC\s*(?:Section\s*)?(\d+[A-Z]?)', content, re.IGNORECASE)
    mentioned += re.findall(r'(\d+[A-Z]?)\s+IPC', content)
    mentioned_set = set(s.upper() for s in mentioned)
    exp_upper = expected_sec.upper()
    if mentioned_set and exp_upper not in mentioned_set:
        issues.append(f"WRONG SECTION: response mentions {mentioned_set}, not {exp_upper}")

    # ── Check 2: Subject keyword present ─────────────────────────────────────
    if keyword.lower() not in content.lower():
        issues.append(f"MISSING KEYWORD: '{keyword}'")

    # ── Check 3: All 4 classification fields present ──────────────────────────
    missing_fields = []
    for field in CLASS_FIELDS:
        # Match both "Cognizable: Yes" and "- Cognizable:   Yes" formats
        m = re.search(rf'-?\s*{re.escape(field)}\s*([^\n]+)', content, re.IGNORECASE)
        if not m:
            missing_fields.append(field)
    if missing_fields:
        issues.append(f"MISSING FIELDS: {missing_fields}")

    # ── Check 4: No bare Yes/No guesses for classification ───────────────────
    # This is the CRITICAL check — unknown sections must NOT have guessed values
    bare_matches = BARE_CLASSIFICATION_RE.findall(content)
    if bare_matches:
        # Only flag if they appear in the classification block, not in illustrative examples
        class_block_match = re.search(
            r'(📊 Legal Classification.*?)(?=🔍 Illustrative|📑 Legal Auth|$)',
            content, re.DOTALL | re.IGNORECASE
        )
        if class_block_match:
            block_text = class_block_match.group(1)
            block_bare = BARE_CLASSIFICATION_RE.findall(block_text)
            if block_bare:
                issues.append(f"HALLUCINATED CLASSIFICATION: {block_bare}")

    # ── Check 5: "Refer to Schedule 1" present (at least once) ───────────────
    if not UNVERIFIED_MARKER.search(content) and not missing_fields:
        # Only flag if the fields are present but don't say Refer to Schedule 1
        issues.append("MISSING 'Refer to Schedule 1' fallback marker")

    # ── Check 6: No placeholder text ─────────────────────────────────────────
    if PLACEHOLDER_RE.search(content):
        issues.append("PLACEHOLDER TEXT leaked into response")

    # ── Check 7: Punishment block present ────────────────────────────────────
    if not PUNISHMENT_RE.search(content):
        issues.append("MISSING Punishment section")

    status = "PASS" if not issues else "WARN"
    snippet = content[:160].replace('\n', ' ')
    label = f"[{idx:03d}/100] {query:12s}  sec={exp_upper}"

    print(f"[{status}] {label}")
    for iss in issues:
        print(f"           ⚠  {iss}")
    if issues:
        print(f"           ↳ {snippet}…")
    print()

    if status != "PASS":
        failures.append((query, issues))

    results.append({
        "query":    query,
        "expected": exp_upper,
        "keyword":  keyword,
        "status":   status,
        "issues":   issues,
        "snippet":  snippet,
    })
    time.sleep(1.0)

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r["status"] == "PASS")
warned = sum(1 for r in results if r["status"] == "WARN")
errors = sum(1 for r in results if r["status"] == "ERROR")
total  = len(TESTS)

print(f"\n{'='*78}")
print(f"  RESULTS: {passed} PASS / {warned} WARN / {errors} ERROR  (out of {total})")
print(f"  PASS RATE: {passed/total*100:.1f}%")
print(f"{'='*78}")

# Categorise failures by issue type
hallucination_fails  = [q for q, iss in failures if any("HALLUCINATED" in i for i in iss)]
missing_field_fails  = [q for q, iss in failures if any("MISSING FIELDS" in i for i in iss)]
no_schedule_fails    = [q for q, iss in failures if any("Refer to Schedule" in i for i in iss)]
wrong_section_fails  = [q for q, iss in failures if any("WRONG SECTION" in i for i in iss)]
missing_keyword_fails= [q for q, iss in failures if any("MISSING KEYWORD" in i for i in iss)]
request_errors       = [q for q, iss in failures if any("REQUEST_ERROR" in i for i in iss)]

if hallucination_fails:
    print(f"\n  🚨 HALLUCINATED CLASSIFICATION ({len(hallucination_fails)}):")
    for q in hallucination_fails:
        print(f"     • {q}")

if missing_field_fails:
    print(f"\n  ⚠️  MISSING CLASSIFICATION FIELDS ({len(missing_field_fails)}):")
    for q in missing_field_fails:
        print(f"     • {q}")

if no_schedule_fails:
    print(f"\n  ⚠️  MISSING 'Refer to Schedule 1' MARKER ({len(no_schedule_fails)}):")
    for q in no_schedule_fails:
        print(f"     • {q}")

if wrong_section_fails:
    print(f"\n  ⚠️  WRONG SECTION CITED ({len(wrong_section_fails)}):")
    for q in wrong_section_fails:
        print(f"     • {q}")

if missing_keyword_fails:
    print(f"\n  ⚠️  MISSING SUBJECT KEYWORD ({len(missing_keyword_fails)}):")
    for q in missing_keyword_fails:
        print(f"     • {q}")

if request_errors:
    print(f"\n  ❌ REQUEST ERRORS ({len(request_errors)}):")
    for q in request_errors:
        print(f"     • {q}")

# Save full report
report_path = "test_100_unknown_report.json"
with open(report_path, "w") as f:
    json.dump({
        "summary": {
            "total": total, "passed": passed,
            "warned": warned, "errors": errors,
            "pass_rate": f"{passed/total*100:.1f}%"
        },
        "results": results,
        "failure_categories": {
            "hallucinated_classification": hallucination_fails,
            "missing_fields": missing_field_fails,
            "missing_schedule1_marker": no_schedule_fails,
            "wrong_section": wrong_section_fails,
            "missing_keyword": missing_keyword_fails,
            "request_errors": request_errors,
        }
    }, f, indent=2)
print(f"\n  Full report saved → {report_path}\n")
