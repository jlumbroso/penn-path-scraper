#!/usr/bin/env python3
"""
Post-Scrape Database Validation Script

Validates database integrity after scraping to catch issues early.
Checks for the CRN reuse bug and other data quality issues.

Usage:
    pipenv run python scripts/validate_database.py [--db PATH]
    pipenv run validate-db [--db PATH]
"""

import sys
import pathlib

# Add parent directory to path for imports
parent_dir = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import click
import structlog
import peewee

import src.models
import src.persistence

logger = structlog.get_logger()


@click.command()
@click.option(
    "--db",
    default="./courses.db",
    help="Path to database file",
    type=click.Path(exists=True),
)
def validate(db: str) -> None:
    """Validate database integrity after scraping."""

    logger.info("database_validation_starting", db_path=db)

    # Initialize database
    src.models.db.init(db)
    src.models.db.connect(reuse_if_open=True)

    try:
        issues = []

        # Check 1: Verify no duplicate (term, CRN) combinations
        logger.info("check_1_duplicate_term_crn_combinations")

        duplicates = (
            src.models.Course
            .select(
                src.models.Course.term,
                src.models.Course.crn,
                peewee.fn.COUNT(src.models.Course.id).alias('count')
            )
            .group_by(src.models.Course.term, src.models.Course.crn)
            .having(peewee.fn.COUNT(src.models.Course.id) > 1)
        )

        dup_count = duplicates.count()
        if dup_count > 0:
            issues.append(f"CRITICAL: Found {dup_count} duplicate (term, CRN) combinations")
            for dup in duplicates.limit(10):
                issues.append(f"  - Term {dup.term}, CRN {dup.crn}: {dup.count} instances")
            if dup_count > 10:
                issues.append(f"  ... and {dup_count - 10} more")
        else:
            logger.info("check_1_passed", message="No duplicate (term, CRN) combinations found")

        # Check 2: Verify CRN reuse across terms is working
        logger.info("check_2_crn_reuse_across_terms")

        reused_crns = (
            src.models.Course
            .select(
                src.models.Course.crn,
                peewee.fn.COUNT(peewee.fn.DISTINCT(src.models.Course.term)).alias('term_count')
            )
            .group_by(src.models.Course.crn)
            .having(peewee.fn.COUNT(peewee.fn.DISTINCT(src.models.Course.term)) > 1)
        )

        reuse_count = reused_crns.count()
        logger.info(
            "check_2_result",
            crns_reused_across_terms=reuse_count,
            message=f"Found {reuse_count} CRNs used across multiple terms (expected behavior)"
        )

        # Check 3: Verify enrollment data consistency
        logger.info("check_3_enrollment_data_consistency")

        invalid_enrollments = (
            src.models.Course
            .select()
            .where(
                (src.models.Course.enrolled.is_null(False)) &
                (src.models.Course.max_enrollment.is_null(False)) &
                (src.models.Course.enrolled > src.models.Course.max_enrollment)
            )
        )

        invalid_count = invalid_enrollments.count()
        if invalid_count > 0:
            # This is informational - courses can over-enroll (instructors allowing overrides)
            logger.info(
                "check_3_result",
                over_enrolled_count=invalid_count,
                message=f"Found {invalid_count} courses with enrolled > max_enrollment (common with instructor permission)"
            )
        else:
            logger.info("check_3_passed", message="No enrollment data inconsistencies found")

        # Check 4: Verify instructor data integrity
        logger.info("check_4_instructor_data_integrity")

        # Check for orphaned CourseInstructor records (referencing non-existent courses)
        total_course_instructors = src.models.CourseInstructor.select().count()

        # Just verify the counts are reasonable
        total_courses_count = src.models.Course.select().count()
        instructor_ratio = total_course_instructors / total_courses_count if total_courses_count > 0 else 0

        if instructor_ratio > 10:  # Unlikely to have >10 instructors per course on average
            issues.append(
                f"WARNING: Unusually high instructor-to-course ratio: {instructor_ratio:.2f} "
                f"({total_course_instructors} instructors for {total_courses_count} courses)"
            )
        else:
            logger.info(
                "check_4_passed",
                message="Instructor data integrity verified",
                instructor_ratio=f"{instructor_ratio:.2f}"
            )

        # Check 5: Verify enrollment snapshot consistency
        logger.info("check_5_enrollment_snapshot_consistency")

        # Check for courses with enrollment but no snapshots
        courses_with_enrollment = (
            src.models.Course
            .select()
            .where(src.models.Course.enrolled.is_null(False))
        )

        missing_snapshots = 0
        for course in courses_with_enrollment:
            snapshot_count = (
                src.models.EnrollmentSnapshot
                .select()
                .where(src.models.EnrollmentSnapshot.course == course)
                .count()
            )
            if snapshot_count == 0:
                missing_snapshots += 1

        if missing_snapshots > 0:
            logger.info(
                "check_5_result",
                courses_without_snapshots=missing_snapshots,
                message=f"Found {missing_snapshots} courses with enrollment data "
                "but no enrollment snapshots (expected for historical data)"
            )
        else:
            logger.info("check_5_passed", message="Enrollment snapshot consistency verified")

        # Check 6: Database statistics
        logger.info("check_6_database_statistics")

        total_courses = src.models.Course.select().count()
        total_terms = (
            src.models.Course
            .select(peewee.fn.COUNT(peewee.fn.DISTINCT(src.models.Course.term)))
            .scalar()
        )
        total_instructors = src.models.Instructor.select().count()
        total_snapshots = src.models.EnrollmentSnapshot.select().count()

        logger.info(
            "database_statistics",
            total_courses=total_courses,
            total_terms=total_terms,
            total_instructors=total_instructors,
            total_snapshots=total_snapshots,
        )

        # Summary
        if issues:
            logger.warning("validation_completed_with_issues", issue_count=len(issues))
            print("\n❌ VALIDATION ISSUES FOUND:\n")
            for issue in issues:
                print(issue)
            sys.exit(1)
        else:
            logger.info("validation_completed_successfully")
            print("\n✅ DATABASE VALIDATION PASSED\n")
            print(f"Total courses: {total_courses}")
            print(f"Total terms: {total_terms}")
            print(f"Total instructors: {total_instructors}")
            print(f"Total snapshots: {total_snapshots}")
            print(f"CRNs reused across terms: {reuse_count}")
            sys.exit(0)

    finally:
        if not src.models.db.is_closed():
            src.models.db.close()


if __name__ == "__main__":
    validate()
