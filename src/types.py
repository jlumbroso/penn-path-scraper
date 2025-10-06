"""
TypedDict definitions for Penn course catalog scraper.

All data structures used throughout the application are defined here
to ensure type safety and clear contracts between components.
"""

import typing


# =============================================================================
# Raw API Response Types (from courses.upenn.edu/api)
# =============================================================================

class MeetingTimeDict(typing.TypedDict):
    """Single meeting time from meetingTimes JSON array."""
    meet_day: str  # "0"=Sun, "1"=Mon, ..., "6"=Sat
    start_time: str  # Military time, e.g., "1715" = 5:15 PM
    end_time: str  # Military time, e.g., "1844" = 6:44 PM


class APICourseSearchResult(typing.TypedDict):
    """Course data from search endpoint (?route=search)."""
    key: str  # Course unique key in database
    code: str  # Course code, e.g., "CIS 1210"
    title: str  # Course title
    crn: str  # Course Reference Number (section identifier)
    hide: str  # Empty string or "1" if hidden
    meetingTimes: str  # JSON-encoded array of MeetingTimeDict
    no: str  # Section number, e.g., "001"
    total: str  # Total number of sections for this course
    schd: str  # Schedule type: "LEC", "REC", "LAB", "SEM", etc.
    stat: str  # Status: "A"=Active, "C"=Closed, etc.
    isCancelled: str  # "1" if cancelled, "" otherwise
    meets: str  # Human-readable meeting time, e.g., "TR 5:15-6:44p"
    mpkey: str  # Meeting pattern key
    instr: str  # Instructor name(s), e.g., "J. Lumbroso" or "Team"
    start_date: str  # ISO date: "2025-08-26"
    end_date: str  # ISO date: "2025-12-08"
    cart_opts: str  # JSON-encoded cart options
    linked_crns: str  # Comma-separated CRNs of linked sections
    auto_enroll_sections: str
    is_enroll_section: str
    srcdb: str  # Term code, e.g., "202530"


class APICourseDetails(typing.TypedDict, total=False):
    """
    Course details from details endpoint (?route=details).

    Note: total=False because not all fields are always present.
    """
    key: str
    mpkey: str
    schd: str
    cart_opts: str
    linked_crns: str
    auto_enroll_sections: str
    is_enroll_section: str
    isTeaching: str
    code: str  # e.g., "CIS 1210"
    section: str  # e.g., "001"
    crn: str
    title: str
    dbtime: str
    status_new: str  # e.g., "Active"
    schedule_type: str  # e.g., "Lecture", "Recitation"
    inst_method_code: str  # e.g., "In Class"
    campus_code: str  # e.g., "Philadelphia"
    hours_html: str  # Credit hours
    xlist: str  # Cross-listed courses
    seats: str  # HTML with enrollment data
    notes_sapr: str
    description: str  # Course description (plain text with HTML links)
    clssnotes: str  # HTML with class notes
    registration_restrictions: str  # HTML with restrictions
    registration_options: str
    fees: str
    attributes_detail: str  # HTML list of course attributes
    meeting_html: str  # HTML with room/time info
    instructordetail_html: str  # HTML with instructor info
    exam_time: str
    linkedhtml: str  # HTML for linked sections
    syllabus: str
    order_books_bn_html: str  # Barnes & Noble book order form
    homepage: str
    canvas_url: str
    canvas_registered_url: str  # HTML link to Canvas
    cat_sections: str
    all_sections: str  # HTML table of all sections
    all_sections__data: str  # JSON data for all sections
    cart_opts_rules_json: str  # JSON rules for cart options
    srcdb: str
    allInGroup: typing.List[APICourseSearchResult]  # All sections for this course


class APISearchResponse(typing.TypedDict):
    """Response from search endpoint."""
    srcdb: str  # Term code
    count: int  # Number of results
    results: typing.List[APICourseSearchResult]


# =============================================================================
# Parsed Data Types (normalized/cleaned versions)
# =============================================================================

class ParsedSeatsDict(typing.TypedDict):
    """Parsed enrollment information from HTML."""
    max_enrollment: typing.Optional[int]  # Maximum capacity (None if unknown)
    seats_available: typing.Optional[int]  # Currently available seats (None if unknown)
    enrolled: typing.Optional[int]  # Current enrollment (None if unknown)


class ParsedMeetingDict(typing.TypedDict):
    """Parsed meeting information from HTML."""
    days: str  # e.g., "TR", "MWF"
    start_time: str  # e.g., "17:15"
    end_time: str  # e.g., "18:44"
    room_code: str  # e.g., "TOWN 217"
    room_url: str  # Facilities URL
    start_date: str  # ISO date
    end_date: str  # ISO date


class InstructorDict(typing.TypedDict):
    """Instructor information."""
    name: str  # Full name or "Team" or "Staff"
    pennkey: typing.NotRequired[str]  # If available


class CourseDict(typing.TypedDict):
    """
    Normalized course data (combines API data + parsed HTML).

    This is the core data structure we'll store in the database.
    """
    # Identifiers
    code: str  # e.g., "CIS 1210"
    crn: str  # Unique section identifier
    term: str  # e.g., "202530"
    section: str  # e.g., "001", "201"

    # Basic info
    title: str
    description: str
    schedule_type: str  # "Lecture", "Recitation", "Lab", etc.
    inst_method_code: str  # "In Class", "Online", etc.
    campus_code: str  # "Philadelphia", "Online", etc.
    credits: str

    # Enrollment (parsed from HTML)
    max_enrollment: typing.Optional[int]  # None if seats data unavailable
    seats_available: typing.Optional[int]  # None if seats data unavailable
    enrolled: typing.Optional[int]  # None if seats data unavailable

    # Meeting info (parsed from HTML)
    meetings: typing.List[ParsedMeetingDict]

    # Instructor info (parsed from HTML)
    instructors: typing.List[InstructorDict]

    # Dates
    start_date: str  # ISO format
    end_date: str  # ISO format

    # Relationships
    linked_crns: typing.List[str]  # Related sections (e.g., lecture <-> recitation)

    # Status
    is_cancelled: bool
    status: str  # "Active", "Closed", etc.

    # Metadata
    last_scraped: str  # ISO timestamp

    # Additional fields (optional)
    notes: typing.NotRequired[str]
    restrictions: typing.NotRequired[str]
    attributes: typing.NotRequired[typing.List[str]]
    attributes_detail: typing.NotRequired[str]
    clssnotes: typing.NotRequired[str]
    exam_time: typing.NotRequired[str]
    fees: typing.NotRequired[str]
    xlist: typing.NotRequired[str]
    canvas_url: typing.NotRequired[str]
    canvas_registered_url: typing.NotRequired[str]
    syllabus: typing.NotRequired[str]
    homepage: typing.NotRequired[str]


class EnrollmentSnapshotDict(typing.TypedDict):
    """Single point-in-time enrollment observation."""
    timestamp: str  # ISO 8601 timestamp
    enrolled: int
    capacity: int
    waitlist: typing.NotRequired[int]  # Not always available


class EnrollmentHistoryDict(typing.TypedDict):
    """Time-series enrollment data for a course section."""
    course_code: str
    term: str
    crn: str
    snapshots: typing.List[EnrollmentSnapshotDict]


# =============================================================================
# Export/Feed Types (for GitHub Pages JSON feeds)
# =============================================================================

class CourseFeedDict(typing.TypedDict):
    """
    Course data for JSON feed export.

    Used in /api/courses/{code}/index.json
    """
    code: str
    title: str
    description: str
    sections: typing.List[typing.Dict[str, typing.Any]]  # Simplified section data
    last_updated: str  # ISO timestamp


class EnrollmentFeedDict(typing.TypedDict):
    """
    Enrollment time-series for JSON feed export.

    Used in /api/courses/{code}/enrollments.json
    """
    course_code: str
    term: str
    sections: typing.List[EnrollmentHistoryDict]
    last_updated: str


class TermFeedDict(typing.TypedDict):
    """
    All courses for a term.

    Used in /api/terms/{term}/index.json
    """
    term: str
    term_name: str  # e.g., "Fall 2025"
    courses: typing.List[typing.Dict[str, typing.Any]]  # Simplified course data
    last_updated: str


class InstructorIndexDict(typing.TypedDict):
    """Entry in instructor search index."""
    name: str
    courses: typing.List[typing.Dict[str, str]]  # [{code, term, crn}, ...]


class SearchIndexDict(typing.TypedDict):
    """
    Search indexes for instructors, departments, etc.

    Used in /api/search/instructors.json, /api/search/departments.json
    """
    index_type: str  # "instructors", "departments", etc.
    entries: typing.List[typing.Dict[str, typing.Any]]
    last_updated: str


class MasterIndexDict(typing.TypedDict):
    """
    Master index of all available data.

    Used in /api/index.json
    """
    version: str  # API version
    last_updated: str
    available_terms: typing.List[typing.Dict[str, str]]  # [{code, name, url}, ...]
    available_schools: typing.List[typing.Dict[str, str]]
    statistics: typing.Dict[str, int]  # {total_courses, total_sections, etc.}
    endpoints: typing.Dict[str, str]  # Available API endpoints


# =============================================================================
# Configuration Types
# =============================================================================

class SchoolConfig(typing.TypedDict):
    """School/college configuration."""
    code: str  # Single letter code
    name: str  # Full name


# List of all schools
SCHOOLS: typing.List[SchoolConfig] = [
    {"code": "A", "name": "School of Arts & Sciences"},
    {"code": "C", "name": "Annenberg School for Communication"},
    {"code": "D", "name": "School of Dental Medicine"},
    {"code": "E", "name": "School of Engineering and Applied Science"},
    {"code": "F", "name": "Stuart Weitzman School of Design"},
    {"code": "G", "name": "Graduate School of Education"},
    {"code": "L", "name": "Penn Carey Law"},
    {"code": "M", "name": "Perelman School of Medicine"},
    {"code": "N", "name": "School of Nursing"},
    {"code": "S", "name": "School of Social Policy & Practice"},
    {"code": "V", "name": "School of Veterinary Medicine"},
    {"code": "W", "name": "The Wharton School"},
]


# Day of week mappings
DAY_CODES: typing.Dict[str, str] = {
    "0": "Sunday",
    "1": "Monday",
    "2": "Tuesday",
    "3": "Wednesday",
    "4": "Thursday",
    "5": "Friday",
    "6": "Saturday",
}

DAY_ABBREVIATIONS: typing.Dict[str, str] = {
    "0": "Su",
    "1": "M",
    "2": "T",
    "3": "W",
    "4": "R",
    "5": "F",
    "6": "Sa",
}


def format_term_code(term: str) -> str:
    """
    Convert term code to human-readable name.

    Examples:
        202530 -> "Fall 2025"
        202510 -> "Spring 2025"
        202520 -> "Summer 2025"
    """
    year = term[:4]
    semester_code = term[4:]

    semester_map = {
        "10": "Spring",
        "20": "Summer",
        "30": "Fall",
    }

    semester = semester_map.get(semester_code, "Unknown")
    return f"{semester} {year}"


def parse_term_name(term_name: str) -> str:
    """
    Convert human-readable term name to term code.

    Examples:
        "Fall 2025" -> "202530"
        "Spring 2025" -> "202510"
    """
    parts = term_name.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid term name: {term_name}")

    semester, year = parts
    semester_map = {
        "Spring": "10",
        "Summer": "20",
        "Fall": "30",
    }

    if semester not in semester_map:
        raise ValueError(f"Invalid semester: {semester}")

    return f"{year}{semester_map[semester]}"
