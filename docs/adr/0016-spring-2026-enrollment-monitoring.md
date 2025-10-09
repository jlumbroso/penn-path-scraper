# ADR-0016: Spring 2026 Advanced Registration Monitoring Strategy

**Date**: 2025-10-08
**Status**: Proposed - Implementation Required Tomorrow (Oct 9, 2025)
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Spring 2026 advanced registration opens Oct 9, 2025
**Urgency**: 🔴 HIGH - Need to start monitoring ASAP to capture enrollment dynamics

## Executive Summary

**Spring 2026 advanced registration starts tomorrow morning (Oct 9, 2025)**. This is our first opportunity to collect **longitudinal enrollment data** during the registration period.

**Goal**: Capture daily enrollment snapshots to analyze:
- Course fill rates
- High-demand courses
- Waitlist patterns
- Department popularity trends
- Time-of-day enrollment spikes

**Implementation**: Set up GitHub Actions cron job to scrape Spring 2026 daily during registration period (Oct 9 - Jan 13, 2026).

---

## Background: Why This Matters

### Previous Data Collection

**Historical terms (Fall 2023 and earlier)**:
- ❌ No enrollment data (scraped too late, after terms ended)
- ✅ Have course catalog data (descriptions, schedules, instructors)

**Recent terms (Spring 2024, Fall 2024, Spring 2025, Fall 2025)**:
- ✅ Have some enrollment snapshots
- ⚠️ Snapshots are sparse (not daily during registration)
- ⚠️ May have missed critical fill-up periods

### Spring 2026 Opportunity

**Advanced registration period**: Oct 9, 2025 - Jan 13, 2026 (14 weeks)

**What we can capture**:
1. **Day 1**: Initial rush (seniors, priority registration)
2. **Week 1-2**: Main registration wave (all undergrads)
3. **Weeks 3-14**: Course swapping, waitlist movement
4. **Dec-Jan**: Final adjustments before add/drop deadline

**Key metrics**:
- `enrolled` - Current enrollment
- `max_enrollment` - Capacity
- `seats_available` - Remaining seats
- **Fill rate** = `enrolled / max_enrollment`
- **Over-enrollment** = `enrolled > max_enrollment` (instructor permission)

---

## Registration Timeline

### Phase 1: Advanced Registration (Oct 9 - Nov 15)

**Who**: Current Penn students by class year
- Oct 9-10: Seniors (priority)
- Oct 11-12: Juniors
- Oct 13-14: Sophomores
- Oct 15-16: Freshmen

**Expected behavior**:
- **High-demand courses fill in 1-2 days** (e.g., CIS 1210, ECON 0100)
- **Waitlists form immediately** for popular courses
- **Multiple enrollments** spike (students add 5-6 courses, drop later)

**Scraping strategy**: **DAILY** during this period

### Phase 2: Adjustment Period (Nov 16 - Dec 20)

**Activity**: Course swapping, waitlist movement

**Expected behavior**:
- Gradual changes as students adjust schedules
- Waitlist → enrolled conversions
- Some courses open up as students drop

**Scraping strategy**: **Every 2-3 days**

### Phase 3: Holiday Break (Dec 21 - Jan 12)

**Activity**: Minimal changes

**Scraping strategy**: **Weekly** (maybe skip entirely)

### Phase 4: Add/Drop Period (Jan 13 - Jan 27)

**Activity**: Final adjustments before semester starts

**Expected behavior**:
- Last-minute adds/drops
- Some courses re-open
- Waitlist clears

**Scraping strategy**: **DAILY** again

---

## Implementation: GitHub Actions Cron Job

### Scrape Schedule

**File**: `.github/workflows/scrape-spring-2026.yml`

**Trigger**: Cron schedule (daily at 6 AM ET)

```yaml
name: Scrape Spring 2026 (Daily Monitoring)

on:
  schedule:
    # Run daily at 6 AM ET (10 AM UTC) during registration period
    - cron: '0 10 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install pipenv
        run: pip install pipenv

      - name: Install dependencies
        run: pipenv install

      - name: Download latest database
        run: |
          gh release download latest-data --pattern "courses.db.gz"
          gunzip courses.db.gz
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Scrape Spring 2026
        run: |
          pipenv run scraper --db courses.db scrape 202610
        env:
          PYTHONUNBUFFERED: 1

      - name: Validate database integrity
        run: |
          pipenv run validate-db --db courses.db

      - name: Verify scrape samples
        run: |
          pipenv run scraper --db courses.db verify-samples scrape-samples/scrape-samples-*.json

      - name: Upload database as release
        run: |
          gzip -f courses.db
          gh release upload latest-data courses.db.gz --clobber
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Trigger deployment
        run: |
          gh workflow run "Deploy to GitHub Pages"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload scrape samples
        uses: actions/upload-artifact@v4
        with:
          name: scrape-samples-${{ github.run_id }}
          path: scrape-samples/
          retention-days: 90
```

**Why 6 AM ET?**
- After most overnight batch jobs complete
- Before students wake up (baseline)
- Consistent time for day-over-day comparison

### Enable/Disable Schedule

**During active monitoring** (Oct 9 - Jan 27):
- Enable cron schedule

**After add/drop period** (Jan 28+):
- Disable cron (comment out schedule)
- Switch to weekly scrapes

---

## Data Collection Strategy

### What to Track

**Per scrape**:
1. **Enrollment snapshot** for EVERY course
2. **Course changes** (new courses added, cancelled courses)
3. **Scrape metadata** (timestamp, duration, error count)

**Database growth**:
- **Day 1**: ~7,000 courses with enrollment = 0
- **Week 1**: Enrollment snapshots for all courses (7,000 × 7 = 49,000 snapshots)
- **14 weeks**: Enrollment snapshots for all courses (7,000 × 98 = 686,000 snapshots)

**Storage**:
- Each snapshot: ~50 bytes (course_id, enrolled, seats_available, timestamp)
- 686,000 snapshots × 50 bytes = **34 MB** (very manageable)

### Snapshot Deduplication

**Problem**: If enrollment doesn't change, do we need a new snapshot?

**Solution**: Only create snapshot if enrollment changed

```python
# In save_course()
last_snapshot = (
    EnrollmentSnapshot
    .select()
    .where(EnrollmentSnapshot.course == course)
    .order_by(EnrollmentSnapshot.timestamp.desc())
    .first()
)

# Only create new snapshot if enrollment changed
if not last_snapshot or last_snapshot.enrolled != enrolled:
    EnrollmentSnapshot.create(
        course=course,
        enrolled=enrolled,
        seats_available=seats_available,
        timestamp=datetime.now()
    )
```

**Benefit**: Reduces snapshot count by ~50% (many courses stable after Week 1)

---

## Monitoring and Alerts

### Success Metrics

**Daily scrape should**:
1. ✅ Complete in <10 minutes
2. ✅ Scrape all 12 schools (~7,000 courses)
3. ✅ Create 0-7,000 new snapshots (depending on changes)
4. ✅ Pass validation checks (no duplicate term-CRN)
5. ✅ Pass sample verification

**Alerts if**:
- ❌ Scrape fails (API errors, network issues)
- ❌ Validation fails (CRN reuse bug detected!)
- ❌ Sample verification fails (corruption detected)
- ❌ Course count drops >10% (data loss)

### Manual Monitoring

**GitHub Actions UI**:
- Check workflow run status daily
- Review logs if failures occur

**Database checks**:
```bash
# Latest snapshot count
sqlite3 courses.db "SELECT COUNT(*) FROM enrollment_snapshots WHERE DATE(timestamp) = DATE('now')"

# Courses with enrollment > max (waitlisted)
sqlite3 courses.db "
  SELECT code, title, enrolled, max_enrollment
  FROM courses
  WHERE term_id = '202610' AND enrolled > max_enrollment
  ORDER BY (enrolled - max_enrollment) DESC
  LIMIT 20
"
```

---

## Analysis Opportunities

### 1. Fill Rate Timeline

**Visualization**: Line chart (time series)

**Metrics**:
- Average fill rate across all courses
- Fill rate by school
- Fill rate by department

**Insight**: How fast do courses fill up?

**Example**:
```
Day 1:  20% filled (priority registration)
Day 2:  45% filled (main rush)
Day 7:  75% filled (adjustment period)
Week 14: 85% filled (final state)
```

### 2. High-Demand Courses

**Metric**: Time to 100% enrollment

**Query**:
```sql
-- Courses that filled in <24 hours
SELECT c.code, c.title, MIN(es.timestamp) as filled_at
FROM courses c
JOIN enrollment_snapshots es ON es.course_id = c.id
WHERE c.term_id = '202610'
  AND es.enrolled >= c.max_enrollment
GROUP BY c.id
HAVING MIN(es.timestamp) < '2025-10-10 06:00:00'
ORDER BY filled_at;
```

**Output**:
```
CIS 1210: Data Structures - Filled in 2 hours
ECON 0100: Intro to Economics - Filled in 4 hours
MGMT 1010: Leadership - Filled in 6 hours
```

### 3. Waitlist Growth Patterns

**Metric**: `enrolled - max_enrollment` over time

**Insight**: Which courses have persistent waitlists?

**Example**:
```
CIS 1210:
  Day 1:  enrolled=120, max=120, waitlist=0
  Day 2:  enrolled=145, max=120, waitlist=25
  Week 1: enrolled=160, max=120, waitlist=40
  Week 14: enrolled=155, max=120, waitlist=35
```

### 4. Department Popularity

**Metric**: Fill rate by department

**Insight**: Which departments are over-subscribed?

**Example**:
```
CIS:  avg fill rate = 98% (high demand)
MATH: avg fill rate = 75% (moderate)
PHIL: avg fill rate = 60% (lower)
```

### 5. Time-of-Day Enrollment Spikes

**If we scrape multiple times per day**:
- Morning spike (9-11 AM): Students register during breaks
- Afternoon plateau (12-5 PM): Steady enrollment
- Evening drop (6-10 PM): Fewer changes

**Use case**: Determine optimal scrape time

---

## Database Management

### Size Projections

**Current database**: 111 MB

**After Spring 2026 monitoring**:
- +34 MB (enrollment snapshots)
- +5 MB (new courses)
- **Total**: ~150 MB (still very manageable)

**GitHub Release**: Max 2 GB per asset (we're using 0.15 GB)

### Backup Strategy

**Before starting daily scrapes**:
1. Tag current database as `pre-spring-2026`
2. Upload to separate release
3. Document how to roll back if needed

**During monitoring**:
- `latest-data` release updates daily
- GitHub Actions artifacts retain last 90 days
- Can recover from any artifact if needed

### Cleanup (Optional)

**After semester ends** (May 2026):
- Keep first snapshot (initial state)
- Keep last snapshot (final state)
- **Thin intermediate snapshots** (keep every 3rd day instead of daily)
- Reduces 98 snapshots → ~30 snapshots per course
- Saves ~60% storage while preserving trends

---

## Rollout Plan

### Day 1 (Oct 9, 2025) - **URGENT**

- [ ] Create `.github/workflows/scrape-spring-2026.yml`
- [ ] Test workflow with manual trigger
- [ ] Verify scrape completes successfully
- [ ] Enable daily cron schedule
- [ ] Monitor first run

### Week 1 (Oct 9-15)

- [ ] Monitor daily scrapes for failures
- [ ] Check enrollment snapshot growth
- [ ] Verify database integrity daily
- [ ] Identify high-demand courses (for testing)

### Week 2 (Oct 16-22)

- [ ] Analyze Week 1 data
- [ ] Identify any issues with data collection
- [ ] Adjust scrape frequency if needed
- [ ] Begin building enrollment visualizations

### Month 2 (Nov 9 onwards)

- [ ] Reduce scrape frequency to every 2-3 days
- [ ] Continue monitoring for anomalies
- [ ] Start analysis of enrollment trends

---

## Questions for Jérémie

1. **Start date**:
   - Should we start **tomorrow (Oct 9)** with daily scrapes?
   - Or wait a few days to ensure workflow is stable?

2. **Scrape frequency**:
   - Daily at 6 AM ET?
   - Or multiple times per day (e.g., 6 AM, 2 PM, 10 PM)?

3. **Snapshot deduplication**:
   - Should we only create snapshots when enrollment changes?
   - Or always create (for consistency)?

4. **Historical baseline**:
   - Should we scrape Spring 2026 NOW (before registration)?
   - To get the "empty" state (enrolled = 0 for all courses)?

5. **Post-registration**:
   - After add/drop (Jan 27), should we:
     - Stop scraping?
     - Switch to weekly scrapes (to track drops)?
     - Continue daily until semester ends?

---

## Success Criteria

By end of Spring 2026 registration (Jan 27, 2026):

1. ✅ **No missed days** during critical periods (Oct 9-16, Jan 13-27)
2. ✅ **Complete dataset**: 90+ snapshots per course
3. ✅ **Zero data corruption**: All validations pass
4. ✅ **Analysis ready**: Can answer "How fast did CIS 1210 fill up?"
5. ✅ **Visualizations deployed**: Enrollment trends visible on website

---

## Related ADRs

- **ADR-0014**: CRN Reuse Bug Fix - Ensures data integrity during monitoring
- **ADR-0015**: Non-Enrollment Visualizations - Maximizes value of historical data
- **ADR-0009**: Visualizations - Foundation for enrollment dashboards

---

**Created**: 2025-10-08
**Status**: ⏳ Awaiting implementation - **URGENT** (starts tomorrow!)
**Next Action**: Create GitHub Actions workflow and test manual trigger
