# ADR-0011: Rooms and Buildings Data Infrastructure

**Date**: 2025-10-04
**Updated**: 2025-10-05
**Status**: Approved
**Deciders**: Jérémie Lumbroso (user), Claude Sonnet 4.5 (assistant)
**Context**: Spatial data integration for campus-aware course analytics

## Context and Problem Statement

During our visualization brainstorming, Jérémie proposed spatial data integration:

> "Maybe room occupancy - like which rooms are most booked, which buildings, etc. - and maybe we can create a rooms/index.json that has a master list of all the rooms, and their sizes. For now, I think it should be a feed that aggregates all the different room codes that exist... Maybe we can group the rooms by their building using the prefix (like 'TOWN 217' and 'TOWN 102' are in the same building, i.e. 'TOWN'). Then later we can have scraping of https://facilities.upenn.edu/maps/locations to create a dataset of buildings, with details and the base64 of the image of the building (this will be a very cool feature of the API that you can get building images like that)."

**The Vision**: Create a spatial layer connecting courses → rooms → buildings → campus map.

## Observed Room Data

From `tests/fixtures/sample_output.json`:

```json
"meetings": [
  {
    "days": "TR",
    "start_time": "08:30:00",
    "end_time": "09:59:00",
    "location": "TOWN 100"
  }
]
```

**Room Code Pattern**: `<BUILDING_CODE> <ROOM_NUMBER>`
- TOWN 100, TOWN 217, TOWN 309, etc. → Towne Building
- WILL 316 → Williams Hall
- DRLB 3N6 → David Rittenhouse Lab

## Phase 1: Room Aggregation (Immediate)

### Goal

Create `/api/v1/rooms/index.json` listing all unique rooms across all scraped courses.

### Data Structure

```json
{
  "rooms": [
    {
      "code": "TOWN 100",
      "building_code": "TOWN",
      "room_number": "100",
      "building_name": "Towne Building",
      "uses": 45,
      "capacity_range": [100, 150],
      "courses": ["CIS 1600-001", "ESE 2100-001"],
      "departments": ["CIS", "ESE"],
      "most_common_schedule_type": "Lecture"
    },
    {
      "code": "TOWN 217",
      "building_code": "TOWN",
      "room_number": "217",
      "building_name": "Towne Building",
      "uses": 23,
      "capacity_range": [16, 20],
      "courses": ["CIS 1600-201", "CIS 1200-205"],
      "departments": ["CIS"],
      "most_common_schedule_type": "Recitation"
    }
  ],
  "total_rooms": 342,
  "total_buildings": 87,
  "last_updated": "2025-10-04T12:00:00Z"
}
```

### Aggregation Logic

```python
def aggregate_rooms(all_courses):
    room_map = {}

    for course in all_courses:
        for section in course.get('sections', []):
            for meeting in section.get('meetings', []):
                location = meeting.get('location')
                if not location:
                    continue

                # Parse room code
                parts = location.split()
                if len(parts) < 2:
                    continue

                building_code = parts[0]
                room_number = ' '.join(parts[1:])

                room_key = location

                if room_key not in room_map:
                    room_map[room_key] = {
                        'code': location,
                        'building_code': building_code,
                        'room_number': room_number,
                        'uses': 0,
                        'courses': set(),
                        'departments': set(),
                        'schedule_types': []
                    }

                room_data = room_map[room_key]
                room_data['uses'] += 1
                room_data['courses'].add(f"{course['code']}-{section['section']}")
                room_data['departments'].add(get_department(course['code']))
                room_data['schedule_types'].append(section.get('schedule_type', 'Unknown'))

    # Post-process
    for room in room_map.values():
        room['courses'] = list(room['courses'])[:5]  # Limit for JSON size
        room['departments'] = list(room['departments'])
        room['most_common_schedule_type'] = most_common(room['schedule_types'])
        del room['schedule_types']  # Don't export raw list

    return list(room_map.values())
```

## Phase 2: Building Metadata (Next Iteration)

### Goal

Scrape Penn Facilities website for building metadata and images.

### Data Source

**URL**: https://facilities.upenn.edu/maps/locations

**Content Per Building**:
- Official building name
- Address
- Building code(s)
- Photo
- Description
- Coordinates (if available)

### Proposed Scraper

```python
def scrape_building_metadata():
    url = "https://facilities.upenn.edu/maps/locations"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.content, 'html.parser')

    buildings = []
    for building_card in soup.find_all(class_='building-card'):  # Hypothetical
        name = building_card.find('h3').text.strip()
        address = building_card.find(class_='address').text.strip()

        # Find image
        img_tag = building_card.find('img')
        img_url = img_tag['src'] if img_tag else None

        # Download image and convert to base64
        img_base64 = None
        if img_url:
            img_response = requests.get(img_url)
            img_base64 = base64.b64encode(img_response.content).decode('utf-8')

        buildings.append({
            'name': name,
            'address': address,
            'image_base64': img_base64,
            'image_mime_type': 'image/jpeg'  # or detect from content-type
        })

    return buildings
```

### Data Structure: `/api/v1/buildings/index.json`

```json
{
  "buildings": [
    {
      "code": "TOWN",
      "name": "Towne Building",
      "full_name": "Towne School of Civil and Mechanical Engineering Building",
      "address": "220 S 33rd Street, Philadelphia, PA 19104",
      "school": "Engineering",
      "departments": ["CIS", "ESE", "MEAM"],
      "total_rooms": 67,
      "total_uses": 342,
      "coordinates": {
        "lat": 39.9522,
        "lng": -75.1932
      },
      "image": {
        "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
        "mime_type": "image/jpeg",
        "width": 800,
        "height": 600
      },
      "description": "Home to the departments of Computer and Information Science, Electrical and Systems Engineering...",
      "url": "https://facilities.upenn.edu/maps/locations/towne-building"
    }
  ],
  "total_buildings": 87,
  "last_updated": "2025-10-04T12:00:00Z"
}
```

## Use Cases Enabled

### 1. Room Utilization Analysis

**Visualization**: Heat map of campus by room usage

```javascript
function calculateRoomUtilization() {
    return rooms.map(room => ({
        code: room.code,
        building: room.building_code,
        utilizationScore: room.uses,
        coursesPerWeek: room.uses  // Assuming 1 meeting/course/week
    })).sort((a, b) => b.utilizationScore - a.utilizationScore);
}
```

**Insights**:
- Which rooms are most heavily used?
- Which buildings have capacity?
- Underutilized spaces

### 2. Building-Level Course Distribution

**Visualization**: Bar chart of courses per building

```javascript
function groupCoursesByBuilding() {
    const buildingMap = new Map();

    rooms.forEach(room => {
        const building = room.building_code;
        if (!buildingMap.has(building)) {
            buildingMap.set(building, {
                code: building,
                totalCourses: 0,
                departments: new Set()
            });
        }

        const data = buildingMap.get(building);
        data.totalCourses += room.uses;
        room.departments.forEach(dept => data.departments.add(dept));
    });

    return Array.from(buildingMap.values())
        .sort((a, b) => b.totalCourses - a.totalCourses);
}
```

**Questions answered**:
- Which building hosts the most courses?
- Where is CIS primarily located?
- Cross-departmental building usage

### 3. Interactive Campus Map

**Visualization**: Leaflet.js map with building markers

```javascript
function createCampusMap() {
    const map = L.map('campus-map').setView([39.9522, -75.1932], 15);

    buildings.forEach(building => {
        const marker = L.marker([building.coordinates.lat, building.coordinates.lng])
            .addTo(map);

        // Popup with building image
        marker.bindPopup(`
            <div>
                <h3>${building.name}</h3>
                <img src="data:${building.image.mime_type};base64,${building.image.base64}"
                     style="max-width: 200px;">
                <p><strong>${building.total_uses}</strong> courses meet here</p>
                <p>Departments: ${building.departments.join(', ')}</p>
            </div>
        `);
    });
}
```

**Features**:
- Click building → see courses
- Color-code by utilization
- Filter by department

### 4. Cross-School Spatial Analysis

**Question**: Do different schools cluster in different parts of campus?

```javascript
function analyzeSchoolClustering() {
    const schoolBuildings = {};

    buildings.forEach(building => {
        building.departments.forEach(dept => {
            const school = getSchool(dept);
            if (!schoolBuildings[school]) {
                schoolBuildings[school] = [];
            }
            schoolBuildings[school].push(building.code);
        });
    });

    return schoolBuildings;
}
```

**Insight**: Engineering courses clustered in East Campus (TOWN, LRSM), Wharton in West (Huntsman, JMHH)

## Proposed Architecture

Based on the decision to implement as a module, here's the proposed project structure:

```
src/
  courses/              # Existing course scraping (refactored)
    api_client.py       # Penn courses API client
    parsers.py          # HTML/JSON parsing for course data
    models.py           # Course, Meeting, Instructor models
    persistence.py      # Database operations for courses
    scraper.py          # Course scraping orchestration

  facilities/           # NEW: Facilities scraping module
    scraper.py          # Scrape facilities.upenn.edu
    parsers.py          # Parse building pages, extract metadata
    models.py           # Room, Building models
    persistence.py      # Database operations for facilities
    enrichment.py       # Enrich course data with room/building info

  shared/               # Shared utilities
    types.py            # TypedDict definitions for both modules
    database.py         # Database connection management
    logging.py          # Structured logging setup

  cli.py                # CLI orchestration for both modules
  export.py             # Export both datasets to JSON
```

### Module Independence with Integration Points

**Independent Operation**:
```bash
# Each module can run independently
penn-scraper courses scrape --term 202530
penn-scraper facilities scrape
```

**Integration Points**:
1. **Database**: Shared database, separate tables
   - `courses` table → `meetings` table (room_code field)
   - `rooms` table → `buildings` table
   - Foreign key: `meetings.room_code` → `rooms.code` (soft reference)

2. **Exports**: Enriched course data when both modules have run
   ```python
   # If facilities data exists, enrich course exports
   if room_exists(meeting.room_code):
       meeting_json["room_capacity"] = room.capacity
       meeting_json["building"] = building.name
   ```

3. **API Structure**: Modular endpoints
   - `/api/v1/{term}/courses/` - Course data
   - `/api/v1/{term}/rooms/` - All room usage per term
   - `/api/v1/rooms/{room}/` - Room usage across terms
   - `/api/v1/rooms/{room}/{term}` - Room usage across per term
   - `/api/v1/facilities/buildings/` - Building metadata (term-independent)

### Implementation Phases

**Phase 1: Minimal Facilities Module** (Week 1-2)
- [ ] Create `src/facilities/` module structure
- [ ] Implement basic building scraper (facilities.upenn.edu)
- [ ] Store building metadata in database
- [ ] CLI: `penn-scraper facilities scrape`
- [ ] Export: `/api/v1/facilities/buildings/index.json`

**Phase 2: Room Aggregation** (Week 3)
- [ ] Parse room codes from existing course meeting data
- [ ] Group by building prefix
- [ ] Calculate per-term usage statistics
- [ ] Export: `/api/v1/{term}/rooms/{room}/index.json`

**Phase 3: Data Enrichment** (Week 4)
- [ ] Link `Meeting` → `Room` → `Building`
- [ ] Enrich course exports with room/building metadata
- [ ] Add room capacity, building name to meeting JSON

**Phase 4: Visualizations** (Week 5-6)
- [ ] Room utilization heat map
- [ ] Building distribution chart
- [ ] Interactive campus map
- [ ] Cross-school spatial analysis

## Technical Considerations

### Base64 Image Storage

**Pros**:
- Self-contained JSON (no external dependencies)
- Works offline
- Simple to implement

**Cons**:
- Large file sizes (base64 is ~33% larger than binary)
- Slower parsing

**Mitigation**:
- Compress images before encoding (max 800px wide)
- Lazy-load images (don't include in main index, fetch on-demand)
- Offer separate image endpoint: `/api/v1/buildings/TOWN/image.json`
- Offer original image: `/api/v1/buildings/TOWN/image.jpg`

**Alternative**: Store images as separate files:

```json
{
  "code": "TOWN",
  "name": "Towne Building",
  "image_url": "/api/v1/buildings/TOWN/image.jpg"
}
```

**Recommendation**: Start with base64 for simplicity, migrate to separate files if size becomes issue.

### Room Code Normalization

Some courses may use inconsistent room codes:
- "TOWN 100" vs "Towne 100" vs "TOWN-100"

**Solution**: Normalize during aggregation:

```python
def normalize_room_code(location):
    # Uppercase
    location = location.upper()
    # Remove dashes
    location = location.replace('-', ' ')
    # Collapse multiple spaces
    location = ' '.join(location.split())
    return location
```

## Clarifying Questions and Answers

### QST: How should rooms API be structured?
- Status: answered
- Why asking: Original design had `/api/v1/rooms/index.json` linking to all courses using each room
- What helps: Understand scalability concerns

**ANS:** (by Jérémie Lumbroso, 2025-10-05)

**Problem identified**:
> "In the index.json, I'm afraid if you link to the courses — that list will be huge, especially because courses can change over terms! Not tractable."

**Solution**: Per-term structure:
```
/api/v1/{term}/rooms/{room}/index.json
```

This gives the list of all sections that take place in that room **in that term**.

**Benefits**:
- Manageable file sizes (only one term's data)
- Temporal consistency (courses tied to specific term)
- Aligns with existing course API structure
- Easy to compare room usage across terms

---

### QST: Should facilities scraper be a separate project or module in this project?
- Status: answered
- Why asking: Need to decide architecture before implementing
- What helps: Analysis of pros/cons, maintenance burden, data integrity

**ANS:** (by Claude Sonnet 4.5, validated by Jérémie Lumbroso, 2025-10-05)

**Decision**: **Module in this project**

#### Rationale

**1. Conceptual Unity**

This project is really about **"Penn academic infrastructure data"** - you can't meaningfully plan paths or analyze courses without knowing:
- Where is LEVN 101?
- What's the capacity?
- Are these two classes in the same building?

Courses and facilities are **tightly coupled** in the real world. They should be in our data model too.

**2. Data Integrity**

```python
# Current Course data has:
Meeting:
  room_code: "LEVN 101"
  room_url: "https://facilities.upenn.edu/maps/locations/levine-hall"

# Facilities module would add:
Room:
  code: "LEVN 101"  # ← MUST MATCH!
  capacity: 80
  building: FK → Building

Building:
  code: "LEVN"
  name: "Levine Hall, Melvin and Claire"
  coordinates: (39.952259, -75.191121)
```

If these are **separate projects**, we have two repos trying to use the same room codes with no enforcement. Recipe for drift.

**3. User Experience**

Someone using `penn-path-scraper` wants **enriched course data**:

```json
{
  "course": "CIS 1210",
  "meetings": [{
    "room": "LEVN 101",
    "room_capacity": 80,
    "building": "Levine Hall",
    "building_location": {"lat": 39.95, "lon": -75.19},
    "walking_distance_from_prev_class": "2min"  // ← requires facilities!
  }]
}
```

They don't want to manually join two datasets.

**4. Infrastructure Reuse**

We already have excellent patterns:
- `structlog` logging
- `click` CLI with subcommands
- `peewee` ORM with migration scripts
- `pytest` testing infrastructure
- Export system

Why rebuild all of this in a second repo?

**5. Different Update Frequencies**

```bash
# CLI design:
penn-scraper courses scrape --term 202530  # Run daily
penn-scraper facilities scrape               # Run weekly

# Cron jobs:
0 2 * * * penn-scraper courses scrape       # 2am daily
0 3 * * 0 penn-scraper facilities scrape    # 3am Sunday
```

One project, different schedules. Clean.

**6. Future-Proofing**

If we later decide to split:
- Already modularized (`src/facilities/`)
- Easy to extract to separate repo
- Git history preserved

But splitting now means we can never easily merge.

---

### Open Questions

1. **Room capacity**: Can we scrape actual room capacities from Penn's systems? Or infer from max_enrollment of courses?

2. **Building coordinates**: Does facilities.upenn.edu provide lat/long? Or use geocoding API?

3. **Historical room data**: Track when courses change rooms semester-to-semester?

4. **Room features**: Capture AV equipment, accessibility, etc.?

5. **Cross-listing**: If CIS 1200 is cross-listed with NETS 1200, do we count room usage twice?

## Success Metrics

- [ ] Complete room inventory (all rooms in current term)
- [ ] Building metadata for top 20 most-used buildings
- [ ] At least one visualization using spatial data
- [ ] Building images successfully encoded and displayable

---

**Related ADRs**:
- ADR-0009: Creative Visualizations (spatial visualizations)
- ADR-0002: JSON Export Structure (rooms/buildings API format)
