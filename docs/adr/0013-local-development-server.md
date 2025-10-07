# ADR-0013: Local Development Server for Visualization Testing

**Date**: 2025-10-06
**Status**: Implemented
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Development workflow, visualization testing

## Context and Problem Statement

After implementing Claude's Creative Corner visualizations (ADR-0009) and the export layer integration (ADR-0007), we needed a way to **test visualizations locally** before deploying to GitHub Pages.

### The Challenge

The landing page (`landing/index.html`) expects:
- A specific API structure: `api/v1/index.json`, `api/v1/terms/{code}/`, `api/v1/search/`
- JSON files exported from the database
- A web server to handle CORS and serve both static assets and API endpoints

**Without a local server**, the workflow was:
1. Run scraper to populate database
2. Export to JSON manually
3. Deploy to GitHub Pages (or commit to git)
4. Wait for deployment
5. Test in browser
6. Find bugs
7. Repeat

This creates a **slow feedback loop** (5-10 minutes per iteration) and makes rapid iteration on visualizations painful.

### What We Needed

A **single command** that:
- ✅ Exports the current database to API JSON structure
- ✅ Serves the landing page with proper routing
- ✅ Handles API requests (`/api/v1/*`) from the exported JSON
- ✅ Auto-opens browser for immediate testing
- ✅ Cleans up temp files automatically
- ✅ Works with any database file (prod, test, historical)

## Decision Drivers

1. **Developer Experience**: One command to start testing
2. **Fast Feedback**: See changes immediately without deploy
3. **Accuracy**: Test with real database exports (same code path as production)
4. **Flexibility**: Support different databases, ports, and configurations
5. **Simplicity**: No external dependencies beyond Python standard library

## Solution: `scripts/serve_local.py`

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     scripts/serve_local.py                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Database Export Phase                                    │
│     ┌──────────────┐                                        │
│     │  courses.db  │                                        │
│     └──────┬───────┘                                        │
│            │                                                 │
│            ▼                                                 │
│     ┌──────────────────┐                                    │
│     │  src.export.*    │  (uses same export code as prod)  │
│     └──────┬───────────┘                                    │
│            │                                                 │
│            ▼                                                 │
│     ┌──────────────────────────────────────┐               │
│     │  Temp Directory (auto-cleanup)        │               │
│     │  /tmp/penn-path-api-XXXXX/            │               │
│     │    api/v1/                            │               │
│     │      ├── index.json                   │               │
│     │      ├── terms/                       │               │
│     │      │   ├── 202530.json              │               │
│     │      │   └── 202520.json              │               │
│     │      └── search/                      │               │
│     │          ├── instructors.json         │               │
│     │          └── departments.json         │               │
│     └──────┬───────────────────────────────┘               │
│            │                                                 │
│            ▼ (copy to landing/api/)                        │
│                                                              │
│  2. Web Server Phase                                        │
│     ┌──────────────────────────────────────┐               │
│     │  DevServerHandler                    │               │
│     │  (http.server.SimpleHTTPRequestHandler)              │
│     ├──────────────────────────────────────┤               │
│     │  Routes:                             │               │
│     │  • /                → index.html     │               │
│     │  • /assets/*       → static files    │               │
│     │  • /api/v1/*       → exported JSON   │               │
│     └──────────────────────────────────────┘               │
│            │                                                 │
│            ▼                                                 │
│     http://localhost:8000                                   │
│     (auto-opens in browser)                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### Phase 1: Database Export (`export_database_to_api()`)

**Step-by-step process**:

1. **Connect to database**:
   ```python
   src.models.db.init(db_path)
   src.models.db.connect()
   ```

2. **Query all terms**:
   ```python
   terms = src.models.Term.select().order_by(src.models.Term.code.desc())
   ```

3. **For each term**:
   - Call `src.export.export_term_to_dict(term.code)` (same function used in production)
   - Write to `api/v1/terms/{code}.json`
   - Collect metadata for master index

4. **Build search indexes**:
   - **Instructors**: Map instructor name → list of courses
   - **Departments**: Map department code → list of courses
   - Enables fast client-side search

5. **Write master index** (`api/v1/index.json`):
   ```json
   {
     "generated_at": "2025-10-06T12:34:56",
     "total_terms": 2,
     "total_courses": 847,
     "total_instructors": 234,
     "terms": [
       {
         "code": "202530",
         "name": "Fall 2025",
         "start_date": "2025-08-26",
         "end_date": "2025-12-08",
         "course_count": 623
       },
       ...
     ]
   }
   ```

**Key Design Decision**: Use the **same export code** (`src.export.export_term_to_dict()`) as production deployment. This guarantees:
- ✅ Testing with identical data structure
- ✅ Bugs caught locally appear in production
- ✅ Online course fields (`inst_method_code`, `campus_code`) exported correctly
- ✅ No drift between dev and prod

#### Phase 2: HTTP Server (`DevServerHandler`)

**Custom request handler** extending `http.server.SimpleHTTPRequestHandler`:

```python
class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # API endpoint routing
        if self.path.startswith('/api/v1/'):
            # Map URL to file system
            # /api/v1/terms/202530/ → api/v1/terms/202530.json
            # /api/v1/index.json    → api/v1/index.json
            # Serve JSON with CORS headers

        # Static file routing
        else:
            # Serve from landing/ directory
            # /               → landing/index.html
            # /assets/js/*    → landing/assets/js/*
            super().do_GET()
```

**CORS Headers**: Added for local development to avoid browser restrictions:
```python
def end_headers(self):
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
    super().end_headers()
```

**Auto-open Browser**: Uses threading to open browser after 1-second delay:
```python
def open_browser():
    time.sleep(1)  # Wait for server to start
    webbrowser.open(f"http://localhost:{port}")

threading.Thread(target=open_browser, daemon=True).start()
```

### File Structure Generated

```
/tmp/penn-path-api-XXXXX/           # Temp directory (auto-cleanup)
└── api/
    └── v1/
        ├── index.json               # Master index with term list
        ├── terms/
        │   ├── 202530.json         # Fall 2025 courses
        │   └── 202520.json         # Summer 2025 courses
        └── search/
            ├── instructors.json     # Instructor → courses mapping
            └── departments.json     # Department → courses mapping

landing/                             # Served as web root
├── index.html                      # Main visualization page
├── assets/
│   ├── js/
│   │   ├── penn-gradient-flash.js
│   │   └── claude-footer.js
│   └── css/
│       └── penn-design-system.css
└── api/                            # Copied from temp (cleaned on exit)
    └── v1/                         # Same structure as above
```

## Usage

### Basic Usage

```bash
# Start server with default database (courses.db) on port 8000
pipenv run serve

# Or directly
python scripts/serve_local.py
```

**Output**:
```
📊 Exporting database: courses.db
   Found 2 terms
   Exporting Summer 2025 (202520)...
   Exporting Spring 2025 (202510)...
✅ Export complete!
   📁 API directory: /tmp/penn-path-api-XXXXX/api/v1
   📊 2 terms, 847 courses, 234 instructors

🚀 Development server running at http://localhost:8000
   📁 Serving from: /Users/.../landing
   🔌 API data from: /tmp/.../api/v1

   Press Ctrl+C to stop
```

### Advanced Usage

```bash
# Test with historical database
python scripts/serve_local.py --db old.courses.db

# Use different port (if 8000 is in use)
python scripts/serve_local.py --port 3000

# Skip re-export (faster iteration if DB unchanged)
python scripts/serve_local.py --no-export --output-dir /tmp/cached-api

# Persist API files for inspection
python scripts/serve_local.py --output-dir ./debug-api-export
```

### Pipfile Integration

Added shortcuts to `Pipfile`:
```ini
[scripts]
serve = "python scripts/serve_local.py"
serve-port = "python scripts/serve_local.py --port"
```

## What Gets Tested

Running the local server allows testing:

### 1. **Functional Visualizations** (existing):
- Department Enrollment Distribution
- Enrollment by School
- Top Courses by Enrollment
- Course Fill Rate Distribution
- Class Size Distribution
- Most In-Demand Courses

### 2. **Claude's Creative Corner** (new in ADR-0009):
- ⭐ **Teaching Stars**: Instructor impact rankings
- 📊 **The Long Tail**: Enrollment concentration curve
- 💎 **Hidden Gems**: Small seminars with availability

### 3. **Export Layer Integration** (ADR-0007):
- Online course fields (`inst_method_code`, `campus_code`) properly exported
- Nullable enrollment fields for historical/cancelled courses
- Complete data pipeline: DB → Export → JSON → Visualization

### 4. **Search Functionality**:
- Instructor search
- Department search

### 5. **Cross-term Filtering**:
- All visualizations support filtering by term, school, department
- Data aggregated correctly across multiple terms

## Development Workflow

### Before (Slow Feedback Loop):
```
1. Edit landing/index.html
2. Commit to git
3. Push to GitHub
4. Wait for GitHub Pages deploy (2-5 min)
5. Test in browser
6. Find bug
7. GOTO 1
```

**Iteration time**: ~5-10 minutes per cycle

### After (Fast Feedback Loop):
```
1. Edit landing/index.html
2. Ctrl+C (stop server)
3. pipenv run serve
4. Test immediately in auto-opened browser
5. Find bug
6. GOTO 1
```

**Iteration time**: ~5 seconds per cycle

## Technical Decisions

### Why Not Use Nginx/Apache?
- ❌ Requires installation and configuration
- ❌ Overkill for local dev
- ❌ Doesn't handle dynamic export

### Why Not Flask/Django?
- ❌ Additional dependency
- ❌ More complex than needed
- ✅ Python stdlib `http.server` is sufficient

### Why Not npm serve / http-server?
- ❌ Requires Node.js
- ❌ Can't handle database export
- ❌ Can't route `/api/v1/` to JSON files

### Why Temp Directory with Cleanup?
- ✅ No git clutter
- ✅ Fresh export each run (catches export bugs)
- ✅ Auto-cleanup on exit
- ❌ Slightly slower (can use `--output-dir` to persist)

### Why Copy to `landing/api/`?
The server serves from `landing/` as root directory. Copying API files there:
- ✅ Simplifies routing (relative paths work)
- ✅ Mimics production structure exactly
- ✅ Browser sees same URL structure as GitHub Pages

## Command-Line Interface

```
usage: serve_local.py [-h] [--db DB] [--port PORT] [--no-export]
                      [--output-dir OUTPUT_DIR]

options:
  --db DB               Path to database file (default: courses.db)
  --port PORT           Port to serve on (default: 8000)
  --no-export           Skip database export (use existing API files)
  --output-dir DIR      Output directory for API files (default: temp)
```

**Examples**:

| Command | Use Case |
|---------|----------|
| `pipenv run serve` | Standard development |
| `--db old.courses.db` | Test with different database |
| `--port 3000` | Avoid port conflicts |
| `--no-export` | Skip export if DB unchanged (faster) |
| `--output-dir ./debug` | Persist API files for inspection |

## Logging and Debugging

**Server logs** distinguish between API and static file requests:
```
[API] GET /api/v1/index.json - 200
[API] GET /api/v1/terms/202530/ - 200
[WEB] GET / - 200
[WEB] GET /assets/js/penn-gradient-flash.js - 200
```

**Export logs** show progress:
```
📊 Exporting database: courses.db
   Found 2 terms
   Exporting Summer 2025 (202520)...
   Exporting Spring 2025 (202510)...
✅ Export complete!
   📊 2 terms, 847 courses, 234 instructors
```

## Benefits and Impact

### For Development:
- ✅ **100x faster** iteration cycles (seconds vs minutes)
- ✅ Test with **real data** from any database
- ✅ Catch **export bugs** before deployment
- ✅ No git commits required for testing

### For Debugging:
- ✅ Inspect exported JSON files in temp directory
- ✅ Verify online course fields are exported correctly
- ✅ Test with historical databases
- ✅ Compare different database exports side-by-side

### For Collaboration:
- ✅ New contributors can test immediately
- ✅ Reproducible testing environment
- ✅ Self-documenting (script shows what it's doing)

## Limitations and Future Work

### Current Limitations:
1. **Single-threaded**: Can only handle one request at a time (fine for dev)
2. **No hot-reload**: Must restart server after HTML/JS changes
3. **No HTTPS**: Uses HTTP (fine for localhost)
4. **Blocks terminal**: Must run in dedicated terminal window

### Potential Improvements:
- [ ] **Hot-reload**: Watch `landing/` for changes, auto-refresh browser
- [ ] **Live export**: Detect database changes, re-export automatically
- [ ] **Better logging**: Color-coded, structured logs
- [ ] **Performance**: Cache exports, only re-export changed terms
- [ ] **Validation**: Check exported JSON against TypedDict schemas

## Related ADRs

- **ADR-0002**: Data Storage and Export Architecture (export structure)
- **ADR-0007**: Course Sections and Enrollment Counting (online course fields)
- **ADR-0009**: Claude's Creative Visualizations (what we're testing)
- **ADR-0012**: Fixing Historical Parsing (databases we test with)

## Conclusion

The local development server (`scripts/serve_local.py`) provides a **fast, accurate, and simple** way to test visualizations before deployment. By using the same export code path as production, it ensures:

1. **Confidence**: What works locally works in production
2. **Speed**: 5-second iteration cycles enable rapid development
3. **Accuracy**: Real database exports, not mocked data
4. **Simplicity**: One command to start testing

This tool was essential for developing and testing Claude's Creative Corner visualizations (ADR-0009) and validating the online course export integration (ADR-0007).

**Key Insight**: Development tools should be as simple as possible but no simpler. Python's stdlib was sufficient - no external dependencies needed.

---

**Implementation**: `scripts/serve_local.py` (2025-10-06)
**Usage**: `pipenv run serve`
**Documentation**: This ADR, `scripts/serve_local.py --help`
