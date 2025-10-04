# Scaling and Performance Strategy

* Status: accepted
* Deciders: Jérémie Lumbroso, Claude Sonnet 4.5
* Date: 2025-10-03

## Context and Problem Statement

The Penn Path Scraper will accumulate data over time, potentially running for years without intervention. We need to address scaling concerns **now** rather than creating a "time bomb" that detonates when the project has become mission-critical infrastructure.

**The Problem**: As the dataset grows, several files will increase in size linearly with each term:
- `/v1/search/instructors.json` - Grows with every term every instructor teaches
- `/v1/search/departments.json` - Grows with every course section offered
- Individual course enrollment histories - Grow with daily snapshots

**The Risk**: If this works well, it becomes invisible infrastructure. By the time we notice file size issues, the system may be deeply integrated into workflows.

## Decision Drivers

* **Prevent future technical debt** - Address scaling issues before they become emergencies
* **Maintain performance** - GitHub Pages serves static files; large files hurt user experience
* **Enable debugging** - Pretty-printed JSON is essential during development
* **Minimize storage** - After debugging phase, optimize for production use
* **Set clear triggers** - Define when optimizations activate automatically

## Considered Options

### File Size Optimization

* **Option A**: Never optimize, rely on gzip compression only
* **Option B**: Minify JSON immediately (lose debugging capability)
* **Option C**: Time-based minification switch (pretty-print during debug phase, minify after)
* **Option D**: File-size-based minification (minify files over threshold)

### Search Index Scaling

* **Option A**: Keep monolithic search indexes forever
* **Option B**: Split immediately into per-entity files
* **Option C**: Hybrid - start monolithic, split when files exceed threshold
* **Option D**: Use database-backed API instead of static files

## Decision Outcome

**Chosen options**:
1. **Option C for JSON minification**: Time-based switch with environment override
2. **Option C for search indexes**: Start monolithic, split when files > 2MB

### Rationale

**JSON Minification** (Option C):
- During initial deployment (2-3 terms), pretty-printed JSON is invaluable for debugging
- After stabilization, minification saves 40-70% file size with zero functionality loss
- Time-based trigger provides predictable behavior
- Environment variable allows manual override for testing

**Search Indexes** (Option C):
- Current monolithic format is simpler and faster for small datasets
- Gzip compression makes even 1MB files acceptable (~100KB compressed)
- Splitting prematurely adds complexity without benefit
- 2MB threshold provides ~5-10 years of runway before optimization needed

## Implementation Details

### JSON Minification Strategy

**Trigger Date**: `2026-04-01` (6 months after initial deployment)

**Behavior**:
- **Before trigger date**: `indent=2` (pretty-printed, human-readable)
- **After trigger date**: `indent=None, separators=(',', ':')` (minified)

**Environment override**:
```bash
# Force minification NOW (for testing)
PENN_SCRAPER_COMPACT_JSON=true pipenv run scraper export

# Force pretty-print ALWAYS (for development)
PENN_SCRAPER_COMPACT_JSON=false pipenv run scraper export
```

**Expected savings**:
- Pretty-printed: ~4-5 bytes per character (with indentation)
- Minified: ~1-2 bytes per character
- **Estimated compression: 50-60% reduction in file size**

### Search Index Splitting (Future)

**Trigger**: Individual search index file > 2MB uncompressed

**Current structure** (monolithic):
```
/v1/search/
  instructors.json      # All instructors → all courses
  departments.json      # All departments → all courses
```

**Future structure** (split):
```
/v1/search/
  instructors/
    index.json          # List of all instructors with links
    lumbroso.json       # All courses taught by Lumbroso
    bhusnurmath.json    # All courses taught by Bhusnurmath
  departments/
    index.json          # List of all departments
    CIS.json            # All CIS courses across all terms
    NETS.json           # All NETS courses across all terms
```

**Migration path**:
1. Monitor file sizes in GitHub Actions logs
2. When threshold exceeded, create ADR-0005 documenting the split
3. Implement split as v2 API (`/v2/search/departments/...`)
4. Maintain v1 for backward compatibility (6-month deprecation window)

### Enrollment Snapshots Optimization

**Problem**: Daily snapshots for 10+ years = massive growth

**Solution**: Snapshot thinning for old data
- **Recent data** (< 1 year old): Keep all daily snapshots
- **Historical data** (> 1 year old): Keep only weekly snapshots

**Example**:
```json
{
  "snapshots": [
    // Recent: daily snapshots
    {"timestamp": "2025-10-03T12:00:00", "enrolled": 48, "capacity": 50},
    {"timestamp": "2025-10-02T12:00:00", "enrolled": 47, "capacity": 50},
    // ... daily for current term

    // Historical: weekly snapshots
    {"timestamp": "2024-10-07T12:00:00", "enrolled": 50, "capacity": 50},
    {"timestamp": "2024-10-14T12:00:00", "enrolled": 50, "capacity": 50}
  ]
}
```

**Implementation**: Background job in GitHub Actions to thin historical snapshots

## Monitoring and Alerts

### GitHub Actions Checks

Add file size monitoring to workflow:

```yaml
- name: Check export file sizes
  run: |
    find ./api/v1/search -name "*.json" -size +2M -exec echo "⚠️  WARNING: {} exceeds 2MB" \;
    find ./api/v1/search -name "*.json" -size +5M -exec echo "🚨 ERROR: {} exceeds 5MB" \; -exit 1
```

### Scaling Milestones

| Milestone | Estimated Timeline | Action Required |
|-----------|-------------------|-----------------|
| Search indexes reach 1MB | ~3 years | Begin planning index split |
| Search indexes reach 2MB | ~5 years | **TRIGGER**: Implement index split (v2 API) |
| Enrollment snapshots > 10K/course | ~5 years | Implement snapshot thinning |
| Total API size > 100MB | ~10 years | Consider CDN or database backend |

## 🚨 TIME BOMB WARNING 🚨

**If you're reading this because things are broken**: The scaling triggers likely activated.

**Check these metrics**:
1. Run `du -sh ./api/v1/search/*.json` - Are files > 2MB?
2. Check GitHub Actions logs for file size warnings
3. Look for slow page loads or timeout errors

**Immediate fixes**:
1. Enable minification: `export PENN_SCRAPER_COMPACT_JSON=true`
2. Implement search index split (see "Future structure" above)
3. Create ADR-0005 documenting the migration

## Positive Consequences

* **Proactive planning**: Issues addressed before they become emergencies
* **Clear triggers**: Automatic behavior changes at predictable milestones
* **Debugging preserved**: Pretty-print mode during development phase
* **Performance optimized**: Minification activates after stabilization
* **Visibility**: Monitoring and alerts prevent surprises

## Negative Consequences

* **Complexity**: Time-based switches add conditional logic
* **Maintenance**: Requires updating trigger dates if deployment delays
* **Testing burden**: Must test both pretty-print and minified modes

## Links

* Extends [ADR-0002 Data Storage and Export Architecture](0002-data-storage-and-export-architecture.md)
* Extends [ADR-0003 API Versioning Strategy](0003-api-versioning-strategy.md)
* Future: ADR-0005 will document search index split when triggered
