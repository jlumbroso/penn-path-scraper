"""
Granular JSON export following ADR-0002 Option C architecture.

Implements the hybrid approach with separate files for:
- Course metadata (static)
- Enrollment history (frequently updated)
- Search indexes
- Term listings

JSON Minification Strategy (ADR-0004):
- Before 2026-04-01: Pretty-printed (indent=2) for debugging
- After 2026-04-01: Minified for performance
- Override with PENN_SCRAPER_COMPACT_JSON environment variable
"""

import datetime
import json
import os
import pathlib
import typing

import src.models


# Minification trigger date (ADR-0004)
MINIFICATION_TRIGGER_DATE = datetime.date(2026, 4, 1)


def _should_compact_json() -> bool:
    """
    Determine if JSON should be compact (minified) based on ADR-0004.

    Returns True if:
    - PENN_SCRAPER_COMPACT_JSON=true (environment override)
    - Current date >= MINIFICATION_TRIGGER_DATE

    Returns False if:
    - PENN_SCRAPER_COMPACT_JSON=false (environment override)
    - Current date < MINIFICATION_TRIGGER_DATE
    """
    # Check environment variable override
    env_compact = os.getenv("PENN_SCRAPER_COMPACT_JSON", "").lower()
    if env_compact == "true":
        return True
    elif env_compact == "false":
        return False

    # Default: time-based trigger
    return datetime.date.today() >= MINIFICATION_TRIGGER_DATE


def _json_dump_kwargs() -> typing.Dict[str, typing.Any]:
    """
    Get kwargs for json.dump() based on compaction setting.

    Returns:
        Pretty-printed: {"indent": 2}
        Minified: {"separators": (',', ':')}
    """
    if _should_compact_json():
        # Minified: no whitespace
        return {"separators": (',', ':')}
    else:
        # Pretty-printed: human-readable
        return {"indent": 2}


def export_granular_structure(output_dir: str) -> None:
    """
    Export all data using ADR-0002 Option C granular structure.

    Structure:
    /api/v1/
      /courses/
        /{course-code}/
          index.json          # Course metadata + current sections
          enrollments.json    # Time-series enrollment data
      /terms/
        /{term-code}/
          index.json          # All courses in this term
      /search/
        instructors.json      # Instructor → courses mapping
        departments.json      # Department → courses mapping
      index.json              # Master index

    Args:
        output_dir: Base directory for API structure (will create /api/v1 subdirectory)
    """
    base_path = pathlib.Path(output_dir)
    api_path = base_path / "api" / "v1"

    # Create directory structure
    (api_path / "courses").mkdir(parents=True, exist_ok=True)
    (api_path / "terms").mkdir(parents=True, exist_ok=True)
    (api_path / "search").mkdir(parents=True, exist_ok=True)

    # Export each component
    _export_courses(api_path / "courses")
    _export_terms(api_path / "terms")
    _export_search_indexes(api_path / "search")
    _export_master_index(api_path / "index.json")


def _export_courses(courses_dir: pathlib.Path) -> None:
    """Export individual course files with metadata and enrollments separated."""
    # Get all unique course codes across all terms
    courses = src.models.Course.select()

    # Group by course code (normalize to handle different sections)
    course_groups: typing.Dict[str, typing.List[src.models.Course]] = {}
    for course in courses:
        # Use base course code (e.g., "CIS-1210" from "CIS 1210 001")
        base_code = course.code.replace(" ", "-")
        if base_code not in course_groups:
            course_groups[base_code] = []
        course_groups[base_code].append(course)

    # Export each course group
    for base_code, course_list in course_groups.items():
        course_path = courses_dir / base_code
        course_path.mkdir(exist_ok=True)

        # Export course metadata (index.json)
        _export_course_metadata(course_path / "index.json", course_list)

        # Export enrollment history (enrollments.json)
        _export_course_enrollments(course_path / "enrollments.json", course_list)


def _export_course_metadata(
    output_file: pathlib.Path, courses: typing.List[src.models.Course]
) -> None:
    """
    Export course metadata (relatively static data).

    Includes: course details, instructors, meetings, linked sections.
    Does NOT include enrollment history (that's in enrollments.json).
    """
    sections = []

    for course in courses:
        # Get instructors
        instructors = [
            ci.instructor.name
            for ci in src.models.CourseInstructor.select().where(
                src.models.CourseInstructor.course == course
            )
        ]

        # Get meetings
        meetings = []
        for meeting in src.models.Meeting.select().where(
            src.models.Meeting.course == course
        ):
            meetings.append(
                {
                    "days": meeting.days,
                    "start_time": meeting.start_time.isoformat()
                    if meeting.start_time
                    else None,
                    "end_time": meeting.end_time.isoformat()
                    if meeting.end_time
                    else None,
                    "location": meeting.room_code if meeting.room_code else "",
                }
            )

        # Get linked sections
        linked_crns = [
            ls.linked_crn
            for ls in src.models.LinkedSection.select().where(
                src.models.LinkedSection.course == course
            )
        ]

        sections.append(
            {
                "crn": course.crn,
                "term": course.term.code,
                "term_name": course.term.name,
                "section": course.section,
                "title": course.title,
                "schedule_type": course.schedule_type,
                "status": course.status,
                "is_cancelled": course.is_cancelled,
                "credits": course.credits,
                "start_date": course.start_date.isoformat()
                if course.start_date
                else None,
                "end_date": course.end_date.isoformat() if course.end_date else None,
                "description": course.description,
                "instructors": instructors,
                "meetings": meetings,
                "linked_sections": linked_crns,
                # Current enrollment snapshot (not history)
                "current_enrollment": {
                    "enrolled": course.enrolled,
                    "max_enrollment": course.max_enrollment,
                    "seats_available": course.seats_available,
                },
            }
        )

    data = {
        "course_code": courses[0].code if courses else "",
        "sections": sections,
        "last_updated": datetime.datetime.now().isoformat(),
    }

    with open(output_file, "w") as f:
        json.dump(data, f, **_json_dump_kwargs())


def _export_course_enrollments(
    output_file: pathlib.Path, courses: typing.List[src.models.Course]
) -> None:
    """
    Export enrollment history (frequently updated data).

    Separate from metadata to minimize git diffs and file sizes.

    Format (ADR-0004):
    - Latest values at section level for quick access
    - Snapshots sorted DESC (newest first) for guaranteed ordering
    """
    sections_enrollment = []

    for course in courses:
        snapshots = []
        for snapshot in (
            src.models.EnrollmentSnapshot.select()
            .where(src.models.EnrollmentSnapshot.course == course)
            .order_by(src.models.EnrollmentSnapshot.timestamp.desc())  # DESC: newest first
        ):
            snapshots.append(
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "enrolled": snapshot.enrolled,
                    "capacity": snapshot.capacity,
                }
            )

        # Extract latest values from first snapshot (newest)
        latest_enrolled = snapshots[0]["enrolled"] if snapshots else None
        latest_capacity = snapshots[0]["capacity"] if snapshots else None
        latest_timestamp = snapshots[0]["timestamp"] if snapshots else None

        sections_enrollment.append(
            {
                "crn": course.crn,
                "term": course.term.code,
                "section": course.section,
                # Latest values for quick access (ADR-0004)
                "enrolled": latest_enrolled,
                "capacity": latest_capacity,
                "timestamp": latest_timestamp,
                # Full history (sorted DESC: newest first)
                "snapshots": snapshots,
            }
        )

    data = {
        "course_code": courses[0].code if courses else "",
        "enrollment_history": sections_enrollment,
        "last_updated": datetime.datetime.now().isoformat(),
    }

    with open(output_file, "w") as f:
        json.dump(data, f, **_json_dump_kwargs())


def _export_terms(terms_dir: pathlib.Path) -> None:
    """Export term listings with all courses."""
    terms = src.models.Term.select()

    for term in terms:
        term_path = terms_dir / term.code
        term_path.mkdir(exist_ok=True)

        courses = src.models.Course.select().where(src.models.Course.term == term)

        course_list = []
        for course in courses:
            course_list.append(
                {
                    "crn": course.crn,
                    "code": course.code,
                    "section": course.section,
                    "title": course.title,
                    "schedule_type": course.schedule_type,
                    "enrolled": course.enrolled,
                    "max_enrollment": course.max_enrollment,
                    "seats_available": course.seats_available,
                }
            )

        data = {
            "term_code": term.code,
            "term_name": term.name,
            "start_date": term.start_date.isoformat() if term.start_date else None,
            "end_date": term.end_date.isoformat() if term.end_date else None,
            "courses": course_list,
            "course_count": len(course_list),
            "last_updated": datetime.datetime.now().isoformat(),
        }

        with open(term_path / "index.json", "w") as f:
            json.dump(data, f, indent=2)


def _export_search_indexes(search_dir: pathlib.Path) -> None:
    """Export search indexes for instructors and departments."""
    # Instructor index
    instructor_index: typing.Dict[str, typing.List[typing.Dict[str, str]]] = {}

    for instructor in src.models.Instructor.select():
        courses = []
        for ci in src.models.CourseInstructor.select().where(
            src.models.CourseInstructor.instructor == instructor
        ):
            courses.append(
                {
                    "crn": ci.course.crn,
                    "code": ci.course.code,
                    "title": ci.course.title,
                    "term": ci.course.term.code,
                }
            )

        if courses:  # Only include instructors who teach courses
            instructor_index[instructor.name] = courses

    with open(search_dir / "instructors.json", "w") as f:
        json.dump(
            {
                "instructors": instructor_index,
                "last_updated": datetime.datetime.now().isoformat(),
            },
            f,
            **_json_dump_kwargs(),
        )

    # Department index (extract from course codes)
    department_index: typing.Dict[str, typing.List[typing.Dict[str, str]]] = {}

    for course in src.models.Course.select():
        # Extract department code (e.g., "CIS" from "CIS 1210")
        dept_code = course.code.split()[0] if " " in course.code else course.code

        if dept_code not in department_index:
            department_index[dept_code] = []

        department_index[dept_code].append(
            {
                "crn": course.crn,
                "code": course.code,
                "title": course.title,
                "term": course.term.code,
            }
        )

    with open(search_dir / "departments.json", "w") as f:
        json.dump(
            {
                "departments": department_index,
                "last_updated": datetime.datetime.now().isoformat(),
            },
            f,
            **_json_dump_kwargs(),
        )


def _export_master_index(output_file: pathlib.Path) -> None:
    """Export master index listing all available data."""
    terms = src.models.Term.select()
    term_list = []

    for term in terms:
        course_count = (
            src.models.Course.select().where(src.models.Course.term == term).count()
        )

        term_list.append(
            {
                "code": term.code,
                "name": term.name,
                "start_date": term.start_date.isoformat() if term.start_date else None,
                "end_date": term.end_date.isoformat() if term.end_date else None,
                "course_count": course_count,
            }
        )

    # Get unique course codes
    all_courses = src.models.Course.select(src.models.Course.code).distinct()
    course_codes = sorted(set(c.code.replace(" ", "-") for c in all_courses))

    # Get instructors count
    instructor_count = src.models.Instructor.select().count()

    data = {
        "api_version": "1.0",
        "generated_at": datetime.datetime.now().isoformat(),
        "terms": term_list,
        "total_terms": len(term_list),
        "total_courses": len(course_codes),
        "total_instructors": instructor_count,
        "endpoints": {
            "courses": "/api/v1/courses/{course-code}/index.json",
            "enrollments": "/api/v1/courses/{course-code}/enrollments.json",
            "terms": "/api/v1/terms/{term-code}/index.json",
            "instructor_search": "/api/v1/search/instructors.json",
            "department_search": "/api/v1/search/departments.json",
        },
    }

    with open(output_file, "w") as f:
        json.dump(data, f, **_json_dump_kwargs())
