"""
Integration tests for CRN reuse across terms.

This test validates that Penn's CRN reuse pattern is handled correctly:
- Same CRN can refer to different courses in different terms
- Each (term, crn) combination creates a separate database record
- No data corruption occurs when scraping multiple terms
"""
import pathlib
import tempfile

import peewee
import pytest

import src.models
import src.persistence
import src.types


@pytest.fixture(scope="function")
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


def test_crn_reuse_creates_separate_records(temp_db):
    """
    Test that same CRN in different terms creates separate records.

    Scenario:
    - Fall 2024: CRN 60563 = CIS 1210 (Data Structures)
    - Fall 2025: CRN 60563 = BE 1000 (Intro to Bioengineering)

    Expected: 2 separate Course records, no data corruption
    """
    # Create terms
    fall_2024 = src.models.Term.create(code="202430", name="Fall 2024")
    fall_2025 = src.models.Term.create(code="202530", name="Fall 2025")

    # Course data for Fall 2024 (CRN 60563)
    fall_2024_course: src.types.CourseDict = {
        "code": "CIS 1210",
        "crn": "60563",
        "term": "202430",
        "section": "001",
        "title": "Data Structures and Algorithms",
        "description": "Learn data structures",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "max_enrollment": 100,
        "seats_available": 10,
        "enrolled": 90,
        "meetings": [],
        "instructors": [{"name": "Jane Doe"}],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "start_date": "2024-08-26",
        "end_date": "2024-12-08",
        "last_scraped": "2024-09-15T12:00:00",
    }

    # Course data for Fall 2025 (SAME CRN, different course)
    fall_2025_course: src.types.CourseDict = {
        "code": "BE 1000",
        "crn": "60563",  # ← SAME CRN
        "term": "202530",
        "section": "001",
        "title": "Introduction to Bioengineering",
        "description": "Intro to bioengineering",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "max_enrollment": 80,
        "seats_available": 20,
        "enrolled": 60,
        "meetings": [],
        "instructors": [{"name": "John Smith"}],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "last_scraped": "2025-10-06T12:00:00",
    }

    # Save Fall 2024 course
    course_2024 = src.persistence.save_course(fall_2024_course)

    # Save Fall 2025 course (SAME CRN)
    course_2025 = src.persistence.save_course(fall_2025_course)

    # Verify: Two separate records exist
    assert src.models.Course.select().count() == 2

    # Verify: Different IDs (not the same record)
    assert course_2024.id != course_2025.id

    # Verify: Both have same CRN but different terms
    assert course_2024.crn == "60563"
    assert course_2025.crn == "60563"
    assert course_2024.term.code == "202430"
    assert course_2025.term.code == "202530"

    # Verify: Fall 2024 data NOT corrupted
    assert course_2024.code == "CIS 1210"
    assert course_2024.title == "Data Structures and Algorithms"
    assert course_2024.enrolled == 90

    # Verify: Fall 2025 data correct
    assert course_2025.code == "BE 1000"
    assert course_2025.title == "Introduction to Bioengineering"
    assert course_2025.enrolled == 60


def test_same_crn_same_term_updates_record(temp_db):
    """
    Test that same CRN in same term updates existing record (not creates new).

    Scenario:
    - First scrape: CRN 60563 in Fall 2025, 60 enrolled
    - Second scrape: CRN 60563 in Fall 2025, 65 enrolled (updated)

    Expected: 1 record, enrollment updated
    """
    # Create term
    fall_2025 = src.models.Term.create(code="202530", name="Fall 2025")

    # First scrape
    first_scrape: src.types.CourseDict = {
        "code": "BE 1000",
        "crn": "60563",
        "term": "202530",
        "section": "001",
        "title": "Introduction to Bioengineering",
        "description": "Intro to bioengineering",
        "schedule_type": "Lecture",
        "inst_method_code": "In Class",
        "campus_code": "Philadelphia",
        "credits": "1",
        "max_enrollment": 80,
        "seats_available": 20,
        "enrolled": 60,  # ← Initial enrollment
        "meetings": [],
        "instructors": [],
        "linked_crns": [],
        "is_cancelled": False,
        "status": "Active",
        "start_date": "2025-08-26",
        "end_date": "2025-12-08",
        "last_scraped": "2025-10-06T12:00:00",
    }

    # Second scrape (enrollment increased)
    second_scrape: src.types.CourseDict = {
        **first_scrape,
        "enrolled": 65,  # ← Updated enrollment
        "seats_available": 15,
        "last_scraped": "2025-10-06T13:00:00",
    }

    # Save first scrape
    course_first = src.persistence.save_course(first_scrape)

    # Save second scrape (should UPDATE, not CREATE)
    course_second = src.persistence.save_course(second_scrape)

    # Verify: Only one record exists
    assert src.models.Course.select().count() == 1

    # Verify: Same record (same ID)
    assert course_first.id == course_second.id

    # Verify: Enrollment updated
    assert course_second.enrolled == 65
    assert course_second.seats_available == 15


def test_unique_constraint_prevents_duplicates(temp_db):
    """
    Test that database enforces unique (term, crn) constraint.

    This should not be possible to violate at the database level.
    """
    # Create term
    fall_2025 = src.models.Term.create(code="202530", name="Fall 2025")

    # Create first course
    course1 = src.models.Course.create(
        term=fall_2025,
        crn="60563",
        code="BE 1000",
        section="001",
        title="Test Course",
        schedule_type="Lecture",
        credits="1",
        start_date="2025-08-26",
        end_date="2025-12-08",
        is_cancelled=False,
        status="Active",
    )

    # Attempt to create duplicate (should raise IntegrityError)
    with pytest.raises(peewee.IntegrityError):
        src.models.Course.create(
            term=fall_2025,
            crn="60563",  # ← DUPLICATE (term, crn)
            code="CIS 1210",
            section="002",
            title="Different Course",
            schedule_type="Lecture",
            credits="1",
            start_date="2025-08-26",
            end_date="2025-12-08",
            is_cancelled=False,
            status="Active",
        )


def test_crn_can_repeat_across_terms(temp_db):
    """
    Test that same CRN can exist in multiple terms without conflict.
    """
    # Create multiple terms
    fall_2022 = src.models.Term.create(code="202230", name="Fall 2022")
    fall_2023 = src.models.Term.create(code="202330", name="Fall 2023")
    fall_2024 = src.models.Term.create(code="202430", name="Fall 2024")
    fall_2025 = src.models.Term.create(code="202530", name="Fall 2025")

    # Create same CRN in all 4 terms
    crn = "60563"
    courses = []

    for term, code, title in [
        (fall_2022, "MATH 1400", "Calculus"),
        (fall_2023, "PHYS 0150", "Physics"),
        (fall_2024, "CIS 1210", "Data Structures"),
        (fall_2025, "BE 1000", "Bioengineering"),
    ]:
        course = src.models.Course.create(
            term=term,
            crn=crn,  # ← SAME CRN in all terms
            code=code,
            section="001",
            title=title,
            schedule_type="Lecture",
            credits="1",
            start_date="2025-08-26",
            end_date="2025-12-08",
            is_cancelled=False,
            status="Active",
        )
        courses.append(course)

    # Verify: 4 separate records
    assert src.models.Course.select().count() == 4

    # Verify: All have same CRN but different terms and course codes
    for i, course in enumerate(courses):
        assert course.crn == crn
        # Verify each has the correct term
        expected_codes = ["MATH 1400", "PHYS 0150", "CIS 1210", "BE 1000"]
        assert course.code == expected_codes[i]


def test_post_scrape_validation():
    """
    Example validation function that should run after every scrape.

    This validates:
    - Course counts match expected
    - No courses have NULL term_id
    - No orphaned foreign keys
    """

    def validate_database_integrity(db_path: str, expected_counts: dict):
        """
        Validate database integrity after scraping.

        Args:
            db_path: Path to database
            expected_counts: Dict of {term_code: expected_course_count}

        Raises:
            AssertionError: If validation fails
        """
        src.models.db.init(db_path)
        src.models.db.connect()

        try:
            # Check course counts per term
            for term_code, expected_count in expected_counts.items():
                term = src.models.Term.get(src.models.Term.code == term_code)
                actual_count = (
                    src.models.Course.select()
                    .where(src.models.Course.term == term)
                    .count()
                )

                assert actual_count == expected_count, (
                    f"Term {term_code}: expected {expected_count} courses, "
                    f"found {actual_count}"
                )

            # Verify no courses have NULL term
            null_term_count = (
                src.models.Course.select()
                .where(src.models.Course.term.is_null())
                .count()
            )
            assert null_term_count == 0, f"Found {null_term_count} courses with NULL term"

            # Verify all courses have valid term foreign key
            orphaned_courses = (
                src.models.Course.select()
                .join(
                    src.models.Term,
                    peewee.JOIN.LEFT_OUTER,
                    on=(src.models.Course.term == src.models.Term.id),
                )
                .where(src.models.Term.id.is_null())
                .count()
            )
            assert (
                orphaned_courses == 0
            ), f"Found {orphaned_courses} courses with invalid term_id"

        finally:
            src.models.db.close()

    # This function should be called after every scrape
    # Example: validate_database_integrity("courses.db", {"202530": 6535, "202430": 6519})
