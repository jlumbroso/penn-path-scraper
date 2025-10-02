"""
Unit tests for data persistence layer.

Tests transformation of API data to database models and persistence operations.
Uses in-memory SQLite database for testing.
"""

import datetime
import pathlib
import json
import typing

import pytest
import peewee

import src.api_client
import src.models
import src.parsers
import src.persistence
import src.types


# Use in-memory database for tests
test_db = peewee.SqliteDatabase(":memory:")


@pytest.fixture(scope="function")
def db():
    """Create fresh in-memory database for each test."""
    # Bind all models to test database
    test_db.bind(src.models.ALL_MODELS, bind_refs=False, bind_backrefs=False)

    # Connect and create tables
    test_db.connect()
    test_db.create_tables(src.models.ALL_MODELS)

    yield test_db

    # Clean up
    test_db.drop_tables(src.models.ALL_MODELS)
    test_db.close()


@pytest.fixture
def sample_api_details() -> src.types.APICourseDetails:
    """Load sample API details response."""
    fixtures_dir = pathlib.Path(__file__).parent.parent / "fixtures"
    with open(fixtures_dir / "api_details_response.json") as f:
        return json.load(f)


@pytest.fixture
def sample_api_search_result() -> src.types.APICourseSearchResult:
    """Load sample API search result."""
    fixtures_dir = pathlib.Path(__file__).parent.parent / "fixtures"
    with open(fixtures_dir / "api_search_response.json") as f:
        data = json.load(f)
        return data["results"][0]


class TestAPIToCourseDict:
    """Tests for transforming API responses to CourseDict."""

    def test_transform_simple_course(self, sample_api_details):
        """Test transforming basic course with all fields."""
        result = src.persistence.api_details_to_course_dict(sample_api_details)

        # Basic fields
        assert result["code"] == "NETS 2130"
        assert result["crn"] == "80595"
        assert result["term"] == "202530"
        assert result["section"] == "001"
        assert result["title"] == "Crowdsourcing and Human Computation"
        assert result["schedule_type"] == "Lecture"

        # Enrollment (parsed from HTML)
        assert result["max_enrollment"] == 50
        assert result["seats_available"] == 2
        assert result["enrolled"] == 48

        # Instructors (parsed from HTML)
        assert len(result["instructors"]) == 1
        assert result["instructors"][0]["name"] == "Jeremie Lumbroso"

        # Meetings (parsed from HTML)
        assert len(result["meetings"]) == 1
        meeting = result["meetings"][0]
        assert meeting["days"] == "TR"
        assert meeting["room_code"] == "WLNT 401B"

        # Status
        assert result["status"] == "Active"
        assert result["is_cancelled"] is False

        # Linked sections
        assert result["linked_crns"] == []

    def test_transform_with_linked_sections(self):
        """Test transforming course with linked recitation."""
        # Course with recitation
        api_data: src.types.APICourseDetails = {
            "code": "CIT 5920",
            "crn": "61969",
            "section": "001",
            "title": "Mathematical Foundations",
            "srcdb": "202530",
            "schedule_type": "Lecture",
            "status_new": "Active",
            "isCancelled": "",
            "seats": '<strong>Maximum Enrollment:</strong> <span class="seats_max">80</span> / <strong>Seats Avail:</strong> <span class="seats_avail">17</span>',
            "meeting_html": '<div class="meet">TR 5:15pm-6:44pm<span class="meet-dates"> (8/26 to 12/8)</span></div>',
            "instructordetail_html": '<div class="instructor-detail">J. Lumbroso</div>',
            "linked_crns": "61970",
            "hours_html": "1",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "description": "Math foundations course",
        }

        result = src.persistence.api_details_to_course_dict(api_data)

        assert result["linked_crns"] == ["61970"]

    def test_transform_cancelled_course(self):
        """Test transforming cancelled course."""
        api_data: src.types.APICourseDetails = {
            "code": "TEST 1000",
            "crn": "99999",
            "section": "001",
            "title": "Cancelled Course",
            "srcdb": "202530",
            "schedule_type": "Lecture",
            "status_new": "Cancelled",
            "isCancelled": "1",
            "seats": '<strong>Maximum Enrollment:</strong> <span class="seats_max">30</span> / <strong>Seats Avail:</strong> <span class="seats_avail">30</span>',
            "meeting_html": "",
            "instructordetail_html": "",
            "linked_crns": "",
            "hours_html": "1",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "description": "",
        }

        result = src.persistence.api_details_to_course_dict(api_data)

        assert result["is_cancelled"] is True
        assert result["status"] == "Cancelled"


class TestSaveCourse:
    """Tests for saving courses to database."""

    def test_save_new_course(self, db):
        """Test saving a new course creates all related objects."""
        course_dict: src.types.CourseDict = {
            "code": "CIS 1210",
            "crn": "12345",
            "term": "202530",
            "section": "001",
            "title": "Data Structures and Algorithms",
            "description": "Learn data structures",
            "schedule_type": "Lecture",
            "credits": "1",
            "max_enrollment": 100,
            "seats_available": 10,
            "enrolled": 90,
            "meetings": [
                {
                    "days": "MW",
                    "start_time": "10:15",
                    "end_time": "11:45",
                    "room_code": "TOWN 100",
                    "room_url": "https://example.com",
                    "start_date": "2025-08-26",
                    "end_date": "2025-12-08",
                }
            ],
            "instructors": [
                {"name": "John Doe"},
                {"name": "Jane Smith"},
            ],
            "linked_crns": [],
            "is_cancelled": False,
            "status": "Active",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "last_scraped": "2025-10-01T12:00:00",
        }

        # Ensure term exists
        src.models.Term.create(code="202530", name="Fall 2025")

        # Save course
        course = src.persistence.save_course(course_dict)

        # Verify course saved
        assert course.crn == "12345"
        assert course.code == "CIS 1210"
        assert course.enrolled == 90

        # Verify instructors created
        assert course.course_instructors.count() == 2
        instructor_names = {ci.instructor.name for ci in course.course_instructors}
        assert "John Doe" in instructor_names
        assert "Jane Smith" in instructor_names

        # Verify meeting created
        assert course.meetings.count() == 1
        meeting = course.meetings.get()
        assert meeting.days == "MW"
        assert meeting.room_code == "TOWN 100"

    def test_save_existing_course_updates(self, db):
        """Test saving existing course updates enrollment."""
        # Create term
        term = src.models.Term.create(code="202530", name="Fall 2025")

        # Create initial course
        course = src.models.Course.create(
            crn="12345",
            term=term,
            code="CIS 1210",
            section="001",
            title="Data Structures",
            description="",
            schedule_type="Lecture",
            credits="1",
            max_enrollment=100,
            seats_available=20,
            enrolled=80,
            start_date="2025-08-26",
            end_date="2025-12-08",
            is_cancelled=False,
            status="Active",
        )

        # Update with new enrollment
        course_dict: src.types.CourseDict = {
            "code": "CIS 1210",
            "crn": "12345",
            "term": "202530",
            "section": "001",
            "title": "Data Structures",
            "description": "",
            "schedule_type": "Lecture",
            "credits": "1",
            "max_enrollment": 100,
            "seats_available": 10,
            "enrolled": 90,  # Changed
            "meetings": [],
            "instructors": [],
            "linked_crns": [],
            "is_cancelled": False,
            "status": "Active",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "last_scraped": "2025-10-01T12:00:00",
        }

        updated_course = src.persistence.save_course(course_dict)

        # Verify updated
        assert updated_course.enrolled == 90
        assert updated_course.seats_available == 10

        # Verify only one course exists
        assert src.models.Course.select().count() == 1

    def test_save_course_with_linked_sections(self, db):
        """Test saving course with linked sections."""
        term = src.models.Term.create(code="202530", name="Fall 2025")

        course_dict: src.types.CourseDict = {
            "code": "CIT 5920",
            "crn": "61969",
            "term": "202530",
            "section": "001",
            "title": "Math Foundations",
            "description": "",
            "schedule_type": "Lecture",
            "credits": "1",
            "max_enrollment": 80,
            "seats_available": 17,
            "enrolled": 63,
            "meetings": [],
            "instructors": [],
            "linked_crns": ["61970", "61971"],
            "is_cancelled": False,
            "status": "Active",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "last_scraped": "2025-10-01T12:00:00",
        }

        course = src.persistence.save_course(course_dict)

        # Verify linked sections saved
        assert course.linked_from.count() == 2
        linked_crns = {ls.linked_crn for ls in course.linked_from}
        assert "61970" in linked_crns
        assert "61971" in linked_crns


class TestEnrollmentSnapshot:
    """Tests for enrollment snapshot creation."""

    def test_create_enrollment_snapshot(self, db):
        """Test creating enrollment snapshot."""
        term = src.models.Term.create(code="202530", name="Fall 2025")
        course = src.models.Course.create(
            crn="12345",
            term=term,
            code="CIS 1210",
            section="001",
            title="Data Structures",
            description="",
            schedule_type="Lecture",
            credits="1",
            max_enrollment=100,
            seats_available=10,
            enrolled=90,
            start_date="2025-08-26",
            end_date="2025-12-08",
            is_cancelled=False,
            status="Active",
        )

        # Create snapshot
        timestamp = datetime.datetime(2025, 10, 1, 12, 0, 0)
        snapshot = src.persistence.create_enrollment_snapshot(
            course=course,
            timestamp=timestamp,
        )

        assert snapshot.enrolled == 90
        assert snapshot.capacity == 100
        assert snapshot.timestamp == timestamp

        # Verify snapshot is associated with course
        assert snapshot.course == course

    def test_multiple_snapshots(self, db):
        """Test creating multiple snapshots tracks enrollment over time."""
        term = src.models.Term.create(code="202530", name="Fall 2025")
        course = src.models.Course.create(
            crn="12345",
            term=term,
            code="CIS 1210",
            section="001",
            title="Data Structures",
            description="",
            schedule_type="Lecture",
            credits="1",
            max_enrollment=100,
            seats_available=20,
            enrolled=80,
            start_date="2025-08-26",
            end_date="2025-12-08",
            is_cancelled=False,
            status="Active",
        )

        # Create first snapshot
        snapshot1 = src.persistence.create_enrollment_snapshot(
            course=course,
            timestamp=datetime.datetime(2025, 10, 1, 12, 0, 0),
        )

        # Update course enrollment
        course.enrolled = 85
        course.seats_available = 15
        course.save()

        # Create second snapshot
        snapshot2 = src.persistence.create_enrollment_snapshot(
            course=course,
            timestamp=datetime.datetime(2025, 10, 2, 12, 0, 0),
        )

        # Verify both snapshots exist
        snapshots = list(course.enrollment_history.order_by(src.models.EnrollmentSnapshot.timestamp))
        assert len(snapshots) == 2
        assert snapshots[0].enrolled == 80
        assert snapshots[1].enrolled == 85


class TestGetOrCreateInstructor:
    """Tests for instructor creation/retrieval."""

    def test_create_new_instructor(self, db):
        """Test creating a new instructor."""
        instructor = src.persistence.get_or_create_instructor("John Doe")

        assert instructor.name == "John Doe"
        assert src.models.Instructor.select().count() == 1

    def test_get_existing_instructor(self, db):
        """Test getting existing instructor doesn't create duplicate."""
        # Create instructor
        instructor1 = src.persistence.get_or_create_instructor("John Doe")

        # Get same instructor
        instructor2 = src.persistence.get_or_create_instructor("John Doe")

        # Should be same instance
        assert instructor1.id == instructor2.id
        assert src.models.Instructor.select().count() == 1


# Note: initialize_database() is tested in integration tests
# Unit testing it here causes peewee global state conflicts with fixture-based tests
