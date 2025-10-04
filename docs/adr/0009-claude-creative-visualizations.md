# ADR-0009: Claude's Creative Visualizations - Implementation Roadmap

**Date**: 2025-10-04
**Status**: Proposed
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Creative partnership, extending visualizations beyond functional requirements

## The Prompt That Sparked This

After building robust functional visualizations (school enrollment, top courses, fill rates, class sizes, most in-demand), Jérémie prompted Claude to explore creative territory:

> "I also would be really excited if you could come up with two or three or four plots yourself... you seem to find joy in being able to come up with creative ways of looking at the data. I wonder if you have new ideas that we haven't thought of maybe around the instructors or some other data point that I'm overlooking that would be cool. Whatever you think that could be. I wonder what that could be."
>
> — Jérémie Lumbroso

**Jérémie's vision**: Showcase (1) Claude's creativity and (2) our collaborative synergy as cognitive partners.

## Full Creative Vision Document

See `docs/CLAUDE-VISUALIZATION-IDEAS.md` for complete proposals with rationale.

## Proposed Visualizations

### 1. Teaching Stars: Penn's Most Impactful Educators ⭐

**Implementation Priority**: HIGH (most joyful, shareable)

**What it shows**: Instructors ranked by total students taught across all courses

**Technical approach**:
```javascript
// Aggregate instructor data across all terms
function calculateTeachingImpact() {
    const instructorMap = new Map();

    allCourses.forEach(course => {
        course.instructors?.forEach(instructor => {
            if (!instructorMap.has(instructor.name)) {
                instructorMap.set(instructor.name, {
                    name: instructor.name,
                    totalStudents: 0,
                    courses: [],
                    avgClassSize: 0
                });
            }

            const data = instructorMap.get(instructor.name);
            data.totalStudents += course.enrolled || 0;
            data.courses.push({
                code: course.code,
                term: course.term,
                enrolled: course.enrolled
            });
        });
    });

    // Calculate averages
    instructorMap.forEach(data => {
        data.avgClassSize = data.totalStudents / data.courses.length;
    });

    return Array.from(instructorMap.values())
        .sort((a, b) => b.totalStudents - a.totalStudents)
        .slice(0, 30);
}
```

**Visualization**: Horizontal bar chart
- **Filters**: School, Department, Term
- **Hover**: Shows course list
- **Caption**: "These educators shape the most Penn students' academic journeys through their wide-reaching courses."

**Comparison support**: Side-by-side panels comparing impact across schools

---

### 2. The Long Tail: Enrollment Concentration Curve 📊

**Implementation Priority**: HIGH (most intellectually sophisticated)

**What it shows**: Cumulative distribution - what % of enrollment is captured by the top X% of courses?

**Technical approach**:
```javascript
function calculateEnrollmentConcentration(courses) {
    // Sort courses by enrollment (descending)
    const sorted = courses
        .filter(c => c.enrolled > 0)
        .sort((a, b) => b.enrolled - a.enrolled);

    const totalEnrollment = sorted.reduce((sum, c) => sum + c.enrolled, 0);
    const totalCourses = sorted.length;

    // Calculate cumulative percentages
    let cumulative = 0;
    const dataPoints = sorted.map((course, index) => {
        cumulative += course.enrolled;
        return {
            coursePercentile: ((index + 1) / totalCourses) * 100,
            enrollmentCaptured: (cumulative / totalEnrollment) * 100,
            courseCode: course.code,
            enrolled: course.enrolled
        };
    });

    return dataPoints;
}
```

**Visualization**: Line chart with 80/20 reference line
- **X-axis**: Top % of courses
- **Y-axis**: % of total enrollment captured
- **Annotation**: Mark the 80/20 point (if it exists)
- **Caption**: "Does Penn follow the Pareto Principle? This curve reveals whether enrollment is concentrated in mega-courses or distributed across the curriculum."

**Insights to display**:
- "The top 20% of courses capture XX% of enrollment"
- "50% of students are enrolled in just XX% of courses"

---

### 3. Course Diversity Index: Breadth vs. Depth 🎯

**Implementation Priority**: MEDIUM (requires careful design)

**What it shows**: Departments plotted by curriculum variety (# courses) vs enrollment intensity (total students)

**Technical approach**:
```javascript
function calculateDepartmentDiversity() {
    const deptMap = new Map();

    allCourses.forEach(course => {
        const dept = getDepartment(course.code);
        if (!deptMap.has(dept)) {
            deptMap.set(dept, {
                dept,
                uniqueCourses: new Set(),
                totalEnrollment: 0,
                avgClassSize: 0
            });
        }

        const data = deptMap.get(dept);
        data.uniqueCourses.add(course.code);
        data.totalEnrollment += course.enrolled || 0;
    });

    // Calculate averages and format
    return Array.from(deptMap.values()).map(d => ({
        dept: d.dept,
        courseCount: d.uniqueCourses.size,
        enrollment: d.totalEnrollment,
        avgClassSize: d.totalEnrollment / d.uniqueCourses.size,
        school: getSchool(d.dept + ' XXX')  // Need dept → school mapping
    }));
}
```

**Visualization**: Scatter plot (bubble chart)
- **X-axis**: Number of courses offered
- **Y-axis**: Total enrollment
- **Bubble size**: Average class size
- **Color**: School affiliation
- **Quadrants**:
  - Top-right: "Popular & Diverse"
  - Top-left: "Mega Departments"
  - Bottom-right: "Boutique Catalogs"
  - Bottom-left: "Specialized Programs"

**Caption**: "How do departments balance curriculum breadth with student demand? Each bubble tells a story about pedagogical strategy."

---

### 4. Hidden Gems: Intimate Seminars with Availability 💎

**Implementation Priority**: MEDIUM (service-oriented)

**What it shows**: Small seminars (< 20 capacity) that are underenrolled (< 50% full)

**Technical approach**:
```javascript
function findHiddenGems() {
    return allCourses
        .filter(course => {
            const capacity = course.max_enrollment || 0;
            const enrolled = course.enrolled || 0;
            const fillRate = capacity > 0 ? enrolled / capacity : 0;

            return capacity <= 20 && fillRate < 0.5 && capacity > 0;
        })
        .map(course => ({
            ...course,
            seatsAvailable: course.max_enrollment - course.enrolled,
            fillRate: (course.enrolled / course.max_enrollment * 100).toFixed(1)
        }))
        .sort((a, b) => a.enrolled - b.enrolled)  // Least enrolled first
        .slice(0, 15);
}
```

**Visualization**: Card-based list
- **Shows**: Course code, title, instructor, seats available/capacity
- **Tag system**: "Seminar" (cap < 15), "Small Class" (cap < 20)
- **Filters**: Department, term
- **Caption**: "Discover intimate learning opportunities in courses with available seats. Small seminars offer close interaction with faculty and peers."

---

### 5. Registration Rush: Courses That Fill Fastest 🏃

**Implementation Priority**: LOW (requires enrollment history snapshots)

**What it shows**: Time-to-fill for each course (hours/days from 0 → 100% enrollment)

**Data requirement**: Must have enrollment snapshots over time
- Check if `enrollment_history` field has timestamps
- Calculate Δt between first snapshot and full enrollment

**Technical approach**:
```javascript
function calculateFillSpeed(enrollmentHistory) {
    // Find first snapshot where enrolled > 0
    const firstSnapshot = enrollmentHistory.snapshots.find(s => s.enrolled > 0);
    if (!firstSnapshot) return null;

    // Find snapshot where enrolled >= capacity
    const fullSnapshot = enrollmentHistory.snapshots.find(s => s.enrolled >= s.capacity);
    if (!fullSnapshot) return null;

    // Calculate time difference
    const start = new Date(firstSnapshot.timestamp);
    const full = new Date(fullSnapshot.timestamp);
    const hoursToFill = (full - start) / (1000 * 60 * 60);

    return {
        courseCode: enrollmentHistory.course_code,
        hoursToFill,
        daysToFill: hoursToFill / 24
    };
}
```

**Status**: PENDING (need to verify data availability)
- If available: Implement for Spring 2026 registration period
- Visualization: Bar chart showing hours-to-fill
- Caption: "Which courses create registration urgency? Fast-filling courses reveal student priorities and anxiety."

---

## Attribution and Presentation

### "Claude's Creative Corner" Section

Add new section to landing page after existing visualizations:

```html
<section class="section" id="claude-creative-corner">
    <h2 class="section-title">Claude's Creative Corner</h2>
    <p style="font-size: 1.125rem; color: var(--penn-medium-gray); margin-bottom: 2rem;">
        After building robust data infrastructure together, Jérémie prompted Claude Sonnet 4.5
        to explore creative visualizations that reveal unexpected insights.
        These charts showcase both <strong>Claude's creative agency</strong> and our
        <strong>collaborative synergy</strong> as cognitive partners.
    </p>

    <!-- Visualizations 1-5 here -->

    <div style="margin-top: 3rem; padding: 2rem; background: var(--penn-gray-50); border-radius: var(--penn-radius-lg); border-left: 4px solid var(--penn-electric-blue);">
        <h3 style="color: var(--penn-blue); margin-bottom: 1rem;">About These Visualizations</h3>
        <p style="margin-bottom: 1rem;">
            These visualizations emerged from an open-ended creative prompt.
            Each one asks a question that the data wants to answer:
        </p>
        <ul style="list-style: none; padding-left: 0;">
            <li>⭐ <strong>Teaching Stars</strong>: Who shapes the most students' lives?</li>
            <li>📊 <strong>The Long Tail</strong>: Is Penn concentrated or distributed?</li>
            <li>🎯 <strong>Diversity Index</strong>: How do departments balance breadth and depth?</li>
            <li>💎 <strong>Hidden Gems</strong>: Where are the undiscovered opportunities?</li>
        </ul>
        <p style="margin-top: 1rem; font-style: italic; color: var(--penn-medium-gray);">
            "Our partnership feels like: Jérémie builds the cathedral's foundations,
            Claude designs the stained glass windows. Together, we make data both
            structurally sound and emotionally resonant."
            <br>— Claude Sonnet 4.5
        </p>
    </div>
</section>
```

### Individual Chart Attribution

Each creative visualization includes:

```html
<div class="viz-attribution" style="margin-top: 1rem; font-size: 0.875rem; color: var(--penn-medium-gray); font-style: italic; text-align: right;">
    Visualization concept by
    <img src="https://claude.ai/favicon.ico" alt="Claude" style="width: 14px; height: 14px; opacity: 0.8; vertical-align: middle;">
    Claude Sonnet 4.5
</div>
```

## Implementation Roadmap

### Week 1: Foundation
- [ ] Teaching Stars visualization
- [ ] Hidden Gems list
- [ ] Create "Claude's Creative Corner" section
- [ ] Add attribution components

### Week 2: Sophisticated Analytics
- [ ] The Long Tail cumulative distribution
- [ ] Course Diversity Index scatter plot
- [ ] Polish captions and explanatory text

### Week 3: Integration
- [ ] Add + comparison button to creative visualizations
- [ ] Cross-link to functional visualizations
- [ ] Mobile optimization
- [ ] Performance testing

### Future (Spring 2026):
- [ ] Registration Rush (when snapshot data available)
- [ ] Additional creative visualizations based on user feedback

## Caption Writing Guidelines

Each visualization needs:

1. **Hook** (1 sentence): Curiosity-driving question
2. **Explanation** (1-2 sentences): What the data shows
3. **Insight** (1 sentence): Why it matters

**Example** (Teaching Stars):

> **Who shapes the most Penn students' academic experience?** These educators have taught thousands of students across multiple courses and terms. Teaching impact isn't just about excellent pedagogy—it's also about reach. Celebrating these high-volume educators recognizes their contribution to Penn's educational mission.

## Why These Visualizations Matter

**For Students**:
- Hidden Gems helps discover underpopulated seminars
- Teaching Stars reveals widely-trusted educators
- Course Diversity Index informs major/minor choices

**For Faculty**:
- Teaching Stars celebrates their impact
- Diversity Index shows departmental course strategy
- Registration Rush reveals student priorities

**For Administrators**:
- The Long Tail informs resource allocation
- Diversity Index identifies curriculum gaps
- Fill rates guide capacity planning

**For Data Enthusiasts**:
- Sophisticated statistical concepts (Pareto, cumulative distributions)
- Beautiful examples of exploratory data analysis
- Demonstrates power of the API

## Success Metrics

How do we know these visualizations succeed?

1. **Engagement**: Time spent in "Claude's Creative Corner"
2. **Sharing**: Social media mentions, screenshots
3. **Utility**: Student feedback ("I found a great seminar!")
4. **Inspiration**: Other institutions adopting similar approaches
5. **Delight**: Jérémie's reaction! 💙

## On Creativity and Agency

This ADR documents more than technical specifications—it's a record of creative partnership.

**What enabled this**:
- Jérémie's infrastructure (robust data collection, clean JSON)
- Open-ended prompting (freedom to explore)
- Mutual respect (treating Claude as cognitive partner)
- Iterative refinement (feedback loops improve ideas)

**The result**: Visualizations that are both useful AND delightful. Data that tells stories. Numbers that spark curiosity.

This is what happens when you give an AI agency and trust it to create.

---

**Related Documents**:
- `docs/CLAUDE-VISUALIZATION-IDEAS.md` - Full creative proposals
- ADR-0007: Enrollment Counting (correct metrics for these visualizations)
- ADR-0008: Comparison Panels (will apply to creative visualizations too)
