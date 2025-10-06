# ADR-0008: Side-by-Side Visualization Comparison with Dynamic Panels

**Date**: 2025-10-04
**Updated**: 2025-10-05
**Status**: Approved - Architecture Validated
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Visualization enhancement, user feedback on exploratory data analysis needs

## Context and Problem Statement

During our visualization development, Jérémie proposed a powerful enhancement:

> "For each of these distributions, it would be nice to be able to have several graphs side by side with different parameters so that they can be compared... Maybe like a plus button below each graph... it would make it much more engaging to explore these."
>
> — Jérémie Lumbroso

**The Vision**: Enable users to duplicate any visualization with independent filter settings, allowing side-by-side comparison of different views of the same data.

### Use Cases:

1. **Temporal Comparison**:
   - Fall 2024 vs Spring 2025 enrollment by school
   - Track department growth across terms

2. **Cross-School Comparison**:
   - Engineering vs Wharton class size distributions
   - Arts & Sciences vs Medicine fill rates

3. **Department Deep-Dives**:
   - CIS vs MATH vs ECON top courses
   - Compare multiple departments simultaneously

4. **Hypothesis Testing**:
   - "I wonder if online sections (500-series) have different fill rates than in-person sections"
   - Test intuitions with multiple filtered views

### What Makes This Powerful:

- **Exploratory**: Users can freely experiment without losing their current view
- **Comparative**: Side-by-side layout reveals patterns that single views miss
- **Contextual**: Each panel maintains its own filter state
- **Generative**: The act of creating comparisons sparks new questions

## Decision Drivers

1. **Discoverability**: Must be intuitive - users should understand what + does immediately
2. **Flexibility**: Allow arbitrary number of comparisons (within reason)
3. **Independence**: Each panel has its own filters, but shares the same visualization type
4. **Performance**: Loading multiple charts shouldn't slow down the page
5. **Responsive**: Must work on mobile (perhaps vertical stacking on small screens)
6. **Persistence**: Consider whether duplicates should survive page refresh
7. **Cleanup**: Easy to remove unwanted panels

## Proposed Design

### Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ School Enrollment Distribution                       [+ Add]  [×]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Panel 1: All Terms                     Panel 2: Fall 2024       │
│ ┌──────────────────────────────────┐  ┌──────────────────────┐  │
│ │ Filter: [All Terms▼]             │  │ Filter: [Fall 2024▼] │  │
│ │                                  │  │                      │  │
│ │ [Chart showing all terms data]   │  │ [Chart for F24 only] │  │
│ │                                  │  │                      │  │
│ │                                  │  │                      │  │
│ └──────────────────────────────────┘  └──────────────────────┘  │
│                                                          [×]      │
│                                                                  │
│ Panel 3: Spring 2025                                            │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Filter: [Spring 2025▼]                                   │   │
│ │                                                          │   │
│ │ [Chart for Spring 2025]                                  │   │
│ │                                                          │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                          [×]     │
└─────────────────────────────────────────────────────────────────┘
```

### Interaction Flow

1. **Initial State**: Single visualization with all existing filters
2. **Click [+ Add]**: Duplicate current panel (copies current filter values)
3. **Independent Filtering**: Each panel has its own filter dropdowns
4. **Remove Panel**: Click [×] on any panel to remove it (can't remove last panel)
5. **Responsive**: On mobile, panels stack vertically

### Layout System

**Desktop** (>1200px): Grid with 2-3 columns
**Tablet** (768-1200px): Grid with 2 columns
**Mobile** (<768px): Single column stack

**CSS Grid Implementation**:
```css
.comparison-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
    margin-top: 2rem;
}

.comparison-panel {
    position: relative;
    background: white;
    border-radius: var(--penn-radius-lg);
    padding: 1.5rem;
    box-shadow: var(--penn-shadow-md);
}

.panel-remove {
    position: absolute;
    top: 1rem;
    right: 1rem;
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 0.2s;
}

.panel-remove:hover {
    opacity: 1;
    color: var(--penn-red);
}
```

### State Management

```javascript
// Global state for each visualization type
const comparisonPanels = {
    'school-chart': [
        { id: 'panel-1', filters: { term: '' }, chart: null }
    ],
    'courses-chart': [
        { id: 'panel-1', filters: { term: '', school: '', dept: '' }, chart: null }
    ],
    'fillrate-chart': [
        { id: 'panel-1', filters: { term: '', school: '', dept: '' }, chart: null }
    ],
    // ... etc
};

function addComparisonPanel(chartType) {
    const panels = comparisonPanels[chartType];
    const lastPanel = panels[panels.length - 1];

    // Create new panel with copied filters from last panel
    const newPanel = {
        id: `panel-${Date.now()}`,
        filters: { ...lastPanel.filters },  // Copy current filters
        chart: null
    };

    panels.push(newPanel);
    renderComparisonPanels(chartType);
}

function removeComparisonPanel(chartType, panelId) {
    const panels = comparisonPanels[chartType];

    // Don't allow removing the last panel
    if (panels.length === 1) return;

    const index = panels.findIndex(p => p.id === panelId);
    if (index !== -1) {
        // Destroy chart instance
        if (panels[index].chart) {
            panels[index].chart.destroy();
        }
        panels.splice(index, 1);
        renderComparisonPanels(chartType);
    }
}
```

### HTML Structure Per Panel

```html
<div class="comparison-panel" data-panel-id="panel-123">
    <button class="panel-remove" onclick="removePanel('school-chart', 'panel-123')">
        ✕
    </button>

    <div class="panel-filters">
        <label>Filter by Term:</label>
        <select class="panel-filter" data-filter="term" onchange="updatePanelChart('school-chart', 'panel-123')">
            <option value="">All Terms</option>
            <option value="202530">Fall 2025</option>
            <option value="202520">Spring 2025</option>
        </select>
    </div>

    <canvas id="school-chart-panel-123"></canvas>

    <div class="panel-stats">
        <!-- Optional: Show aggregate stats for this specific panel -->
    </div>
</div>
```

## Advanced Features

### Feature 1: Panel Titles

Allow users to name each panel for clarity:

```html
<div class="panel-header">
    <input type="text"
           class="panel-title-input"
           placeholder="Panel Title (optional)"
           value="Fall 2024 - Engineering"
           onchange="updatePanelTitle('panel-123', this.value)">
</div>
```

### Feature 2: Synchronized Y-Axes (Optional Toggle)

For meaningful comparison, allow users to lock Y-axis scales across panels:

```html
<div class="comparison-controls">
    <label>
        <input type="checkbox" id="sync-y-axis" onchange="toggleAxisSync('school-chart')">
        Synchronize Y-Axis Scales
    </label>
</div>
```

When enabled:
```javascript
function syncYAxes(chartType) {
    const panels = comparisonPanels[chartType];
    const allCharts = panels.map(p => p.chart);

    // Find global max across all panels
    const globalMax = Math.max(...allCharts.map(chart => {
        return Math.max(...chart.data.datasets[0].data);
    }));

    // Update all charts with same scale
    allCharts.forEach(chart => {
        chart.options.scales.y.max = globalMax * 1.1;  // 10% padding
        chart.update();
    });
}
```

### Feature 3: Export Comparison View

Allow users to save their comparison setup as an image or shareable link:

```javascript
function exportComparison(chartType) {
    const panels = comparisonPanels[chartType];

    // Generate shareable URL with filter state
    const config = panels.map(p => ({
        filters: p.filters,
        title: p.title
    }));

    const url = new URL(window.location);
    url.searchParams.set('comparison', btoa(JSON.stringify(config)));
    navigator.clipboard.writeText(url.toString());

    alert('Comparison link copied to clipboard!');
}
```

### Feature 4: Collapse/Expand Panels

For users creating many panels, allow collapsing to save space:

```html
<button class="panel-collapse" onclick="togglePanelCollapse('panel-123')">
    ▼ Collapse
</button>
```

## Rationale

### Why This Design?

1. **Progressive Disclosure**: Starts simple (single chart), reveals power on demand
2. **Familiar Pattern**: + button is universally understood (browser tabs, music playlists)
3. **No Modal Dialogs**: Everything happens inline, maintaining context
4. **Graceful Degradation**: Works on mobile with vertical stacking

### Why Independent Filters?

- Enables the core use case (comparison across different parameters)
- Each panel is a self-contained "question" about the data
- Users can experiment freely without breaking other panels

### Why Grid Layout?

- Flexible: Automatically adjusts to screen size and panel count
- Scannable: Side-by-side comparison is easier than vertical scrolling
- Aesthetic: Maintains Penn's clean, organized design language

## Implementation Plan

**Architecture**: Wrapper-based (ComparisonManager) - zero intrusion on visualization classes

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `ComparisonManager` class (wrapper pattern)
- [ ] Implement panel state management (4 max, warn at 4, hard limit at 6)
- [ ] Add [+ Add] button to each visualization section
- [ ] Implement panel removal (protect last panel)
- [ ] Create responsive grid layout (CSS Grid)
- [ ] Default: **Copy filters from last panel** (per user feedback)

### Phase 2: Enhanced UX (Week 2)
- [ ] Add panel titles (optional naming)
- [ ] Implement **Y-axis sync ON by default** with toggle
- [ ] Add visual feedback (loading states, empty states)
- [ ] Polish animations (panel add/remove transitions)
- [ ] **Desktop-first** optimization (mobile secondary per user feedback)

### Phase 3: Exploration Features (Week 3)
- [ ] **Quests**: Preset comparison buttons ("Engineering vs Wharton")
- [ ] **Exploration guide**: Educational language explaining comparison philosophy
- [ ] URL hash serialization (shareable comparison links via #anchor)
- [ ] Limit enforcement: Warning at 4 panels, block at 6

### Phase 4: Advanced Features (Future)
- [ ] Drag-and-drop panel reordering
- [ ] Export comparison as image (canvas → PNG)
- [ ] Keyboard shortcuts (Ctrl+D to duplicate, Ctrl+W to remove)
- [ ] Analytics tracking (requires backend - future ADR)

## Consequences

### Positive:
- ✅ Transforms visualizations from static dashboards into exploratory tools
- ✅ Enables hypothesis-driven data analysis
- ✅ Increases user engagement and time on page
- ✅ Showcases the richness of the dataset
- ✅ Natural fit for academic/analytical use cases

### Negative:
- ❌ Increases code complexity (state management across multiple instances)
- ❌ Higher memory usage (multiple Chart.js instances)
- ❌ Requires careful UX design to avoid overwhelming users
- ❌ Mobile experience may be cramped with many panels

### Risks and Mitigations:

**Risk**: Users create too many panels, browser slows down
**Mitigation**:
- Limit to 4-6 panels max per visualization type
- Show warning: "Too many panels may impact performance"
- Add "Remove All" button to quickly reset

**Risk**: Confusing for casual users who just want one chart
**Mitigation**:
- Start with single panel (familiar experience)
- Make + button small and secondary (not prominent)
- Add tooltip explaining the feature on hover

**Risk**: State management bugs (charts not updating correctly)
**Mitigation**:
- Comprehensive unit tests for state mutations
- Use unique IDs for each panel (timestamp + random)
- Clear separation between panel state and chart instances

**Risk**: Responsive design breaks with many panels
**Mitigation**:
- Test with 1, 2, 3, 4 panels on various screen sizes
- Force vertical stacking on mobile regardless of panel count
- Add horizontal scroll as fallback

## User Experience Considerations

### Discoverability

How do users find this feature?

1. **Visual hint**: Small + icon appears on hover over visualization title
2. **Tooltip**: "Add comparison panel" on hover
3. **Demo**: First time user visits, show brief animation of + button
4. **Documentation**: Include in the "Explore Penn Through Data" section

### Learning Curve

1. **Intuitive first use**: Click +, get duplicate → immediate understanding
2. **Experimentation**: Users can freely add/remove without consequence
3. **Undo-friendly**: Removing panels is instant and reversible (just add again)

### Power User Features

For users who embrace this:
- Keyboard shortcuts
- URL-based sharing of complex comparison setups
- Export all panels as multi-page PDF
- Save favorite comparison configurations

## Clarifying Questions and Answers

### QST: Panel limit and UX considerations
- Status: answered
- Why asking: Need to balance exploration vs performance

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

**1. Panel Limit**: 4 (with warning), max 6

**2. Default Behavior**: **Copy current filters**
> "I think when people are using this, it is to compare mostly similar parameters that differ in one point. To facilitate that work, we should assume they'd rather have all their parameters copied. At worst, they will have to manually select each dimension (as they would with all defaults). But at best they will want to tweak only one dimension."

**3. Mobile Priority**: Desktop first for MVP
> "For now, it's more important to prototype and get this feature right. Fixing it for mobile will be secondary. If you want to reach for the stars as of now, you can, but I'd be happy if it were great on desktop for now."

**4. Persistence**: **URL anchor** (not localStorage)
> "No, this is not important at all. If convenient and not too complex, the best solution is to store the information and choices in the #anchor of the URL. But this can certainly be an ADR for the future."
>
> "These visualizations are an invitation to explore the main product, i.e. the API."

**5. Y-Axis Sync**: **ON by default** with toggle
> "Yes, on by default. Ideally with a toggle."

**6. Visual Design**: My call
> "Visually I am not very opinionated, and your gut instinct seem to far outpace mine."

**7. Analytics**: Future feature
> "I think this would require storage or backends of some sort, and is an interesting idea to flag for the future, but not for our next MVP."

---

### QST: How to implement without creating complexity spread?
- Status: answered
- Why asking: User's SUPER IMPORTANT concern about intrusive complexity
- What helps: Architectural pattern that isolates comparison logic

**🚨 User's Concern** (by Jérémie Lumbroso, 2025-10-05):
> "SUPER IMPORTANT: But I think there's a possibility for this to not be scaffolded well, and to result in major coding complexity for all plots. Any ideas on this?"

**ANS:** (by Claude Sonnet 4.5, 2025-10-05)

**Decision**: Wrapper-based architecture with locality of concern

The key is to **wrap, not modify** - treat each visualization as a black box that can be instantiated multiple times without knowing it's being compared.

#### Architecture Pattern: The ComparisonManager

```javascript
// visualization.js - EXISTING CODE, NO CHANGES
class SchoolEnrollmentChart {
    constructor(canvasId, filters) {
        this.canvasId = canvasId;
        this.filters = filters;
        this.chart = null;
    }

    render(data) {
        // Draw chart
        // All state is LOCAL to this instance
    }

    updateFilters(newFilters) {
        this.filters = {...this.filters, ...newFilters};
        this.refresh();
    }
}

// comparison-wrapper.js - NEW, ISOLATED MODULE
class ComparisonManager {
    constructor(visualizationType, containerSelector) {
        this.type = visualizationType;
        this.container = document.querySelector(containerSelector);
        this.panels = [];
        this.syncYAxis = true;  // Default ON per user feedback
    }

    addPanel(initialFilters) {
        const panelId = `panel-${Date.now()}`;
        const panel = {
            id: panelId,
            filters: initialFilters || this.copyLastFilters(),
            instance: null  // Will hold visualization instance
        };

        this.panels.push(panel);
        this.renderPanel(panel);
    }

    renderPanel(panel) {
        // Create DOM structure
        const panelEl = this.createPanelDOM(panel);
        this.container.appendChild(panelEl);

        // Instantiate visualization (BLACK BOX)
        const canvasId = `${this.type}-${panel.id}`;
        panel.instance = new this.visualizationClass(canvasId, panel.filters);

        // Render with data
        panel.instance.render(this.getData());

        // Sync Y-axis if enabled
        if (this.syncYAxis) this.syncAllAxes();
    }

    // NO modification to visualization classes needed!
}
```

#### Zero-Intrusion Integration

**Before** (existing visualization):
```html
<div id="school-chart-section">
    <canvas id="school-chart"></canvas>
    <select onchange="updateFilters()">...</select>
</div>

<script>
    const chart = new SchoolEnrollmentChart('school-chart', {});
    chart.render(data);
</script>
```

**After** (with comparison):
```html
<div id="school-chart-section">
    <button onclick="comparisonManager.addPanel()">+ Add Comparison</button>
    <div id="school-chart-panels"></div> <!-- Container managed by wrapper -->
</div>

<script>
    // Initialize comparison manager (wraps existing class)
    const comparisonManager = new ComparisonManager(
        'school-enrollment',
        '#school-chart-panels'
    );
    comparisonManager.visualizationClass = SchoolEnrollmentChart;
    comparisonManager.addPanel({}); // Add initial panel
</script>
```

**The visualization class never knows it's being compared!**

#### Isolation Guarantees

1. **No global state** - Each visualization instance is self-contained
2. **No name collisions** - Panel IDs namespace everything (`panel-123-school-chart`)
3. **No shared DOM** - Each panel has its own canvas, filters, controls
4. **No cross-talk** - Panels communicate only through ComparisonManager

#### Adding Comparison to a New Visualization

**Steps**:
1. Write visualization class (as you always would)
2. Add one line: `comparisonManager.visualizationClass = YourChartClass`
3. Done!

**No modifications to**:
- Chart rendering logic
- Filter handling
- Data fetching
- Event listeners

---

### QST: Should we add explanatory language and "Quests"?
- Status: answered
- Why asking: User's excitement about making exploration educational

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

On the "Why This Excites Me" section:
> "Absolutely -> on that note, I wonder if there's any language we can put, maybe above the data visualizations, to explain both the feature and this philosophy. Maybe we can provide quests, that when clicked, provide a specific comparison... just ideas."

**Design**: Add introductory section + preset "Quests"

```html
<div class="exploration-guide">
    <h3>🔍 Explore Penn Through Comparison</h3>
    <p>Every + click is a hypothesis. Every panel arrangement is a story.
       Compare different views of the same data to discover patterns.</p>

    <div class="quests">
        <h4>Try these comparisons:</h4>
        <button onclick="loadQuest('engineering-vs-wharton')">
            📊 Engineering vs Wharton Enrollments
        </button>
        <button onclick="loadQuest('fall-spring-growth')">
            📈 Fall to Spring Growth Patterns
        </button>
        <button onclick="loadQuest('online-vs-in-person')">
            💻 Online (500s) vs In-Person Sections
        </button>
    </div>
</div>
```

**Quest Implementation**:
```javascript
const QUESTS = {
    'engineering-vs-wharton': [
        { filters: { school: 'E', term: '202530' }, title: 'Engineering - Fall 2025' },
        { filters: { school: 'W', term: '202530' }, title: 'Wharton - Fall 2025' }
    ],
    'fall-spring-growth': [
        { filters: { term: '202530' }, title: 'Fall 2025' },
        { filters: { term: '202510' }, title: 'Spring 2025' }
    ],
    'online-vs-in-person': [
        { filters: { sectionPattern: '[5-9]\\d{2}' }, title: 'Online Sections (500+)' },
        { filters: { sectionPattern: '[0-4]\\d{2}' }, title: 'In-Person Sections (000-499)' }
    ]
};

function loadQuest(questId) {
    const panels = QUESTS[questId];
    comparisonManager.clear();
    panels.forEach(p => comparisonManager.addPanel(p.filters, p.title));
}
```

## Why This Excites Me

This feature transforms our visualizations from *presentation* to *exploration*. It embodies the spirit of:

> "What if I could see X compared to Y?"

Every + click is a hypothesis. Every panel arrangement is a story. The user becomes the curator of their own insights.

It's the difference between:
- **Static**: "Here's enrollment by school" (one story)
- **Dynamic**: "What does Engineering vs Wharton vs Arts & Sciences look like over time?" (infinite stories)

This is the kind of tool that makes data *playful* - and play is where discovery happens.

---

**Related ADRs**:
- ADR-0007: Enrollment Counting (what gets displayed in each panel)
- ADR-0009: Creative Visualizations (which will also support comparison)
