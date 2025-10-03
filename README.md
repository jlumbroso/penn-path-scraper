# Penn Path Scraper

**A beautiful CLI for scraping and analyzing Penn's course catalog data.**

Create longitudinal datasets of course enrollments, track registration trends, and explore course data across terms. Built with test-driven development and production-quality architecture.

## ✨ Features

- 🎯 **Complete Course Data**: Scrape courses, instructors, rooms, meeting times, and enrollment
- 📈 **Enrollment Tracking**: Capture enrollment snapshots over time for trend analysis
- 🔍 **Interactive Search**: Beautiful search interface with fuzzy matching
- 🎬 **Demo Mode**: Quick demonstration with live scraping + search
- 🌈 **Beautiful CLI**: Rich formatting, progress bars, and intuitive interface
- 🧪 **Well-Tested**: 70 unit tests, 92% code coverage, TDD approach
- 📊 **Multi-Term Support**: Scrape current + next term for advance registration data
- 📦 **JSON Export**: Static feeds for GitHub Pages and data visualization
- 🤖 **Automated Scraping**: GitHub Actions workflow for daily updates
- 🗄️ **Historical Preservation**: Keep old terms while refreshing current data

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd penn-path-scraper

# Install dependencies
pipenv install

# Try the demo!
pipenv run demo
```

### Demo Mode

The fastest way to see the scraper in action:

```bash
pipenv run demo

# Or with a specific school
pipenv run scraper demo --school W  # Wharton
```

This will:
1. Scrape one school's courses for the current term
2. Enter an interactive search mode
3. Let you explore the data in real-time

## 📖 Usage

### Scraping

Scrape courses from Penn's catalog:

```bash
# Scrape current term for all schools
pipenv run scraper scrape

# Scrape specific term
pipenv run scraper scrape 202530  # Fall 2025

# Scrape specific schools only
pipenv run scraper scrape --schools E,W,A  # Engineering, Wharton, Arts & Sciences

# Include next term (for advance registration data)
pipenv run scraper scrape --next-term

# Skip enrollment snapshots
pipenv run scraper scrape --no-snapshots
```

### Searching

Search through scraped courses:

```bash
# Interactive search
pipenv run scraper search

# Direct search
pipenv run scraper search "data structures"

# Search by instructor
pipenv run scraper search lumbroso

# Filter by term
pipenv run scraper search "networks" --term 202530

# Limit results
pipenv run scraper search "intro" --limit 50
```

### Enrollment Tracking

View enrollment history for a course:

```bash
# Track a specific course
pipenv run scraper track "CIS 1210"

# Track in specific term
pipenv run scraper track "CIS 1210" --term 202530
```

### Statistics

View database stats:

```bash
pipenv run scraper stats
```

### JSON Export

Export course data to JSON for static hosting:

```bash
# Export all terms to ./data directory
pipenv run scraper export

# Export to custom directory
pipenv run scraper export --output-dir ./public

# Export specific term only
pipenv run scraper export --term 202530
```

Exported data includes:
- **index.json**: List of all available terms with metadata
- **{term_code}.json**: Complete course data for each term
  - Course details (code, title, CRN, section, etc.)
  - Enrollment history (time-series snapshots)
  - Instructors and meeting times
  - Linked sections

Perfect for:
- GitHub Pages hosting
- Static site generators
- Frontend data visualization
- Historical analysis

## 🤖 Automated Scraping

The repository includes a GitHub Actions workflow that automatically:

1. **Runs daily at 6 AM UTC** (2 AM ET)
2. **Scrapes current + next term** for advance registration data
3. **Exports to JSON** in the `./data` directory
4. **Commits changes** to the repository
5. **Preserves historical data** across runs

### Manual Trigger

You can manually trigger the workflow from the Actions tab in GitHub.

### Historical Preservation

The scraper **preserves old terms** when refreshing current/next term data. This means you build a comprehensive longitudinal dataset over time without losing historical information.

## 🏗️ Architecture

### Clean Separation of Concerns

```
src/
├── types.py           # TypedDict definitions for type safety
├── models.py          # Peewee ORM models (9 models)
├── parsers.py         # HTML parsing utilities
├── api_client.py      # Penn Courses API client
├── persistence.py     # Data transformation & persistence
├── scraper.py         # Orchestration layer
├── export.py          # JSON export for static feeds
└── cli.py             # Beautiful Click CLI
```

### Database Schema

**SQLite database** with the following models:

- `Term`: Academic terms (Fall, Spring, Summer)
- `School`: Penn schools (Engineering, Wharton, etc.)
- `Course`: Course sections with current enrollment
- `Instructor`: Deduplicated instructor records
- `CourseInstructor`: Many-to-many relationship
- `Meeting`: Course meeting times and locations
- `LinkedSection`: Related sections (lectures ↔ recitations)
- `EnrollmentSnapshot`: Time-series enrollment data
- `ScrapeLog`: Scraping activity logs

### Data Flow

```
Penn API → API Client → Parsers → CourseDict → Persistence → Database
                                                              ↓
                                                         Snapshots
```

## 🧪 Testing

We follow TDD with comprehensive test coverage:

```bash
# Run all unit tests (70 tests)
pipenv run test

# Run with coverage report (92% coverage)
pipenv run coverage

# Generate HTML coverage report
pipenv run coverage-html
open htmlcov/index.html

# Run tests in parallel (fast!)
pipenv run test-parallel

# Type checking
pipenv run typecheck
```

### Test Structure

- `tests/unit/` - Fast unit tests with mocked APIs
- `tests/fixtures/` - Real API response samples
- Uses pytest-mock for clean mocking
- 70/70 tests passing, 0 warnings

## 📊 Available Schools

| Code | School |
|------|--------|
| A | School of Arts & Sciences |
| C | Annenberg School for Communication |
| D | School of Dental Medicine |
| E | School of Engineering and Applied Science |
| F | Stuart Weitzman School of Design |
| G | Graduate School of Education |
| L | Penn Carey Law |
| M | Perelman School of Medicine |
| N | School of Nursing |
| S | School of Social Policy & Practice |
| V | School of Veterinary Medicine |
| W | The Wharton School |

## 🔧 Development

### Code Quality Standards

- **Type Safety**: Full TypedDict coverage, mypy compatible
- **Import Style**: No `from` imports - full namespaces only
- **Commit Format**: Conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- **Documentation**: ADRs for architectural decisions
- **Testing**: TDD approach, pytest-mock, 90%+ coverage

### Development Commands

```bash
# Quick iteration
pipenv run check-fast     # Stop on first test failure
pipenv run test-parallel  # Fast parallel testing

# Coverage analysis
pipenv run coverage       # Terminal report
pipenv run coverage-html  # HTML report

# Type checking
pipenv run typecheck      # Run mypy

# CLI testing
pipenv run scraper --help
pipenv run demo
```

### Adding New Features

1. Write tests first (TDD)
2. Run `pipenv run test-unit`
3. Implement feature
4. Ensure tests pass
5. Update coverage: `pipenv run coverage`
6. Commit with conventional format

## 📝 Configuration

### Database Location

Default: `~/.penn-scraper/courses.db`

Override with `--db` flag:

```bash
pipenv run scraper --db /custom/path/courses.db scrape
```

### Rate Limiting

API client includes:
- User agent rotation
- Configurable delay between requests (default: 0.5s)
- Graceful error handling

## 🎯 Use Cases

### Course Registration Analytics

```bash
# Scrape every day during registration
pipenv run scraper scrape --next-term

# Track popular courses
pipenv run scraper track "CIS 1210"
```

### Department Research

```bash
# Scrape specific schools
pipenv run scraper scrape --schools E

# Search by department
pipenv run scraper search "CIS"
```

### Enrollment Forecasting

```bash
# Collect snapshots over time
pipenv run scraper scrape  # Run periodically

# Analyze trends
pipenv run scraper track "NETS 2130"
```

## 📚 Documentation

- `docs/TESTING.md` - Comprehensive testing guide
- `docs/adr/` - Architecture Decision Records
- `docs/prompts/CLICK.md` - CLI best practices
- `docs/prompts/PYTEST.md` - Testing patterns

## 🤝 Contributing

1. Follow TDD - write tests first
2. Maintain type safety with TypedDict
3. Use full namespace imports
4. Write ADRs for significant decisions
5. Keep coverage above 90%

## 🏆 Project Highlights

- **70 unit tests, all passing**
- **92% code coverage**
- **Zero warnings**
- **Beautiful CLI with rich-click**
- **Production-ready architecture**
- **Automated GitHub Actions workflow**
- **JSON export for static feeds**
- **Historical data preservation**
- **Comprehensive error handling**
- **Structured logging with structlog**

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [rich-click](https://github.com/ewels/rich-click) - Beautiful CLI output
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Peewee](http://docs.peewee-orm.com/) - Lightweight ORM
- [pytest](https://pytest.org/) - Testing framework
- [structlog](https://www.structlog.org/) - Structured logging

---

**Made with ❤️ for Penn Course Research**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
