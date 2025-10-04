# Workflow Separation and Deployment Architecture

* Status: accepted
* Deciders: Jérémie Lumbroso, Claude Sonnet 4.5 (with strategic insights from GPT-5 Thinking)
* Date: 2025-10-04

Technical Story: After deploying landing page enhancements and API fixes, we identified critical inefficiencies in deployment workflows: landing page changes were triggering expensive 2.5-hour scraper runs, and lack of concurrency control could lead to overlapping scrapes.

## Context and Problem Statement

The Penn Path Scraper has two distinct deployment concerns:

1. **Landing page updates**: HTML/CSS/JS changes for user-facing documentation and visualization
2. **Data scraping**: 2.5-hour process to scrape Penn's course catalog and update database + JSON API

Initially, both were coupled in a single workflow, causing several problems:
- Any change to landing page files triggered full 2.5-hour scrape
- No way to test landing page fixes without waiting 2.5 hours
- Manual workflow triggers could overlap with scheduled cron jobs
- Concurrent 2.5-hour scrapes could conflict (database locks, resource waste)

How should we structure GitHub Actions workflows to:
- Allow independent deployment of landing page updates (seconds, not hours)
- Prevent landing page changes from triggering data scraping
- Prevent concurrent scrape runs from overlapping
- Maintain data consistency across deployments
- Keep workflows simple and maintainable

## Decision Drivers

* **User feedback**: "Can we update the landing part of the project without rerunning the scraper? It took 2h30 and I don't want to wait that long to double check the fixes work" (Jérémie, after discovering path mismatch bugs)
* **Expensive scrapes**: 2.5-hour runtime makes iteration on landing page impossible
* **Concurrency risk**: Manual triggers + cron schedule could cause overlapping runs
* **Logical separation**: Landing page is presentation layer; scraping is data layer
* **Fast iteration needs**: Fixing HTML/CSS bugs should deploy in seconds, not hours
* **Resource efficiency**: Don't waste GitHub Actions minutes on unnecessary scrapes
* **Data consistency**: Overlapping scrapes could corrupt database

## Considered Options

1. **Two separate workflows with path filters** (deploy-landing.yml + scrape.yml)
2. **Single workflow with conditional jobs**
3. **Status quo** (single workflow, all changes trigger scrape)

## Decision Outcome

Chosen option: **"Two separate workflows with path filters and concurrency control"**, because it:
- Provides complete separation of concerns (landing vs data)
- Enables 30-second landing page deployments vs 2.5-hour scrapes
- Uses GitHub's path filters to prevent cross-triggering
- Adds concurrency control to prevent overlapping scrapes
- Keeps each workflow simple and focused
- Allows independent manual triggers for each concern

### Positive Consequences

* **Fast iteration**: Landing page changes deploy in ~30 seconds
* **No wasted resources**: Landing changes don't trigger scrapes
* **Concurrency safety**: `cancel-in-progress: true` prevents overlapping scrapes
* **Clear separation**: Each workflow has single responsibility
* **Easy debugging**: Workflow failures are isolated to their concern
* **Flexibility**: Can trigger landing deployment OR scrape independently

### Negative Consequences

* **Two workflows to maintain**: Slightly more YAML to manage (but worth it)
* **Coordination needed**: Both workflows must preserve data properly (API JSON, database)
* **Documentation overhead**: Must explain workflow separation to contributors

## Pros and Cons of the Options

### Two Separate Workflows (chosen)

**Structure:**
- `.github/workflows/deploy-landing.yml` - Fast landing page deployments
- `.github/workflows/scrape.yml` - Data scraping and API generation

* Good, because **dramatic speed improvement**: 30 seconds vs 2.5 hours for landing changes
* Good, because **clear separation of concerns**: Presentation vs data
* Good, because **independent triggers**: Can deploy landing OR run scrape separately
* Good, because **path filters prevent cross-triggering**: Landing changes don't run scrape
* Good, because **concurrency control** prevents overlapping scrapes
* Good, because **easier to reason about**: Each workflow has one job
* Good, because **faster debugging**: Know exactly which workflow failed
* Bad, because **two files to maintain** (but both are simple)
* Bad, because **must preserve data carefully** in both workflows

**Implementation:**

`deploy-landing.yml` triggers:
```yaml
on:
  workflow_dispatch:  # Manual trigger
  push:
    branches: [main]
    paths:
      - 'landing/**'
      - 'api/index.html'
```

`scrape.yml` triggers with paths-ignore:
```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - '.github/workflows/scrape.yml'
      - 'src/**'
      - 'Pipfile*'
    paths-ignore:
      - 'landing/**'
      - 'api/index.html'
      - 'docs/**'
      - '**.md'
```

Concurrency control:
```yaml
concurrency:
  group: scrape
  cancel-in-progress: true
```

### Single Workflow with Conditional Jobs

Keep one workflow but use job-level `if` conditions based on changed files.

* Good, because only one workflow file
* Bad, because **complex conditional logic** (hard to read and debug)
* Bad, because **still runs workflow** even if jobs skip (shows as "success" confusingly)
* Bad, because **no concurrency control** for specific job types
* Bad, because **harder to trigger independently** (need to pass inputs)
* Bad, because **mixed concerns** in one workflow make it harder to understand

Example (rejected approach):
```yaml
jobs:
  scrape:
    if: contains(github.event.head_commit.modified, 'src/')

  deploy-landing:
    if: contains(github.event.head_commit.modified, 'landing/')
```

### Status Quo (single workflow)

Keep existing single workflow that always runs both scrape and deploy.

* Good, because simplest to understand initially
* Bad, because **2.5 hour wait** to test landing page changes
* Bad, because **wasted resources** (GitHub Actions minutes, energy)
* Bad, because **no concurrency protection** (overlapping scrapes possible)
* Bad, because **poor developer experience** (can't iterate on UI)
* Bad, because **coupling** of unrelated concerns

## Implementation Details

### Deploy Landing Page Workflow

File: `.github/workflows/deploy-landing.yml`

**Purpose**: Deploy landing page updates quickly without touching data.

**Key features:**
- Restores existing API data from gh-pages (preserves scraped JSON)
- Deploys only landing page files
- Runs in ~30 seconds
- Auto-triggers on landing/** changes

```yaml
steps:
  - name: Download latest API data from gh-pages
    run: |
      git clone --branch gh-pages --single-branch \
        https://github.com/${{ github.repository }}.git gh-pages-content || true
      mkdir -p ./deploy
      if [ -d "gh-pages-content/api" ]; then
        cp -r gh-pages-content/api ./deploy/
      fi

  - name: Copy landing page
    run: |
      cp -r ./landing/* ./deploy/
      if [ -f "api/index.html" ]; then
        cp api/index.html ./deploy/api/
      fi

  - name: Deploy to GitHub Pages
    uses: peaceiris/actions-gh-pages@v4
```

### Scrape Workflow Updates

File: `.github/workflows/scrape.yml`

**Key additions:**

**1. Concurrency control** (GPT-5 Thinking's critical insight):
```yaml
concurrency:
  group: scrape
  cancel-in-progress: true
```

**Why critical:**
- Scrape runs for 2.5 hours
- Cron schedule: daily at 6 AM UTC
- Manual triggers possible
- Without concurrency control: manual trigger at 5:59 AM + cron at 6:00 AM = 2 concurrent scrapes
- With concurrency control: second trigger cancels first (prevents database conflicts)

**2. Path filters** to prevent landing changes from triggering:
```yaml
paths:
  - '.github/workflows/scrape.yml'  # Workflow changes should trigger
  - 'src/**'                         # Python source changes should trigger
  - 'Pipfile*'                       # Dependency changes should trigger
paths-ignore:
  - 'landing/**'                     # Landing changes should NOT trigger
  - 'api/index.html'                 # API landing page should NOT trigger
  - 'docs/**'                        # Documentation should NOT trigger
  - '**.md'                          # Markdown files should NOT trigger
```

**3. Database storage** (see ADR-0005):
- Removed database from gh-pages deployment
- Deploy only JSON API to Pages
- Database handled separately via Releases

```yaml
- name: Prepare deployment directory (JSON only)
  run: |
    mkdir -p ./deploy
    cp -r ./landing/* ./deploy/
    cp -r ./api ./deploy/  # API JSON files, no database
```

## Decision Timeline

**Discovery phase** (2025-10-04 morning):
1. User discovered path mismatch bugs in landing page (`/v1/` vs `/api/v1/`)
2. Fixed bugs in `landing/index.html`
3. Realized testing fixes requires 2.5-hour scrape run
4. User asked: "Can we update the landing part without rerunning the scraper?"

**Analysis phase** (Claude):
- Identified landing/scraping as separate concerns
- Proposed separate workflow solution
- Estimated 30-second deployment vs 2.5-hour scrape

**Strategic consultation** (GPT-5 Thinking):
- Confirmed workflow separation
- **Critically identified concurrency risk**: overlapping scrapes
- Recommended `concurrency: { group: scrape, cancel-in-progress: true }`
- This was the key insight we (Jérémie + Claude) had missed

**Implementation** (Claude):
- Created `deploy-landing.yml` with path filters
- Updated `scrape.yml` with concurrency control + paths-ignore
- Tested path filter logic
- Documented in ADRs

**Result**: Shipped both workflows in commit c54a01e

## Real-World Impact

**Before:**
1. Discover HTML bug in landing page
2. Fix HTML
3. Commit + push
4. Wait 2.5 hours for scrape to complete
5. Check if fix worked
6. If broken, repeat (another 2.5 hours)

**After:**
1. Discover HTML bug in landing page
2. Fix HTML
3. Commit + push
4. Wait 30 seconds for landing deployment
5. Check if fix worked
6. If broken, repeat (another 30 seconds)

**Time savings**: 2h 29m 30s per iteration (99.7% reduction)

## Testing Strategy

**Landing page deployment test:**
```bash
# Make trivial change to landing page
echo "<!-- test -->" >> landing/index.html
git add landing/index.html
git commit -m "test: landing page deployment"
git push

# Should trigger ONLY deploy-landing.yml (30s)
# Should NOT trigger scrape.yml
```

**Scrape workflow test:**
```bash
# Make change to scraper
echo "# test" >> src/cli.py
git add src/cli.py
git commit -m "test: scraper code"
git push

# Should trigger scrape.yml (2.5h)
# Should NOT trigger deploy-landing.yml
```

**Concurrency test:**
```bash
# Manual trigger scrape.yml from GitHub Actions UI
# Immediately trigger again
# Second run should cancel first run
```

## Future Enhancements

### Workflow Visualization

Add workflow status badges to README:
```markdown
![Scrape Status](https://github.com/jlumbroso/penn-path-scraper/workflows/Scrape%20Penn%20Courses/badge.svg)
![Landing Status](https://github.com/jlumbroso/penn-path-scraper/workflows/Deploy%20Landing%20Page/badge.svg)
```

### Dependency on Scrape Data

Consider adding check in `deploy-landing.yml` to warn if API data is missing:
```yaml
- name: Validate API data exists
  run: |
    if [ ! -d "gh-pages-content/api/v1" ]; then
      echo "⚠️  Warning: No API data found on gh-pages"
      echo "Landing page will deploy but API calls will fail"
      echo "Run scrape.yml workflow first to generate API data"
    fi
```

### Workflow Metrics

Add timing information to workflow outputs for monitoring:
```yaml
- name: Report deployment time
  run: |
    echo "✅ Deployment completed in ${{ steps.deploy.outputs.duration }}"
```

## Links

* Builds on: [ADR-0005: Database Storage](0005-database-storage-github-releases.md) (database no longer in gh-pages)
* Relates to: [ADR-0002: Granular JSON](0002-granular-json-structure-option-c.md) (JSON API structure on Pages)
