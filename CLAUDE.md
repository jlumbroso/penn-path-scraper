# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

USER: Jérémie Lumbroso

## RULE #1: COMMIT ALL DISCUSSION IMMEDIATELY TO AN ADR OR AIDR!!

**Core Principle**: Our conversations are precious and capture decision-making. **Never let discussion stay only in conversation** - commit it to documents immediately.

### The Workflow

**When the user gives you a stream-of-consciousness dump**:

1. **Read the dump** (use subagents for large files)
2. **Chunk into distinct threads** - identify separate topics/decisions
3. **Create an ADR for each thread** using [`docs/adr/template-with-human-ai-collaboration.md`](docs/adr/template-with-human-ai-collaboration.md)
4. **Seed each ADR** with relevant extract from the user's dump
5. **Ask for supporting materials** using precise XML tags: `<code-example>`, `<api-call>`, `<documentation>`, `<url>`
6. **Iterate on each ADR separately** - track evolution with iteration numbers

**Key Patterns**:
- Use `--------------------` dividers to separate sections
- Use XML tags (starting on their own line) for easy grepping:
  - `<code-example>` - Code snippets
  - `<api-call>` - API request/response specs
  - `<documentation>` - Reference docs
  - `<url>` - External resources
  - `<model-question>` - Your clarifying questions (with `<answer>` tags for human responses)
- Mark deciders: user (Jérémie Lumbroso) and model (Sonnet 4.5 or Opus 4.1)
- Increment iteration number each time ADR is updated
- Navigate Q&A: `grep '<answer status="unanswered"'` to find questions needing answers

**Why This Matters**:
- ✅ Stream-of-consciousness preserved in version control (not lost after compaction)
- ✅ Model has agency to engage strategically with information
- ✅ Each ADR becomes focused discussion of one topic
- ✅ Shared artifacts persist across context windows
- ✅ Future collaborators (including future instances of you!) can understand decisions

**Templates**:
- Standard ADR: [`docs/adr/template.md`](docs/adr/template.md)
- Human-AI Collaboration ADR: [`docs/adr/template-with-human-ai-collaboration.md`](docs/adr/template-with-human-ai-collaboration.md)

**See Also**: [`docs/SHARED-WORKING-PRACTICES.md`](docs/SHARED-WORKING-PRACTICES.md) for our collaboration philosophy 

## Git Commit Message Format

Use conventional commit format: `<type>: <subject>` (lowercase)

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to build process, auxiliary tools, dependencies
- `style`: Code style changes (formatting, semicolons, etc)
- `perf`: Performance improvements
- `ci`: CI configuration changes
- `build`: Build system or external dependency changes

## PEP 8 Python Package

- Only use `import ...` no `from` extractions, so full namespaces are used and code can easily be copy-pasted and locally everything is resolved (this is my rule)

- Organize in the right order: As per PEP 8, the style guide for Python code, imports should be grouped at the top of the file in the following order: 
  - Standard library imports.
  - Related third-party imports.
  - Local application/library-specific imports.

- A blank line should separate each group of imports for readability. Within each group, the import statements should be sorted alphabetically. 

## Project Overview

This is a scraper for the course catalog at Penn. This is to create a longitudinal dataset.

We will collect all data:
- across all terms
- for every department/program
- for every course
- we collect all the information
- with the instructors
- the rooms
- the times
- the recitations
- the enrollments

and the important part is want to be able to record variations in enrollment, so we want a current enrollment field, but also a list of [<scrape time>, <enrollment at that time>]

The scraper will be run periodically and generate JSON file or files that will be served statically. We need to determine that infrastructure. It would be nice to run a script on GitHub Actions on a cronjob (like once a day), and have a comprehensive scraping generate a JSON file. The scraping should be error-tolerant. Username cycling, maybe a nice logging.

## Website info

The website is: https://courses.upenn.edu/

The best way to extract the catalog is with querying the catalog for each school.

It seems to be doing API queries

fetch("https://courses.upenn.edu/api/?page=fose&route=search&coll=G", {
  "headers": {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9,fr;q=0.8",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"99\", \"Google Chrome\";v=\"139\", \"Chromium\";v=\"139\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-requested-with": "XMLHttpRequest"
  },
  "referrer": "https://courses.upenn.edu/",
  "body": "%7B%22other%22%3A%7B%22srcdb%22%3A%22202530%22%7D%2C%22criteria%22%3A%5B%7B%22field%22%3A%22coll%22%2C%22value%22%3A%22G%22%7D%5D%7D",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
});

returns:

contents of query-output.json

The possible values of coll are:

<select id="crit-coll" class="form-control" data-type="single-column" data-enpassusermodified="yes">
<option value="">School</option><option value="C">Annenberg School for Communication</option><option value="G">Graduate School of Education</option><option value="L">Penn Carey Law</option><option value="M">Perelman School of Medicine</option><option value="A">School of Arts &amp; Sciences</option><option value="D">School of Dental Medicine</option><option value="E">School of Engineering and Applied Science</option><option value="N">School of Nursing</option><option value="S">School of Social Policy &amp; Practice</option><option value="V">School of Veterinary Medicine</option><option value="F">Stuart Weitzman School of Design</option><option value="W">The Wharton School</option></select>


## Possible libraries
Using pipenv:
- structlog for logging
- click (and extensions listed in ./docs/CLICK.md) for command line interface
- pyyaml for settings perhaps
- fake-useragent (or whatever its called?)
- requests
- pytest
- bs4

maybe you think we need to use a database as a backend to store the data.


## Development Commands

```bash
# Testing
pipenv run test                    # Run unit tests (default)
pipenv run test-unit               # Fast unit tests
pipenv run test-integration        # Real API tests
pipenv run test-all                # Complete test suite (unit + integration)
pipenv run check-fast              # Fast fail: stop on first failure

# Coverage
pipenv run coverage                # Coverage report for unit tests (92% current)
pipenv run coverage-html           # Generate HTML coverage report
pipenv run coverage-all            # Coverage for all tests

# Code Quality
pipenv run typecheck               # Run mypy type checker

# Performance
pipenv run test-parallel           # Run tests in parallel (fast)

# Documentation
# See docs/TESTING.md for detailed testing guide
```

## Testing Strategy

### Unit Tests
- Mock all external API calls
- Use fixtures from real API responses (stored in `tests/fixtures/`)
- Should run fast without network access

### Integration Tests
- Test against real endpoints
- Use environment variable to enable: `RUN_INTEGRATION_TESTS=true`
- Should gracefully skip if endpoints are unavailable

## Type Safety

- Use TypedDict for all data structures (in `src/types.py`)
- No `from` imports - use full namespaces
- Return types should be fully specified
- Provider methods should use the defined TypedDict types

## Project Structure

```
├── src/
│   ├── types.py       # TypedDict definitions
├── tests/
│   ├── unit/          # Fast tests with mocked data
│   └── integration/   # Tests against real APIs
├── scripts/           # Development utilities
└── docs/adr/          # Architecture Decision Records
```

