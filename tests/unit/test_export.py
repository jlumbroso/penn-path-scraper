"""
Unit tests for JSON export functionality.

Tests export of course data to JSON for static feeds.
"""

import datetime
import json
import pathlib
import typing

import pytest

import src.export
import src.models


@pytest.fixture
def _test_db():
    """Create in-memory test database."""
    import peewee

    db = peewee.SqliteDatabase(":memory:")
    db.bind(src.models.ALL_MODELS, bind_refs=False, bind_backrefs=False)
    db.connect()
    db.create_tables(src.models.ALL_MODELS)
    yield db
    db.drop_tables(src.models.ALL_MODELS)
    db.close()


@pytest.fixture
def sample_data(_test_db):
    """Create sample data for export tests."""
    # Create term
    term = src.models.Term.create(
        code="202530",
        name="Fall 2025",
        start_date=datetime.date(2025, 8, 26),
        end_date=datetime.date(2025, 12, 8),
    )

    # Create school
    school = src.models.School.create(code="E", name="School of Engineering")

    # Create instructor
    instructor = src.models.Instructor.create(name="Lumbroso, Jeremie")

    # Create course
    course = src.models.Course.create(
        crn="12345",
        term=term,
        code="CIS 1210",
        section="001",
        title="Data Structures and Algorithms",
        schedule_type="Lecture",
        status="Active",
        is_cancelled=False,
        enrolled=45,
        max_enrollment=50,
        seats_available=5,
        credits=1.0,
        start_date=datetime.date(2025, 8, 26),
        end_date=datetime.date(2025, 12, 8),
        description="Introduction to fundamental data structures",
    )

    # Link course to instructor
    src.models.CourseInstructor.create(course=course, instructor=instructor)

    # Create enrollment snapshots
    base_time = datetime.datetime(2025, 8, 1, 12, 0, 0)
    src.models.EnrollmentSnapshot.create(
        course=course,
        timestamp=base_time,
        enrolled=30,
        capacity=50,
    )
    src.models.EnrollmentSnapshot.create(
        course=course,
        timestamp=base_time + datetime.timedelta(days=1),
        enrolled=40,
        capacity=50,
    )
    src.models.EnrollmentSnapshot.create(
        course=course,
        timestamp=base_time + datetime.timedelta(days=2),
        enrolled=45,
        capacity=50,
    )

    # Create meeting
    src.models.Meeting.create(
        course=course,
        days="TR",
        start_time=datetime.time(10, 30),
        end_time=datetime.time(12, 0),
        room_code="TOWNE 303",
        start_date=datetime.date(2025, 8, 26),
        end_date=datetime.date(2025, 12, 8),
    )

    return {"term": term, "school": school, "instructor": instructor, "course": course}


class TestExportTermToDict:
    """Tests for exporting term data to dictionary."""

    def test_export_term_includes_metadata(self, sample_data):
        """Test exported term includes metadata."""
        result = src.export.export_term_to_dict("202530")

        assert result["term_code"] == "202530"
        assert result["term_name"] == "Fall 2025"
        assert result["start_date"] == "2025-08-26"
        assert result["end_date"] == "2025-12-08"
        assert "courses" in result
        assert "exported_at" in result

    def test_export_term_includes_courses(self, sample_data):
        """Test exported term includes course data."""
        result = src.export.export_term_to_dict("202530")

        assert len(result["courses"]) == 1
        course = result["courses"][0]

        assert course["crn"] == "12345"
        assert course["code"] == "CIS 1210"
        assert course["title"] == "Data Structures and Algorithms"
        assert course["section"] == "001"
        assert course["enrolled"] == 45
        assert course["max_enrollment"] == 50

    def test_export_term_includes_enrollment_history(self, sample_data):
        """Test exported term includes enrollment snapshots."""
        result = src.export.export_term_to_dict("202530")

        course = result["courses"][0]
        assert "enrollment_history" in course
        assert len(course["enrollment_history"]) == 3

        # Check first snapshot
        snapshot = course["enrollment_history"][0]
        assert "timestamp" in snapshot
        assert snapshot["enrolled"] == 30
        assert snapshot["capacity"] == 50

    def test_export_term_includes_instructors(self, sample_data):
        """Test exported term includes instructor data."""
        result = src.export.export_term_to_dict("202530")

        course = result["courses"][0]
        assert "instructors" in course
        assert len(course["instructors"]) == 1
        assert course["instructors"][0] == "Lumbroso, Jeremie"

    def test_export_term_includes_meetings(self, sample_data):
        """Test exported term includes meeting data."""
        result = src.export.export_term_to_dict("202530")

        course = result["courses"][0]
        assert "meetings" in course
        assert len(course["meetings"]) == 1

        meeting = course["meetings"][0]
        assert meeting["days"] == "TR"
        assert meeting["start_time"] == "10:30:00"
        assert meeting["end_time"] == "12:00:00"
        assert meeting["location"] == "TOWNE 303"

    def test_export_empty_term(self, _test_db):
        """Test exporting term with no courses."""
        term = src.models.Term.create(
            code="202610",
            name="Spring 2026",
        )

        result = src.export.export_term_to_dict("202610")

        assert result["term_code"] == "202610"
        assert result["courses"] == []

    def test_export_nonexistent_term(self, _test_db):
        """Test exporting term that doesn't exist raises error."""
        with pytest.raises(src.models.Term.DoesNotExist):
            src.export.export_term_to_dict("999999")


class TestExportTermToJSON:
    """Tests for exporting term to JSON file."""

    def test_export_to_json_file(self, sample_data, tmp_path):
        """Test exporting term to JSON file."""
        output_path = tmp_path / "202530.json"

        src.export.export_term_to_json("202530", str(output_path))

        # Verify file exists
        assert output_path.exists()

        # Verify valid JSON
        with open(output_path) as f:
            data = json.load(f)

        assert data["term_code"] == "202530"
        assert len(data["courses"]) == 1

    def test_export_creates_directory(self, sample_data, tmp_path):
        """Test export creates parent directory if needed."""
        output_path = tmp_path / "data" / "terms" / "202530.json"

        src.export.export_term_to_json("202530", str(output_path))

        assert output_path.exists()

    def test_export_overwrites_existing(self, sample_data, tmp_path):
        """Test export overwrites existing JSON file."""
        output_path = tmp_path / "202530.json"

        # Create initial export
        src.export.export_term_to_json("202530", str(output_path))
        initial_size = output_path.stat().st_size

        # Export again
        src.export.export_term_to_json("202530", str(output_path))

        # File should still exist with same or similar size
        assert output_path.exists()
        assert output_path.stat().st_size > 0


class TestExportAllTerms:
    """Tests for exporting all terms."""

    def test_export_all_terms(self, sample_data, tmp_path):
        """Test exporting all terms to directory."""
        # Create second term
        term2 = src.models.Term.create(code="202610", name="Spring 2026")

        src.export.export_all_terms(str(tmp_path))

        # Check both files exist
        assert (tmp_path / "202530.json").exists()
        assert (tmp_path / "202610.json").exists()

    def test_export_all_creates_index(self, sample_data, tmp_path):
        """Test export_all creates index file."""
        src.export.export_all_terms(str(tmp_path))

        index_path = tmp_path / "index.json"
        assert index_path.exists()

        with open(index_path) as f:
            index = json.load(f)

        assert "terms" in index
        assert len(index["terms"]) == 1
        assert index["terms"][0]["code"] == "202530"
        assert index["terms"][0]["name"] == "Fall 2025"
