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
    # Note: The 'isCancelled' field was retired by Penn and is inconsistent.
    # Use 'status_new' as the authoritative source.
    status = api_data.get("status_new", "Active")
    is_cancelled = (status == "Canceled")

    # Build CourseDict
    course_dict: src.types.CourseDict = {
        "code": api_data["code"],
        "crn": api_data["crn"],
        "term": api_data["srcdb"],
        "section": api_data.get("section", ""),
        "title": api_data.get("title", ""),
        "description": api_data.get("description", ""),
        "schedule_type": api_data.get("schedule_type", ""),
        "inst_method_code": api_data.get("inst_method_code", ""),
        "campus_code": api_data.get("campus_code", ""),
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

    # Add optional fields if present
    if api_data.get("attributes_detail"):
        course_dict["attributes_detail"] = api_data["attributes_detail"]
    if api_data.get("clssnotes"):
        course_dict["clssnotes"] = api_data["clssnotes"]
    if api_data.get("exam_time"):
        course_dict["exam_time"] = api_data["exam_time"]
    if api_data.get("fees"):
        course_dict["fees"] = api_data["fees"]
    if api_data.get("xlist"):
        course_dict["xlist"] = api_data["xlist"]
    if api_data.get("canvas_url"):
        course_dict["canvas_url"] = api_data["canvas_url"]
    if api_data.get("canvas_registered_url"):
        course_dict["canvas_registered_url"] = api_data["canvas_registered_url"]
    if api_data.get("syllabus"):
        course_dict["syllabus"] = api_data["syllabus"]
    if api_data.get("homepage"):
        course_dict["homepage"] = api_data["homepage"]
    if api_data.get("registration_restrictions"):
        course_dict["restrictions"] = api_data["registration_restrictions"]
    if api_data.get("clssnotes"):
        course_dict["notes"] = api_data["clssnotes"]

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
            "inst_method_code": course_dict["inst_method_code"],
            "campus_code": course_dict["campus_code"],
            "credits": course_dict["credits"],
            "max_enrollment": course_dict["max_enrollment"],
            "seats_available": course_dict["seats_available"],
            "enrolled": course_dict["enrolled"],
            "start_date": course_dict["start_date"],
            "end_date": course_dict["end_date"],
            "is_cancelled": course_dict["is_cancelled"],
            "status": course_dict["status"],
            "last_scraped": course_dict["last_scraped"],
            # Optional fields
            "attributes_detail": course_dict.get("attributes_detail"),
            "clssnotes": course_dict.get("clssnotes"),
            "exam_time": course_dict.get("exam_time"),
            "fees": course_dict.get("fees"),
            "xlist": course_dict.get("xlist"),
            "canvas_url": course_dict.get("canvas_url"),
            "canvas_registered_url": course_dict.get("canvas_registered_url"),
            "syllabus": course_dict.get("syllabus"),
            "homepage": course_dict.get("homepage"),
            "notes": course_dict.get("notes"),
            "restrictions": course_dict.get("restrictions"),
        },
    )

    # Update if already exists
    if not created:
        course.code = course_dict["code"]
        course.section = course_dict["section"]
        course.title = course_dict["title"]
        course.description = course_dict["description"]
        course.schedule_type = course_dict["schedule_type"]
        course.inst_method_code = course_dict["inst_method_code"]
        course.campus_code = course_dict["campus_code"]
        course.credits = course_dict["credits"]
        course.max_enrollment = course_dict["max_enrollment"]
        course.seats_available = course_dict["seats_available"]
        course.enrolled = course_dict["enrolled"]
        course.start_date = course_dict["start_date"]
        course.end_date = course_dict["end_date"]
        course.is_cancelled = course_dict["is_cancelled"]
        course.status = course_dict["status"]
        course.last_scraped = course_dict["last_scraped"]
        # Optional fields
        course.attributes_detail = course_dict.get("attributes_detail")
        course.clssnotes = course_dict.get("clssnotes")
        course.exam_time = course_dict.get("exam_time")
        course.fees = course_dict.get("fees")
        course.xlist = course_dict.get("xlist")
        course.canvas_url = course_dict.get("canvas_url")
        course.canvas_registered_url = course_dict.get("canvas_registered_url")
        course.syllabus = course_dict.get("syllabus")
        course.homepage = course_dict.get("homepage")
        course.notes = course_dict.get("notes")
        course.restrictions = course_dict.get("restrictions")
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

    # Add instructors (deduplicate to avoid UNIQUE constraint violations)
    # Some API responses contain duplicate instructor entries
    seen_instructors = set()
    for instructor_dict in course_dict["instructors"]:
        instructor = get_or_create_instructor(instructor_dict["name"])

        # Skip if we've already linked this instructor to this course
        if instructor.id not in seen_instructors:
            src.models.CourseInstructor.create(
                course=course,
                instructor=instructor,
            )
            seen_instructors.add(instructor.id)

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
