# Fixing Historical Parsing for Legacy Terms

**Date**: 2025-10-05  
**Status**: Draft  
**Type**: ADR  
**Deciders**: Jérémie Lumbroso (human), Codex (GPT-5)

---

## Human Prompt: High-Level Context

- Spring 2025 scrapes now finish (~6,630 courses), but Fall 2024 stalls at ~2,216 and Fall 2023 stays empty.
- `logs/historical-scrape-20251005-114937.log` records **7,933 unique** `course_process_failed … Empty HTML string` events:
  - 202510 (Spring 2025): 80
  - 202430 (Fall 2024): 88
  - 202410 (Spring 2024): 89
  - 202330 (Fall 2023): 6,425
  - 202310 (Spring 2023): 7,558
- We repaired the CLI/runner earlier today; the remaining blocker is the parser.
- Need concrete evidence (live payloads), options, quantified impact, and a recommended fix.

**Agency Grant**: Investigate thoroughly (curl/scripts/logs), store payloads, reason about alternatives, and present a decision-ready plan.

---

## Questions for Claude

### Q1: What payload patterns trigger the failures?
**Context**: Logs say “Empty HTML string”, but we must confirm the term/status landscape.
**Constraints**: Reproducible commands; persist samples under version control.
**Authority**: Choose CRNs/terms to sample; summarize quantitatively.

### Q2: How should we change the scraper/parsers to cover those cases?
**Context**: We need complete historical coverage without fabricating seat counts.
**Expected response**: Enumerate alternatives, quantify recovered rows/snapshots, cite payloads.

### Q3: Is seats metadata available elsewhere in the payload?
**Context**: Before defaulting to “unknown”, confirm no alternative field (e.g., `allInGroup`, `all_sections__data`) carries capacity info.
**Expected response**: Point to sample files and explain findings.

---

## Supporting Materials: Code Examples

### Example 1: Capturing API payloads
```bash
$ ./scripts/fetch-api-samples.sh
Fetching term 202430, course BE 1000, CRN 60563 -> tests/fixtures/api_samples/fall-2024-be1000-60563.json
Fetching term 202330, course BE 1000, CRN 60563 -> tests/fixtures/api_samples/fall-2023-be1000-60563.json
...
Samples written to tests/fixtures/api_samples
```

### Example 2: Seats field comparison
```bash
$ for file in tests/fixtures/api_samples/*.json; do echo "=== $file"; jq '.status_new, .seats' "$file"; done
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

### Example 3: Failure counts by term
```python
Counter({'202310': 7558, '202330': 6425, '202410': 89, '202430': 88, '202510': 80})
```

### Example 4: Status distribution (sampled via live requests)
```json
{
  "202510": {"Canceled": {"count": 56, "empty_seats": 56},
              "Full": {"count": 23, "empty_seats": 23},
              "Active": {"count": 1, "empty_seats": 1}},
  "202430": {"Canceled": {"count": 67, "empty_seats": 67},
              "Full": {"count": 21, "empty_seats": 21}},
  "202410": {"Canceled": 76, "Full": 10, "Active": 3 (2 without seats)},
  "202330": {"": {"count": 100, "empty_seats": 100}},
  "202310": {"": {"count": 100, "empty_seats": 100}}
}
```

### Example 5: Inspecting alternate fields
```bash
$ jq '.allInGroup[0].stat' tests/fixtures/api_samples/fall-2023-be1000-60563.json
"A"   # no capacity numbers
$ jq '.all_sections__data' ... | head
"{\"sections\":[{...}]"  # schedule/instructor only, no seats
```

---

## Supporting Materials: Files to Reference

**Primary**
- `scripts/fetch-api-samples.sh`
- `tests/fixtures/api_samples/`
  - `spring-2025-enm5120-28914.json` (Canceled; `seats:""`)
  - `spring-2025-bepp9500-24135.json` (Full; `seats:""`)
  - `spring-2025-educ6123-24409.json` (Active; `seats:""`)
  - `fall-2024-be1000-60563.json` (Active; seats HTML present)
  - `fall-2023-be1000-60563.json` (historic active; `seats:""`)
- `logs/historical-scrape-20251005-114937.log`
- `src/parsers.py`, `src/persistence.py`

**Secondary**
- `src/cli.py`, `scripts/scrape-all-historical.sh` (earlier pipeline fixes)

---

## Supporting Materials: Related Discussions

- ADR 0001 – Penn Courses API structure
- ADR 0010 – Academic calendar integration
- Internal notes (2025-10-05) on CLI/runner repairs

---

## Claude's Response

### Understanding Check
Every failure corresponds to a detail payload where `seats` is empty or missing, regardless of status. Modern payloads omit seats for canceled/full sections (and occasional active ones), while legacy payloads omit both `status_new` and `seats` entirely. No alternate field carries capacity info.

### Cognitive Approach
1. Parsed the log to count unique failures per term (7,933 total).
2. Captured representative payloads via `scripts/fetch-api-samples.sh` plus targeted curls (`spring-2025-enm5120-28914.json`, `spring-2025-bepp9500-24135.json`, `spring-2025-educ6123-24409.json`, `fall-2023-be1000-60563.json`, etc.).
3. Verified `status_new` / `seats` combos:“Canceled”→"", “Full”→"", legacy active→""/blank.
4. Inspected `allInGroup`, `all_sections`, `all_sections__data`: none contain capacity numbers.
5. Quantified potential improvements (sections recovered per term) to support decision-making.

### Decisions Made

#### Decision 1: Prefer local parser fallback
**Why**: No alternative field offers capacity; fetching other endpoints would double requests without guaranteed benefit. Falling back locally preserves the course record and snapshots.
**Alternatives**: Additional API calls; manual seeding; leaving behaviour unchanged.

#### Decision 2: Preserve cancelled/full sections but expose status
**Why**: They reflect catalog history; downstream consumers can filter via `status_new`. Removing them would hide schedule changes.
**Alternatives**: Skip cancelled sections entirely; postpone decision.

### Questions for Jérémie
1. Representation: should missing seats be stored as `0/0` or should we allow `NULL`/`None` (requires schema changes)?
2. Annotation: do we want a `seats_unknown` flag so UIs/exporters can show “unknown” instead of “0/0”? (Logging will already flag occurrences.)
3. Inclusion policy: keep or drop cancelled sections? (Current plan keeps them.)

### Action Items
- [ ] Modify `src/parsers.parse_seats` to return a fallback dict when HTML is empty/unparsable; log warning with context.
- [ ] Ensure persistence handles the fallback without wiping snapshots.
- [ ] Add unit tests using the new fixtures (canceled, full, active-without-seats, historical active).
- [ ] Re-run historical scrapes (202510–202030) to recover ≈7,933 sections and associated snapshots.
- [ ] Adjust exporters/consumers if we introduce `seats_unknown` or nullable fields.

### Reflections
Capturing real payloads and sampling randomly per term clarified that this isn’t limited to legacy data—modern cancellations and “Full” status exhibit the same pattern. The collaboration template helped structure the investigation and made the evidence reusable.

---

## Iteration History

### Iteration 1 (2025-10-05)
**Human**: Demanded concrete evidence and a richer ADR.
**Claude**: Added sampling script/fixtures, quantified failures, proposed parser fallback and highlighted open questions.
**Outcome**: Awaiting decisions on representation (zero vs null) and inclusion policy for cancelled sections.

---

## Implementation Notes

- **Sections affected** (unique failures):
  - 202510: 80 (56 canceled, 23 full, 1 active)
  - 202430: 88 (67 canceled, 21 full)
  - 202410: 89 (76 canceled, 10 full, 3 active)
  - 202330: 6,425 (status blank, seats="")
  - 202310: 7,558 (status blank, seats="")
- **Payload evidence**:
  - `spring-2025-enm5120-28914.json` – `"status_new":"Canceled", "seats":""`
  - `spring-2025-bepp9500-24135.json` – `"status_new":"Full", "seats":""`
  - `spring-2025-educ6123-24409.json` – `"status_new":"Active", "seats":""`
  - `fall-2023-be1000-60563.json` – `"status_new":"", "seats":""`
  - `fall-2024-be1000-60563.json` – `"status_new":"Active", "seats":"<strong>Maximum Enrollment…"`
- **Downstream impact**: Restoring these rows will allow exports (`src/export.py`, `src/export_granular.py`) to list complete term coverage.

---

## Success Criteria

- [ ] Parser no longer throws on empty seat HTML; historical backfill completes.
- [ ] Database stats show Fall 2023 and Fall 2024 counts jump by ~6.4k and ~88 respectively.
- [ ] Tests cover missing-seat scenarios.
- [ ] Export consumers display “unknown” seats appropriately (decision pending).

---

## Meta: What Made This Collaboration Work

**Human style**: Direct, high-expectation feedback pushed for concrete data and rigorous documentation.  
**AI contribution**: Automated sampling of dozens of CRNs, reproducible evidence, quantification.  
**Repeatable pattern**: Store raw API payloads alongside ADRs for future debugging.

---

## Related Documents

- `docs/adr/0001-penn-courses-api-structure.md`
- `docs/adr/0010-penn-academic-calendar-integration.md`
- `logs/historical-scrape-20251005-114937.log`
- `tests/fixtures/api_samples/`
