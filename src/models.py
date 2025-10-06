"""
Peewee ORM models for Penn course catalog database.

Database schema for storing scraped course data and enrollment history.
Uses SQLite as the backend database.
"""

import datetime
import json
import typing

import peewee


# Database instance (will be initialized by persistence layer)
db = peewee.SqliteDatabase(None)


class BaseModel(peewee.Model):
    """Base model with common functionality."""

    class Meta:
        database = db


# =============================================================================
# Core Models
# =============================================================================

class Term(BaseModel):
    """Academic term/semester."""

    code = peewee.CharField(primary_key=True)  # e.g., "202530"
    name = peewee.CharField()  # e.g., "Fall 2025"
    start_date = peewee.DateField(null=True)
    end_date = peewee.DateField(null=True)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "terms"


class School(BaseModel):
    """School/College within Penn."""

    code = peewee.CharField(primary_key=True)  # e.g., "E"
    name = peewee.CharField()  # e.g., "School of Engineering and Applied Science"
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "schools"


class Course(BaseModel):
    """
    Course offering (a specific section in a specific term).

    Note: This represents a section, not a course catalog entry.
    The same course code (e.g., "CIS 1210") will have multiple
    Course records across different terms and sections.
    """

    # Primary identifiers
    crn = peewee.CharField(primary_key=True)  # Course Reference Number (unique per term)
    term = peewee.ForeignKeyField(Term, backref="courses", on_delete="CASCADE")

    # Course identification
    code = peewee.CharField(index=True)  # e.g., "CIS 1210"
    section = peewee.CharField()  # e.g., "001", "201"
    title = peewee.CharField()

    # Content
    description = peewee.TextField(null=True)
    notes = peewee.TextField(null=True)
    restrictions = peewee.TextField(null=True)

    # Schedule information
    schedule_type = peewee.CharField()  # "Lecture", "Recitation", "Lab", etc.
    inst_method_code = peewee.CharField(null=True)  # "In Class", "Online", etc.
    campus_code = peewee.CharField(null=True)  # "Philadelphia", "Online", etc.
    credits = peewee.CharField()

    # Enrollment (current snapshot)
    # Note: These are nullable because cancelled/full/historical courses
    # may not have seats data available in the API response
    max_enrollment = peewee.IntegerField(null=True)
    seats_available = peewee.IntegerField(null=True)
    enrolled = peewee.IntegerField(null=True)

    # Dates
    start_date = peewee.DateField()
    end_date = peewee.DateField()

    # Status
    is_cancelled = peewee.BooleanField(default=False)
    status = peewee.CharField()  # "Active", "Closed", etc.

    # Metadata and course resources
    attributes = peewee.TextField(null=True)  # JSON array of course attributes
    attributes_detail = peewee.TextField(null=True)  # HTML: Degree requirements, fulfillments
    clssnotes = peewee.TextField(null=True)  # HTML: Important student notices
    exam_time = peewee.CharField(null=True)  # Final exam schedule
    fees = peewee.CharField(null=True)  # Course fees
    xlist = peewee.CharField(null=True)  # Cross-listing information

    # Web resources
    canvas_url = peewee.CharField(null=True)
    canvas_registered_url = peewee.CharField(null=True)
    syllabus = peewee.CharField(null=True)  # URL or HTML link to syllabus
    homepage = peewee.CharField(null=True)  # Course website

    last_scraped = peewee.DateTimeField(default=datetime.datetime.now)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "courses"
        indexes = (
            # Composite index for efficient lookups
            (("term", "code"), False),
        )

    def save(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """Override save to update updated_at timestamp."""
        self.updated_at = datetime.datetime.now()
        return super().save(*args, **kwargs)


class Instructor(BaseModel):
    """Instructor/professor."""

    # Use auto-incrementing ID as primary key
    id = peewee.AutoField()

    name = peewee.CharField(index=True)
    pennkey = peewee.CharField(null=True, index=True)
    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "instructors"
        indexes = (
            # Unique constraint on name (since we may not have pennkey)
            (("name",), True),
        )


class CourseInstructor(BaseModel):
    """Many-to-many relationship between courses and instructors."""

    course = peewee.ForeignKeyField(Course, backref="course_instructors", on_delete="CASCADE")
    instructor = peewee.ForeignKeyField(Instructor, backref="instructor_courses", on_delete="CASCADE")

    class Meta:
        table_name = "course_instructors"
        indexes = (
            # Ensure each course-instructor pair is unique
            (("course", "instructor"), True),
        )


class Meeting(BaseModel):
    """Course meeting time and location."""

    id = peewee.AutoField()
    course = peewee.ForeignKeyField(Course, backref="meetings", on_delete="CASCADE")

    # Meeting time
    days = peewee.CharField()  # e.g., "TR", "MWF"
    start_time = peewee.TimeField()  # e.g., "17:15:00"
    end_time = peewee.TimeField()  # e.g., "18:44:00"

    # Location
    room_code = peewee.CharField(null=True)  # e.g., "TOWN 217"
    room_url = peewee.CharField(null=True)  # Facilities map URL

    # Date range (for courses that don't meet the full term)
    start_date = peewee.DateField()
    end_date = peewee.DateField()

    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "meetings"
        indexes = (
            (("course",), False),
        )


class LinkedSection(BaseModel):
    """
    Linked sections (e.g., lecture <-> recitation).

    This represents relationships between sections that must be
    taken together or are otherwise related.
    """

    id = peewee.AutoField()
    course = peewee.ForeignKeyField(Course, backref="linked_from", on_delete="CASCADE")
    linked_crn = peewee.CharField()  # CRN of the linked section

    class Meta:
        table_name = "linked_sections"
        indexes = (
            (("course", "linked_crn"), True),  # Unique constraint
        )


class EnrollmentSnapshot(BaseModel):
    """
    Point-in-time enrollment observation.

    Stores enrollment data at each scrape to build time-series.
    """

    id = peewee.AutoField()
    course = peewee.ForeignKeyField(Course, backref="enrollment_history", on_delete="CASCADE")

    # Timestamp of this observation
    timestamp = peewee.DateTimeField(index=True)

    # Enrollment data at this time
    enrolled = peewee.IntegerField()
    capacity = peewee.IntegerField()
    waitlist = peewee.IntegerField(null=True)  # Not always available

    created_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "enrollment_snapshots"
        indexes = (
            (("course", "timestamp"), False),
        )


class ScrapeLog(BaseModel):
    """
    Log of scraping runs.

    Tracks when scrapes occurred and their status for debugging
    and monitoring.
    """

    id = peewee.AutoField()
    started_at = peewee.DateTimeField(default=datetime.datetime.now)
    completed_at = peewee.DateTimeField(null=True)

    # What was scraped
    term = peewee.ForeignKeyField(Term, backref="scrape_logs", null=True, on_delete="SET NULL")
    school = peewee.ForeignKeyField(School, backref="scrape_logs", null=True, on_delete="SET NULL")

    # Results
    status = peewee.CharField()  # "running", "completed", "failed"
    courses_scraped = peewee.IntegerField(default=0)
    errors_count = peewee.IntegerField(default=0)
    error_details = peewee.TextField(null=True)  # JSON array of error messages

    class Meta:
        table_name = "scrape_logs"


# =============================================================================
# Helper Functions
# =============================================================================

# List all models for easy iteration
ALL_MODELS = [
    Term,
    School,
    Course,
    Instructor,
    CourseInstructor,
    Meeting,
    LinkedSection,
    EnrollmentSnapshot,
    ScrapeLog,
]


def create_tables() -> None:
    """Create all database tables."""
    db.create_tables(ALL_MODELS)


def drop_tables() -> None:
    """Drop all database tables (for testing)."""
    db.drop_tables(ALL_MODELS)


def initialize_database(db_path: str) -> None:
    """
    Initialize the database connection and create tables if needed.

    Args:
        db_path: Path to SQLite database file
    """
    db.init(db_path)
    db.connect()
    create_tables()


def close_database() -> None:
    """Close the database connection."""
    if not db.is_closed():
        db.close()


# =============================================================================
# Utility Functions for Data Conversion
# =============================================================================

def course_to_dict(course: Course) -> typing.Dict[str, typing.Any]:
    """
    Convert a Course model instance to a dictionary.

    This is useful for generating JSON exports.
    """
    return {
        "crn": course.crn,
        "term": course.term.code,
        "code": course.code,
        "section": course.section,
        "title": course.title,
        "description": course.description,
        "notes": course.notes,
        "restrictions": course.restrictions,
        "schedule_type": course.schedule_type,
        "inst_method_code": course.inst_method_code,
        "campus_code": course.campus_code,
        "credits": course.credits,
        "max_enrollment": course.max_enrollment,
        "seats_available": course.seats_available,
        "enrolled": course.enrolled,
        "start_date": course.start_date.isoformat(),
        "end_date": course.end_date.isoformat(),
        "is_cancelled": course.is_cancelled,
        "status": course.status,
        "attributes": json.loads(course.attributes) if course.attributes else [],
        "attributes_detail": course.attributes_detail,
        "clssnotes": course.clssnotes,
        "exam_time": course.exam_time,
        "fees": course.fees,
        "xlist": course.xlist,
        "canvas_url": course.canvas_url,
        "canvas_registered_url": course.canvas_registered_url,
        "syllabus": course.syllabus,
        "homepage": course.homepage,
        "instructors": [
            {"name": ci.instructor.name, "pennkey": ci.instructor.pennkey}
            for ci in course.course_instructors
        ],
        "meetings": [
            {
                "days": m.days,
                "start_time": m.start_time.isoformat(),
                "end_time": m.end_time.isoformat(),
                "room_code": m.room_code,
                "room_url": m.room_url,
                "start_date": m.start_date.isoformat(),
                "end_date": m.end_date.isoformat(),
            }
            for m in course.meetings
        ],
        "linked_sections": [ls.linked_crn for ls in course.linked_from],
        "last_scraped": course.last_scraped.isoformat(),
    }


def get_enrollment_history(course: Course) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Get enrollment history for a course as a list of snapshots.

    Returns:
        List of enrollment snapshots, sorted by timestamp
    """
    snapshots = (
        EnrollmentSnapshot.select()
        .where(EnrollmentSnapshot.course == course)
        .order_by(EnrollmentSnapshot.timestamp)
    )

    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "enrolled": s.enrolled,
            "capacity": s.capacity,
            "waitlist": s.waitlist,
        }
        for s in snapshots
    ]
