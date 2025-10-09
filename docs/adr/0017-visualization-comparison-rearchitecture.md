# ADR-0017: Visualization Comparison Rearchitecture - Grouped Data, Not Panels

**Date**: 2025-10-08
**Status**: Approved
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: User feedback on ADR-0008 ComparisonManager implementation
**Supersedes**: ADR-0008 (partial)

## Context and Problem Statement

After implementing ADR-0008's ComparisonManager (side-by-side panel approach), user testing revealed fundamental UX issues:

### What We Built (ADR-0008)
- Side-by-side panels, each with independent chart
- Each panel ~400-500px wide
- Separate filter controls per panel
- "Compare" by placing charts next to each other

### Problems Discovered

1. **Space Constraints**: Horizontal bars for 10+ schools in 450px width → illegible labels
2. **Visual Bloat**: Too much padding around panels → charts become tiny
3. **Color Confusion**: Same colors in both panels → hard to distinguish Panel 1 vs Panel 2 data
4. **Wrong Mental Model**: Users don't want "two separate charts" - they want "one chart with multiple datasets"

### User Feedback (Jérémie, 2025-10-08)

> "Two tiny plots side by side with very different colors, with half the captions removed, it just makes it not legible at all."
>
> "For the department enrollment distribution... the right way would be to combine the bars two by two with the first graph is the first bar, the second graph is the second bar. So you would get to compare the ordering of the departments and also the size."
>
> "I think the comparison editor should be in the data, like the legend, the key. So at the top, you can do plus, and it adds another term to the legend for the second plot."

**Core Insight**: Users want **grouped/overlaid data on a SINGLE chart**, not multiple miniature charts.

---

## Decision

### Architecture: Vanilla JS Modular Components (Not React)

**Decision**: Build reusable vanilla JavaScript component classes.

**Rationale**:
- ✅ No build step required (works immediately on GitHub Pages)
- ✅ Faster iteration during development
- ✅ Easier to maintain in conversational context
- ✅ Can migrate to React later if complexity grows
- ✅ Still component-based (class modules with encapsulation)

**Alternative Considered**: React
- ❌ Requires build step (webpack/vite)
- ❌ Adds deployment complexity
- ❌ Heavier for relatively simple visualizations
- ✅ Better for complex state (but we don't have that yet)

**Alternative Considered**: Separate repo
- ❌ Increases coordination overhead
- ❌ Harder to iterate quickly
- ✅ Could work if visualization layer grows significantly

**Conclusion**: Start vanilla, reassess if we hit complexity ceiling.

---

## Comparison Paradigms by Chart Type

Different visualizations require different comparison approaches:

### Type 1: Grouped Bar Charts (Most Common)

**Use Case**: Department Enrollment, School Enrollment

**User Expectation**: See Fall 2025 bars next to Spring 2025 bars for EACH category

**Implementation**:
```
Engineering [Fall 2025] | Engineering [Spring 2025]
Wharton [Fall 2025] | Wharton [Spring 2025]
Arts & Sciences [Fall 2025] | Arts & Sciences [Spring 2025]
```

**Controls**:
- **+ Add Term** button in legend area
- Each added term creates a new dataset in Chart.js
- All terms on ONE chart with grouped bars
- Color-coded by term (Fall = blue gradient, Spring = red gradient)

### Type 2: Overlaid Line Charts

**Use Case**: Long Tail Enrollment

**User Expectation**: Multiple colored lines on same plot

**Implementation**:
- Each selected term/school = one line
- Different colors per selection
- Shared axes
- Legend shows all selections

### Type 3: Stacked/Grouped Metrics

**Use Case**: Fill Rate Distribution, Class Size Distribution

**User Expectation**: Depends on context
- **Fill Rate**: Grouped bars per range bucket
- **Class Size**: Pie charts side-by-side OK (small data)

### Type 4: Ranked Lists

**Use Case**: Top Courses, Most in Demand

**User Expectation**: Bump chart showing rank changes over time

**Implementation**:
- Bump chart library (d3.js or Chart.js with custom rendering)
- X-axis: Terms
- Y-axis: Rank (1-20)
- Lines connecting same course across terms
- Shows how CIS 1210 moved from #3 → #1

---

## Modular Component Architecture

### Core Reusable Components

#### 1. `TermSelector`
**Purpose**: Select multiple terms for comparison

**Features**:
- **+ Add Term** button
- Chips/badges for selected terms
- Remove term with × button
- Gray out terms with "(no enroll. data avail.)"
- Returns array of selected term codes

**Usage**:
```javascript
const termSelector = new TermSelector({
    containerId: 'term-selector',
    availableTerms: allTerms,
    termsWithoutEnrollment: ['202220', '202120'],
    onSelectionChange: (selectedTerms) => {
        updateChart(selectedTerms);
    }
});
```

#### 2. `SchoolSelector`
**Purpose**: Select schools for filtering/comparison

**Features**:
- Button/chip per school (compact, no padding)
- Toggle mode: Click = select only that school
- Checkbox mode: Multi-select
- Visual states: selected, unselected, disabled
- Returns array of selected school codes

**Modes**:
- **Single-select**: Click Engineering → only Engineering selected
- **Multi-select**: Checkbox per school

**Usage**:
```javascript
const schoolSelector = new SchoolSelector({
    containerId: 'school-selector',
    mode: 'single', // or 'multi'
    onSelectionChange: (selectedSchools) => {
        updateChart(selectedSchools);
    }
});
```

#### 3. `ChartDataBuilder`
**Purpose**: Transform course data into Chart.js datasets

**Features**:
- Filter courses by term, school, department
- Group by categories (school, department)
- Build datasets with stable colors
- Handle null enrollment gracefully

**Usage**:
```javascript
const builder = new ChartDataBuilder(allCourses);
const datasets = builder.buildGroupedBarDatasets({
    terms: ['202530', '202510'],
    groupBy: 'school',
    metric: 'enrolled'
});
// Returns: [{label: 'Fall 2025', data: [...]}, {label: 'Spring 2025', data: [...]}]
```

#### 4. `StableColorPalette`
**Purpose**: Consistent colors across all visualizations

**Features**:
- Department-to-color mapping (CIS = blue, ECON = teal, etc.)
- School-to-color mapping (uses school metadata)
- Term-to-gradient mapping (Fall = warm, Spring = cool)
- Semantic colors (Engineering = Penn Blue, Wharton = Penn Red)

**Usage**:
```javascript
const colors = new StableColorPalette();
colors.getSchoolColor('E');  // '#011F5B' (Penn Blue for Engineering)
colors.getDepartmentColor('CIS');  // '#0A3380' (dark blue)
colors.getTermGradient('202530');  // ['#011F5B', '#0A3380', ...] (Fall gradient)
```

---

## School Metadata System

### Data Structure

**File**: `landing/school-metadata.json`

```json
{
    "E": {
        "full_name": "School of Engineering and Applied Science",
        "short_name": "Engineering",
        "code": "E",
        "abbreviation": "SEAS",
        "url": "https://www.seas.upenn.edu/",
        "color": "#011F5B",
        "description": "Engineering and applied sciences"
    },
    "W": {
        "full_name": "The Wharton School",
        "short_name": "Wharton",
        "code": "W",
        "abbreviation": "Wharton",
        "url": "https://www.wharton.upenn.edu/",
        "color": "#990000",
        "description": "Business and finance"
    },
    "A": {
        "full_name": "School of Arts & Sciences",
        "short_name": "Arts & Sciences",
        "code": "A",
        "abbreviation": "SAS",
        "url": "https://www.sas.upenn.edu/",
        "color": "#4CAF50",
        "description": "Liberal arts and sciences"
    }
    // ... all 12 schools
}
```

### Color Assignment Strategy

**Semantic Matching** (where possible):
- **Engineering (E)**: Penn Blue `#011F5B` - Technical, precise
- **Wharton (W)**: Penn Red `#990000` - Bold, business-like
- **Arts & Sciences (A)**: Green `#4CAF50` - Natural, broad
- **Medicine (M)**: Hospital blue `#63C7FF` - Clinical
- **Design (F)**: Purple `#7B2D8E` - Creative
- **Nursing (N)**: Pink `#FF9800` - Care-focused
- **Law (L)**: Dark gray `#2D2926` - Authoritative
- **Education (G)**: Yellow `#FFC107` - Teaching
- **Veterinary (V)**: Earth brown `#807456` - Animals
- **Dental (D)**: Teal `#019CDE` - Clinical
- **Communication (C)**: Orange `#FF9800` - Media
- **Social Policy (S)**: Indigo `#3F51B5` - Social science

**Usage in Charts**:
```javascript
import schoolMeta from './school-metadata.json';

const schoolColor = schoolMeta['E'].color;  // '#011F5B'
const schoolURL = schoolMeta['E'].url;      // Link to SEAS site
```

---

## Implementation Roadmap

### Phase 1: Quick Fixes (30 minutes)

**Issues**:
1. Term formatting: "202530" → "Fall 2025"
2. Sorting broken in Most in Demand Courses
3. School chart orientation (flip to horizontal)
4. Top Courses: Labels cut off, sections duplicated
5. Teaching Stars: "No instructor data" bug
6. Terms count bug: Showing "17 terms" instead of 16

**Files to Fix**:
- `landing/index.html` - Term formatting in dropdowns
- Chart initialization - Sorting logic
- School chart - Change `indexAxis: 'y'`
- Top Courses - Filter logic, label display

### Phase 2: School Metadata (15 minutes)

**Tasks**:
- Create `landing/school-metadata.json`
- Define all 12 schools with metadata
- Assign semantic colors
- Test loading in page

### Phase 3: Modular Components (2 hours)

**File Structure**:
```
landing/
├── components/
│   ├── term-selector.js
│   ├── school-selector.js
│   ├── chart-data-builder.js
│   └── stable-color-palette.js
├── school-metadata.json
└── index.html
```

**Tasks**:
- Implement TermSelector class
- Implement SchoolSelector class
- Implement ChartDataBuilder class
- Implement StableColorPalette class
- Add to index.html before main script

### Phase 4: Rebuild Department Chart (1 hour)

**Goal**: Engineering[Fall] | Engineering[Spring] grouped bars

**Approach**:
```javascript
// Old: Single term, single dataset
loadDepartmentChart(termCode);

// New: Multiple terms, grouped datasets
const termSelector = new TermSelector({...});
termSelector.onSelectionChange((selectedTerms) => {
    const builder = new ChartDataBuilder(allCourses);
    const datasets = builder.buildGroupedBarDatasets({
        terms: selectedTerms,
        groupBy: 'department',
        metric: 'enrolled'
    });

    departmentChart.data.datasets = datasets;
    departmentChart.update();
});
```

**Chart.js Config**:
```javascript
{
    type: 'bar',
    data: {
        labels: ['CIS', 'ECON', 'MATH', ...],  // Departments
        datasets: [
            {
                label: 'Fall 2025',
                data: [1200, 980, 750, ...],
                backgroundColor: '#011F5B'
            },
            {
                label: 'Spring 2025',
                data: [1150, 1020, 780, ...],
                backgroundColor: '#990000'
            }
        ]
    },
    options: {
        plugins: {
            legend: { display: true }  // Show term legend
        }
    }
}
```

### Phase 5: Apply to Other Charts (2 hours)

**Charts to Update**:
1. School Enrollment (same grouped bar approach)
2. Long Tail Enrollment (overlaid lines)
3. Top Courses (bump chart for rank changes)
4. Fill Rate Distribution (grouped bars)

---

## Comparison Feature Examples

### Example 1: Department Enrollment Over Time

**User Action**:
1. Click "+ Add Term" → Select "Fall 2025"
2. Click "+ Add Term" → Select "Spring 2025"
3. Chart shows grouped bars

**Result**:
```
[CIS]
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ Fall 2025 (1,200 students)
  ▓▓▓▓▓▓▓▓▓▓▓▓ Spring 2025 (1,150 students)

[ECON]
  ▓▓▓▓▓▓▓▓▓▓ Fall 2025 (980 students)
  ▓▓▓▓▓▓▓▓▓▓▓ Spring 2025 (1,020 students) ← Grew!

[MATH]
  ▓▓▓▓▓▓▓ Fall 2025 (750 students)
  ▓▓▓▓▓▓▓▓ Spring 2025 (780 students)
```

**Insight**: ECON grew from Fall to Spring, CIS shrank

### Example 2: School Comparison Within Term

**User Action**:
1. TermSelector: Set to "Fall 2025"
2. SchoolSelector: Click "Engineering" → only Engineering
3. SchoolSelector: Shift+click "Wharton" → add Wharton

**Result**: Chart filters to only Engineering and Wharton bars for Fall 2025

---

## Migration Strategy for Existing Visualizations

### Department Enrollment Chart

**Before**:
```html
<select id="term-select">...</select>
<canvas id="enrollment-chart"></canvas>
```

**After**:
```html
<div id="term-selector-container"></div>
<canvas id="enrollment-chart"></canvas>

<script>
const termSelector = new TermSelector({
    containerId: 'term-selector-container',
    defaultSelection: ['202530'],  // Fall 2025
    onSelectionChange: (terms) => {
        const builder = new ChartDataBuilder(allCourses);
        const datasets = builder.buildGroupedBarDatasets({
            terms,
            groupBy: 'department',
            metric: 'enrolled'
        });
        updateDepartmentChart(datasets);
    }
});
</script>
```

### School Enrollment Chart

**Before**:
```javascript
// Horizontal bars (indexAxis: 'y')
// Single term only
```

**After**:
```javascript
// Vertical bars (indexAxis: 'x') - matches Department chart
// Multiple terms with grouped bars
// Same TermSelector + ChartDataBuilder pattern
```

---

## Term Formatting Fix

### Problem
Terms showing as "202530" instead of "Fall 2025"

### Root Cause
Term display uses `term.code` instead of `term.name` or formatted version

### Solution
Create helper function:
```javascript
function formatTermCode(termCode) {
    const year = '20' + termCode.substring(2, 4);
    const semester = termCode.substring(4, 5);

    const semesterMap = {
        '1': 'Spring',
        '2': 'Summer',
        '3': 'Fall'
    };

    return `${semesterMap[semester]} ${year}`;
}

// Usage
formatTermCode('202530');  // "Fall 2025"
formatTermCode('202410');  // "Spring 2024"
```

Apply to:
- All dropdown option labels
- Chart titles
- Legend labels
- Filter displays

---

## Gray Out Terms Without Enrollment Data

### Implementation

**TermSelector Component**:
```javascript
class TermSelector {
    constructor({ availableTerms, termsWithoutEnrollment }) {
        this.disabledTerms = new Set(termsWithoutEnrollment);
    }

    renderTermButton(termCode) {
        const disabled = this.disabledTerms.has(termCode);
        const label = disabled
            ? `${formatTermCode(termCode)} (no enroll. data avail.)`
            : formatTermCode(termCode);

        return `
            <button
                data-term="${termCode}"
                ${disabled ? 'disabled class="disabled"' : ''}>
                ${label}
            </button>
        `;
    }
}
```

**CSS**:
```css
button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
    color: var(--penn-medium-gray);
}
```

---

## What Happens to ComparisonManager?

### Decision: Keep but Don't Use (Yet)

**Rationale**:
- Good engineering work, just wrong use case
- May be useful for pie charts or future visualizations
- Document as "experimental" in ADR-0008
- Revisit if we find a chart that actually needs side-by-side panels

**Files**:
- Keep `landing/comparison-manager.js`
- Remove from Department/School charts
- Update ADR-0008 with "Lessons Learned"

---

## Success Criteria

**Phase 1 Complete**:
- [ ] All terms display as "Fall 2025" format
- [ ] Most in Demand sorting fixed
- [ ] School chart flipped to horizontal
- [ ] Top Courses labels all visible
- [ ] Teaching Stars loads correctly
- [ ] Terms count shows 16 (not 17)

**Phase 2 Complete**:
- [ ] School metadata JSON exists
- [ ] All 12 schools have colors, URLs, abbreviations
- [ ] Colors semantically meaningful

**Phase 3 Complete**:
- [ ] TermSelector component works
- [ ] SchoolSelector component works
- [ ] ChartDataBuilder returns correct datasets
- [ ] StableColorPalette provides consistent colors

**Phase 4 Complete**:
- [ ] Department chart shows grouped bars
- [ ] Can add multiple terms via + button
- [ ] Bars grouped: Engineering[Fall] | Engineering[Spring]
- [ ] Legend shows all terms
- [ ] Colors stable across selections

**Phase 5 Complete**:
- [ ] School chart uses same pattern
- [ ] Long Tail uses overlaid lines
- [ ] Top Courses shows all labels
- [ ] Terms without enrollment grayed out

---

## Related ADRs

- **ADR-0008**: Side-by-Side Comparison (superseded for most use cases)
- **ADR-0009**: Creative Visualizations
- **ADR-0015**: Non-Enrollment Visualizations
- **ADR-0016**: Spring 2026 Monitoring

---

## Lessons Learned from ADR-0008

### What We Got Right
- ✅ Zero-intrusion wrapper pattern (good architecture)
- ✅ Filter state management (reusable concept)
- ✅ Y-axis sync idea (still valid for grouped bars)
- ✅ Panel color coding (inspired stable color palette)

### What We Got Wrong
- ❌ **Mental Model**: Users don't think in "panels" - they think in "datasets"
- ❌ **Space Usage**: Side-by-side doesn't work for dense horizontal bars
- ❌ **Comparison Paradigm**: Separate charts ≠ comparison (grouped data = comparison)

### Key Insight
> "Comparison in data visualization means showing differences ON THE SAME CHART, not showing separate charts next to each other."
>
> — Learned from user feedback

---

**Status**: ✅ APPROVED - Ready for implementation
**Next Action**: Implement Phase 1 quick fixes
**Estimated Time**: Phase 1-2: 45 min, Phase 3: 2 hrs, Phase 4-5: 3 hrs
**Total**: ~6 hours of implementation
