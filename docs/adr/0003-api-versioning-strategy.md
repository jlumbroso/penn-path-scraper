# API Versioning Strategy for Static JSON Exports

* Status: accepted
* Deciders: Jérémie Lumbroso, Claude Sonnet 4.5
* Date: 2025-10-03

## Context and Problem Statement

The Penn Path Scraper exports a granular JSON API structure (per ADR-0002 Option C) that will be committed to the main branch and potentially served via GitHub Pages. We need a versioning strategy that allows us to evolve the API structure over time without breaking existing consumers.

How should we version the exported JSON API to support future schema changes and maintain backward compatibility?

## Decision Drivers

* **Future-proofing**: We may need to change the JSON structure as requirements evolve
* **Breaking changes**: Need a way to introduce breaking changes without disrupting existing consumers
* **Path stability**: Clients should have predictable, stable URLs
* **GitHub Pages compatibility**: Versioning must work with static file hosting
* **Simplicity**: Avoid over-engineering for hypothetical future needs

## Considered Options

* **Option 1**: No versioning (`/api/...`)
* **Option 2**: Version in path (`/api/v1/...`)
* **Option 3**: Version in filename (`/api/courses-v1.json`)
* **Option 4**: Version in JSON payload only

## Decision Outcome

Chosen option: **"Option 2: Version in path (`/api/v1/...`)"**, because it provides a clear upgrade path, follows REST API best practices, and works seamlessly with static hosting while keeping the current version simple.

### Positive Consequences

* Clear migration path: Can introduce `/api/v2/` alongside `/api/v1/` when needed
* Standard practice: Aligns with common REST API versioning patterns
* Easy to deploy: Both versions can coexist during transition periods
* GitHub Pages friendly: URL-based versioning works perfectly with static file hosting

### Negative Consequences

* Slightly longer paths: URLs include `/v1/` segment
* Must maintain old versions: Can't easily deprecate old API versions without breaking clients
* Migration burden: Future changes to v2 require maintaining both structures

## Pros and Cons of the Options

### Option 1: No Versioning

Structure: `/api/courses/CIS-1210/index.json`

* Good, because simplest implementation
* Good, because shortest URLs
* Bad, because no upgrade path for breaking changes
* Bad, because any schema change could break all consumers

### Option 2: Version in Path (CHOSEN)

Structure: `/api/v1/courses/CIS-1210/index.json`

* Good, because follows REST API best practices
* Good, because allows parallel deployment of multiple versions
* Good, because version is immediately visible in URL
* Good, because works with static hosting (GitHub Pages)
* Bad, because slightly longer URLs
* Bad, because requires maintaining multiple directory structures if we ship v2

### Option 3: Version in Filename

Structure: `/api/courses-v1/CIS-1210/index.json`

* Good, because version is in the URL
* Bad, because non-standard approach
* Bad, because inconsistent naming (`courses-v1` vs `courses-v2`)
* Bad, because harder to organize and maintain

### Option 4: Version in JSON Payload Only

Structure: `/api/courses/CIS-1210/index.json` contains `{"version": "1.0", ...}`

* Good, because clean URLs
* Bad, because clients must fetch files to discover version
* Bad, because no way to support multiple versions simultaneously
* Bad, because breaking changes still break all consumers

## Implementation Details

### Directory Structure

```
/api/v1/
  index.json
  /courses/
    /CIS-1210/
      index.json
      enrollments.json
  /terms/
    /202530/
      index.json
  /search/
    instructors.json
    departments.json
```

### Endpoint Format

All endpoints include the version prefix:
- `/api/v1/courses/{course-code}/index.json`
- `/api/v1/courses/{course-code}/enrollments.json`
- `/api/v1/terms/{term-code}/index.json`
- `/api/v1/search/instructors.json`
- `/api/v1/search/departments.json`

### Future Migration Path

When we need to introduce breaking changes:
1. Create `/api/v2/` directory alongside `/api/v1/`
2. Export to both structures during transition period
3. Update documentation to recommend v2
4. Eventually deprecate v1 (but keep files for backward compatibility)

## Links

* Extends [ADR-0002 Data Storage and Export Architecture](0002-data-storage-and-export-architecture.md)
* Master index at `/api/v1/index.json` includes `api_version` field for schema version tracking
