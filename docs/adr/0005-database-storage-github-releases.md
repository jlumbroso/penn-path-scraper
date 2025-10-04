# Database Storage via GitHub Releases

* Status: accepted
* Deciders: Jérémie Lumbroso, Claude Sonnet 4.5 (with strategic consultation from GPT-5 Thinking)
* Date: 2025-10-04

Technical Story: After successful 2.5-hour scrape yielded 10MB SQLite database, we needed to address long-term storage strategy for scaling to 100+ terms (projected 1GB+ uncompressed database).

## Context and Problem Statement

The Penn Path Scraper collects longitudinal course enrollment data across multiple terms. Each term generates approximately 10MB of data in a SQLite database. With plans to collect historical data (10+ past terms) and ongoing daily updates, the database will grow to 100MB+ in the near term and 500MB+ long-term.

How should we store and distribute this binary database file in a way that:
- Doesn't bloat the git repository with daily binary updates
- Remains publicly accessible for researchers and students
- Scales efficiently to 500MB+ without hitting service limits
- Preserves historical data across workflow runs
- Minimizes storage costs and complexity

Initial implementation stored the database in the gh-pages branch for persistence across GitHub Actions runs, but this approach was identified as unsustainable due to git bloat from binary file commits.

## Decision Drivers

* **Git bloat concern**: Daily 10MB binary commits to gh-pages = 3.65GB/year in git history
* **Scaling trajectory**: 10 terms × 10MB = 100MB; 50 terms × 10MB = 500MB
* **GitHub repository limits**: 1GB soft limit, warnings at repo size growth
* **Public accessibility**: Data should be downloadable without git/LFS client
* **Cost constraints**: Free tier only, avoid paid services (AWS S3, LFS bandwidth)
* **Maintainability**: Minimize infrastructure complexity
* **API separation**: JSON API served on GitHub Pages should remain fast and separate from binary data
* **Compression potential**: Binary database compresses well (80% reduction with gzip)
* **Pedagogical transparency**: Repository may become public for teaching purposes

## Considered Options

1. **GitHub Releases** (with compression)
2. **Git LFS** (Large File Storage)
3. **Continue with gh-pages** (status quo)
4. **External storage** (AWS S3, R2, etc.)

## Decision Outcome

Chosen option: **"GitHub Releases with gzip compression"**, because it:
- Eliminates git bloat entirely (releases are separate from repo history)
- Has no bandwidth or storage limits (unlike LFS)
- Provides stable, public download URLs
- Supports versioning (rolling "latest" + monthly snapshots)
- Costs nothing
- Scales to 500MB+ without issues
- Integrates cleanly with GitHub Actions workflows

### Positive Consequences

* **No git history pollution**: Binary database never committed to any git branch
* **80% size reduction**: gzip -9 compression reduces 10MB → ~2MB per release
* **Scalability**: Can grow to 100+ terms without infrastructure changes
* **Public access**: Direct download URLs work from anywhere:
  ```bash
  curl -L https://github.com/jlumbroso/penn-path-scraper/releases/download/latest-data/courses.db.gz
  ```
* **Discoverability**: `/api/v1/db-manifest.json` provides metadata (SHA256, size, download URL)
* **Clean separation**: GitHub Pages serves JSON API; Releases serve binary database
* **Version history**: Can maintain monthly snapshot releases for historical analysis
* **No vendor lock-in**: Standard gzip format, SQLite database

### Negative Consequences

* **Release management complexity**: Need to handle release creation/updates in workflow
* **Public visibility**: Database is publicly accessible (but data is already public from Penn)
* **Manual monthly snapshots**: Archival versioning requires additional workflow logic (future enhancement)
* **Download overhead**: Users must decompress before use (but saves 80% bandwidth)

## Pros and Cons of the Options

### GitHub Releases (with compression)

Rolling release strategy: `latest-data` tag overwritten daily, with optional monthly snapshots (`2025-10-data`, `2025-11-data`, etc.).

* Good, because no git bloat (releases are outside repo history)
* Good, because no bandwidth limits (unlike LFS which charges after 1GB/month)
* Good, because no storage limits (unlike artifacts which expire after 90 days)
* Good, because gzip compression achieves 80% size reduction (10MB → 2MB)
* Good, because public access via stable URLs
* Good, because first-class versioning support (tags, release notes, checksums)
* Good, because easy restoration in workflows using `gh` CLI
* Good, because free forever (no LFS/S3 costs as database grows)
* Bad, because requires managing release lifecycle in workflows
* Bad, because users must decompress manually (but this is trivial)

**Implementation:**
```yaml
# Compress
gzip -9 -k ./db/courses.db

# Upload to rolling release
uses: softprops/action-gh-release@v1
with:
  tag_name: latest-data
  files: ./db/courses.db.gz

# Restore in next run
gh release download latest-data -p "courses.db.gz" -D ./db/
gunzip ./db/courses.db.gz
```

### Git LFS (Large File Storage)

Use Git LFS to track `*.db` files, keeping pointers in git and data in LFS storage.

* Good, because integrated with git workflow
* Good, because handles binary diffs properly
* Bad, because **bandwidth limits**: 1GB/month free, then $5/50GB
* Bad, because with 2MB compressed × 30 days/month = 60MB/month baseline, but uncompressed fetches = 300MB/month
* Bad, because **storage limits**: 1GB free storage (would hit limit at 100 terms)
* Bad, because at scale (50 terms, daily updates): ~450MB/month bandwidth → $5-10/month ongoing cost
* Bad, because requires LFS extension for cloning/contributing
* Bad, because public users can't easily download without git

**Cost projection at scale:**
- Year 1 (10 terms): ~$0-5/month
- Year 5 (50 terms): ~$10-20/month
- Total 5-year cost: ~$500-1000

### Continue with gh-pages (status quo)

Keep committing compressed database to gh-pages branch daily.

* Good, because already implemented and working
* Good, because simple workflow
* Bad, because **massive git bloat**: Even compressed, 2MB × 365 days = 730MB/year
* Bad, because bloat is permanent in git history (can't remove without force-push)
* Bad, because violates best practice of no binary files in git
* Bad, because GitHub 1GB repo soft limit would be reached in ~18 months
* Bad, because slow clones as repo grows
* Bad, because bloat affects both main repo and gh-pages branch

**Projected timeline:**
- 6 months: 365MB bloat
- 12 months: 730MB bloat (warnings)
- 18 months: 1.1GB bloat (exceeds soft limit)

### External Storage (AWS S3, Cloudflare R2, etc.)

Upload database to object storage service, reference from API.

* Good, because designed for large binary files
* Good, because very cheap storage ($0.023/GB/month S3)
* Good, because fast access with CDN
* Bad, because requires AWS account + credentials management
* Bad, because adds external dependency and complexity
* Bad, because requires payment setup (credit card, billing)
* Bad, because overkill for current scale (100MB-500MB)
* Bad, because less transparent for public/educational use
* Bad, because vendor lock-in (migration complexity)

**When to reconsider:** If database exceeds 1GB and download bandwidth becomes bottleneck.

## Implementation Details

### Workflow Changes (commit c54a01e)

**Database compression before upload:**
```yaml
- name: Compress database for release
  run: |
    gzip -9 -k ./db/courses.db
    echo "✅ Compressed database: $(du -h ./db/courses.db.gz | cut -f1)"
```

**Upload to GitHub Release:**
```yaml
- name: Upload database to latest-data release
  uses: softprops/action-gh-release@v1
  with:
    tag_name: latest-data
    name: Latest Course Data
    files: ./db/courses.db.gz
    body: |
      **Latest Penn Course Data**
      Updated: ${{ github.event.head_commit.timestamp }}
      Workflow: ${{ github.run_id }}
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Restoration in subsequent runs:**
```yaml
- name: Restore database from latest release
  run: |
    mkdir -p ./db
    if gh release download latest-data -p "courses.db.gz" -D ./db/ 2>/dev/null; then
      gunzip ./db/courses.db.gz
      echo "✅ Restored database from latest-data release"
    else
      echo "ℹ️  No existing database found - starting fresh"
    fi
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Discoverability Manifest

Created `/api/v1/db-manifest.json` to advertise database availability:
```json
{
  "database": {
    "release_tag": "latest-data",
    "download_url": "https://github.com/jlumbroso/penn-path-scraper/releases/download/latest-data/courses.db.gz",
    "compressed_size": 2097152,
    "sha256": "abc123...",
    "format": "sqlite3",
    "compression": "gzip",
    "updated_at": "2025-10-04T12:00:00Z"
  },
  "instructions": {
    "download": "curl -L <url> -o courses.db.gz",
    "decompress": "gunzip courses.db.gz"
  }
}
```

## Team Decision Process

This decision emerged from collaborative consultation:

1. **Initial concern** (Jérémie): "10MB database now, but 100MB when we scrape historical terms. Binary files will fuck with git badly."

2. **Analysis phase** (Claude Sonnet 4.5):
   - Evaluated 4 options (Releases, LFS, gh-pages, S3)
   - Recommended GitHub Releases based on cost/scale analysis
   - Identified LFS bandwidth limits as critical blocker

3. **Strategic consultation** (GPT-5 Thinking):
   - Confirmed Releases architecture: "Keep JSON on Pages; move SQLite to Releases"
   - Added compression insight: "gzip -9 or zstd" (80% reduction)
   - Suggested monthly snapshots for versioning
   - Provided production-ready YAML implementation

4. **Final decision** (Jérémie + Claude):
   - Synthesized recommendations
   - Chose Releases + compression
   - Added db-manifest.json for discoverability
   - Implemented with cleaner `gh` CLI vs curl approach

## Future Enhancements

### Monthly Snapshot Releases (planned)

Automate creation of dated snapshot releases on 1st of each month:

```yaml
- name: Create monthly snapshot
  if: ${{ startsWith(github.ref, 'refs/heads/') && endsWith(env.TODAY, '-01') }}
  run: |
    TAG="$(date -u +'%Y-%m')-data"
    gh release create "$TAG" ./db/courses.db.gz \
      --title "$TAG" \
      --notes "Monthly snapshot: $(date -u +'%B %Y')"
```

**Versioning strategy:**
- `latest-data` - Rolling release (daily overwrites)
- `2025-10-data` - October 2025 snapshot (permanent)
- `2025-11-data` - November 2025 snapshot (permanent)
- etc.

### Database Schema Versioning

Add `PRAGMA user_version` to track schema migrations, expose in manifest.

### Compression Evaluation

Consider `zstd` vs `gzip` for better compression ratio (may achieve 85-90% reduction).

## Links

* Refined by: [ADR-0006: Workflow Separation](0006-workflow-separation-deployment.md) (deployment architecture)
* Relates to: [ADR-0002: Granular JSON Structure](0002-granular-json-structure-option-c.md) (JSON API remains on Pages)
* Relates to: [ADR-0004: Scaling and Performance](0004-scaling-and-performance-strategy.md) (overall scaling strategy)
