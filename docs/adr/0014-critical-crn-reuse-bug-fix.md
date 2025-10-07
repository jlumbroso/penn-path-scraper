# ADR-0014: Critical CRN Reuse Bug and Database Schema Fix

**Date**: 2025-10-06
**Status**: CRITICAL - Requires Immediate Fix
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Data corruption discovered after historical scraping
**Severity**: 🔴 **CRITICAL** - Historical data is corrupted and unreliable

## Executive Summary

**THE BUG**: Penn reuses Course Reference Numbers (CRNs) every semester. Our database uses CRN as the sole primary key, causing courses from different terms to **overwrite each other** when scraped. Fall 2025 scraped 6,535 courses, but only 2,268 are correctly tagged - the other 4,267 are mislabeled with historical term IDs.

**THE IMPACT**: All historical course data is unreliable. Term-by-term analytics are corrupted. Enrollment snapshots may be associated with wrong terms.

**THE FIX**: Change primary key to composite `(term, crn)` and rebuild database from clean scrapes or recover from unmigrated databases.

---

## The Discovery

After the successful historical scrape on 2025-10-06 that completed 16 terms cleanly, GPT-5 analysis revealed a catastrophic discrepancy:

```
Expected: 6,535 Fall 2025 courses (per scraper logs)
Actual:   2,268 courses with term_id=202530 (Fall 2025)
Missing:  4,267 courses
```

**Where are the missing 4,267 courses?**

SQLite query revealed they exist in the database but are **mislabeled with wrong term IDs**:
- 4,254 courses tagged as `term_id=202430` (Fall 2024)
- 8 courses tagged as `term_id=202330` (Fall 2023)
- 5 courses tagged as `term_id=202230` (Fall 2022)

All these mis-tagged courses have `last_scraped` timestamps of `2025-10-06 12:30-14:07` - **the exact time window of the Fall 2025 scrape**.

This means: **Fall 2025 course data overwrote historical course records but kept the old term foreign keys**.

---

## Root Cause Analysis

### The Schema Design Flaw

**src/models.py:64**:
```python
class Course(BaseModel):
    # Primary identifiers
    crn = peewee.CharField(primary_key=True)  # ← THE BUG
    term = peewee.ForeignKeyField(Term, backref="courses", on_delete="CASCADE")
```

**The comment says**: "Course Reference Number (unique per term)"
**The reality is**: CRN is the SOLE primary key, not `(term, crn)`

### How Penn's CRN System Works

Penn's course registration system **reuses CRNs every semester**:

| Term | CRN | Course | Instructor |
|------|-----|--------|------------|
| Fall 2025 | 60563 | BE 1000-001 | John Smith |
| Fall 2024 | 60563 | CIS 1210-001 | Jane Doe |
| Spring 2024 | 60563 | MATH 1400-001 | Bob Johnson |

The **same CRN** (60563) refers to **completely different courses** in different terms.

### The Persistence Layer Bug

**src/persistence.py:131-132**:
```python
course, created = src.models.Course.get_or_create(
    crn=course_dict["crn"],  # ← Only looks up by CRN, ignoring term
    defaults={
        "term": term,  # ← Only sets term when CREATING new record
        # ... other fields ...
    },
)
```

**What happens when scraping a course with a reused CRN**:

1. **Lookup**: `get_or_create(crn="60563")` searches ONLY by CRN
2. **Found**: Returns existing record from Fall 2024 (different term!)
3. **Update**: Lines 167-196 update ALL fields (title, enrollment, etc.)
4. **Critical omission**: `course.term` is **NEVER updated**

Result: Fall 2025 data overwrites Fall 2024 data, but the record still points to `term_id=202430` (Fall 2024).

### Concrete Example

**Database state before scraping Fall 2025**:
```sql
crn    term_id  code         title                 last_scraped
60563  202430   CIS 1210     Data Structures       2024-09-15
```

**What should happen**:
```sql
-- Old record preserved
60563  202430   CIS 1210     Data Structures       2024-09-15

-- New record created
60563  202530   BE 1000      Intro to Bioengineering   2025-10-06
```

**What actually happens**:
```sql
-- Old record MUTATED with new data but old term_id
60563  202430   BE 1000      Intro to Bioengineering   2025-10-06
         ^^^^^ ← WRONG TERM! This is Fall 2025 data!
```

---

## Scope of Data Corruption

### Affected Records

From the historical scrape on 2025-10-06:

| Term ID | Term Name | Records with Fall 2025 Data | Should Be |
|---------|-----------|---------------------------|-----------|
| 202530 | Fall 2025 | 2,268 (correct) | 6,535 |
| 202430 | Fall 2024 | 4,254 (corrupted) | 0 |
| 202330 | Fall 2023 | 8 (corrupted) | 0 |
| 202230 | Fall 2022 | 5 (corrupted) | 0 |

**Total**: 4,267 out of 6,535 Fall 2025 courses (65%) are mislabeled.

### Impact on Historical Data

**Every historical term that shares CRNs with Fall 2025 is now corrupted**:

1. **Fall 2024 (202430)**:
   - Original course count: 6,519 (as of earlier scrape)
   - Current state: Mix of real Fall 2024 courses + 4,254 Fall 2025 courses
   - **Cannot distinguish** which is which without checking `last_scraped` timestamps

2. **Fall 2023 (202330)**: 8 courses overwritten
3. **Fall 2022 (202220)**: 5 courses overwritten

**The cascading effect**: If we scrape Spring 2025 next, it will overwrite Fall 2025 data, which already overwrote Fall 2024 data. Each scrape **amplifies the corruption**.

### Impact on Related Tables

**EnrollmentSnapshot**:
- Snapshots are linked to `course_id` via foreign key
- If a course record gets its data overwritten, **enrollment snapshots now point to the wrong term**
- Example: Fall 2024 enrollment snapshots may now be associated with a record containing Fall 2025 data

**Meeting**:
- Meeting times are linked to courses via foreign key
- Overwritten courses lose their original meeting data
- Cannot reconstruct historical room assignments or schedules

**CourseInstructor**:
- Instructor assignments are linked to courses
- Overwritten courses lose their original instructor associations
- Historical teaching records are corrupted

---

## Why This Happened (The Rookie Mistake)

### Classic Database Design Error

This is a **textbook case** of choosing the wrong primary key:

❌ **Wrong**: Single-column primary key on non-unique field
✅ **Correct**: Composite primary key on `(term, crn)`

The comment in src/models.py:64 reveals the misunderstanding:
```python
crn = peewee.CharField(primary_key=True)  # Course Reference Number (unique per term)
```

CRNs are only unique **within** a term, not **across** terms. The primary key should enforce this constraint.

### How It Went Undetected

1. **Early testing scraped only one term** (Fall 2025):
   - All CRNs were new → no collisions → appeared to work

2. **Export and visualizations looked correct**:
   - When Fall 2025 is scraped first, all 6,535 records have correct term IDs
   - exports (`fall2025-courses-orig.db`) showed 6k+ courses

3. **Historical scraping revealed the bug**:
   - Scraping Fall 2024 AFTER Fall 2025 caused CRN collisions
   - Fall 2024 data overwrote Fall 2025 data
   - Fall 2025 data moved to Fall 2024's term ID
   - Only noticed when comparing course counts

### Why It's "My Bad" (Jérémie)

> "It's my bad for not catching it sooner — a rookie mistake!"

This reflects:
1. Not testing multi-term scenarios early
2. Trusting CRN uniqueness without verifying Penn's reuse policy
3. Not adding integration tests that scrape multiple overlapping terms
4. Not validating course counts after each scrape

---

## Can the Data Be Recovered?

### Assessment: **Partial Recovery Possible**

#### What's Lost Forever
- ❌ **Pure historical database**: Once courses are overwritten, original values are gone
- ❌ **First-pass historical data**: If Fall 2024 was scraped first, then overwritten by Fall 2025, we can't recover Fall 2024

#### What Can Be Recovered

✅ **From unmigrated databases**:
- `fall2025-courses-orig.db`: Has correct Fall 2025 data (6,535 courses)
- `biggest.old.courses.db`: Has earlier snapshot before corruption
- These can be merged to reconstruct a clean database

✅ **From timestamps and metadata**:
```python
# Courses with last_scraped in Fall 2025 scrape window belong to Fall 2025
SELECT crn, term_id, code, last_scraped
FROM courses
WHERE last_scraped BETWEEN '2025-10-06 12:30:00' AND '2025-10-06 14:07:00'
```

✅ **From meeting dates**:
```python
# Match meeting dates to term dates
SELECT c.crn, c.term_id, m.start_date, m.end_date
FROM courses c
JOIN meetings m ON m.course_id = c.crn
WHERE m.start_date >= '2025-08-26'  -- Fall 2025 start
```

✅ **From course start/end dates**:
```python
# Match course dates to term dates
SELECT crn, term_id, start_date, end_date
FROM courses
WHERE start_date >= '2025-08-26' AND end_date <= '2025-12-08'
```

### Recovery Strategy

**Option A: Rebuild from Unmigrated Databases** (RECOMMENDED)
1. Extract correct Fall 2025 data from `fall2025-courses-orig.db`
2. Extract correct historical data from `biggest.old.courses.db`
3. Apply the schema fix (composite primary key)
4. Import each term separately with new schema
5. Validate course counts match original scrape logs

**Option B: Forensic Term Reassignment**
1. Use `last_scraped` timestamps to identify scrape windows
2. Match courses to terms based on:
   - Meeting start/end dates
   - Course start/end dates
   - Enrollment snapshot timestamps
3. Update `term_id` for mis-tagged courses
4. Validate by comparing to scrape log counts

**Option C: Clean Re-scrape** (SIMPLEST but loses historical data)
1. Apply the schema fix
2. Create new database from scratch
3. Re-scrape all terms (if API still provides historical data)
4. Note: API may not return Spring 2022 and earlier (already observed)

---

## The Fix

### Schema Changes Required

**Before** (src/models.py:54-65):
```python
class Course(BaseModel):
    # Primary identifiers
    crn = peewee.CharField(primary_key=True)  # ← BUG: Not truly unique
    term = peewee.ForeignKeyField(Term, backref="courses", on_delete="CASCADE")
```

**After** (Recommended):
```python
class Course(BaseModel):
    # Surrogate primary key
    id = peewee.AutoField(primary_key=True)

    # Natural key: (term, crn) is unique
    crn = peewee.CharField(index=True)  # NOT primary_key
    term = peewee.ForeignKeyField(Term, backref="courses", on_delete="CASCADE")

    class Meta:
        table_name = "courses"
        indexes = (
            # Enforce uniqueness on (term, crn)
            (("term", "crn"), True),  # True = UNIQUE constraint
        )
```

**Alternative** (Composite Primary Key):
```python
class Course(BaseModel):
    # Composite primary key
    crn = peewee.CharField()
    term = peewee.ForeignKeyField(Term, backref="courses", on_delete="CASCADE")

    class Meta:
        table_name = "courses"
        primary_key = peewee.CompositeKey('term', 'crn')
```

**Why surrogate ID is better**:
- ✅ Simpler foreign key references (single column)
- ✅ Easier to work with in ORMs
- ✅ More flexibility if we need to change natural key later
- ✅ Standard practice in modern database design

### Persistence Layer Changes

**Before** (src/persistence.py:131-132):
```python
course, created = src.models.Course.get_or_create(
    crn=course_dict["crn"],  # ← Only CRN, ignores term
    defaults={...}
)
```

**After**:
```python
course, created = src.models.Course.get_or_create(
    term=term,
    crn=course_dict["crn"],  # ← Composite lookup
    defaults={...}
)

# Update block MUST include term assignment
if not created:
    course.term = term  # ← CRITICAL: Update term if record reused
    course.code = course_dict["code"]
    # ... rest of updates ...
    course.save()
```

### Migration Script Required

**New script**: `scripts/migrate_composite_primary_key.py`

```python
def migrate_to_composite_key(old_db_path: str, new_db_path: str):
    """
    Migrate from single CRN key to (term, crn) composite.

    Strategy:
    1. Create new database with fixed schema
    2. Copy terms table
    3. Copy courses with validation:
       - Check for CRN collisions within same term (shouldn't exist)
       - Preserve all courses (no data loss)
    4. Copy related tables (meetings, instructors, etc.)
    5. Validate counts match
    """
```

---

## Implementation Plan

### Phase 1: Stop the Bleeding (IMMEDIATE)
- [ ] **Halt all scraping** until fix is deployed
- [ ] Document current database state
- [ ] Back up all existing databases (courses.db, old.courses.db, etc.)
- [ ] Tag current git commit as `pre-crn-fix`

### Phase 2: Schema Fix (WEEK 1)
- [ ] Update `src/models.py` with surrogate ID + unique constraint
- [ ] Update `src/persistence.py` to use composite lookup
- [ ] Add `course.term = term` to update block
- [ ] Write migration script
- [ ] Add integration test: scrape two terms with overlapping CRNs

### Phase 3: Data Recovery (WEEK 1-2)
- [ ] Implement recovery script using unmigrated databases
- [ ] Validate recovered data:
  - Course counts per term match scrape logs
  - Enrollment snapshots align with correct terms
  - Meeting dates align with term dates
- [ ] Generate comparison report: old DB vs recovered DB

### Phase 4: Testing (WEEK 2)
- [ ] Unit tests for new persistence logic
- [ ] Integration test: scrape Fall 2024, then Fall 2025
- [ ] Verify CRN 60563 creates TWO records, not one overwritten record
- [ ] Test enrollment snapshot associations

### Phase 5: Re-scrape and Deploy (WEEK 3)
- [ ] Clean re-scrape with fixed schema
- [ ] Validate all term counts
- [ ] Export to JSON with new data
- [ ] Deploy updated visualizations
- [ ] Monitor for any issues

---

## Validation Criteria

### Success Metrics

1. **Schema Validation**:
   ```sql
   -- Should NOT be possible (unique constraint violation)
   INSERT INTO courses (term_id, crn, ...) VALUES (202530, '60563', ...);
   INSERT INTO courses (term_id, crn, ...) VALUES (202530, '60563', ...);
   ```

2. **Multi-Term CRN Validation**:
   ```sql
   -- Should have multiple records for same CRN
   SELECT COUNT(*) FROM courses WHERE crn = '60563';
   -- Expected: >= 2 (one per term that used this CRN)
   ```

3. **Course Count Validation**:
   ```sql
   SELECT term_id, COUNT(*) FROM courses GROUP BY term_id;
   -- Fall 2025 (202530): 6,535 (from scrape log)
   -- Fall 2024 (202430): 6,519 (from original scrape)
   ```

4. **Term Foreign Key Validation**:
   ```sql
   -- No orphaned term references
   SELECT c.crn, c.term_id, t.code
   FROM courses c
   LEFT JOIN terms t ON c.term_id = t.id
   WHERE t.id IS NULL;
   -- Expected: 0 rows
   ```

5. **Enrollment Snapshot Alignment**:
   ```sql
   -- Snapshots should be within term date range
   SELECT c.crn, c.term_id, t.start_date, t.end_date,
          MIN(es.timestamp), MAX(es.timestamp)
   FROM courses c
   JOIN terms t ON c.term_id = t.id
   JOIN enrollment_snapshots es ON es.course_id = c.id
   GROUP BY c.crn, c.term_id
   HAVING MIN(es.timestamp) < t.start_date
      OR MAX(es.timestamp) > t.end_date;
   -- Expected: 0 rows (all snapshots within term dates)
   ```

---

## Related Issues and ADRs

### Related ADRs
- **ADR-0001**: Database Schema Design (this fixes a fundamental flaw)
- **ADR-0007**: Course Sections and Enrollment Counting (affected by data corruption)
- **ADR-0012**: Fixing Historical Parsing (historical scrape revealed this bug)

### Historical Context

**Why wasn't this caught earlier?**
1. Early development focused on single-term scraping (Fall 2025)
2. Export and visualization testing used single-term databases
3. No integration tests for multi-term scenarios
4. Trusted CRN uniqueness without verifying Penn's reuse policy

**Prior evidence we missed**:
- Comment in src/models.py:64 says "unique per term" but schema doesn't enforce it
- No unique constraint on `(term, crn)` in original schema
- No validation logic to detect CRN collisions

---

## Lessons Learned

### Database Design Principles Violated

1. **Primary keys must enforce actual uniqueness**
   - CRNs are only unique within a term, not globally
   - Should have used composite key from day 1

2. **Comments are not constraints**
   - The comment "unique per term" should have been a UNIQUE constraint
   - Database should enforce invariants, not documentation

3. **Test with realistic scenarios early**
   - Should have scraped 2+ terms in initial testing
   - Multi-term integration test would have caught this immediately

4. **Validate data after operations**
   - Should have checked: "Did we actually insert 6,535 courses?"
   - Course count discrepancy would have raised alarm

### Process Improvements

1. **Schema Review Checklist**:
   - [ ] Primary key enforces true uniqueness
   - [ ] Foreign keys have appropriate cascades
   - [ ] Unique constraints match business logic
   - [ ] Indexes support common queries

2. **Integration Testing Requirements**:
   - [ ] Multi-term scraping scenarios
   - [ ] CRN collision detection
   - [ ] Data validation after each scrape
   - [ ] Course count verification

3. **Monitoring and Alerts**:
   - [ ] Log course counts per term after scrape
   - [ ] Alert if counts decrease unexpectedly
   - [ ] Validate foreign key consistency

---

## Impact Assessment

### Data Quality
- ⚠️ **Current database**: UNRELIABLE for multi-term analysis
- ⚠️ **Historical exports**: Only valid if scraped before corruption
- ✅ **Unmigrated databases**: Still valid, can be used for recovery

### Analytics and Visualizations
- ❌ **Term-by-term comparisons**: INVALID (courses assigned to wrong terms)
- ❌ **Enrollment trends**: UNRELIABLE (snapshots may be in wrong terms)
- ❌ **Historical instructor data**: CORRUPTED (associations overwritten)
- ✅ **Single-term analysis**: OK if using unmigrated database

### Production Impact
- 🔴 **Cannot deploy current database** to production
- 🔴 **Must fix schema before** next scrape
- 🟡 **Can use unmigrated databases** for temporary deployment
- 🟢 **No impact on live API** (Penn's API is unaffected)

---

## Questions for Jérémie

1. **Recovery preference**:
   - Option A (rebuild from unmigrated DBs)?
   - Option B (forensic reassignment)?
   - Option C (clean re-scrape)?

2. **Urgency**:
   - Should I implement the fix immediately?
   - Or document first, implement later?

3. **Unmigrated databases**:
   - Do you have unmigrated versions for Fall 2024, Fall 2023?
   - Or only Fall 2025?

4. **Historical data priority**:
   - How critical is it to recover Fall 2024 data?
   - Or can we accept clean re-scrape (loses historical snapshots)?

---

## Conclusion

This is a **critical database design flaw** that corrupts historical data through CRN reuse. The bug is well-understood, fixable, and partially recoverable.

**Immediate action required**:
1. Stop scraping until fix is deployed
2. Implement schema fix (surrogate ID + unique constraint)
3. Update persistence logic to use composite lookup
4. Recover data from unmigrated databases
5. Add integration tests to prevent regression

**The silver lining**: We caught this relatively early (16 terms scraped) and have unmigrated databases for recovery. The fix is straightforward and will make the system robust for future multi-term scraping.

---

## Prevention Strategy: Never Let This Happen Again

After 4-5 failed attempts at historical scraping, we need systemic changes to prevent similar mistakes.

### 1. Schema-Level Protections (IMPLEMENTED)

**Fix**: Composite unique constraint on `(term, crn)`

```python
class Course(BaseModel):
    id = peewee.AutoField(primary_key=True)
    crn = peewee.CharField(index=True)  # NOT primary key
    term = peewee.ForeignKeyField(Term, ...)

    class Meta:
        indexes = (
            # Database enforces uniqueness - can't violate even with buggy code
            (("term", "crn"), True),  # UNIQUE constraint
        )
```

**Why this prevents the bug**:
- ✅ **Database rejects** duplicate (term, crn) combinations
- ✅ **Code cannot accidentally** create duplicates
- ✅ **Explicit error** if persistence logic is wrong
- ✅ **Self-documenting** - schema shows intent

**File**: src/models.py:67-127

### 2. Persistence Layer Safeguards (IMPLEMENTED)

**Fix**: Composite lookup in `get_or_create()`

```python
# BEFORE (buggy):
course, created = Course.get_or_create(crn=crn, defaults={...})

# AFTER (correct):
course, created = Course.get_or_create(
    term=term,        # ← Include term in lookup
    crn=crn,          # ← Composite key
    defaults={...}
)

if not created:
    course.term = term  # ← Defensive: ensure term is correct
    course.save()
```

**Why this prevents the bug**:
- ✅ **Lookup uses both** term and CRN
- ✅ **Creates separate records** for same CRN in different terms
- ✅ **Defensive term update** catches edge cases
- ✅ **Clear intent** in code comments

**File**: src/persistence.py:131-171

### 3. Integration Testing (IMPLEMENTED)

**Fix**: Test CRN reuse across multiple terms

```python
def test_crn_reuse_creates_separate_records(temp_db):
    """
    Scenario:
    - Fall 2024: CRN 60563 = CIS 1210
    - Fall 2025: CRN 60563 = BE 1000 (different course, same CRN)

    Expected: 2 separate records, no corruption
    """
```

**Test coverage**:
- ✅ Same CRN in different terms → separate records
- ✅ Same CRN in same term → updates existing record
- ✅ Database unique constraint prevents duplicates
- ✅ CRN can repeat across 4+ terms

**File**: tests/integration/test_crn_reuse.py

### 4. Ground-Truth Sampling (IMPLEMENTED) 🔴 KEY FIX

**The Problem with Validation**: All post-hoc validations are circular reasoning!
- Scraper log says "saved 6535" but database has 2268 → which is truth?
- CRN reuse distribution only works AFTER you have 2+ terms
- Term isolation only works if you scrape incrementally
- Expected counts assume scraper logs are correct (they're not if bug is active!)

**The Real Solution**: Ground-truth sampling DURING insertion

```python
# During scraping, BEFORE inserting to database:
1. Randomly sample 1/100 courses
2. Write samples to JSON file OUTSIDE database (ground truth)
3. After scraping, verify samples are in database with correct data
4. If sample says "Term 202530, CRN 60563" but DB has "Term 202430, CRN 60563"
   → CORRUPTION DETECTED!
```

**Why This Works**:
- ✅ **External truth**: Samples stored OUTSIDE database, can't be corrupted
- ✅ **Database ID**: Each database gets unique ID, prevents checking wrong database
- ✅ **Works on first scrape**: Doesn't require multiple terms or baselines
- ✅ **Catches bug immediately**: Not weeks later when comparing terms
- ✅ **Non-circular**: Samples are captured before insertion, independent of database state

**Usage**:
```bash
# Scraping automatically samples 1/100 courses
pipenv run scraper scrape 202530

# Saves samples to: scrape-samples/scrape-samples-20251006-123456-{db_id}.json

# Verify samples match database
pipenv run scraper verify-samples scrape-samples/scrape-samples-*.json
```

**Verification Output**:
```
📊 SUMMARY
  Total samples: 65
  ✅ Verified:   65 (100.0%)
  ❓ Missing:    0 (0.0%)
  ⚠️  Mismatched: 0 (0.0%)
  🔴 CORRUPTED:  0 (0.0%)

✅ ALL SAMPLES VERIFIED - DATABASE IS CORRECT
```

**If Bug Active**:
```
🔴 CORRUPTION DETECTED!
  CRN 60563: Expected in 202530 (BE 1000) but is in 202430 (CIS 1210)
  CRN 70234: Expected in 202530 (PHYS 150) but is in 202430 (MATH 240)
  ... and 43 more

❌ DATABASE IS CORRUPTED - CRN REUSE BUG DETECTED
```

**Files**:
- src/scrape_verification.py - Sampling and verification logic
- src/persistence.py:128 - Sample courses during insertion
- src/cli.py:138,260 - Initialize sampling
- src/cli.py:181,359 - Save samples after scraping
- src/cli.py:926-975 - Verify-samples command

### 5. Additional Validations (IMPLEMENTED)

**Secondary checks** (help but not sufficient alone):

1. ✅ **CRN reuse distribution** - with 2+ terms, expect >10% reuse
2. ✅ **Term isolation** - scraping Term B doesn't update Term A
3. ✅ **No orphaned courses** - all have valid term foreign keys
4. ✅ **Date alignment** - courses within term dates

**Files**:
- src/validation.py - Validation logic
- src/cli.py:854-923 - Validate command

### 6. Process Changes (MANDATORY)

**Scraping workflow checklist**:

```bash
# 1. Scrape a term (automatically samples 1/100 courses)
pipenv run scraper scrape 202530

# 2. IMMEDIATELY verify samples (THE KEY CHECK!)
pipenv run scraper verify-samples scrape-samples/scrape-samples-*.json

# 3. If verification passes, data is correct
#    If verification fails → CORRUPTION DETECTED, fix required

# 4. Optional: Run additional validations
pipenv run validate
```

**What makes this work**:
- ✅ Step 2 compares database to ground truth captured BEFORE insertion
- ✅ Non-circular: samples are independent of database state
- ✅ Works on first scrape (doesn't need multiple terms)
- ✅ If samples show Term A but DB has Term B → immediate corruption detection

**Historical scraping workflow**:

```bash
# 1. Start historical scrape
pipenv run scraper scrape-historical

# 2. After completion, validate ALL terms
pipenv run validate

# 3. Check for anomalies in the report
# Look for: unexpected counts, date misalignments, etc.

# 4. Before deploying, spot-check a few CRNs
sqlite3 courses.db "SELECT term_id, crn, code, title
                    FROM courses
                    WHERE crn = '60563'
                    ORDER BY term_id DESC;"

# Expected: Multiple rows (one per term), different courses
```

### 7. Documentation Requirements

**Every schema change must**:
1. ✅ Update model docstrings with assumptions
2. ✅ Add comments explaining WHY constraints exist
3. ✅ Update ADR with rationale
4. ✅ Add integration test demonstrating correct behavior

**Example from this fix**:
```python
class Course(BaseModel):
    """
    IMPORTANT: CRNs are reused across terms by Penn. The unique identifier
    is the combination (term, crn), not crn alone.
    """
    # ... rest of model
```

### 8. Code Review Checklist

**Before merging persistence layer changes**:
- [ ] Does the lookup use ALL natural key fields?
- [ ] Are there unique constraints in the schema?
- [ ] Is there an integration test with realistic scenarios?
- [ ] Does validation catch if this breaks?
- [ ] Would a beginner understand the code comments?

### 9. Monitoring and Alerts

**After deployment, monitor**:
- Course count trends (should grow or stay stable, not shrink)
- Validation failures (should be zero)
- CRN collision attempts (should trigger unique constraint errors)

**Future improvement**: Add automated alerts
```python
# After each scrape
validation_result = run_all_validations()
if not validation_result:
    send_alert("Database validation failed! Check logs.")
```

---

## Summary: What We Built

| Layer | Protection | File | Status |
|-------|-----------|------|--------|
| **Schema** | UNIQUE(term, crn) constraint | src/models.py | ✅ Implemented |
| **Persistence** | Composite lookup | src/persistence.py | ✅ Implemented |
| **Sampling** 🔴 KEY | Ground-truth sampling (1/100) | src/scrape_verification.py | ✅ Implemented |
| **Verification** 🔴 KEY | Verify samples match database | src/cli.py verify-samples | ✅ Implemented |
| **Testing** | CRN reuse integration tests | tests/integration/test_crn_reuse.py | ✅ Implemented |
| **Validation** | Secondary checks | src/validation.py | ✅ Implemented |
| **Workflow** | Mandatory sample verification | This ADR | ✅ Documented |

---

## Next Steps

1. **Delete corrupted database** (`courses.db`)
2. **Create fresh database** with new schema
3. **Run historical scrape** with fixes in place
4. **Validate after EACH term** is scraped
5. **Before declaring success**, manually verify:
   ```sql
   -- Should show multiple terms for same CRN
   SELECT term_id, crn, code, title FROM courses WHERE crn = '60563';
   ```

---

**Created**: 2025-10-06
**Updated**: 2025-10-06
**Status**: ✅ IMPLEMENTED - Ready for testing
