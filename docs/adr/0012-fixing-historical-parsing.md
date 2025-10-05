# Fixing Historical Parsing for Legacy Terms

**Date**: 2025-10-05
**Status**: Draft
**Type**: ADR
**Deciders**: Jérémie Lumbroso (human), Codex (GPT-5)

---

## Human Prompt: High-Level Context

- We patched the historical runner (CLI result schema, `--no-skip-existing`, per-term+school skip checks) and verified Spring 2025 now populates ~6.6k courses.
- Fall 2024 tops out around 2.2k courses and Fall 2023 remains empty despite the scraper visiting every CRN.
- Logs flood with `course_process_failed … error='Empty HTML string'` and the exported term indexes omit those legacy offerings.
- Need to understand the precise failure mode, capture raw API payloads for posterity, and propose a parser fix that lets the historical backfill complete.

**Agency Grant**: Investigate legacy API behaviour, gather reproducible evidence (curl/script), document findings, and recommend a concrete parser change for human approval. Feel free to create helper scripts and fixture files.

---

## Questions for Claude

### Q1: What exactly is the legacy API returning that breaks the scraper?
**Context**: The warnings mention “Empty HTML string,” but we need the raw payloads to confirm.
**Constraints**: Use commands/scripts that can be rerun later; store outputs under version control.
**Your call**: Choose representative term/CRN pairs and how to persist them.

### Q2: What parser change should we adopt so the scrape succeeds?
**Context**: We must ingest historical data even when optional seat metadata is missing.
**Expected response**: Describe the code change (files, logic, side effects) and its trade-offs.

---

## Supporting Materials: Code Examples

### Example 1: Collecting API detail payloads
```bash
$ ./scripts/fetch-api-samples.sh
Fetching term 202510, course BE 1000, CRN 10613 -> tests/fixtures/api_samples/spring-2025-be1000-10613.json
Fetching term 202430, course BE 1000, CRN 60563 -> .../fall-2024-be1000-60563.json
Fetching term 202330, course BE 1000, CRN 60563 -> .../fall-2023-be1000-60563.json
Fetching term 202430, course CHEM 1101, CRN 80134 -> .../fall-2024-chem1101-80134.json
Fetching term 202330, course OIDD 2910, CRN 60251 -> .../fall-2023-oidd2910-60251.json
Samples written to tests/fixtures/api_samples
```

### Example 2: Comparing `seats` fields across eras
```bash
$ for file in tests/fixtures/api_samples/*.json; do echo "=== $file"; jq '.seats' "$file"; done
=== .../spring-2025-be1000-10613.json
"<strong>Maximum Enrollment:</strong> <span class=\"seats_max\">85</span> / <strong>Seats Avail:</strong> <span class=\"seats_avail\">28</span>"
=== .../fall-2024-be1000-60563.json
"<strong>Maximum Enrollment:</strong> <span class=\"seats_max\">40</span> / <strong>Seats Avail:</strong> <span class=\"seats_avail\">1</span>"
=== .../fall-2024-chem1101-80134.json
""
=== .../fall-2023-be1000-60563.json
""
=== .../fall-2023-oidd2910-60251.json
""
```

### Example 3: Log evidence of parser aborts (Fall 2023 excerpt)
```text
82654:2025-10-05 16:23:00 [info     ] scrape_term_start              ... term=202330
82660:2025-10-05 16:23:01 [info     ] get_course_details             course_code='BE 1000' crn=60563 term=202330
82664:2025-10-05 16:23:01 [warning  ] course_process_failed          ... error='Empty HTML string'
82669:2025-10-05 16:23:02 [warning  ] course_process_failed          ... error='Empty HTML string'
... (every CRN for 202330 fails similarly)
```

---

## Supporting Materials: Files to Reference

**Primary**:
- `scripts/fetch-api-samples.sh` – reproducible script that captures live detail payloads.
- `tests/fixtures/api_samples/*.json` – saved responses for Spring 2025, Fall 2024, Fall 2023 (multiple departments).
- `logs/historical-scrape-20251005-114937.log` – shows scrape progress and `Empty HTML string` warnings.
- `src/parsers.py` – `parse_seats` currently raises on empty/malformed HTML.

**Secondary**:
- `src/persistence.py` – how parsed seat data feeds into course persistence and snapshot creation.
- `src/cli.py` / `scripts/scrape-all-historical.sh` – context on previous fixes enabling the current run.

---

## Supporting Materials: Related Discussions

- ADR 0001 – Penn Courses API structure (term codes, payload expectations).
- ADR 0010 – Academic calendar integration (clarifies Summer term codes).
- Internal notes from 2025-10-05 covering CLI and runner fixes earlier in the day.

---

## Claude's Response

### Understanding Check
Older course-detail payloads return an empty string for `seats`, so `parse_seats` raises `ValueError("Empty HTML string")`. `_process_course` logs the warning, skips the course, and no record/snapshot is stored. This occurs occasionally for Spring 2025, frequently for Fall 2024, and universally for Fall 2023, explaining the term-count discrepancy (`pipenv run scraper --db ./courses.db stats`).

### Cognitive Approach
1. Reviewed the human/AI collaboration template to align on format and expectations.
2. Authored and ran `scripts/fetch-api-samples.sh` to fetch live payloads for representative CRNs across Spring 2025, Fall 2024, and Fall 2023; stored them in `tests/fixtures/api_samples/`.
3. Used `jq` to compare the `seats` field across samples; newer terms include the `<span class="seats_max">…</span>` block, while many legacy payloads return `""`.
4. Cross-referenced scrape logs showing `Empty HTML string` warnings for the same CRNs, confirming the parser abort path is responsible for missing data.

### Decisions Made

#### Decision 1: Persist evidence via script + fixtures
**Why**: Provides reusable proof and avoids relying solely on log snippets or mutable network responses.
**Alternatives considered**: Inline curl commands; relying on stale fixtures.
**Chosen approach**: Keep the script in `scripts/`, outputs in `tests/fixtures/api_samples/`, so future runs can refresh samples if the API changes.

#### Decision 2: Recommend parser fallback (gracefully handle missing seats)
**Why**: Scraper should ingest historical courses even when seat HTML is absent; missing data is better represented as zero/unknown than dropped rows.
**Alternatives considered**: Additional API lookups for legacy terms, manual data seeding, or leaving behaviour unchanged.
**Chosen approach**: Update `parse_seats` to detect empty/whitespace HTML and return a default `ParsedSeatsDict` (e.g., 0/0/0) while logging a warning; optionally mark a metadata flag for downstream consumers.

### Questions for Jérémie
1. When `seats` is unavailable, should we persist zeros or `NULL` values? (Zeros are easy but may imply actual capacity.)
2. Do we want an explicit marker (e.g., `course.attributes['seats_unknown'] = true`) so dashboards can display “Unknown” instead of “0/0”?

### Action Items
- [ ] Modify `src/parsers.parse_seats` to return a fallback dict when HTML is empty/unparsable; ensure warning log remains.
- [ ] Update or confirm `src.persistence.api_details_to_course_dict` tolerates the fallback (no extra deletes needed).
- [ ] Add tests covering empty-seat payloads using the new fixtures.
- [ ] Re-run historical scrapes for Fall 2024 / Fall 2023 and confirm term counts increase (expect parity with newer terms).
- [ ] Optional: annotate courses with a “seats unknown” flag for downstream clarity.

### Reflections
The collaboration template forced a structured investigation: evidence gathering (script + fixtures), log correlation, and a targeted recommendation rather than a vague intuition. Storing the samples will help future debugging sessions.

---

## Iteration History

### Iteration 1 (2025-10-05)
**Human**: Requested concrete curl-based evidence and a richer ADR.
**Claude**: Captured live payloads, rewrote ADR using the new template, and proposed a parser fallback.
**Outcome**: Awaiting decision on the fallback semantics (zero vs null) before implementing.

---

## Implementation Notes

- Script location: `scripts/fetch-api-samples.sh` (Mac-compatible; uses `curl`, `python`, `stat`).
- Sample payloads illustrating the issue:
  - `tests/fixtures/api_samples/spring-2025-be1000-10613.json` → `seats` contains the expected HTML.
  - `tests/fixtures/api_samples/fall-2024-chem1101-80134.json` → `seats` is an empty string.
  - `tests/fixtures/api_samples/fall-2023-be1000-60563.json` → `seats` is an empty string.
- Scrape log references: `logs/historical-scrape-20251005-114937.log` lines ~82660+ (Fall 2023) show consistent failures with `Empty HTML string`.

---

## Success Criteria

- [ ] Parser fallback prevents `Empty HTML string` exceptions during historical scrapes.
- [ ] Database stats show non-zero course counts for Fall 2024 and Fall 2023 after rerun.
- [ ] Tests cover empty seat scenarios and pass.

---

## Meta: What Made This Collaboration Work

**Human working style that helped**
- Direct feedback to gather concrete evidence and adopt the human/AI template improved clarity.

**AI capabilities that were useful**
- Automating API sampling and correlating payloads with log warnings.

**Patterns to repeat**
- Store raw API samples whenever diagnosing upstream issues; include them in ADR supporting materials.

---

## Related Documents

- `docs/adr/0001-penn-courses-api-structure.md`
- `docs/adr/0010-penn-academic-calendar-integration.md`
- `logs/historical-scrape-20251005-114937.log`
- `tests/fixtures/api_samples/`
