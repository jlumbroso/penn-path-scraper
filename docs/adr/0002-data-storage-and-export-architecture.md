# Data Storage and Export Architecture

* Status: proposed
* Deciders: Jérémie Lumbroso (user), Claude Sonnet 4.5 (model)
* Date: 2025-10-01

Technical Story: Design the architecture for storing scraped course data, tracking enrollment changes over time, and exporting to static JSON feeds for GitHub Pages distribution.

## Context and Problem Statement

We need to scrape course data repeatedly over time to build a longitudinal dataset tracking enrollment changes. The scraped data must be stored somewhere during collection, then exported to static JSON feeds that can be hosted on GitHub Pages. How should we structure the data storage, and what format should the exported feeds take?

## Decision Drivers

* Need to track enrollment changes over time (time-series data)
* Scraper will run periodically (daily via GitHub Actions)
* Must be error-tolerant (can resume after failures)
* Output must be static JSON files for GitHub Pages
* Should enable multiple "views" of the data (by course, by instructor, by term)
* Need clean, type-safe Python code
* Want comprehensive test coverage (TDD approach)

## Considered Options

### For Intermediate Storage:
1. **SQLite database** - Single-file relational database
2. **In-memory Python objects** - Store in memory, dump to JSON at end
3. **JSON files directly** - Write JSON files as we scrape
4. **PostgreSQL/MySQL** - Full database server

### For Data Export:
1. **Monolithic JSON file** - Single large file with all data
2. **Granular JSON feeds** - Many small files, different views of data
3. **SQLite database as distribution** - Distribute the SQLite file itself

### For Data Access Layer:
1. **SQLAlchemy ORM** - Full-featured ORM
2. **Peewee ORM** - Lightweight ORM
3. **Raw SQL with helper functions** - Direct SQL queries
4. **Dataclasses + custom persistence** - No ORM, manual mapping

## Decision Outcome

### Clear Decisions (Accepted):

#### 1. Use SQLite for Intermediate Storage

**Chosen**: SQLite database

**Rationale**:
- Built into Python standard library (no extra dependencies)
- Single portable file
- ACID transactions (atomic updates, safe for crashes)
- Can query efficiently for generating feeds
- Easy to inspect/debug with SQLite tools
- Supports indexes for performance
- Perfect for this use case (single writer, complex queries for export)

#### 2. Use Granular JSON Feeds for Export

**Chosen**: Multiple small JSON files organized by different access patterns

**Rationale**:
- Enables efficient data access (clients only fetch what they need)
- GitHub Pages serves static files well
- Can use index.json trick for clean URLs
- Allows different views without duplicating data
- Better for versioning (smaller diffs in git)

#### 3. Type Safety with TypedDict

**Chosen**: Define all data structures as TypedDict classes

**Rationale**:
- Type safety without runtime overhead
- Clear contracts for data structures
- IDE autocomplete support
- Mypy validation
- Documentation through types
- Follows project guidelines (CLAUDE.md)

#### 4. Test-Driven Development with pytest

**Chosen**: Write tests first, use pytest framework

**Rationale**:
- Forces clear interface design
- Catches regressions
- Documents expected behavior
- Makes refactoring safer
- Pytest is powerful and flexible

### Open Questions (Need User Input):

## Open Question 1: ORM vs. Raw SQL

**Context**: How should we interact with the SQLite database?

### Option A: No ORM - Raw SQL with Helper Functions

**Approach**:
```python
def save_course(db: sqlite3.Connection, course: CourseDict) -> None:
    db.execute("""
        INSERT OR REPLACE INTO courses (code, title, description)
        VALUES (?, ?, ?)
    """, (course['code'], course['title'], course['description']))
```

* Good: Lightweight, no dependencies, explicit
* Good: Full control over SQL
* Good: Easy to optimize queries
* Bad: More boilerplate code
* Bad: Manual mapping between Python objects and SQL

### Option B: Lightweight ORM (Peewee)

**Approach**:
```python
class Course(peewee.Model):
    code = peewee.CharField(primary_key=True)
    title = peewee.CharField()
    description = peewee.TextField()
```

* Good: Less boilerplate
* Good: Automatic mapping
* Good: Still lightweight (~1 dependency)
* Bad: Another abstraction layer
* Bad: Learning curve

### Option C: SQLAlchemy ORM

**Approach**:
```python
class Course(Base):
    __tablename__ = 'courses'
    code = Column(String, primary_key=True)
    title = Column(String)
    description = Column(Text)
```

* Good: Industry standard
* Good: Very powerful
* Good: Great for complex queries
* Bad: Heavy dependency
* Bad: Overkill for this use case
* Bad: Steeper learning curve

**My Recommendation**: Option A (Raw SQL) - keeps things simple and explicit for this use case.

## Open Question 2: JSON Feed Granularity

**Context**: What different JSON feeds should we generate?

### Feed Structure Options:

#### Option A: Comprehensive Feed Set
```
/api/
  /courses/
    /CIS-1210/
      index.json          # Course details + current sections
      enrollments.json    # Time-series enrollment data
      history.json        # Historical sections (past terms)
  /instructors/
    /lumbroso/
      index.json          # All courses taught
  /departments/
    /CIS/
      index.json          # All CIS courses
  /terms/
    /202530/
      index.json          # All courses in Fall 2025
  /schools/
    /engineering/
      index.json          # All Engineering courses
  index.json              # Master index of everything
```

* Good: Maximum flexibility
* Good: Efficient queries (only fetch what you need)
* Bad: Many files to generate
* Bad: More complex to maintain

#### Option B: Minimal Feed Set
```
/api/
  /courses/
    /CIS-1210/
      index.json          # Everything about this course
  /terms/
    /202530/
      index.json          # All courses this term
  index.json              # Master index
```

* Good: Simpler
* Good: Fewer files
* Bad: Less flexible
* Bad: Larger file sizes

#### Option C: Hybrid Approach
```
/api/
  /courses/
    /CIS-1210/
      index.json          # Course details + current term
      enrollments.json    # Time-series data
  /terms/
    /202530/
      index.json          # All courses this term
  /search/
    instructors.json      # Index of all instructors → courses
    departments.json      # Index of all departments → courses
  index.json              # Master index
```

* Good: Balance of flexibility and simplicity
* Good: Separate time-series data (updated frequently)
* Good: Search indexes are separate
* Bad: Still somewhat complex

**My Recommendation**: Option C (Hybrid) - separates frequently-updated data from static data.

## Open Question 3: Enrollment History Schema

**Context**: How should we structure time-series enrollment data?

### Option A: Array of Snapshots
```json
{
  "course": "CIS-1210",
  "term": "202530",
  "crn": "12345",
  "snapshots": [
    {
      "timestamp": "2025-09-01T10:00:00Z",
      "enrolled": 48,
      "capacity": 50,
      "waitlist": 5
    },
    {
      "timestamp": "2025-09-02T10:00:00Z",
      "enrolled": 50,
      "capacity": 50,
      "waitlist": 12
    }
  ]
}
```

* Good: Simple structure
* Good: Easy to process
* Good: Chronological order is obvious
* Bad: Can get large for courses scraped many times

### Option B: Compact Delta Format
```json
{
  "course": "CIS-1210",
  "term": "202530",
  "crn": "12345",
  "initial": {
    "timestamp": "2025-09-01T10:00:00Z",
    "enrolled": 48,
    "capacity": 50
  },
  "changes": [
    {
      "timestamp": "2025-09-02T10:00:00Z",
      "enrolled": 50,
      "waitlist": 12
    }
  ]
}
```

* Good: More compact (only store changes)
* Good: Still easy to reconstruct
* Bad: Slightly more complex to process
* Bad: Optimization might be premature

### Option C: Separate Files by Date Range
```json
/api/courses/CIS-1210/enrollments/2025-09.json
/api/courses/CIS-1210/enrollments/2025-10.json
```

* Good: Keeps files small
* Good: Can archive old months
* Bad: More complex to query across time ranges
* Bad: More files to manage

**My Recommendation**: Option A (Array of Snapshots) - simple and clear, optimize later if needed.

## Open Question 4: Incremental vs. Full Scraping

**Context**: When the scraper runs, should it scrape everything or only what changed?

### Option A: Full Scrape Every Time
- Scrape all schools × all active terms
- Update enrollment numbers for all courses
- Simple, no state tracking needed

* Good: Simpler logic
* Good: Self-healing (fixes any missing data)
* Good: No state to track
* Bad: Slower (more API calls)
* Bad: More likely to hit rate limits

### Option B: Incremental Updates
- Only scrape current/upcoming terms
- Skip courses that haven't changed (hash comparison)
- Track what's been scraped

* Good: Faster
* Good: Fewer API calls
* Good: Gentler on their servers
* Bad: More complex
* Bad: Need to track state
* Bad: Risk of missing updates

**My Recommendation**: Start with Option A (Full Scrape) for current term only, add incremental later if needed.

## Implementation Plan

1. **Phase 1**: Core Infrastructure
   - Define TypedDict data structures
   - Create SQLite schema
   - Build basic scraper with tests (TDD)

2. **Phase 2**: Data Collection
   - Implement full scraper for one term
   - Store in SQLite
   - Handle errors gracefully

3. **Phase 3**: Export & Distribution
   - Generate JSON feeds from SQLite
   - Set up GitHub Pages structure
   - Create index pages

4. **Phase 4**: Automation
   - GitHub Actions workflow
   - Scheduled scraping (daily)
   - Commit & push updated data

## Next Steps

Need user decisions on:
1. ORM choice (my rec: Raw SQL)
2. Feed granularity (my rec: Hybrid approach)
3. Enrollment schema (my rec: Array of snapshots)
4. Scraping strategy (my rec: Full scrape of current term)

## Links

* Supersedes: [ADR-0001](0001-penn-courses-api-structure.md) - API structure documentation
* Related: [CLAUDE.md](/CLAUDE.md) - Project guidelines
