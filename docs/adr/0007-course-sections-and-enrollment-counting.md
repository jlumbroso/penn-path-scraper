# ADR-0007: Course Sections and Enrollment Counting Strategy

**Date**: 2025-10-04
**Status**: Proposed (Revision 2 - Data-Driven Analysis)
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Visualization analysis, actual data structure review

## Context and Problem Statement

**CRITICAL CORRECTION**: My initial proposal (Revision 1) incorrectly suggested using heuristics to infer section types from section numbers. Jérémie correctly pointed out that **the data already contains explicit `schedule_type` fields**. This ADR is completely rewritten based on actual data structure.

### Actual Data Structure (from `tests/fixtures/sample_output.json`):

Example: **CIS 1600 - Mathematical Foundations of Computer Science**

```json
{
  "crn": "61699",
  "section": "001",
  "schedule_type": "Lecture",  // ← EXPLICIT FIELD!
  "credits": "1",               // ← Lectures have credits
  "instructors": ["Rajiv Gandhi"],
  "current_enrollment": {
    "enrolled": 34,
    "max_enrollment": 140
  },
  "linked_sections": ["61701", "61702", ...]  // ← Links to recitations
}
```

```json
{
  "crn": "61701",
  "section": "201",
  "schedule_type": "Recitation",  // ← EXPLICIT FIELD!
  "credits": "0",                  // ← Recitations have 0 credits
  "instructors": [],               // ← Often no instructor listed
  "current_enrollment": {
    "enrolled": 4,
    "max_enrollment": 16
  },
  "linked_sections": ["61699", "61700"]  // ← Links to lectures
}
```

### Key Data Insights:

**CIS 1600 Enrollment Breakdown**:
- 2 Lecture sections (001, 002): 34 + 128 = **162 students** enrolled
- 17 Recitation sections (201-218): Sum = **147 students** enrolled

**The Mismatch (162 vs 147)**:
- 15 students enrolled in lecture but not yet in recitation
- Students must register for BOTH lecture AND recitation
- Recitations have limited capacity (16 per section)

### The Core Counting Question:

**What does "enrollment" mean in different contexts?**

1. **School-level aggregates** ("How many students is Engineering teaching?")
   - Should count **unique students**, not seats
   - Counting both lecture + recitation **double-counts** the same students

2. **Contact hours / teaching load** ("How much teaching is happening?")
   - Lectures: 2 hours/week
   - Recitations: 1 hour/week
   - Both represent real teaching effort

3. **Course demand** ("Is this course popular?")
   - Lecture enrollment = students who want the course
   - Recitation enrollment = students who completed registration

4. **Fill rate analysis** ("Are courses at capacity?")
   - Lecture fill rate: 162 / 290 = 56%
   - Recitation fill rate: 147 / 272 = 54%
   - Similar rates suggest balanced capacity planning

## Decision Drivers

1. **Semantic Accuracy**: "Students taking CIS 1600" should mean unique individuals, not seat-counts
2. **Data Integrity**: Use explicit fields (`schedule_type`, `credits`, `linked_sections`) not heuristics
3. **Multiple Metrics**: Different questions need different counting approaches
4. **Teaching Recognition**: Both lectures and recitations represent real pedagogical work
5. **Transparency**: Users should understand what's being counted

## Analysis of Actual Data Structure

### Fields Available (No Heuristics Needed!):

| Field | Values | Use for Counting |
|-------|--------|------------------|
| `schedule_type` | "Lecture", "Recitation", "Laboratory", "Seminar", etc. | Primary filter |
| `credits` | "1", "0.5", "0" | Lectures have credits, recitations often don't |
| `linked_sections` | Array of CRNs | Explicit relationships |
| `instructors` | Array of names | Lectures typically have instructors, recitations may not |

### Enrollment Patterns Observed:

**Pattern 1: Lecture + Recitation Requirement**
- Course: CIS 1600
- Structure: 2 lectures, 17 recitations
- Student experience: Must enroll in 1 lecture + 1 recitation
- **Counting rule**: Use lecture enrollment for unique students

**Pattern 2: Multiple Lecture Sections (Same Content)**
- Course: CIS 1600
- Sections: 001 (34 enrolled), 002 (128 enrolled)
- Student experience: Choose one lecture section
- **Counting rule**: Sum across lecture sections

**Pattern 3: Recitation Variability**
- Recitation capacity: Consistent (16 per section)
- Recitation enrollment: Highly variable (0 to 16)
- Reflects: Student scheduling preferences, registration timing
- **Counting rule**: Recitations are a separate metric (contact hours)

## Considered Options

### Option 1: Count Only Lectures (RECOMMENDED for Student Counts)

**Approach**: When calculating "students taking a course" or "school enrollment", only count lecture sections.

**Rationale**:
- Avoids double-counting students
- Reflects unique individuals
- Lectures have `credits > 0`
- Lectures have `instructors` (typically)

**Implementation**:
```python
def count_unique_students(sections):
    lectures = [s for s in sections if s['schedule_type'] == 'Lecture']
    return sum(s['current_enrollment']['enrolled'] for s in lectures)
```

**Use cases**:
- ✅ School-level enrollment totals
- ✅ Department size comparisons
- ✅ "Top Courses by Enrollment" visualization
- ✅ Course popularity rankings

### Option 2: Separate Metrics for Lectures vs Recitations

**Approach**: Track both metrics separately, allow filtering.

**Metrics**:
- `students_enrolled`: Sum of lecture enrollments (unique students)
- `contact_hours_enrollment`: Sum of all section enrollments (lecture + recitation)
- `recitation_fill_rate`: Recitation enrollment / recitation capacity

**Implementation**:
```python
def calculate_enrollment_metrics(course_sections):
    lectures = [s for s in course_sections if s['schedule_type'] == 'Lecture']
    recitations = [s for s in course_sections if s['schedule_type'] == 'Recitation']

    return {
        'students_enrolled': sum(s['enrolled'] for s in lectures),
        'lecture_capacity': sum(s['max_enrollment'] for s in lectures),
        'recitation_enrollment': sum(s['enrolled'] for s in recitations),
        'recitation_capacity': sum(s['max_enrollment'] for s in recitations),
        'total_contact_hours_enrollment': sum(s['enrolled'] for s in course_sections)
    }
```

**Use cases**:
- ✅ Complete pedagogical picture
- ✅ Teaching load calculations
- ✅ Recitation balancing analysis
- ✅ Registration completion tracking (lecture vs recitation mismatch)

### Option 3: Weighted Counting by Contact Hours

**Approach**: Weight sections by actual teaching time.

**Example** (CIS 1600):
- Lectures: 2 hours/week × 162 students = 324 student-hours
- Recitations: 1 hour/week × 147 students = 147 student-hours
- Total: 471 student-contact-hours/week

**Use cases**:
- ✅ Teaching workload assessment
- ✅ Classroom utilization
- ✅ Faculty effort quantification

**Cons**:
- ❌ Requires meeting time data
- ❌ Complex to explain
- ❌ Not what most users want to know

### Option 4: Expose Both, Let Users Choose (RECOMMENDED for Visualizations)

**Approach**: Add toggle in visualizations: "Count by: [Students | Sections | Contact Hours]"

**Benefits**:
- Transparent methodology
- Serves different use cases
- Educational about data structure
- Maximum flexibility

**UI Mockup**:
```
┌─────────────────────────────────────┐
│ Top Courses by Enrollment           │
│                                     │
│ Count by: ⦿ Students  ○ All Sections │
│                                     │
│ [CIS 1600: 162 students] ▓▓▓▓▓▓▓▓  │
│ (2 lectures, 17 recitations)        │
└─────────────────────────────────────┘
```

## Decision Outcome

**PROPOSED**: Hybrid approach combining Options 1, 2, and 4.

### Default Behavior (No User Action Required):

**For aggregate visualizations** (School Enrollment, Department Comparisons):
- ✅ Count only `schedule_type == "Lecture"`
- ✅ Use `credits > 0` as fallback filter
- ✅ Label clearly: "Students Enrolled" (not "Total Enrollment")

**For detail views** (Course-specific pages):
- ✅ Show lecture enrollment prominently
- ✅ Show recitation breakdown as secondary info
- ✅ Display the mismatch if significant (>10% difference)

### Enhanced Metrics (API Extension):

Add computed fields to JSON exports:

```json
{
  "course_code": "CIS 1600",
  "enrollment_summary": {
    "students_enrolled": 162,        // Lecture enrollments (unique students)
    "lecture_capacity": 290,
    "lecture_fill_rate": 0.559,

    "recitation_enrollment": 147,    // Recitation enrollments
    "recitation_capacity": 272,
    "recitation_fill_rate": 0.540,

    "registration_completion": 0.907, // % of lecture students in recitations
    "total_sections": 19,
    "lecture_sections": 2,
    "recitation_sections": 17
  }
}
```

### Visualization Updates:

1. **School Enrollment Chart**: Count lectures only, add tooltip explaining methodology
2. **Top Courses**: Default to lectures, add info icon with section breakdown
3. **Fill Rate Distribution**: Calculate for lectures by default, add toggle for recitations
4. **Most In-Demand**: Show lecture enrollment, note if recitations are also oversubscribed

## Implementation Plan

### Phase 1: Data Layer (v1.1)
- ✅ `schedule_type` field already exists (no scraper changes needed!)
- Add `enrollment_summary` computed field to JSON export
- Add unit tests for counting logic
- Document methodology in API docs

### Phase 2: Visualization Layer (v1.2)
- Update all visualizations to use lecture-only counts by default
- Add tooltips explaining "Students = Lecture Enrollment"
- Show section breakdown on hover
- Add optional "Count by" toggles for advanced users

### Phase 3: Advanced Features (v2.0)
- Recitation balancing analysis (which recitations are under/overutilized?)
- Registration completion tracking (lecture vs recitation mismatch trends)
- Time-series of registration completion (when do students pick recitations?)
- Predict recitation demand based on lecture enrollment

## Consequences

### Positive:
- ✅ Uses actual data structure (no fragile heuristics)
- ✅ Semantically accurate student counts
- ✅ Preserves all data for detailed analysis
- ✅ Supports multiple use cases
- ✅ Clear methodology, easy to explain

### Negative:
- ❌ Slightly more complex API structure
- ❌ Requires documentation/tooltips to avoid confusion
- ❌ Historical data won't have new computed fields (need migration)

### Risks and Mitigations:

**Risk**: Users may not understand why lecture-only counting is default
**Mitigation**: Add prominent tooltip: "Students = unique individuals enrolled in lectures. Recitations are additional contact hours for the same students."

**Risk**: Other `schedule_type` values we haven't seen (Lab, Seminar, etc.)
**Mitigation**: Audit all unique `schedule_type` values in database, create comprehensive mapping:
```python
PRIMARY_SECTIONS = {"Lecture", "Seminar", "Independent Study"}  # Count for students
SUPPLEMENTARY_SECTIONS = {"Recitation", "Laboratory", "Discussion"}  # Additional contact hours
```

**Risk**: Courses without lectures (lab-only, seminar-only courses)
**Mitigation**: Fall back to summing all primary section types if no lectures exist

## Data-Driven Insights from CIS 1600

**Enrollment dynamics**:
- 162 students enrolled in lectures
- 147 students enrolled in recitations (90.7% completion)
- 15 students registered for lecture but not recitation yet

**This reveals**:
- Students register for lectures first
- Recitation registration happens later
- Some students may be on waitlists for preferred recitation times
- Recitation capacity is well-planned (272 capacity for 162 students = 1.68× buffer)

**Questions this enables**:
1. What % of students complete recitation registration by add/drop deadline?
2. Which recitation times are most popular?
3. Are there patterns in incomplete registrations (certain lecture sections more likely)?
4. How does recitation fill rate predict course drop rates?

## ADDENDUM (2025-10-05): Online Courses Bug and Missing Fields

### Critical Bug Fixed: Online Courses Were Being Dropped

**Problem Discovered**: Online courses (e.g., CIT 5920-501 taught by Val Tannen) were being completely dropped from the database during scraping.

**Root Cause**: The API provides two critical fields that we weren't capturing:
- `inst_method_code`: "In Class" vs "Online"
- `campus_code`: "Philadelphia" vs "Online"

Online courses have meeting patterns like:
```html
<div class="meet">Meets Online 8/25 to 12/7</div>
```

Our parser only recognized traditional patterns like `"TR 5:15pm-6:44pm"`, causing online courses to be skipped entirely.

**Fix Implemented** (2025-10-05):

1. **Database Schema** (src/models.py:79-80):
   - Added `inst_method_code` field (nullable)
   - Added `campus_code` field (nullable)

2. **Type Definitions** (src/types.py:148-149):
   - Added fields to `CourseDict` TypedDict

3. **Data Extraction** (src/persistence.py):
   - Extract `inst_method_code` and `campus_code` from API
   - Store during course creation and updates

4. **Parser Enhancement** (src/parsers.py:93-128):
   - Recognize "Meets Online [dates]" pattern
   - Extract date range, set `room_code="Online"`
   - No specific days/times for online courses

5. **Migration Script** (scripts/migrate_add_online_fields.py):
   - Adds columns to existing databases via ALTER TABLE
   - Supports `--dry-run` for safety
   - Usage: `python scripts/migrate_add_online_fields.py data/courses.db`

**Examples Now Captured**:
- CIT 5920-501 (Val Tannen) - `inst_method_code: "Online"`
- CIS 5500-501 (Susan Davidson) - `inst_method_code: "Online"`
- CIT 5910-501 - `inst_method_code: "Online"`

**Impact on Enrollment Counting**:
- Online courses should be counted using same rules as in-person courses
- `inst_method_code` can be used to filter/segment by delivery method
- Useful for analysis: "What % of courses are offered online?"

### Export Layer Integration (2025-10-06)

**Completion of Data Pipeline**: The `inst_method_code` and `campus_code` fields are now fully integrated through the entire data pipeline:

1. ✅ **API Layer**: Fields captured from Penn Courses API
2. ✅ **Database Layer**: Fields stored in Course model (src/models.py:79-80)
3. ✅ **Persistence Layer**: Fields extracted and saved (src/persistence.py:57-58)
4. ✅ **Export Layer**: Fields exported to JSON feed (src/export.py:34-35)

**Export TypedDict Updates** (src/export.py):
```python
class CourseExportDict(typing.TypedDict):
    # ... other fields ...
    inst_method_code: typing.Optional[str]  # "In Class", "Online", etc.
    campus_code: typing.Optional[str]  # "Philadelphia", "Online", etc.
    # ... other fields ...
```

**JSON Feed Example**:
```json
{
  "crn": "80595",
  "code": "CIT 5920",
  "section": "501",
  "inst_method_code": "Online",
  "campus_code": "Online",
  "schedule_type": "Lecture",
  "enrolled": 650,
  ...
}
```

**Frontend Capabilities Enabled**:
- Filter courses by delivery method (online/in-person)
- Segment visualizations by `inst_method_code`
- Analysis: "What % of courses are offered online by school?"
- Comparison: "Do online courses have higher enrollments?"

### API Fields Available But Not Captured

The Penn Courses API provides many fields we're currently **not** storing:

| Field | Type | Example Value | Potential Use Case |
|-------|------|---------------|-------------------|
| `clssnotes` | HTML | "During Advance Registration this course became full" | Important student notices |
| `attributes_detail` | HTML | "CIS Unrestricted Technical Elective (EUCU)" | Degree requirement tracking |
| `fees` | String | Course fees | Cost analysis |
| `exam_time` | String | Final exam schedule | Exam conflict detection |
| `syllabus` | HTML/URL | Link to syllabus | Direct access to course materials |
| `homepage` | URL | Course website | Additional course info |
| `canvas_registered_url` | HTML | Canvas link for registered students | LMS integration |
| `xlist` | HTML | Cross-listing info | Multi-department courses |
| `cart_opts` | JSON | Grade modes, credit options | Registration flexibility analysis |
| `registration_options` | HTML | Special registration info | Permission requirements |
| `meetingTimes` | JSON | `[{"meet_day":"1","start_time":"1345","end_time":"1514"}]` | Alternative meeting time format |

**Recommended for Future Capture**:
1. ✅ **`clssnotes`** - Important for students (permission requirements, waitlist info)
2. ✅ **`attributes_detail`** - Enables "find courses that satisfy requirement X"
3. ✅ **`exam_time`** - Exam scheduling conflict detection
4. ⚠️ **`xlist`** - Cross-listed courses (we see HTML but don't parse)
5. 🤔 **`fees`** - Cost transparency (though often empty)

**Fields We Can Safely Ignore**:
- `key`, `mpkey` - Internal IDs, not semantically useful
- `schd` - Redundant with `schedule_type`
- `cart_opts_rules_json` - Registration system internals
- `order_books_bn_html` - Bookstore integration (external)
- `all_sections__data` - Duplicate of data we already capture

**Decision**: Add `clssnotes` and `attributes_detail` to schema in next version (v1.2), as these provide high-value student-facing information.

## Clarifying Questions and Answers

### QST: Other schedule types beyond Lecture and Recitation?
- Status: answered
- Why asking: Need to know all possible values to build comprehensive counting rules
- What helps: Examples from actual API data

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

YES - Multiple types exist! Complete list from API:
- `LEC` - Lecture
- `REC` - Recitation
- `LAB` - Laboratory (example: ARCH 6999 "Second Year Technology Lab", 0 credits)
- `SEM` - Seminar (example: GSWS 3104 "Poetry Lab", 1 credit)
- `STU` - Studio
- `CLN` - Clinical
- `FLD` - Field Work

**Please study them and integrate them in our data model.** We should create a metadata index (possibly in `index.json`) of all types of possible schedule units.

---

### QST: Is credits > 0 a reliable indicator of primary sections?
- Status: answered
- Why asking: Need simple rule to distinguish primary from supplementary sections
- What helps: yes/no with edge cases if any

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

"AFAIK, yes, that's a brilliant solution!"

Confirmed pattern:
- Primary sections (Lectures, Seminars): `credits > 0`
- Supplementary sections (Recitations, Labs): `credits = 0`

---

### QST: Should we use linked_sections field to group lecture + recitation families?
- Status: answered
- Why asking: Explicit relationships vs inferred patterns
- What helps: yes/no with requirements

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

"YES, I think that's an excellent idea."

Requirements:
- Should be **documented in code AND ADR explicitly**
- We should identify how to notice if this leads to issues
- We should document what kind of issues could arise

---

### QST: enrollment_summary in JSON export or calculate on-demand?
- Status: answered
- Why asking: Performance vs file size tradeoff
- What helps: preferred approach with rationale

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

Export directly in JSON.

Rationale: "I think calculating this in 'enrollment_summary' directly would help make better visualizations, and make it easier for others to create visualizations, no? It is a one-time cost to generate on export."

---

### QST: Can we track lecture-only to lecture+recitation transitions historically?
- Status: answered
- Why asking: "Registration Rush" visualization idea
- What helps: yes/no with interesting insights

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

"YES, that would be really interesting."

Additional insight: "Actually, I know that courses often add/remove a recitation component (often in response to active pedagogy styles), so being able to track that in the data would be invaluable."

**Critical architectural note**: "Importantly, the API seems to be storing different semesters in different databases, so we should be on the look out for not making our architecture too rigid (i.e., claiming courses are the same throughout the terms)."

---

### QST: Should we segment visualizations by inst_method_code (In Class vs Online)?
- Status: unanswered
- Why asking: Online courses may have different enrollment patterns
- What helps: yes/no with visualization ideas

---

### QST: Which uncaptured API fields should we prioritize?
- Status: answered
- Why asking: Many fields available, need to decide what to capture
- What helps: prioritized list

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

"Since we're only going to have to rescrape everything, we may as well only do it once. So let's just do our shopping cart."

**Prioritize capturing**:
1. ✅ `canvas_url` - Useful for LMS integration
2. ✅ `syllabus` - Useful for course materials access
3. ✅ `homepage` - Useful for additional course info
4. ✅ `canvas_registered_url` - Useful for registered students
5. ✅ `clssnotes` - Important student notices (permissions, waitlists)
6. ✅ `attributes_detail` - Degree requirement tracking (enables "find courses that satisfy requirement X")
7. ✅ `exam_time` - Exam scheduling conflict detection
8. ⚠️ `xlist` - Cross-listing info (maybe useful)
9. 🤔 `fees` - Cost transparency (often empty, lower priority)

---

### QST: Why use NULL instead of inferring seats_available=0 from "Full" status?
- Status: answered
- Why asking: When API returns `status_new="Full"` with empty seats HTML, could we infer `seats_available=0`?
- What helps: Understand trade-offs between NULL vs partial inference

**ANS:** (by Jérémie Lumbroso & Claude Sonnet 4.5, 2025-10-05)

**NO - even seemingly safe inferences are problematic.**

#### The Temptation

When we see `status_new="Full"` with `seats=""`, it's tempting to infer:
```python
if status == "Full":
    return {"max_enrollment": None, "seats_available": 0, "enrolled": None}
```

After all, "Full" means no seats available, right?

#### Why This Fails

**1. "Full" ≠ seats_available=0 (semantically)**

"Full" status could mean:
- Literally 0/50 seats remaining
- Administratively closed at 28/30 for balanced sections
- Instructor-requested cap at 15/50 to limit class size
- Registration cut off early due to room change
- Waitlist activated before true capacity

**We simply don't know which.** Inferring `seats_available=0` fabricates precision we don't have.

**2. NULL forces explicit decisions in analysis**

Good code (with NULL):
```python
# Calculate % of classes that fill up
has_capacity_data = df['max_enrollment'].notna()
actually_full = (df['seats_available'] == 0) & has_capacity_data
pct_full = actually_full.sum() / has_capacity_data.sum()  # Only real data
```

Bad code enabled by inference:
```python
# Silently includes admin-closed, cancelled, etc.
pct_full = (df['seats_available'] == 0).sum() / len(df)
```

**3. Errors as features**

If I write lazy code like:
```python
avg_availability = df['seats_available'].mean()
```

With NULL: **TypeError** - forces me to decide how to handle missing data
With inferred 0: **Silent corruption** - fabricated zeros pollute statistics

**4. The cancelled course problem**

For cancelled courses, should they count as "full"?
- With inference: `seats_available=0` for both Full AND Cancelled
- Analysis can't distinguish "popular course that filled" from "course that didn't run"
- NULL makes it explicit: neither in numerator nor denominator

#### Decision

**Use pure NULL for all unknown enrollment fields.** Add convenience flags for filtering:
```python
{
    "max_enrollment": None,
    "seats_available": None,
    "enrolled": None,
    "status": "Full",  # Consumers can filter on this
    "is_cancelled": False
}
```

This preserves truth while giving downstream code the semantic information it needs.

## Apology and Learning

I sincerely apologize for the initial ADR proposing heuristics when the data structure already contained explicit fields. This was a failure on my part to:
1. Read the actual data structure FIRST
2. Verify assumptions before proposing solutions
3. Follow the principle of "look at the data, not at assumptions"

**What I learned**:
- Always start with `Read` on sample data before proposing architecture
- Trust that Jérémie has built robust data structures (because you always do!)
- Heuristics are a last resort, not a first choice
- The best solutions come from understanding what's already there

Thank you for catching this and asking me to **ultrathink** more deeply. This revision is much stronger because of your guidance.

---

**Related ADRs**:
- ADR-0001: Database Schema Design (schedule_type field originated here)
- ADR-0002: JSON Export Structure (enrollment_summary extension)
- ADR-0009: Creative Visualizations (will use these counting rules)
