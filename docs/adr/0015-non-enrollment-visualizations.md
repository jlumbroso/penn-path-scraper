# ADR-0015: Non-Enrollment Visualizations for Historical Terms

**Date**: 2025-10-08
**Status**: Proposed
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Historical terms (Fall 2023 and earlier) have course data but no enrollment snapshots
**Motivation**: Spring 2026 advanced registration starts tomorrow; need to maximize value from all data

## Problem

Historical terms (Fall 2023, Summer 2023, Spring 2023, Fall 2022, Summer 2022) have comprehensive course data but **no enrollment information** (all `enrolled` and `max_enrollment` fields are null).

Current visualizations are enrollment-focused and show "N/A" or empty charts for these terms, making ~26,000 courses invisible in the interface.

## Available Data Fields (Non-Enrollment)

From the Course model, we have rich data that doesn't require enrollment:

| Field | Example Values | Use Case |
|-------|---------------|----------|
| `schedule_type` | Lecture, Recitation, Laboratory, Seminar, Studio, Clinical, Field Work, Independent Study, Dissertation, Masters Thesis, Senior Thesis | Course format analysis |
| `inst_method_code` | In Class, Online, Hybrid, Active Learning, Clinical Based Learning, Field Work, Research, Internship, Independent Study | Instruction mode trends |
| `campus_code` | Philadelphia, Online, Wharton San Francisco | Campus distribution |
| `credits` | 0.5, 1.0, 1.5, ... | Credit hour distribution |
| `code` | CIS-1210, MATH-1400, etc. | Department/school breakdown |
| `attributes` | JSON array of requirements | Fulfillment analysis |

## Proposed Visualizations

### 1. Course Offerings by Department (All Terms)

**Chart Type**: Horizontal bar chart (top 20 departments)

**Data Required**: Course code prefix (department)

**Query**:
```javascript
// Group by department (CIS, MATH, etc.)
const deptCounts = {};
courses.forEach(course => {
    const dept = course.code.split(/[\s-]+/)[0];
    deptCounts[dept] = (deptCounts[dept] || 0) + 1;
});
```

**Why Useful**:
- Shows which departments offer most courses
- Works for ALL terms, including historical
- Helps students find large vs small programs
- Identifies cross-school departments (STAT in Wharton, etc.)

---

### 2. Schedule Type Distribution

**Chart Type**: Donut chart

**Data Required**: `schedule_type`

**Categories**:
- Lecture (majority)
- Recitation
- Laboratory
- Seminar
- Studio
- Independent Study
- Clinical
- Field Work
- Dissertation/Thesis

**Query**:
```javascript
const scheduleTypes = {};
courses.forEach(course => {
    const type = course.schedule_type || 'Unknown';
    scheduleTypes[type] = (scheduleTypes[type] || 0) + 1;
});
```

**Why Useful**:
- Shows teaching format diversity
- Engineering (labs) vs Arts (studios) vs Medicine (clinical)
- Identifies research-heavy programs (many independent studies)

---

### 3. Instruction Method Trends

**Chart Type**: Stacked area chart (over time)

**Data Required**: `inst_method_code`, `term_id`

**Categories**:
- In Class
- Online
- Hybrid
- Active Learning
- Clinical Based Learning
- Field Work
- Research
- Internship
- Independent Study

**Query**:
```javascript
// Group by term and instruction method
const methodsByTerm = {};
courses.forEach(course => {
    if (!methodsByTerm[course.term]) methodsByTerm[course.term] = {};
    const method = course.inst_method_code || 'In Class';
    methodsByTerm[course.term][method] = (methodsByTerm[course.term][method] || 0) + 1;
});
```

**Why Useful**:
- **COVID-19 impact**: Shows shift to online during pandemic (Fall 2022, Spring 2023)
- **Return to campus**: Documents post-COVID transition
- **Hybrid learning**: Growth of hybrid model
- Works for ALL terms including historical

---

### 4. Campus Distribution

**Chart Type**: Pie chart or donut chart

**Data Required**: `campus_code`

**Categories**:
- Philadelphia (main campus)
- Online
- Wharton San Francisco

**Query**:
```javascript
const campusCounts = {};
courses.forEach(course => {
    const campus = course.campus_code || 'Philadelphia';
    campusCounts[campus] = (campusCounts[campus] || 0) + 1;
});
```

**Why Useful**:
- Shows Penn's geographic reach
- Online program growth
- Wharton SF executive programs

---

### 5. Credit Hour Distribution

**Chart Type**: Histogram

**Data Required**: `credits`

**Bins**: 0.5, 1.0, 1.5, 2.0, ..., 6.0+

**Query**:
```javascript
const creditBins = {};
courses.forEach(course => {
    const credits = parseFloat(course.credits) || 0;
    const bin = Math.floor(credits * 2) / 2; // Round to nearest 0.5
    creditBins[bin] = (creditBins[bin] || 0) + 1;
});
```

**Why Useful**:
- Most courses are 1.0 CU (Penn's standard)
- Identifies half-credit courses, intensive courses (1.5 CU)
- Lab add-ons (0.5 CU recitations)

---

### 6. School-Level Course Distribution

**Chart Type**: Treemap or sunburst chart

**Data Required**: Course code → department → school mapping

**Hierarchy**:
```
Penn
├── Engineering
│   ├── CIS (Computer Science)
│   ├── MEAM (Mechanical Engineering)
│   └── ...
├── Wharton
│   ├── FNCE (Finance)
│   ├── MGMT (Management)
│   └── ...
├── Arts & Sciences
│   ├── MATH
│   ├── PHYS
│   └── ...
└── ...
```

**Why Useful**:
- Visual hierarchy of Penn's academic structure
- Compare school sizes
- Department dominance within schools

---

### 7. Course Format by School

**Chart Type**: Grouped bar chart

**Data Required**: `code` (for school), `schedule_type`

**X-Axis**: Schools (Engineering, Wharton, Arts & Sciences, etc.)
**Y-Axis**: Count
**Groups**: Lecture, Lab, Seminar, Studio, Clinical

**Why Useful**:
- Engineering: High lab count
- Arts & Sciences: Mix of lectures and seminars
- Medicine: Clinical focus
- Design: Studio-heavy

---

### 8. Longitudinal Department Growth

**Chart Type**: Line chart (multi-series)

**Data Required**: `code`, `term_id`

**Series**: Top 10 departments (CIS, ECON, MATH, etc.)

**Query**:
```javascript
const deptByTerm = {};
courses.forEach(course => {
    const dept = course.code.split(/[\s-]+/)[0];
    if (!deptByTerm[course.term]) deptByTerm[course.term] = {};
    deptByTerm[course.term][dept] = (deptByTerm[course.term][dept] || 0) + 1;
});
```

**Why Useful**:
- **CIS expansion**: Likely growing due to AI/CS demand
- **Seasonal patterns**: Summer terms have fewer courses
- **Program stability**: Which departments maintain consistent offerings?
- Works for ALL historical terms

---

## Implementation Strategy

### Phase 1: Add to Existing Landing Page

**Location**: After current "Department Enrollment Distribution" chart

**New Section**: "📊 Course Catalog Analysis (All Terms)"

**Layout**:
```html
<section id="catalog-analysis">
    <h2>📊 Course Catalog Analysis</h2>
    <p class="subtitle">Explore course data across all terms, including historical data</p>

    <div class="chart-grid">
        <div class="chart-card">
            <h3>Course Offerings by Department</h3>
            <select id="catalog-term-select">
                <option value="all">All Terms</option>
                <option value="202530">Fall 2025</option>
                ...
            </select>
            <canvas id="dept-offerings-chart"></canvas>
        </div>

        <div class="chart-card">
            <h3>Schedule Type Distribution</h3>
            <canvas id="schedule-type-chart"></canvas>
        </div>

        <div class="chart-card">
            <h3>Instruction Method Trends</h3>
            <canvas id="instruction-method-chart"></canvas>
        </div>

        <div class="chart-card">
            <h3>Campus Distribution</h3>
            <canvas id="campus-chart"></canvas>
        </div>
    </div>
</section>
```

### Phase 2: Modify Export to Include These Fields

**Current export**: `api/v1/terms/{term}/index.json` includes enrollment data

**Add**:
```json
{
    "catalog_stats": {
        "schedule_types": {
            "Lecture": 4500,
            "Recitation": 800,
            "Laboratory": 600,
            ...
        },
        "instruction_methods": {
            "In Class": 5200,
            "Online": 800,
            "Hybrid": 400,
            ...
        },
        "campus_distribution": {
            "Philadelphia": 6000,
            "Online": 500,
            ...
        },
        "credit_distribution": {
            "0.5": 200,
            "1.0": 5500,
            "1.5": 300,
            ...
        },
        "department_counts": {
            "CIS": 150,
            "MATH": 120,
            "ECON": 110,
            ...
        }
    }
}
```

**File**: `src/export_granular.py` - add to `generate_term_index()`

### Phase 3: Update GitHub Actions Workflow

**Deploy workflow** already exports JSON from latest database.

**No changes needed** - just redeploy after implementing visualizations.

---

## Benefits

1. ✅ **Maximize historical data value**: 26,000 historical courses become useful
2. ✅ **COVID-19 documentation**: Visualize pandemic's impact on teaching methods
3. ✅ **Program trends**: Track department growth/decline over time
4. ✅ **Academic diversity**: Show Penn's teaching format variety
5. ✅ **Student utility**: Help students understand course structures
6. ✅ **No backend changes**: Uses existing data, just new visualizations
7. ✅ **Spring 2026 ready**: Can track advanced registration patterns

---

## Spring 2026 Advanced Registration Context

**Tomorrow** (Oct 9): Spring 2026 advanced registration opens

**Implication**: We can now start collecting **live enrollment snapshots** for Spring 2026

**Strategy**:
1. **Scrape Spring 2026 daily** during registration period
2. **Collect enrollment snapshots** (this is the KEY data)
3. **Track enrollment trends** (how fast do courses fill?)
4. **Identify high-demand courses** (enrolled > max = waitlists)

**These visualizations prepare us** by:
- Showing course catalog structure BEFORE enrollment
- Providing baseline for non-enrollment analytics
- Demonstrating value of historical data

---

## Implementation Priority

### High Priority (Week 1)
1. **Instruction Method Trends** - Shows COVID impact, most visually interesting
2. **Course Offerings by Department** - Most requested by students
3. **Schedule Type Distribution** - Shows academic diversity

### Medium Priority (Week 2)
4. **Longitudinal Department Growth** - Requires aggregation across terms
5. **School-Level Course Distribution** - Needs treemap library

### Low Priority (Week 3+)
6. **Campus Distribution** - Less variation (mostly Philadelphia)
7. **Credit Hour Distribution** - Mostly 1.0 CU, less interesting
8. **Course Format by School** - Requires complex grouping

---

## Questions for Jérémie

1. **Which visualization is most valuable** for your use case?
   - Instruction method trends (COVID impact)?
   - Department growth over time?
   - Schedule type diversity?

2. **Spring 2026 scraping schedule**:
   - Should I set up daily cron scrapes?
   - What time of day (to capture daily enrollment changes)?

3. **Historical term priority**:
   - Should we try to scrape older terms (Spring 2022, Fall 2021)?
   - Or focus on recent + future terms?

4. **Visualization library**:
   - Stick with Chart.js (current)?
   - Or add D3.js for advanced viz (treemap, sunburst)?

---

## Next Steps

1. ✅ Document non-enrollment visualizations (this ADR)
2. [ ] Implement Phase 1: Add catalog analysis section to landing page
3. [ ] Modify `export_granular.py` to include catalog stats
4. [ ] Test visualizations with Fall 2023 data (all null enrollment)
5. [ ] Deploy updated landing page
6. [ ] Set up Spring 2026 daily scraping cron job

---

**Created**: 2025-10-08
**Status**: Awaiting user feedback on priorities
