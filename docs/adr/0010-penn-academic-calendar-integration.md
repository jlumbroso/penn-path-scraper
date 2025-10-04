# ADR-0010: Penn Academic Calendar Integration

**Date**: 2025-10-04
**Status**: Proposed
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Enhancing API with temporal metadata for registration analysis

## Context and Problem Statement

During our creative visualization brainstorming, Jérémie suggested:

> "You could scrape from https://almanac.upenn.edu/penn-academic-calendar to generate calendars for each term - so that the API has a dataset that lets them know when sign ups start, advanced registration, etc. It could be super useful."

**The Opportunity**: Contextual temporal data unlocks time-based analysis:
- "Registration Rush" visualization (time-to-fill calculations)
- Drop/add period analysis
- Pre-registration vs general registration comparison
- Historical trend analysis aligned with academic calendar

## Data Source

**URL**: https://almanac.upenn.edu/penn-academic-calendar

**Content**: Per-term academic calendar including:
- Advanced registration start/end
- General registration (drop/add) period
- Course selection deadlines
- Semester start/end dates
- Exam periods
- Break periods

**Example** (Fall 2024):
```
Advanced Registration: April 1-12, 2024
Drop/Add Period: August 26 - September 9, 2024
Classes Begin: August 28, 2024
Midterm Break: October 10-13, 2024
Last Day of Classes: December 10, 2024
Final Exams: December 12-19, 2024
```

## Proposed Data Structure

### `/api/v1/calendars/index.json`

Master index of all scraped calendars:

```json
{
  "calendars": [
    {
      "term_code": "202530",
      "term_name": "Fall 2025",
      "academic_year": "2025-2026",
      "url": "/api/v1/calendars/202530.json"
    }
  ],
  "last_updated": "2025-10-04T12:00:00Z"
}
```

### `/api/v1/calendars/202530.json`

Per-term calendar with structured events:

```json
{
  "term_code": "202530",
  "term_name": "Fall 2025",
  "academic_year": "2025-2026",
  "events": [
    {
      "event_type": "advanced_registration",
      "name": "Advanced Registration Period",
      "start_date": "2025-04-01",
      "end_date": "2025-04-12",
      "description": "Currently enrolled students register for fall courses"
    },
    {
      "event_type": "drop_add",
      "name": "Drop/Add Period",
      "start_date": "2025-08-25",
      "end_date": "2025-09-08",
      "description": "Students may add/drop courses without penalty"
    },
    {
      "event_type": "classes_begin",
      "name": "First Day of Classes",
      "start_date": "2025-08-27",
      "description": "Fall semester instruction begins"
    },
    {
      "event_type": "course_selection_deadline",
      "name": "Course Selection Deadline",
      "start_date": "2025-09-08",
      "description": "Last day to add/drop without 'W' on transcript"
    },
    {
      "event_type": "classes_end",
      "name": "Last Day of Classes",
      "start_date": "2025-12-09",
      "description": "Fall semester instruction ends"
    },
    {
      "event_type": "finals",
      "name": "Final Examination Period",
      "start_date": "2025-12-11",
      "end_date": "2025-12-18"
    }
  ],
  "source_url": "https://almanac.upenn.edu/penn-academic-calendar#fall-2025",
  "last_updated": "2025-10-04T12:00:00Z"
}
```

## Scraping Strategy

### Approach 1: Parse HTML Tables

Penn Almanac presents calendars in HTML tables by semester.

**Scraper implementation**:
```python
import requests
import bs4
import datetime
import re

def scrape_penn_calendar(year):
    url = f"https://almanac.upenn.edu/penn-academic-calendar"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.content, 'html.parser')

    # Find sections by semester
    calendars = []
    for section in soup.find_all('h3'):  # Assuming h3 headers like "Fall 2025"
        term_name = section.text.strip()
        term_code = parse_term_code(term_name)

        # Find table following this header
        table = section.find_next('table')
        if not table:
            continue

        events = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all('td')
            if len(cells) >= 2:
                event_name = cells[0].text.strip()
                date_str = cells[1].text.strip()

                event = parse_event(event_name, date_str, term_code)
                if event:
                    events.append(event)

        calendars.append({
            'term_code': term_code,
            'term_name': term_name,
            'events': events
        })

    return calendars

def parse_term_code(term_name):
    # "Fall 2025" → "202530"
    # "Spring 2025" → "202520"
    # "Summer 2025" → "202510"
    season_map = {'Fall': '30', 'Spring': '20', 'Summer': '10'}
    match = re.match(r'(\w+)\s+(\d{4})', term_name)
    if match:
        season, year = match.groups()
        return year + season_map.get(season, '00')
    return None

def parse_event(event_name, date_str, term_code):
    # Parse date strings like:
    # "April 1-12, 2024"
    # "August 28, 2024"
    # "December 12-19, 2024"

    event_type = classify_event(event_name)

    # Extract dates using regex
    # (Implementation would handle various date formats)

    return {
        'event_type': event_type,
        'name': event_name,
        'start_date': start_date,  # ISO format
        'end_date': end_date,      # ISO format or null
        'description': generate_description(event_name)
    }

def classify_event(event_name):
    keywords = {
        'advanced_registration': ['advanced registration', 'advance registration'],
        'drop_add': ['drop/add', 'add/drop', 'course selection'],
        'classes_begin': ['classes begin', 'instruction begins'],
        'classes_end': ['classes end', 'instruction ends', 'last day of classes'],
        'finals': ['final exam', 'finals week'],
        'break': ['spring break', 'fall break', 'thanksgiving']
    }

    event_lower = event_name.lower()
    for event_type, patterns in keywords.items():
        if any(p in event_lower for p in patterns):
            return event_type

    return 'other'
```

### Approach 2: Structured Data Extraction with LLM

If HTML parsing is brittle (tables change format), use LLM to extract structured data:

```python
def extract_calendar_with_llm(html_content, term_name):
    prompt = f"""
    Extract academic calendar events from this HTML for {term_name}.
    Return JSON array of events with fields:
    - event_type (advanced_registration | drop_add | classes_begin | classes_end | finals | break | other)
    - name (event name from calendar)
    - start_date (YYYY-MM-DD format)
    - end_date (YYYY-MM-DD format, null if single day)
    - description (brief description)

    HTML:
    {html_content}
    """

    # Call LLM API with structured output
    response = call_llm(prompt, response_format="json")
    return json.loads(response)
```

**Pros**: Robust to format changes, handles natural language
**Cons**: Requires API calls, slower, adds dependency

**Recommendation**: Start with HTML parsing, fall back to LLM if parsing fails.

## Use Cases Enabled

### 1. Registration Rush Visualization

With calendar data, calculate time-to-fill:

```javascript
function calculateRegistrationMetrics(course, calendar) {
    const advRegStart = calendar.events.find(e => e.event_type === 'advanced_registration').start_date;
    const dropAddEnd = calendar.events.find(e => e.event_type === 'drop_add').end_date;

    // Find when course hit certain enrollment milestones
    const snapshots = course.enrollment_history.snapshots;

    const milestones = {
        '25%': findTimeToReach(snapshots, course.max_enrollment * 0.25, advRegStart),
        '50%': findTimeToReach(snapshots, course.max_enrollment * 0.50, advRegStart),
        '75%': findTimeToReach(snapshots, course.max_enrollment * 0.75, advRegStart),
        '100%': findTimeToReach(snapshots, course.max_enrollment, advRegStart)
    };

    return {
        courseCode: course.code,
        milestones,
        filledDuringAdvReg: snapshots.some(s => s.enrolled >= course.max_enrollment && s.timestamp < dropAddEnd)
    };
}
```

**Visualization**: Timeline chart showing when courses filled

### 2. Drop/Add Analysis

Compare enrollment changes during drop/add period:

```javascript
function analyzeDropAddBehavior(course, calendar) {
    const dropAddStart = new Date(calendar.events.find(e => e.event_type === 'drop_add').start_date);
    const dropAddEnd = new Date(calendar.events.find(e => e.event_type === 'drop_add').end_date);

    const snapshotsDuring = course.enrollment_history.snapshots.filter(s => {
        const timestamp = new Date(s.timestamp);
        return timestamp >= dropAddStart && timestamp <= dropAddEnd;
    });

    const enrollmentStart = snapshotsDuring[0]?.enrolled || 0;
    const enrollmentEnd = snapshotsDuring[snapshotsDuring.length - 1]?.enrolled || 0;

    return {
        courseCode: course.code,
        dropAddChange: enrollmentEnd - enrollmentStart,
        netGain: enrollmentEnd > enrollmentStart,
        volatility: calculateVolatility(snapshotsDuring)
    };
}
```

**Insight**: Which courses gain students during drop/add? Which lose students?

### 3. Academic Timeline Visualization

Show enrollment progression overlaid on academic calendar:

```
Advanced Registration │ Drop/Add Period    │ Mid-term │ Finals
─────────────────────────────────────────────────────────────
April 1-12            │ Aug 25 - Sep 8    │ Oct 10   │ Dec 12-19

Enrollment: ▁▂▃▄▅▆▇███████████──────────────────────────
              ^                ^           ^
             Opens          Deadline    No changes
```

## Implementation Plan

### Phase 1: Scraper Development
- [ ] Implement HTML parser for almanac.upenn.edu
- [ ] Handle date parsing (various formats)
- [ ] Classify events into standard types
- [ ] Generate JSON exports

### Phase 2: API Integration
- [ ] Create `/api/v1/calendars/` endpoint structure
- [ ] Add calendar data to deployment workflow
- [ ] Version control for calendar data

### Phase 3: Visualization Integration
- [ ] Add calendar context to enrollment visualizations
- [ ] Implement "Registration Rush" timeline chart
- [ ] Add drop/add analysis visualization

## Open Questions

1. **Historical calendars**: How far back does Penn Almanac archive calendars? Can we scrape historical data?

2. **Calendar changes**: If Penn updates a calendar (e.g., extends drop/add), how do we handle versioning?

3. **Multiple calendars**: Some schools (Wharton, Law) have different calendars. Do we need school-specific calendars?

4. **Timezone**: All dates in UTC or EST? Penn operates in EST.

5. **Event granularity**: Should we capture hour-level precision (e.g., "Registration opens 8am") or just dates?

## Success Criteria

- [ ] Calendar data for all current and upcoming terms
- [ ] Automated scraping on schedule (monthly?)
- [ ] Integration with enrollment history for time-based analysis
- [ ] At least one visualization using calendar data

---

**Related ADRs**:
- ADR-0009: Creative Visualizations (Registration Rush requires calendar data)
