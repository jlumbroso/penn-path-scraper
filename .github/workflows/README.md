# GitHub Actions Workflows

This directory contains automated workflows for scraping and deploying Penn course data.

## Historical Scraping Workflows

### 🆕 `scrape-historical-fresh.yml` - Fresh Start

**Use when:**
- ✅ Database schema has changed (e.g., CRN reuse fix)
- ✅ Database is corrupted and needs rebuild
- ✅ You want to start completely fresh

**What it does:**
1. **Deletes** existing database artifact
2. Creates fresh database with current schema
3. Scrapes all specified terms from scratch
4. Uploads new database artifact

**Trigger:** Manual only (button in Actions tab)

**Concurrency:** Queues if another job is running (doesn't cancel)

---

### 🔄 `scrape-historical-resume.yml` - Resume/Incremental

**Use when:**
- ✅ Daily incremental scrapes (automatic cron)
- ✅ Resuming after timeout
- ✅ Continuing after manual stop

**What it does:**
1. **Downloads** existing database artifact
2. Checks `ScrapeLog` for completed (term, school) combinations
3. **Only scrapes incomplete schools** (per-school resume granularity)
4. Updates database artifact

**Trigger:**
- **Cron**: Daily at 2 AM UTC (9 PM EST / 10 PM EDT)
- **Manual**: Button in Actions tab

**Concurrency:** Skips if another job is running (cancel-in-progress)

---

## How to Use

### First Time: Fresh Scrape

1. Go to **Actions** tab in GitHub
2. Select **"Historical Scrape (Fresh Start)"**
3. Click **"Run workflow"**
4. Configure:
   - Terms: `202530,202430,202410,202330,202310,202230` (or your list)
   - Schools: Leave empty for all, or `E,W,A` for specific schools
   - Sample rate: `100` (production) or `10` (testing)
5. Click **"Run workflow"** button

This will take several hours but will complete in one run or resume automatically if it times out at 6 hours.

### Daily Updates: Automatic

The resume workflow runs **automatically every day** at 2 AM UTC. It will:
- Download the existing database
- Check which schools are incomplete
- Only scrape what's needed
- Update the artifact

### Manual Resume

If you need to manually trigger a resume:

1. Go to **Actions** tab
2. Select **"Historical Scrape (Resume/Incremental)"**
3. Click **"Run workflow"**
4. Use same settings as fresh scrape
5. Click **"Run workflow"** button

---

## Understanding the Resume Logic

### Old Logic (BROKEN) ❌
```
if (term has ANY courses):
    skip entire term
```
**Problem:** After scraping Annenberg, would skip entire Fall 2024 term!

### New Logic (FIXED) ✅
```
for each school in schools:
    if ScrapeLog shows (term, school) is completed:
        skip this school
    else:
        scrape this school
```
**Benefit:** After scraping Annenberg, only Annenberg is skipped. Wharton, Engineering, etc. still get scraped!

---

## Artifacts

### courses-database
- **Contents**: SQLite database with all scraped courses
- **Retention**: 90 days
- **Updated by**: Both workflows
- **Download**: Actions tab → Workflow run → Artifacts section

### scrape-samples-XXXXX
- **Contents**: Ground-truth samples for verification (1 in 100 courses)
- **Retention**: 30 days
- **Purpose**: Detect data corruption (see ADR-0014)

---

## Troubleshooting

### "Database artifact not found"

**On resume workflow:**
- This is OK for the first run
- It will create a fresh database

**Solution:** Run the fresh workflow first to create the initial artifact

### "Concurrency: workflow was skipped"

This means another scrape is already running. This is **intentional** to prevent conflicts.

**Solution:** Wait for the current run to finish, or cancel it if needed

### "Verification failed"

Ground-truth samples don't match database. This indicates corruption!

**Solution:**
1. Check the verification output
2. If widespread corruption, run fresh workflow
3. Report issue if CRN reuse bug has returned

### "Workflow timed out at 6 hours"

This is normal for very large scrapes.

**Solution:**
- The resume workflow will automatically continue where it left off
- Check `ScrapeLog` to see which schools completed
- Manually trigger resume workflow if needed

---

## Monitoring

### Check Progress

**View current scrape:**
1. Go to **Actions** tab
2. Click on running workflow
3. Expand "Run historical scrape" step
4. Watch real-time progress

**Check database stats:**
1. Wait for workflow to finish
2. Expand "Generate database stats" step
3. See courses per term, completed scrapes, etc.

### Query ScrapeLog

Download the database artifact and run:

```bash
sqlite3 courses.db "
  SELECT t.code, s.code, sl.status, sl.courses_scraped
  FROM scrape_logs sl
  JOIN terms t ON sl.term_id = t.id
  JOIN schools s ON sl.school_id = s.id
  ORDER BY t.code DESC, s.code
"
```

Shows which (term, school) combinations are complete.

---

## Deployment Workflow

### `deploy-landing.yml`

Automatically deploys the landing page to GitHub Pages when changes are pushed to main branch.

**Trigger:** Push to `main` branch (automatic)

**What it builds:**
- Landing page at `landing/index.html`
- Static course data exports
- Deployed to GitHub Pages

---

## Related Documentation

- **ADR-0014**: CRN Reuse Bug Fix (why fresh scrape is needed)
- **ADR-0015**: Resume Logic Per-School Granularity (how resume works)
- **docs/TESTING.md**: Testing strategies
- **README.md**: General project documentation
