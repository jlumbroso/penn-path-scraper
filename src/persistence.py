"""
Data persistence layer.

Transforms API responses to database models and handles CRUD operations.
"""

import datetime
import typing

import peewee

import src.models
import src.parsers
import src.types


def api_details_to_course_dict(
    api_data: src.types.APICourseDetails,
) -> src.types.CourseDict:
    """
    Transform API course details to normalized CourseDict.

    Args:
        api_data: Raw API response with HTML fields

    Returns:
        CourseDict ready for database persistence
    """
    # Parse HTML fields
    seats = src.parsers.parse_seats(api_data.get("seats", ""))
    meetings = src.parsers.parse_meeting_html(api_data.get("meeting_html", ""))
    instructors = src.parsers.parse_instructor_html(
        api_data.get("instructordetail_html", "")
    )

    # Parse linked CRNs
    linked_crns_str = api_data.get("linked_crns", "")
    linked_crns = []
    if linked_crns_str and linked_crns_str.strip():
        linked_crns = [crn.strip() for crn in linked_crns_str.split(",")]

    # Determine cancellation status
    is_cancelled = bool(api_data.get("isCancelled"))
    status = api_data.get("status_new", "Active")

    # Build CourseDict
    course_dict: src.types.CourseDict = {
        "code": api_data["code"],
        "crn": api_data["crn"],
        "term": api_data["srcdb"],
        "section": api_data.get("section", ""),
        "title": api_data.get("title", ""),
        "description": api_data.get("description", ""),
        "schedule_type": api_data.get("schedule_type", ""),
        "credits": api_data.get("hours_html", ""),
        "max_enrollment": seats["max_enrollment"],
        "seats_available": seats["seats_available"],
        "enrolled": seats["enrolled"],
        "meetings": meetings,
        "instructors": instructors,
        "linked_crns": linked_crns,
        "is_cancelled": is_cancelled,
        "status": status,
        "start_date": api_data.get("start_date", ""),
        "end_date": api_data.get("end_date", ""),
        "last_scraped": datetime.datetime.now().isoformat(),
    }

    return course_dict


def get_or_create_instructor(name: str) -> src.models.Instructor:
    """
    Get existing instructor or create new one.

    Args:
        name: Instructor name

    Returns:
        Instructor model instance
    """
    instructor, created = src.models.Instructor.get_or_create(name=name)
    return instructor


def save_course(course_dict: src.types.CourseDict) -> src.models.Course:
    """
    Save or update course in database.

    Creates or updates Course record along with related Instructor,
    Meeting, and LinkedSection records.

    Args:
        course_dict: Normalized course data

    Returns:
        Course model instance
    """
    # Get term
    term = src.models.Term.get(src.models.Term.code == course_dict["term"])

    # Create or update course
    course, created = src.models.Course.get_or_create(
        crn=course_dict["crn"],
        defaults={
            "term": term,
            "code": course_dict["code"],
            "section": course_dict["section"],
            "title": course_dict["title"],
            "description": course_dict["description"],
            "schedule_type": course_dict["schedule_type"],
            "credits": course_dict["credits"],
            "max_enrollment": course_dict["max_enrollment"],
            "seats_available": course_dict["seats_available"],
            "enrolled": course_dict["enrolled"],
            "start_date": course_dict["start_date"],
            "end_date": course_dict["end_date"],
            "is_cancelled": course_dict["is_cancelled"],
            "status": course_dict["status"],
            "last_scraped": course_dict["last_scraped"],
        },
    )

    # Update if already exists
    if not created:
        course.code = course_dict["code"]
        course.section = course_dict["section"]
        course.title = course_dict["title"]
        course.description = course_dict["description"]
        course.schedule_type = course_dict["schedule_type"]
        course.credits = course_dict["credits"]
        course.max_enrollment = course_dict["max_enrollment"]
        course.seats_available = course_dict["seats_available"]
        course.enrolled = course_dict["enrolled"]
        course.start_date = course_dict["start_date"]
        course.end_date = course_dict["end_date"]
        course.is_cancelled = course_dict["is_cancelled"]
        course.status = course_dict["status"]
        course.last_scraped = course_dict["last_scraped"]
        course.save()

    # Clear existing related records to avoid duplicates
    if not created:
        src.models.CourseInstructor.delete().where(
            src.models.CourseInstructor.course == course
        ).execute()
        src.models.Meeting.delete().where(
            src.models.Meeting.course == course
        ).execute()
        src.models.LinkedSection.delete().where(
            src.models.LinkedSection.course == course
        ).execute()

    # Add instructors
    for instructor_dict in course_dict["instructors"]:
        instructor = get_or_create_instructor(instructor_dict["name"])
        src.models.CourseInstructor.create(
            course=course,
            instructor=instructor,
        )

    # Add meetings
    for meeting_dict in course_dict["meetings"]:
        src.models.Meeting.create(
            course=course,
            days=meeting_dict.get("days", ""),
            start_time=meeting_dict.get("start_time", ""),
            end_time=meeting_dict.get("end_time", ""),
            room_code=meeting_dict.get("room_code", ""),
            room_url=meeting_dict.get("room_url", ""),
            start_date=meeting_dict.get("start_date", ""),
            end_date=meeting_dict.get("end_date", ""),
        )

    # Add linked sections
    for linked_crn in course_dict["linked_crns"]:
        src.models.LinkedSection.create(
            course=course,
            linked_crn=linked_crn,
        )

    return course


def create_enrollment_snapshot(
    course: src.models.Course,
    timestamp: datetime.datetime,
) -> src.models.EnrollmentSnapshot:
    """
    Create enrollment snapshot for time-series tracking.

    Args:
        course: Course to snapshot
        timestamp: Time of snapshot

    Returns:
        EnrollmentSnapshot model instance
    """
    snapshot = src.models.EnrollmentSnapshot.create(
        course=course,
        timestamp=timestamp,
        enrolled=course.enrolled,
        capacity=course.max_enrollment,
    )
    return snapshot


def initialize_database(db_path: str) -> None:
    """
    Initialize database with tables and seed data.

    Args:
        db_path: Path to SQLite database file
    """
    # Initialize database connection
    src.models.db.init(db_path)
    src.models.db.connect()

    # Create tables
    src.models.db.create_tables(src.models.ALL_MODELS)

    # Seed schools
    for school_config in src.types.SCHOOLS:
        src.models.School.get_or_create(
            code=school_config["code"],
            defaults={"name": school_config["name"]},
        )
