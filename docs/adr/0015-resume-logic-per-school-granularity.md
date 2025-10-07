# ADR-0015: Resume Logic with Per-School Granularity

**Date**: 2025-10-07
**Status**: Implemented
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)

## Context

The `scrape-historical` command was designed to support resume capability for long-running scrapes (e.g., GitHub Actions with 6-hour timeouts). However, the resume logic had a critical flaw.

## The Problem

### Current Resume Logic (BROKEN)

```python
# src/cli.py:297-307
if skip_existing:
    existing_courses = Course.select().where(term == term_code).count()
    if existing_courses > 0:
        skip_entire_term()  # ← BUG!
```

**Scenario:**
1. Start historical scrape: Fall 2024, all schools
2. Successfully scrape Annenberg (41 courses) ✅
3. Job times out after 6 hours ⏱️
4. Resume scrape: "Fall 2024 has 41 courses, skip it!" ❌
5. **Result**: Wharton, Engineering, SAS, etc. never get scraped!

### Root Cause

Resume logic checks at **term-level granularity** instead of **(term, school) granularity**.

**The scraper operates school-by-school:**
- `scrape_term()` iterates: `for school in schools: scrape_school(term, school)`
- Each school takes ~30-60 seconds
- Some schools have 1000+ courses, others have 40

**The resume logic doesn't track this:**
- Only checks: "Does this term have ANY courses?"
- Doesn't check: "Which schools for this term are complete?"

## Decision

**Implement per-school resume granularity using two complementary approaches:**

### Approach 1: ScrapeLog Tracking (Explicit)

Use the existing `ScrapeLog` model which tracks `(term, school, status)`:

```python
class ScrapeLog(BaseModel):
    term = ForeignKeyField(Term)
    school = ForeignKeyField(School)
    status = CharField()  # "completed", "failed", "running"
    courses_scraped = IntegerField()
    started_at = DateTimeField()
    completed_at = DateTimeField()
```

**Resume logic:**
```python
def is_school_complete(term_code: str, school_code: str) -> bool:
    """Check if (term, school) was already successfully scraped."""
    log = ScrapeLog.select().where(
        (ScrapeLog.term.code == term_code) &
        (ScrapeLog.school.code == school_code) &
        (ScrapeLog.status == 'completed')
    ).first()
    return log is not None
```

### Approach 2: Course Count Heuristic (Fallback)

For backwards compatibility with databases that don't have ScrapeLog entries:

```python
def has_courses_for_school(term_code: str, school_code: str) -> bool:
    """Check if we have any courses for (term, school)."""
    # Get all courses for term with code prefixes matching this school
    # E.g., Wharton = "ACCT", "BEPP", "FNCE", "LGST", "MGMT", "MKTG", "OIDD", "STAT"
    # This is imperfect but works for most cases
    count = Course.select().where(
        (Course.term.code == term_code) &
        (Course.code.startswith_any(SCHOOL_DEPT_PREFIXES[school_code]))
    ).count()
    return count > 0
```

**But wait** - mapping school codes to department prefixes is fragile. Let's use a simpler heuristic:

```python
def estimate_school_completion(term_code: str, school_code: str) -> bool:
    """
    Heuristic: If we have courses for this term, check if we scraped this school.

    Since we scrape atomically (entire school or nothing), if we have ANY courses
    for a school, we likely have ALL courses for that school.
    """
    # This is actually hard without school tracking on Course model
    # Better to just use ScrapeLog
    pass
```

**Actually, the cleanest solution:**

Just use **ScrapeLog** exclusively. If there's no ScrapeLog entry, assume incomplete.

## Implementation

### 1. Update Scraper to Write ScrapeLog

```python
# src/scraper.py - in scrape_school()
def scrape_school(self, term: str, school_code: str) -> SchoolScrapeResult:
    # Get/create School and Term objects
    term_obj = Term.get(Term.code == term)
    school_obj = School.get(School.code == school_code)

    # Create scrape log entry
    log = ScrapeLog.create(
        term=term_obj,
        school=school_obj,
        status='running',
        started_at=datetime.now()
    )

    try:
        # ... scrape courses ...

        # Update log on success
        log.status = 'completed'
        log.completed_at = datetime.now()
        log.courses_scraped = courses_saved
        log.save()

    except Exception as e:
        log.status = 'failed'
        log.error_details = str(e)
        log.save()
        raise
```

### 2. Update scrape_historical Resume Logic

```python
# src/cli.py - in scrape_historical()
for term_code in term_codes:
    # Get schools to scrape
    schools_to_scrape = school_codes or [s["code"] for s in src.types.SCHOOLS]

    # Filter out completed schools (per-school granularity!)
    if skip_existing:
        incomplete_schools = []
        for school_code in schools_to_scrape:
            if not is_school_completed(term_code, school_code):
                incomplete_schools.append(school_code)
            else:
                console.print(f"  ⏭️  Skipping {school_code} - already complete")

        if not incomplete_schools:
            console.print(f"  ⏭️  Skipping term {term_code} - all schools complete")
            continue

        schools_to_scrape = incomplete_schools

    # Scrape only incomplete schools
    result = scraper.scrape_term(
        term=term_code,
        schools=schools_to_scrape,
        ...
    )
```

### 3. Helper Function

```python
def is_school_completed(term_code: str, school_code: str) -> bool:
    """
    Check if (term, school) was successfully scraped.

    Returns:
        True if ScrapeLog shows this (term, school) as 'completed'
    """
    try:
        term_obj = src.models.Term.get(src.models.Term.code == term_code)
        school_obj = src.models.School.get(src.models.School.code == school_code)

        log = src.models.ScrapeLog.select().where(
            (src.models.ScrapeLog.term == term_obj) &
            (src.models.ScrapeLog.school == school_obj) &
            (src.models.ScrapeLog.status == 'completed')
        ).first()

        return log is not None

    except src.models.Term.DoesNotExist:
        return False  # Term doesn't exist yet
    except src.models.School.DoesNotExist:
        return False  # School doesn't exist (shouldn't happen)
```

## Consequences

### Positive

✅ **Correct resume behavior**: Resume at school-level, not term-level
✅ **Efficient**: Only re-scrape incomplete schools
✅ **Explicit tracking**: ScrapeLog shows exactly what was scraped
✅ **Debuggable**: Can query ScrapeLog to see scraping history
✅ **Idempotent**: Can re-run scrape-historical safely

### Negative

⚠️ **Backwards compatibility**: Old databases without ScrapeLog will re-scrape everything
- Mitigation: This is acceptable since we're flushing the database anyway due to schema changes

⚠️ **ScrapeLog must be atomic**: If scraper crashes mid-school, status stays "running"
- Mitigation: Check for stale "running" entries (started >24h ago)

## Testing

### Test Scenario 1: Resume After Timeout

```bash
# Scrape 2 schools
pipenv run scraper scrape 202430 -s C,W
# Manually stop after Annenberg completes

# Resume (should only scrape Wharton)
pipenv run scraper scrape 202430 -s C,W

# Verify ScrapeLog
sqlite3 courses.db "SELECT term_id, school_code, status FROM scrape_logs"
# Should show:
# 202430|C|completed
# 202430|W|completed
```

### Test Scenario 2: Historical with Resume

```bash
# Start historical scrape
pipenv run scraper scrape-historical --terms 202430,202410

# After first term completes, check ScrapeLog
sqlite3 courses.db "SELECT term_id, school_code, status, courses_scraped
                    FROM scrape_logs WHERE term_id='202430'"

# Resume (should skip 202430, scrape 202410)
pipenv run scraper scrape-historical --terms 202430,202410
```

### Test Scenario 3: Failed School Retry

```bash
# Manually set a school to 'failed'
sqlite3 courses.db "UPDATE scrape_logs
                    SET status='failed'
                    WHERE term_id='202430' AND school_code='W'"

# Re-run (should re-scrape Wharton)
pipenv run scraper scrape 202430 -s W
```

## Comparison: Before vs After

### Before (Broken)

```
Scrape Fall 2024:
  - Annenberg ✅ (41 courses)
  - Wharton ✅ (1,200 courses)
  - [timeout at 6 hours]

Resume Fall 2024:
  - Check: "Does Fall 2024 have courses?" → YES (1,241 total)
  - Skip entire term ❌
  - Engineering never scraped ❌
  - SAS never scraped ❌
```

### After (Fixed)

```
Scrape Fall 2024:
  - Annenberg ✅ (41 courses) → ScrapeLog: (202430, C, completed)
  - Wharton ✅ (1,200 courses) → ScrapeLog: (202430, W, completed)
  - [timeout at 6 hours]

Resume Fall 2024:
  - Check: "Is (Fall 2024, Annenberg) complete?" → YES, skip ✅
  - Check: "Is (Fall 2024, Wharton) complete?" → YES, skip ✅
  - Check: "Is (Fall 2024, Engineering) complete?" → NO, scrape! ✅
  - Check: "Is (Fall 2024, SAS) complete?" → NO, scrape! ✅
```

## Related ADRs

- **ADR-0014**: CRN Reuse Bug Fix - Required database flush, which necessitates full re-scrape
- **ADR-0012**: Historical Parsing - Initial historical scraping implementation

## Alternatives Considered

### Alternative 1: Track Completion Per-Term

Keep checking term-level, but also check expected course count:

```python
expected_count = get_expected_course_count(term)  # How?
actual_count = Course.select().where(term=term).count()
if actual_count >= expected_count * 0.95:  # 95% threshold
    skip_term()
```

**Rejected**: We don't know the expected count without scraping.

### Alternative 2: Course Code Prefix Heuristic

Map school codes to department prefixes:

```python
SCHOOL_DEPTS = {
    'W': ['ACCT', 'BEPP', 'FNCE', 'LGST', 'MGMT', 'MKTG', 'OIDD', 'STAT'],
    'E': ['CIS', 'CIT', 'ESE', 'MEAM', 'MSE', 'NETS'],
    # ...
}

def has_school_courses(term, school):
    for dept in SCHOOL_DEPTS[school]:
        if Course.select().where(term=term, code.startswith(dept)).count() > 0:
            return True
```

**Rejected**:
- Fragile (cross-listed courses, new departments)
- Maintenance burden (keeping mappings updated)
- ScrapeLog is explicit and reliable

### Alternative 3: Add School Foreign Key to Course

```python
class Course:
    school = ForeignKeyField(School)
```

Then check:
```python
if Course.select().where(term=term, school=school).count() > 0:
    skip_school()
```

**Rejected**:
- Requires schema migration
- Courses can be cross-listed across schools
- Adds complexity to Course model
- ScrapeLog already exists and is designed for this

## Implementation Status

- [x] Design decision
- [ ] Implement ScrapeLog tracking in scraper.py
- [ ] Update scrape_historical resume logic
- [ ] Add is_school_completed() helper
- [ ] Add tests for resume scenarios
- [ ] Update documentation

---

**Created**: 2025-10-07
**Status**: ✅ Ready for Implementation
