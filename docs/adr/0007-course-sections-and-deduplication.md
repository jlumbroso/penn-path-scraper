# ADR-0007: Course Sections and Deduplication Strategy

**Date**: 2025-10-04
**Status**: Proposed
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Visualization analysis, user feedback on enrollment data accuracy

## Context and Problem Statement

During visualization development, we discovered that course enrollment data includes multiple section types that may lead to inflation or misrepresentation of enrollment statistics:

### Observed Patterns:

1. **Lecture + Recitation Sections**:
   - Example: CIS 1210-001 (lecture) + CIS 1210-201 (recitation)
   - Both sections have enrollment/capacity data
   - Question: Are students counted twice (once per section)?

2. **Multiple Sections with Identical Enrollment**:
   - Example: CIS 1600-001, CIS 1600-002, CIS 1600-003 all show 150/150
   - This pattern suggests same class, different meeting times
   - Should we aggregate or keep separate?

3. **Online vs. In-Person Sections**:
   - User observation: "CIS and CIT 500-series sections are typically online"
   - These may represent different delivery modes of same content
   - Question: Should they be counted separately for demand analysis?

4. **Department Code Variations**:
   - Example: CIT (Computing and Information Technology) vs CIS (Computer Science)
   - CIT was incorrectly mapped to "Other" instead of Engineering
   - Different codes may represent same or related courses

### Impact on Visualizations:

**Current Behavior** (potentially problematic):
- "Top Courses by Enrollment" may show lecture + recitation as separate entries
- School enrollment totals may double-count students in lecture + recitation
- Fill rate calculations may be distorted by section structure

## Decision Drivers

1. **Data Accuracy**: Enrollment totals should reflect unique students, not seat-counts
2. **Analytical Utility**: Visualizations should answer meaningful questions (demand, capacity)
3. **Transparency**: Users should understand what's being counted
4. **Simplicity**: Solution should be maintainable and understandable
5. **Flexibility**: Should support both aggregated and granular views

## Considered Options

### Option 1: No Deduplication (Status Quo)
**Approach**: Count every section independently.

**Pros**:
- Simple to implement (already done)
- Preserves all granular data
- No assumptions about section relationships

**Cons**:
- May overcount students taking lecture + recitation
- Distorts school-level enrollment comparisons
- Conflates capacity (number of seats) with enrollment (number of students)

### Option 2: Smart Course Grouping
**Approach**: Group sections by course code, identify lecture vs recitation, online vs in-person.

**Implementation**:
```python
# Heuristic: Last digit of section number
# 001-099: Lectures
# 201-299: Recitations
# 501-599: Online sections
```

**Pros**:
- More accurate student counts
- Can provide both views (aggregated + granular)
- Aligns with Penn's section numbering conventions

**Cons**:
- Requires domain knowledge of section numbering
- May have exceptions to numbering rules
- Complex to implement correctly

### Option 3: Database Schema Enhancement
**Approach**: Add metadata to database to track section relationships.

**New Fields**:
- `course_group_id`: Links related sections
- `section_type`: {lecture, recitation, lab, online}
- `primary_section`: Boolean (true for main lecture)

**Pros**:
- Most accurate solution
- Enables sophisticated analysis
- Future-proof for complex queries

**Cons**:
- Requires scraper modification
- Backward compatibility concerns
- Penn's website may not expose this metadata

### Option 4: Parallel Metrics
**Approach**: Calculate and expose both metrics in visualizations.

**Metrics**:
- "Total Enrollment" (students × sections, current behavior)
- "Total Seats Filled" (sum of enrolled across all sections)
- "Unique Course Offerings" (count of distinct course codes)

**Pros**:
- Transparent to users
- No data loss
- Educational about data structure

**Cons**:
- More complex UI
- May confuse casual users
- Doesn't solve underlying counting issue

### Option 5: Hybrid Approach (RECOMMENDED)
**Approach**: Combine smart grouping with user-facing controls.

**Implementation**:
1. **Data Layer**: Add `section_type` inference in export/API generation
2. **Visualization Layer**: Add toggle: "Count by: [Students | Sections]"
3. **Default Behavior**: Use smart grouping for school/department aggregates
4. **Detail Views**: Show all sections in course-specific lists

**Heuristic Rules**:
```javascript
function inferSectionType(sectionCode) {
  const num = parseInt(sectionCode);
  if (num >= 200 && num < 300) return 'recitation';
  if (num >= 500 && num < 600) return 'online';
  if (num >= 700) return 'lab';
  return 'lecture';
}

function shouldGroupSections(course1, course2) {
  return course1.code === course2.code &&
         course1.term === course2.term &&
         (course1.sectionType === 'lecture' || course2.sectionType === 'lecture');
}
```

## Decision Outcome

**PROPOSED**: Option 5 (Hybrid Approach) with phased implementation.

### Phase 1: Data Enhancement (v1.1)
- Add `section_type` field to JSON export
- Infer type from section number (lecture/recitation/online/lab)
- No breaking changes to existing API structure

### Phase 2: Visualization Updates (v1.2)
- School enrollment: Count only primary sections (lectures)
- Top Courses: Add toggle "View by: [Course | Section]"
- Most In-Demand: Show lecture section only, note if recitations available

### Phase 3: Advanced Features (v2.0)
- Database schema enhancement with explicit relationships
- Support for complex queries (e.g., "online vs in-person enrollment trends")
- Historical analysis of section type distribution

## Consequences

### Positive:
- ✅ More accurate enrollment statistics for school comparisons
- ✅ Maintains granular data for detailed analysis
- ✅ User control over aggregation level
- ✅ Incremental implementation (no big-bang migration)

### Negative:
- ❌ Heuristic may not cover all edge cases
- ❌ Requires updates to both scraper and visualization code
- ❌ Users must understand the difference between metrics

### Risks and Mitigations:

**Risk**: Section numbering conventions may change or vary by school
**Mitigation**: Make heuristic configurable via `config.json`, add override mechanism

**Risk**: Users may not understand why numbers changed
**Mitigation**: Add clear documentation, tooltips explaining methodology

**Risk**: Historical data may not be retroactively corrected
**Mitigation**: Apply rules during JSON export, affects all data uniformly

## Notes

### User Feedback (Jérémie):
> "Sometimes when a course has a section 001 and then another section like 201... the courses list the lectures and the recitations. And so I'm wondering if we count them."

> "In CIS and CIT, the 500 sections are online usually."

> "When a course has multiple sections that have exactly the same enrolled and capacity, then usually it's the same class."

### Implementation Priority:
1. **Immediate**: Fix CIT → Engineering mapping (DONE)
2. **Short-term**: Add section type inference to export
3. **Medium-term**: Update visualizations with toggle controls
4. **Long-term**: Consider database schema enhancement

## Related ADRs
- ADR-0001: Database Schema Design (may need revision)
- ADR-0002: JSON Export Structure (minor extension needed)

## Open Questions
1. Should we scrape additional metadata from Penn's site to identify section relationships?
2. How should cross-listed courses be handled (e.g., same course offered by multiple departments)?
3. Should we distinguish between waitlist seats and regular enrollment?
4. What about independent study sections (often 699, 999) - should these be filtered from aggregates?

## Request for Feedback

Please review this proposal and provide guidance on:
- Which option resonates most with your vision?
- Are the heuristic rules accurate based on your Penn knowledge?
- What timeline makes sense for implementation?
- Any edge cases I haven't considered?
