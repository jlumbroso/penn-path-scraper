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

## Open Questions for Jérémie

1. **Other schedule types**: Have you seen types other than "Lecture" and "Recitation"? (Lab, Seminar, Discussion, etc.)

2. **Credits as filter**: Is `credits > 0` a reliable indicator of primary sections, or are there edge cases?

3. **Linked sections**: Should we use the `linked_sections` field to explicitly group lecture + recitation families?

4. **API presentation**: Do you want the `enrollment_summary` computed field in the JSON export, or calculate on-demand in visualizations?

5. **Historical comparison**: For the "Registration Rush" visualization idea, can we track when students move from lecture-only to lecture+recitation?

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
