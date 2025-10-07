"""
JSON export functionality for static feeds.

Exports course data to JSON for GitHub Pages hosting and frontend consumption.
"""

import datetime
import json
import pathlib
import typing

import src.models


class TermExportDict(typing.TypedDict):
    """Exported term data."""

    term_code: str
    term_name: str
    start_date: typing.Optional[str]
    end_date: typing.Optional[str]
    exported_at: str
    courses: typing.List["CourseExportDict"]


class CourseExportDict(typing.TypedDict):
    """Exported course data."""

    crn: str
    code: str
    section: str
    title: str
    schedule_type: str
    inst_method_code: typing.Optional[str]  # "In Class", "Online", etc.
    campus_code: typing.Optional[str]  # "Philadelphia", "Online", etc.
    status: str
    is_cancelled: bool
    enrolled: typing.Optional[int]  # Nullable for historical/cancelled courses
    max_enrollment: typing.Optional[int]  # Nullable for historical/cancelled courses
    seats_available: typing.Optional[int]  # Nullable for historical/cancelled courses
    credits: str
    start_date: typing.Optional[str]
    end_date: typing.Optional[str]
    description: str
    instructors: typing.List[str]
    meetings: typing.List["MeetingExportDict"]
    enrollment_history: typing.List["EnrollmentSnapshotExportDict"]


class MeetingExportDict(typing.TypedDict):
    """Exported meeting data."""

    days: str
    start_time: typing.Optional[str]
    end_time: typing.Optional[str]
    location: str


class EnrollmentSnapshotExportDict(typing.TypedDict):
    """Exported enrollment snapshot."""

    timestamp: str
    enrolled: int
    capacity: int


class TermIndexEntry(typing.TypedDict):
    """Term index entry."""

    code: str
    name: str
    start_date: typing.Optional[str]
    end_date: typing.Optional[str]
    course_count: int


class TermIndexDict(typing.TypedDict):
    """Index of all terms."""

    terms: typing.List[TermIndexEntry]
    generated_at: str


def export_term_to_dict(term_code: str) -> TermExportDict:
    """
    Export term data to dictionary.

    Args:
        term_code: Term code to export

    Returns:
        Dictionary with complete term data including courses and enrollment history

    Raises:
        Term.DoesNotExist: If term doesn't exist
    """
    # Get term
    term = src.models.Term.get(src.models.Term.code == term_code)

    # Get all courses for this term
    courses = src.models.Course.select().where(src.models.Course.term == term)

    # Export each course
    exported_courses: typing.List[CourseExportDict] = []
    for course in courses:
        # Get instructors
        instructors = [
            ci.instructor.name
            for ci in src.models.CourseInstructor.select().where(
                src.models.CourseInstructor.course == course
            )
        ]

        # Get meetings
        meetings: typing.List[MeetingExportDict] = []
        for meeting in src.models.Meeting.select().where(
            src.models.Meeting.course == course
        ):
            location = meeting.room_code if meeting.room_code else ""

            meetings.append(
                {
                    "days": meeting.days,
                    "start_time": meeting.start_time.isoformat()
                    if meeting.start_time
                    else None,
                    "end_time": meeting.end_time.isoformat()
                    if meeting.end_time
                    else None,
                    "location": location,
                }
            )

        # Get enrollment history
        enrollment_history: typing.List[EnrollmentSnapshotExportDict] = []
        for snapshot in (
            src.models.EnrollmentSnapshot.select()
            .where(src.models.EnrollmentSnapshot.course == course)
            .order_by(src.models.EnrollmentSnapshot.timestamp)
        ):
            enrollment_history.append(
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "enrolled": snapshot.enrolled,
                    "capacity": snapshot.capacity,
                }
            )

        # Build course dict
        course_dict: CourseExportDict = {
            "crn": course.crn,
            "code": course.code,
            "section": course.section,
            "title": course.title,
            "schedule_type": course.schedule_type,
            "inst_method_code": course.inst_method_code,
            "campus_code": course.campus_code,
            "status": course.status,
            "is_cancelled": course.is_cancelled,
            "enrolled": course.enrolled,
            "max_enrollment": course.max_enrollment,
            "seats_available": course.seats_available,
            "credits": course.credits,
            "start_date": course.start_date.isoformat() if course.start_date else None,
            "end_date": course.end_date.isoformat() if course.end_date else None,
            "description": course.description,
            "instructors": instructors,
            "meetings": meetings,
            "enrollment_history": enrollment_history,
        }
        exported_courses.append(course_dict)

    # Build term dict
    result: TermExportDict = {
        "term_code": term.code,
        "term_name": term.name,
        "start_date": term.start_date.isoformat() if term.start_date else None,
        "end_date": term.end_date.isoformat() if term.end_date else None,
        "exported_at": datetime.datetime.now().isoformat(),
        "courses": exported_courses,
    }

    return result


def export_term_to_json(term_code: str, output_path: str) -> None:
    """
    Export term data to JSON file.

    Args:
        term_code: Term code to export
        output_path: Path to output JSON file

    Creates parent directories if needed. Overwrites existing file.
    """
    # Export to dict
    data = export_term_to_dict(term_code)

    # Create parent directory
    path = pathlib.Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def export_all_terms(output_dir: str) -> None:
    """
    Export all terms to JSON files.

    Args:
        output_dir: Directory to write JSON files

    Creates one file per term: {term_code}.json
    Also creates index.json with list of all terms.
    """
    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Export each term
    terms = src.models.Term.select()
    index_entries: typing.List[TermIndexEntry] = []

    for term in terms:
        # Export term to file
        term_file = output_path / f"{term.code}.json"
        export_term_to_json(term.code, str(term_file))

        # Count courses
        course_count = (
            src.models.Course.select()
            .where(src.models.Course.term == term)
            .count()
        )

        # Add to index
        index_entries.append(
            {
                "code": term.code,
                "name": term.name,
                "start_date": term.start_date.isoformat() if term.start_date else None,
                "end_date": term.end_date.isoformat() if term.end_date else None,
                "course_count": course_count,
            }
        )

    # Write index
    index: TermIndexDict = {
        "terms": index_entries,
        "generated_at": datetime.datetime.now().isoformat(),
    }

    index_path = output_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
