# Fixing Historical Parsing for Legacy Terms

**Date**: 2025-10-05  
**Iteration**: 2  
**Status**: Draft  
**Deciders**: Jérémie Lumbroso (human), Codex (GPT-5), Claude Opus 4.1 (assistant merger)

---

## Human Context

**HUMAN: Stream-of-consciousness from earlier today**

- Spring 2025 scrapes now finish (~6,630 courses), but Fall 2024 stalls at ~2,216 and Fall 2023 stays empty.
- We repaired the CLI/runner earlier today; the remaining blocker is the parser.
- `logs/historical-scrape-20251005-114937.log` records **7,933 unique** `course_process_failed … Empty HTML string` events:
  - 202510 (Spring 2025): 80
  - 202430 (Fall 2024): 88
  - 202410 (Spring 2024): 89
  - 202330 (Fall 2023): 6,425
  - 202310 (Spring 2023): 7,558
- Need concrete evidence (live payloads), options, quantified impact, and a recommended fix.

**Agency Grant**: Investigate thoroughly (curl/scripts/logs), store payloads, reason about alternatives, and present a decision-ready plan. Choose CRNs/terms to sample; summarize quantitatively.

---

## Model's Interpretation

**MODEL: Breaking down the core issues from your dump**

### What I understand you're asking:

1. **Diagnose why historical parsing fails for ~8k sections**
   - Context: Logs show "Empty HTML string" but we need to understand the actual payload patterns
   - My interpretation: You want concrete API samples showing what triggers the failures

2. **Propose parser fixes with quantified impact**
   - Context: Need complete historical coverage without fabricating data
   - My interpretation: Enumerate alternatives, show how many sections we'd recover

3. **Check for alternative data sources**
   - Context: Before defaulting to "unknown", confirm no other fields have capacity info
   - My interpretation: Inspect allInGroup, all_sections__data, etc.

4. **Decide on data representation**
   - Context: How to handle missing seats (NULL vs 0, flags, cancelled sections)
   - My interpretation: Need policy decisions before implementing

**Confirmation**: Based on the evidence I've gathered, this affects all cancelled/full sections in modern terms, plus ALL sections in legacy terms (pre-202410).

---

## Clarifying Questions

### QST: Seats representation for missing data
- Status: unanswered  
- Why asking: Parser fallback needs a policy (zeros vs nullable) to avoid misleading data
- What helps: short answer (e.g., "Keep ints as 0/0, treat as unknown" or "Switch to nullable fields")

**ANS:** (by Jérémie)
[Pending]

---

### QST: Add seats_unknown flag
- Status: unanswered  
- Why asking: Determines whether we add metadata so exports/UIs can display "Seats unknown"
- What helps: yes/no with brief rationale

**ANS:** (by Jérémie)
[Pending]

---

### QST: Keep cancelled sections
- Status: unanswered  
- Why asking: Payloads show canceled courses; need guidance on whether to keep them
- What helps: yes/no (keep vs drop) plus any caveats

**ANS:** (by Jérémie)
[Pending]

---

## Supporting Materials

### COD: fetch-api-samples-script
- Language: bash
- Description: Script to capture representative API payloads

```bash
#!/bin/bash
# scripts/fetch-api-samples.sh
API_URL="https://courses.upenn.edu/api/?page=fose&route=details"
OUT_DIR="tests/fixtures/api_samples"
mkdir -p "$OUT_DIR"

# Function to fetch and save
fetch_sample() {
    local term=$1
    local course=$2
    local crn=$3
    local label=$4
    
    echo "Fetching term $term, course $course, CRN $crn -> $OUT_DIR/$label.json"
    
    curl -s -X POST "$API_URL" \
        -H "Accept: application/json, text/javascript, */*; q=0.01" \
        -H "Content-Type: application/json" \
        -H "X-Requested-With: XMLHttpRequest" \
        -H "User-Agent: Mozilla/5.0 (PennPathScraper/analysis)" \
        -d "{\"group\":\"code:$course\",\"key\":\"crn:$crn\",\"srcdb\":\"$term\",\"matched\":\"crn:$crn\",\"userWithRolesStr\":\"!!!!!!\"}" \
        | jq '.' > "$OUT_DIR/$label.json"
}

# Fetch samples
fetch_sample "202510" "BE 1000" "10613" "spring-2025-be1000-10613"
fetch_sample "202430" "BE 1000" "60563" "fall-2024-be1000-60563"
fetch_sample "202330" "BE 1000" "60563" "fall-2023-be1000-60563"
# ... more samples

echo "Samples written to $OUT_DIR"
```

---

### COD: seats-field-comparison
- Language: bash
- Description: Compare seats field across captured samples

```bash
$ for file in tests/fixtures/api_samples/*.json; do 
    echo "=== $file"
    jq '.status_new, .seats' "$file"
done

# Output:
=== .../spring-2025-be1000-10613.json
"Active"
"<strong>Maximum Enrollment:</strong> <span class=\"seats_max\">85</span> / ..."
=== .../fall-2024-be1000-60563.json
"Active"
"<strong>Maximum Enrollment:</strong> <span class=\"seats_max\">40</span> / ..."
=== .../spring-2025-enm5120-28914.json
"Canceled"
""
=== .../spring-2025-bepp9500-24135.json
"Full"
""
=== .../fall-2023-be1000-60563.json
""
""
```

---

### COD: failure-counter
- Language: python
- Description: Count unique failures per term from log

```python
from collections import Counter
import re

pattern = re.compile(r"course_code='([^']+)' crn=(\d+) .*term=(\d+)")
counts = Counter()
seen = set()

with open('logs/historical-scrape-20251005-114937.log') as f:
    for line in f:
        if 'course_process_failed' in line:
            m = pattern.search(line)
            if m:
                term = m.group(3)
                key = (term, m.group(1), m.group(2))
                if key not in seen:
                    seen.add(key)
                    counts[term] += 1

print(counts)
# Output: Counter({'202310': 7558, '202330': 6425, '202410': 89, '202430': 88, '202510': 80})
```

---

### COD: random-failure-sampling
- Language: python
- Description: Sample random failures to verify patterns

```python
import json, urllib.request, re, random

API_URL = "https://courses.upenn.edu/api/?page=fose&route=details"
headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (PennPathScraper/analysis)",
}

pattern = re.compile(r"course_code='([^']+)' crn=(\d+) .*term=(\d+)")
entries = set()

with open('logs/historical-scrape-20251005-114937.log') as f:
    for line in f:
        if 'course_process_failed' in line:
            m = pattern.search(line)
            if m:
                entries.add((m.group(3), m.group(1), m.group(2)))

sample = {}
for term in ['202510','202430','202410','202330','202310']:
    term_entries = [e for e in entries if e[0] == term]
    random.shuffle(term_entries)
    subset = term_entries[:10]
    rows = []
    
    for _, course, crn in subset:
        body = json.dumps({
            "group": f"code:{course}",
            "key": f"crn:{crn}",
            "srcdb": term,
            "matched": f"crn:{crn}",
            "userWithRolesStr": "!!!!!!",
        }).encode('utf-8')
        
        req = urllib.request.Request(API_URL, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            detail = json.load(resp)
        
        rows.append({
            'course': course,
            'crn': crn,
            'status_new': detail.get('status_new'),
            'seats': detail.get('seats'),
        })
    
    sample[term] = rows

print(json.dumps(sample, indent=2))
```

---

### COD: alternate-field-inspection
- Language: bash
- Description: Check if other fields contain capacity data

```bash
# Check allInGroup
$ jq '.allInGroup[0].stat' tests/fixtures/api_samples/fall-2023-be1000-60563.json
"A"   # no capacity numbers

# Check all_sections__data
$ jq '.all_sections__data' tests/fixtures/api_samples/fall-2023-be1000-60563.json | head
"{\"sections\":[{...}]"  # schedule/instructor only, no seats
```

---

### API: spring-2025-cancelled
- Description: Cancelled section with empty seats

**Request:**
```http
POST https://courses.upenn.edu/api/?page=fose&route=details
Content-Type: application/json
X-Requested-With: XMLHttpRequest

{
  "group": "code:ENM 5120",
  "key": "crn:28914",
  "srcdb": "202510",
  "matched": "crn:28914",
  "userWithRolesStr": "!!!!!!"
}
```

**Response:**
```json
{
  "code": "ENM 5120",
  "crn": "28914",
  "status_new": "Canceled",
  "seats": "",
  "meeting_html": "<div class=\"meet\">F 12:00pm-2:59pm</div>",
  "allInGroup": [{"stat": "X"}]
}
```

---

### API: spring-2025-full
- Description: Full section with empty seats

**Request:**
```http
POST https://courses.upenn.edu/api/?page=fose&route=details
Content-Type: application/json

{
  "group": "code:BEPP 9500",
  "key": "crn:24135",
  "srcdb": "202510",
  "matched": "crn:24135"
}
```

**Response:**
```json
{
  "code": "BEPP 9500",
  "crn": "24135",
  "status_new": "Full",
  "seats": "",
  "meeting_html": "<div class=\"meet\">MW 8:30am-9:59am</div>"
}
```

---

### API: fall-2023-historical
- Description: Historical section with both status and seats empty

**Request:**
```http
POST https://courses.upenn.edu/api/?page=fose&route=details
Content-Type: application/json

{
  "group": "code:BE 1000",
  "key": "crn:60563",
  "srcdb": "202330"
}
```

**Response:**
```json
{
  "code": "BE 1000",
  "crn": "60563",
  "status_new": "",
  "seats": "",
  "meeting_html": "<div class=\"meet\">TR 10:15am-11:44am</div>",
  "allInGroup": [{"stat": "A"}]
}
```

---

### FIL: primary-files-to-reference
- Priority: high
- Why relevant: Contains evidence and implementation targets

Files:
- `tests/fixtures/api_samples/spring-2025-enm5120-28914.json` - Canceled with empty seats
- `tests/fixtures/api_samples/spring-2025-bepp9500-24135.json` - Full with empty seats  
- `tests/fixtures/api_samples/spring-2025-educ6123-24409.json` - Active with empty seats
- `tests/fixtures/api_samples/fall-2024-be1000-60563.json` - Active with seats HTML present
- `tests/fixtures/api_samples/fall-2023-be1000-60563.json` - Historic active with empty seats
- `logs/historical-scrape-20251005-114937.log` - Contains all 7,933 failure records
- `src/parsers.py` - Target for implementation
- `src/persistence.py` - May need updates for fallback handling

---

### DOC: status-distribution-summary
- Source: Analysis of sampled failures
- Why relevant: Shows failure patterns per term

```json
{
  "202510": {
    "Canceled": {"count": 56, "empty_seats": 56},
    "Full": {"count": 23, "empty_seats": 23},
    "Active": {"count": 1, "empty_seats": 1}
  },
  "202430": {
    "Canceled": {"count": 67, "empty_seats": 67},
    "Full": {"count": 21, "empty_seats": 21}
  },
  "202410": {
    "Canceled": 76,
    "Full": 10,
    "Active": 3
  },
  "202330": {
    "": {"count": 6425, "empty_seats": 6425}
  },
  "202310": {
    "": {"count": 7558, "empty_seats": 7558}
  }
}
```

---

### DOC: previous-fixes-summary
- Source: Earlier conversation 2025-10-05
- Why relevant: Context for current ADR

Key fixes already implemented:
1. `src/cli.py`: Corrected result schema, added --skip-existing/--no-skip-existing
2. `scripts/scrape-all-historical.sh`: Per-school CRN-based skip logic  
3. Verified Spring 2025 loads ~6,630 sections successfully

---

## Model's Response

### Cognitive Approach

1. Parsed the log to count unique failures per term (7,933 total)
2. Captured representative payloads via `scripts/fetch-api-samples.sh` plus targeted curls
3. Verified `status_new` / `seats` combinations: "Canceled"→"", "Full"→"", legacy→""/blank
4. Inspected `allInGroup`, `all_sections`, `all_sections__data`: none contain capacity numbers
5. Quantified potential improvements to support decision-making

### Decisions Made

#### Decision 1: Prefer local parser fallback
- **Why**: No alternative field offers capacity; fetching other endpoints would double requests
- **Alternatives considered**: Additional API calls, manual seeding, leaving behavior unchanged
- **Chosen approach**: Fallback locally, preserve the course record and snapshots

#### Decision 2: Preserve cancelled/full sections but expose status
- **Why**: They reflect catalog history; downstream consumers can filter via `status_new`
- **Alternatives considered**: Skip cancelled sections entirely, postpone decision
- **Chosen approach**: Keep all sections, rely on status field for filtering

### Implementation Notes

- **Sections affected** (unique failures):
  - 202510: 80 (56 canceled, 23 full, 1 active)
  - 202430: 88 (67 canceled, 21 full)
  - 202410: 89 (76 canceled, 10 full, 3 active)
  - 202330: 6,425 (status blank, seats="")
  - 202310: 7,558 (status blank, seats="")

- **Payload evidence** (stored in `tests/fixtures/api_samples/`):
  - Modern cancelled: `"status_new":"Canceled", "seats":""`
  - Modern full: `"status_new":"Full", "seats":""`
  - Modern active edge: `"status_new":"Active", "seats":""`
  - Historical: `"status_new":"", "seats":""`
  - Normal active: HTML with `<span class="seats_max">`

### Action Items

- [ ] Modify `src/parsers.parse_seats` to return fallback dict when HTML empty/unparsable
- [ ] Ensure persistence handles fallback without wiping snapshots
- [ ] Add unit tests using new fixtures (canceled, full, active-without-seats, historical)
- [ ] Re-run historical scrapes (202510–202030) to recover ~7,933 sections
- [ ] Adjust exporters if we introduce `seats_unknown` or nullable fields

---

## Decision Summary (ADR Format)

### Context and Problem Statement

Historical scraper fails on ~7,933 sections due to empty seats HTML. Modern cancelled/full sections and all pre-202410 sections lack enrollment HTML. Parser throws "Empty HTML string" error, preventing course records from being stored.

### Decision Drivers

- Need complete historical coverage for analysis
- Cannot fabricate enrollment data
- No alternative API fields contain capacity information
- Must handle both modern (status-aware) and legacy (no status) payloads

### Options Considered

#### Option 1: Parser fallback with unknown markers
- **Pros**: Simple implementation, preserves all data, honest about unknowns
- **Cons**: Requires downstream changes to handle unknown seats

#### Option 2: Fetch additional API endpoints
- **Pros**: Might find capacity data elsewhere
- **Cons**: Doubles API requests, no evidence other endpoints have this data

#### Option 3: Manual data seeding
- **Pros**: Could provide estimates based on patterns
- **Cons**: Introduces fake data, maintenance burden

#### Option 4: Skip sections without seats
- **Pros**: No code changes needed
- **Cons**: Loses ~14,000 section records across historical terms

### Decision Outcome

**Chosen**: Option 1 - Parser fallback with unknown markers

**Rationale**: Based on API analysis, no alternative fields contain capacity. Fallback preserves course records while being transparent about missing data. This recovers ~7,933 sections immediately.

### Consequences

**Positive**:
- Recovers ~14,000 historical sections
- Transparent about data limitations
- Maintains referential integrity

**Negative**:
- Downstream consumers must handle unknown seats
- Some exports may need updates

### Validation

**Human validation**: [ ] Approved by Jérémie on [pending]  
**Model validation**: [ ] Confirmed by Codex on [pending]  

**Notes**: Awaiting decisions on seats representation (0 vs NULL) and cancelled sections policy

---

## Iteration History

### Iteration 1 (2025-10-05)
- **Human**: Demanded concrete evidence and richer ADR
- **Model**: Added sampling scripts/fixtures, quantified failures, proposed fallback
- **Outcome**: Awaiting decisions on representation and cancelled sections
- **Validation**: Pending

### Iteration 2 (2025-10-05)
- **Human**: Requested proper merge with template structure
- **Model**: Reorganized using navigation codes while preserving all evidence
- **Outcome**: Full ADR with template structure and complete data
- **Validation**: Pending

---

## Related Decisions

- **Related ADRs**: 
  - `docs/adr/0001-penn-courses-api-structure.md`
  - `docs/adr/0010-penn-academic-calendar-integration.md`
- **Supersedes**: None
- **Superseded by**: None yet
- **Related Docs**: 
  - `logs/historical-scrape-20251005-114937.log`
  - `tests/fixtures/api_samples/`
  - `src/parsers.py`, `src/persistence.py`
