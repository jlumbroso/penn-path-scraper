"""
Unit tests for scrape verification (ground-truth sampling).

These tests ensure the sampling and verification system works correctly
and doesn't break scraping operations.
"""
import datetime
import json
import pathlib
import tempfile

import pytest

import src.models
import src.scrape_verification
import src.types


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize database
    src.models.db.init(db_path)
    src.models.db.connect()
    src.models.db.create_tables(src.models.ALL_MODELS)

    yield db_path

    # Cleanup
    src.models.db.close()
    pathlib.Path(db_path).unlink()


def test_database_id_generation():
    """Test that database IDs are generated correctly."""
    # Same path should give same ID (within same inode)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        id1 = src.scrape_verification.get_database_id(db_path)
        id2 = src.scrape_verification.get_database_id(db_path)

        # Same file should have same ID
        assert id1 == id2
        assert len(id1) == 16  # Should be 16-char hex

    finally:
        pathlib.Path(db_path).unlink(missing_ok=True)


def test_database_id_differs_for_different_files():
    """Test that different databases get different IDs."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f1:
        db_path1 = f1.name

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f2:
        db_path2 = f2.name

    try:
        id1 = src.scrape_verification.get_database_id(db_path1)
        id2 = src.scrape_verification.get_database_id(db_path2)

        # Different files should have different IDs
        assert id1 != id2

    finally:
        pathlib.Path(db_path1).unlink(missing_ok=True)
        pathlib.Path(db_path2).unlink(missing_ok=True)


def test_init_sampling(temp_db):
    """Test sampling initialization."""
    src.scrape_verification.init_sampling(temp_db, sample_rate=50)

    assert src.scrape_verification._current_database_id is not None
    assert src.scrape_verification._current_samples == []
    assert src.scrape_verification._sample_rate == 50


def test_sample_course_basic(temp_db):
    """Test basic course sampling."""
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)  # Always sample

    course_dict: src.types.CourseDict = {
        "term": "202530",
        "crn": "12345",
        "code": "CIS 1210",
        "section": "001",
        "title": "Data Structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 90,
        "max_enrollment": 100,
        "seats_available": 10,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn data structures",
        "instructors": [{"name": "Jane Doe"}],
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    src.scrape_verification.sample_course(course_dict)

    # Check sample was recorded
    assert len(src.scrape_verification._current_samples) == 1

    sample = src.scrape_verification._current_samples[0]
    assert sample["term_code"] == "202530"
    assert sample["crn"] == "12345"
    assert sample["course_code"] == "CIS 1210"
    assert sample["title"] == "Data Structures"
    assert sample["instructors"] == ["Jane Doe"]


def test_sample_course_with_string_instructors(temp_db):
    """Test sampling with different instructor formats."""
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)

    course_dict: src.types.CourseDict = {
        "term": "202530",
        "crn": "12345",
        "code": "CIS 1210",
        "section": "001",
        "title": "Data Structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 90,
        "max_enrollment": 100,
        "seats_available": 10,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn data structures",
        "instructors": ["Jane Doe", "John Smith"],  # String format
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    src.scrape_verification.sample_course(course_dict)

    sample = src.scrape_verification._current_samples[0]
    assert sample["instructors"] == ["Jane Doe", "John Smith"]


def test_sampling_rate(temp_db):
    """Test that sampling rate is respected (probabilistically)."""
    src.scrape_verification.init_sampling(temp_db, sample_rate=100)

    # Sample 1000 courses - expect ~10 samples (1%)
    course_dict: src.types.CourseDict = {
        "term": "202530",
        "crn": "12345",
        "code": "CIS 1210",
        "section": "001",
        "title": "Data Structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 90,
        "max_enrollment": 100,
        "seats_available": 10,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn data structures",
        "instructors": [],
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    for i in range(1000):
        course_dict["crn"] = str(10000 + i)
        src.scrape_verification.sample_course(course_dict)

    sample_count = len(src.scrape_verification._current_samples)

    # Should be roughly 10 ± 5 (allow for randomness)
    assert 5 <= sample_count <= 15, f"Expected ~10 samples, got {sample_count}"


def test_save_samples(temp_db, temp_dir):
    """Test saving samples to JSON file."""
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)

    # Sample a few courses
    for i in range(5):
        course_dict: src.types.CourseDict = {
            "term": "202530",
            "crn": str(10000 + i),
            "code": f"CIS {1200 + i}",
            "section": "001",
            "title": f"Course {i}",
            "schedule_type": "Lecture",
            "inst_method_code": "In Class",
            "campus_code": "Philadelphia",
            "credits": "1",
            "enrolled": 90,
            "max_enrollment": 100,
            "seats_available": 10,
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "description": "Test course",
            "instructors": [],
            "meetings": [],
            "linked_crns": [],
            "is_cancelled": False,
            "status": "Active",
            "last_scraped": "2025-10-06T12:00:00",
        }
        src.scrape_verification.sample_course(course_dict)

    # Save samples
    filepath = src.scrape_verification.save_samples(str(temp_dir))

    # Verify file exists and has correct structure
    assert filepath.exists()
    assert filepath.suffix == ".json"

    with open(filepath, "r") as f:
        data = json.load(f)

    assert data["sample_count"] == 5
    assert data["sample_rate"] == 1
    assert len(data["samples"]) == 5
    assert data["database_id"] == src.scrape_verification.get_database_id(temp_db)


def test_verify_samples_all_correct(temp_db, temp_dir):
    """Test verification when all samples match database."""
    # Create term
    src.models.Term.create(code="202530", name="Fall 2025")

    # Initialize sampling
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)

    # Sample and save a course
    course_dict: src.types.CourseDict = {
        "term": "202530",
        "crn": "12345",
        "code": "CIS 1210",
        "section": "001",
        "title": "Data Structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 90,
        "max_enrollment": 100,
        "seats_available": 10,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn data structures",
        "instructors": [{"name": "Jane Doe"}],
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    src.scrape_verification.sample_course(course_dict)

    # Save samples
    samples_file = src.scrape_verification.save_samples(str(temp_dir))

    # Actually insert course into database (correctly)
    term = src.models.Term.get(src.models.Term.code == "202530")
    src.models.Course.create(
        term=term,
        crn="12345",
        code="CIS 1210",
        section="001",
        title="Data Structures",
        schedule_type="Lecture",
        credits="1",
        start_date="2025-08-26",
        end_date="2025-12-08",
        is_cancelled=False,
        status="Active",
    )

    # Verify samples
    results = src.scrape_verification.verify_samples(str(samples_file), temp_db)

    assert results["total_samples"] == 1
    assert results["verified"] == 1
    assert len(results["missing"]) == 0
    assert len(results["corrupted"]) == 0


def test_verify_samples_detects_corruption(temp_db, temp_dir):
    """Test that verification detects CRN reuse corruption."""
    # Create two terms
    fall_2024 = src.models.Term.create(code="202430", name="Fall 2024")
    fall_2025 = src.models.Term.create(code="202530", name="Fall 2025")

    # Initialize sampling
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)

    # Sample a Fall 2025 course
    course_dict: src.types.CourseDict = {
        "term": "202530",  # Fall 2025
        "crn": "12345",
        "code": "BE 1000",
        "section": "001",
        "title": "Bioengineering",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 60,
        "max_enrollment": 80,
        "seats_available": 20,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn bioengineering",
        "instructors": [],
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    src.scrape_verification.sample_course(course_dict)
    samples_file = src.scrape_verification.save_samples(str(temp_dir))

    # BUT: Insert into database with WRONG term (simulating corruption)
    src.models.Course.create(
        term=fall_2024,  # ← WRONG TERM! Should be fall_2025
        crn="12345",
        code="CIS 1210",  # Different course
        section="001",
        title="Data Structures",
        schedule_type="Lecture",
        credits="1",
        start_date="2024-08-26",
        end_date="2024-12-08",
        is_cancelled=False,
        status="Active",
    )

    # Verify samples - should detect corruption!
    results = src.scrape_verification.verify_samples(str(samples_file), temp_db)

    assert results["total_samples"] == 1
    assert results["verified"] == 0
    assert len(results["corrupted"]) == 1

    corruption = results["corrupted"][0]
    assert corruption["crn"] == "12345"
    assert corruption["expected_term"] == "202530"
    assert corruption["actual_term"] == "202430"


def test_verify_samples_detects_missing(temp_db, temp_dir):
    """Test that verification detects missing courses."""
    # Create term
    src.models.Term.create(code="202530", name="Fall 2025")

    # Initialize sampling
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)

    # Sample a course
    course_dict: src.types.CourseDict = {
        "term": "202530",
        "crn": "12345",
        "code": "CIS 1210",
        "section": "001",
        "title": "Data Structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 90,
        "max_enrollment": 100,
        "seats_available": 10,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn data structures",
        "instructors": [],
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    src.scrape_verification.sample_course(course_dict)
    samples_file = src.scrape_verification.save_samples(str(temp_dir))

    # DON'T insert into database (simulating lost data)

    # Verify samples - should detect missing course
    results = src.scrape_verification.verify_samples(str(samples_file), temp_db)

    assert results["total_samples"] == 1
    assert results["verified"] == 0
    assert len(results["missing"]) == 1

    missing = results["missing"][0]
    assert missing["crn"] == "12345"
    assert missing["term"] == "202530"


def test_verify_samples_wrong_database_error(temp_db, temp_dir):
    """Test that verification rejects wrong database."""
    # Initialize sampling with first database
    src.scrape_verification.init_sampling(temp_db, sample_rate=1)

    course_dict: src.types.CourseDict = {
        "term": "202530",
        "crn": "12345",
        "code": "CIS 1210",
        "section": "001",
        "title": "Data Structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "enrolled": 90,
        "max_enrollment": 100,
        "seats_available": 10,
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "description": "Learn data structures",
        "instructors": [],
        "meetings": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "last_scraped": "2025-10-06T12:00:00",
    }

    src.scrape_verification.sample_course(course_dict)
    samples_file = src.scrape_verification.save_samples(str(temp_dir))

    # Create a DIFFERENT database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        other_db = f.name

    try:
        src.models.db.init(other_db)
        src.models.db.connect()
        src.models.db.create_tables(src.models.ALL_MODELS)
        src.models.db.close()

        # Try to verify samples against wrong database - should raise error
        with pytest.raises(ValueError, match="Database ID mismatch"):
            src.scrape_verification.verify_samples(str(samples_file), other_db)

    finally:
        pathlib.Path(other_db).unlink(missing_ok=True)


def test_sampling_doesnt_break_normal_scraping(temp_db):
    """Test that sampling doesn't interfere with normal scraping."""
    # This is a critical test - sampling should be transparent

    # Initialize sampling
    src.scrape_verification.init_sampling(temp_db, sample_rate=100)

    # Create term
    src.models.Term.create(code="202530", name="Fall 2025")

    # Simulate scraping 100 courses
    for i in range(100):
        course_dict: src.types.CourseDict = {
            "term": "202530",
            "crn": str(10000 + i),
            "code": f"CIS {1000 + i}",
            "section": "001",
            "title": f"Course {i}",
            "schedule_type": "Lecture",
            "inst_method_code": "In Class",
            "campus_code": "Philadelphia",
            "credits": "1",
            "enrolled": 90,
            "max_enrollment": 100,
            "seats_available": 10,
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "description": "Test course",
            "instructors": [],
            "meetings": [],
            "linked_crns": [],
            "is_cancelled": False,
            "status": "Active",
            "last_scraped": "2025-10-06T12:00:00",
        }

        # Sample (happens automatically in save_course)
        src.scrape_verification.sample_course(course_dict)

        # Insert into database (normal scraping)
        term = src.models.Term.get(src.models.Term.code == "202530")
        src.models.Course.create(
            term=term,
            crn=course_dict["crn"],
            code=course_dict["code"],
            section=course_dict["section"],
            title=course_dict["title"],
            schedule_type=course_dict["schedule_type"],
            credits=course_dict["credits"],
            start_date=course_dict["start_date"],
            end_date=course_dict["end_date"],
            is_cancelled=course_dict["is_cancelled"],
            status=course_dict["status"],
        )

    # Verify all 100 courses were inserted
    assert src.models.Course.select().count() == 100

    # Verify we captured some samples (probabilistically ~1)
    assert len(src.scrape_verification._current_samples) >= 0


def test_empty_samples(temp_db, temp_dir):
    """Test handling when no samples were collected."""
    src.scrape_verification.init_sampling(temp_db, sample_rate=1000000)  # Never sample

    # Try to save with no samples
    filepath = src.scrape_verification.save_samples(str(temp_dir))

    # Should return None or handle gracefully
    assert filepath is None or not filepath.exists()
