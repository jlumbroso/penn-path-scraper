# Penn Courses API Structure and Endpoints

* Status: accepted
* Deciders: Jérémie Lumbroso (user), Claude Sonnet 4.5 (model)
* Date: 2025-10-01

Technical Story: Initial API exploration to understand the courses.upenn.edu API structure for building a comprehensive course catalog scraper.

## Context and Problem Statement

We need to scrape the Penn course catalog (https://courses.upenn.edu/) to build a longitudinal dataset that captures course information across all terms, departments, and programs, including enrollment data over time. How can we efficiently access all course data through the website's API?

## Decision Drivers

* Need to collect comprehensive course data (instructors, rooms, times, recitations, enrollments)
* Must track enrollment changes over time (periodic scraping)
* Should support historical data (multiple terms/semesters)
* Must be error-tolerant and scalable
* Need to understand the complete API surface area

## Considered Options

* Option 1: Scrape HTML pages directly using BeautifulSoup
* Option 2: Use the JSON API endpoints (discovered through browser network inspection)
* Option 3: Use a headless browser (Selenium/Playwright) to interact with the UI

## Decision Outcome

Chosen option: "Option 2: Use the JSON API endpoints", because it provides structured data, is more reliable than HTML parsing, and is more efficient than headless browsing.

### Positive Consequences

* Clean, structured JSON responses that are easy to parse
* Faster execution compared to headless browsers
* More stable than HTML parsing (less likely to break with UI changes)
* Can collect historical data going back to Fall 2022

### Negative Consequences

* API is undocumented and could change without notice
* Requires understanding of internal API structure through reverse engineering
* Some fields contain HTML that needs further parsing (seats, meeting_html)

## API Structure Documentation

### Base URL
```
https://courses.upenn.edu/api/
```

### Available Endpoints

#### 1. Search Endpoint
**URL**: `?page=fose&route=search&coll={SCHOOL_CODE}`

**Method**: POST

**Request Body**:
```json
{
  "other": {
    "srcdb": "202530"
  },
  "criteria": [
    {
      "field": "coll",
      "value": "W"
    }
  ]
}
```

**Response**: Returns list of courses matching the search criteria
```json
{
  "srcdb": "202530",
  "count": 658,
  "results": [
    {
      "key": "34",
      "code": "ACCT 1010",
      "title": "Accounting and Financial Reporting",
      "crn": "60201",
      "meetingTimes": "[{\"meet_day\":\"1\",\"start_time\":\"830\",\"end_time\":\"959\"}]",
      "no": "001",
      "total": "8",
      "schd": "LEC",
      "stat": "A",
      "instr": "L. Hail",
      "start_date": "2025-08-26",
      "end_date": "2025-12-08",
      "linked_crns": "",
      ...
    }
  ]
}
```

**Search Criteria Options**:
- `field: "coll"` - Search by school/college
- `field: "keyword"` - Search by keyword (instructor, course name, etc.)

#### 2. Course Details Endpoint
**URL**: `?page=fose&route=details`

**Method**: POST

**Request Body**:
```json
{
  "group": "code:NETS 2130",
  "key": "crn:80595",
  "srcdb": "202530",
  "matched": "crn:80595",
  "userWithRolesStr": "!!!!!!"
}
```

**Response**: Returns detailed information about a specific course section
```json
{
  "key": "7960",
  "code": "NETS 2130",
  "section": "001",
  "crn": "80595",
  "title": "Crowdsourcing and Human Computation",
  "seats": "<strong>Maximum Enrollment:</strong> <span class=\"seats_max\">50</span> / <strong>Seats Avail:</strong> <span class=\"seats_avail\">2</span>",
  "description": "Crowdsourcing and human computation are emerging fields...",
  "meeting_html": "<div class=\"meet\">TR 1:45pm-3:14pm<span class=\"meet-room-202530\"> in <a href=\"...\">WLNT 401B</a></span><span class=\"meet-dates\"> (8/26 to 12/8)</span></div>",
  "instructordetail_html": "<div class=\"instructor-detail\">Jeremie Lumbroso</div>",
  "linked_crns": "",
  "allInGroup": [...],
  ...
}
```

**Key Fields for Scraping**:
- `seats`: Contains enrollment data (max enrollment and seats available) as HTML
- `meeting_html`: Contains room and time information as HTML
- `instructordetail_html`: Contains instructor name(s) as HTML
- `linked_crns`: CRNs of linked sections (e.g., recitations)
- `allInGroup`: Array of all sections for this course

#### 3. Filter Data Endpoint
**URL**: `?page=fose&route=load-filter-data`

**Method**: POST

**Request Body**:
```json
{
  "srcdb": "202530"
}
```

**Response**: Returns available filter options for a given term

#### 4. Keyword Search Endpoint
**URL**: `?page=fose&route=search&keyword={keyword}`

**Method**: POST

**Request Body**:
```json
{
  "other": {
    "srcdb": "202530"
  },
  "criteria": [
    {
      "field": "keyword",
      "value": "lumbroso"
    }
  ]
}
```

**Response**: Returns courses matching the keyword

### School Codes (coll parameter)

| Code | School Name |
|------|-------------|
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

### Term Codes (srcdb parameter)

Format: `YYYY[10|20|30]`
- `10` = Spring semester
- `20` = Summer semester
- `30` = Fall semester

**Available Terms** (as of 2025-10-01):
- `202530` = Fall 2025
- `202520` = Summer 2025
- `202510` = Spring 2025
- `202430` = Fall 2024
- `202420` = Summer 2024
- `202410` = Spring 2024
- `202330` = Fall 2023
- `202320` = Summer 2023
- `202310` = Spring 2023
- `202230` = Fall 2022
- `202220` = Summer 2022

### Enrollment Data Extraction

Enrollment data is in the `seats` field as HTML:
```html
<strong>Maximum Enrollment:</strong> <span class="seats_max">50</span> /
<strong>Seats Avail:</strong> <span class="seats_avail">2</span>
```

**Calculation**: Current enrollment = `seats_max - seats_avail` (e.g., 50 - 2 = 48 students)

### Room Information Extraction

Room data is in the `meeting_html` field as HTML:
```html
<div class="meet">TR 5:15pm-6:44pm
  <span class="meet-room-202530"> in
    <a href="https://www.facilities.upenn.edu/maps/locations/towne-building" target="_blank">
      TOWN 217
    </a>
  </span>
  <span class="meet-dates"> (8/26 to 12/8)</span>
</div>
```

### Meeting Times Structure

The `meetingTimes` field contains JSON-encoded array:
```json
[
  {
    "meet_day": "1",
    "start_time": "1715",
    "end_time": "1844"
  },
  {
    "meet_day": "3",
    "start_time": "1715",
    "end_time": "1844"
  }
]
```

**Day codes**:
- `0` = Sunday
- `1` = Monday
- `2` = Tuesday
- `3` = Wednesday
- `4` = Thursday
- `5` = Friday
- `6` = Saturday

**Time format**: 24-hour military time (e.g., `1715` = 5:15 PM)

### Recitations and Linked Sections

Courses with recitations have:
- `linked_crns`: Comma-separated list of linked section CRNs
- Lecture sections link to recitation CRNs
- Recitation sections link back to lecture CRNs

Example:
- Lecture CIT 5920-001 (CRN 61969): `"linked_crns": "61970"`
- Recitation CIT 5920-201 (CRN 61970): `"linked_crns": "61969"`

## Implementation Notes

### Scraping Strategy

1. **Iterate through all schools** (12 school codes)
2. **For each school, iterate through all terms** (11+ terms available)
3. **Use search endpoint** to get list of courses for school+term
4. **For each course, use details endpoint** to get full information
5. **Parse HTML fields** (seats, meeting_html, instructordetail_html) to extract structured data
6. **Store enrollment with timestamp** for longitudinal tracking

### Required Libraries

- `requests` or `urllib` for HTTP requests
- `json` for parsing responses
- `beautifulsoup4` for parsing HTML fields
- `fake-useragent` for user agent rotation (error tolerance)
- `structlog` for logging
- `click` for CLI interface

### Error Handling Considerations

- Handle rate limiting (if implemented by server)
- Retry failed requests with exponential backoff
- Handle malformed HTML in fields
- Handle missing/null values in API responses
- Log failed requests for later retry

## Links

* Related: [CLAUDE.md](/CLAUDE.md) - Project overview and guidelines
* Related: [more-api.md](/docs/prompts/more-api.md) - Additional API examples provided by user
