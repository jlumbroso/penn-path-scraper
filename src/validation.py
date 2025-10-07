"""
Database validation utilities.

These functions check database integrity after scraping to catch
data corruption issues immediately rather than discovering them weeks later.
"""
import datetime
import sys
import typing

import structlog

import src.models


logger = structlog.get_logger()


class ValidationError(Exception):
    """Raised when database validation fails."""

    pass


def validate_term_course_counts(
    expected_counts: typing.Optional[typing.Dict[str, int]] = None,
    tolerance: int = 0,
) -> typing.Dict[str, int]:
    """
    Validate course counts per term.

    Args:
        expected_counts: Optional dict of {term_code: expected_count}.
                        If provided, raises ValidationError if counts don't match.
        tolerance: Allow counts to differ by this many courses (default: 0)

    Returns:
        Dict of {term_code: actual_count}

    Raises:
        ValidationError: If counts don't match expected (when provided)
    """
    actual_counts = {}

    for term in src.models.Term.select():
        count = (
            src.models.Course.select()
            .where(src.models.Course.term == term)
            .count()
        )
        actual_counts[term.code] = count

        logger.info(
            "term_course_count",
            term=term.name,
            term_code=term.code,
            count=count,
        )

    # Validate against expected counts if provided
    if expected_counts:
        for term_code, expected_count in expected_counts.items():
            actual_count = actual_counts.get(term_code, 0)

            if abs(actual_count - expected_count) > tolerance:
                raise ValidationError(
                    f"Term {term_code}: expected {expected_count} courses "
                    f"(±{tolerance}), but found {actual_count}"
                )

    return actual_counts


def validate_no_orphaned_courses() -> int:
    """
    Check for courses with invalid term foreign keys.

    Returns:
        Count of orphaned courses (should be 0)

    Raises:
        ValidationError: If orphaned courses found
    """
    import peewee

    # Find courses with NULL term
    null_term_count = (
        src.models.Course.select()
        .where(src.models.Course.term.is_null())
        .count()
    )

    if null_term_count > 0:
        raise ValidationError(f"Found {null_term_count} courses with NULL term_id")

    # Find courses with term_id that doesn't exist in terms table
    orphaned_count = (
        src.models.Course.select()
        .join(
            src.models.Term,
            peewee.JOIN.LEFT_OUTER,
            on=(src.models.Course.term == src.models.Term.id),
        )
        .where(src.models.Term.id.is_null())
        .count()
    )

    if orphaned_count > 0:
        raise ValidationError(
            f"Found {orphaned_count} courses with invalid term_id foreign key"
        )

    logger.info("no_orphaned_courses", null_count=null_term_count, orphaned=orphaned_count)
    return 0


def validate_crn_uniqueness_per_term() -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Check that (term, crn) combinations are unique.

    This should be enforced by database constraint, but we check anyway.

    Returns:
        List of duplicate (term, crn) combinations (should be empty)

    Raises:
        ValidationError: If duplicates found
    """
    import peewee

    # Find duplicate (term, crn) pairs
    duplicates = (
        src.models.Course.select(
            src.models.Course.term,
            src.models.Course.crn,
            peewee.fn.COUNT(src.models.Course.id).alias("count"),
        )
        .group_by(src.models.Course.term, src.models.Course.crn)
        .having(peewee.fn.COUNT(src.models.Course.id) > 1)
    )

    duplicate_list = []
    for dup in duplicates:
        term = src.models.Term.get_by_id(dup.term)
        duplicate_list.append(
            {
                "term_code": term.code,
                "term_name": term.name,
                "crn": dup.crn,
                "count": dup.count,
            }
        )

    if duplicate_list:
        raise ValidationError(
            f"Found {len(duplicate_list)} duplicate (term, crn) combinations: "
            f"{duplicate_list}"
        )

    logger.info("crn_uniqueness_validated", duplicates_found=len(duplicate_list))
    return duplicate_list


def validate_term_date_alignment() -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Check that course dates align with their term dates.

    Courses should have start/end dates within their term's date range.

    Returns:
        List of courses with misaligned dates

    Raises:
        ValidationError: If significant misalignment found (>10% of courses)
    """
    misaligned = []

    for course in src.models.Course.select().join(src.models.Term):
        term = course.term

        # Skip if term or course doesn't have dates
        if not term.start_date or not term.end_date:
            continue
        if not course.start_date or not course.end_date:
            continue

        # Check if course dates are within term dates (with some tolerance)
        # Allow 7 days before term start (for early-start courses)
        # Allow 7 days after term end (for extended courses)
        tolerance = datetime.timedelta(days=7)

        if (
            course.start_date < (term.start_date - tolerance)
            or course.end_date > (term.end_date + tolerance)
        ):
            misaligned.append(
                {
                    "crn": course.crn,
                    "code": course.code,
                    "term": term.code,
                    "course_start": course.start_date.isoformat(),
                    "course_end": course.end_date.isoformat(),
                    "term_start": term.start_date.isoformat(),
                    "term_end": term.end_date.isoformat(),
                }
            )

    total_courses = src.models.Course.select().count()
    misalignment_rate = len(misaligned) / total_courses if total_courses > 0 else 0

    # If more than 10% of courses are misaligned, something is seriously wrong
    if misalignment_rate > 0.10:
        raise ValidationError(
            f"Found {len(misaligned)} courses ({misalignment_rate:.1%}) "
            f"with dates misaligned from their term. This suggests data corruption."
        )

    logger.info(
        "term_date_alignment_validated",
        misaligned_count=len(misaligned),
        misalignment_rate=f"{misalignment_rate:.2%}",
    )

    return misaligned


def validate_recent_scrapes(hours: int = 24) -> typing.Dict[str, int]:
    """
    Check for courses that were scraped recently.

    This helps detect if a scrape actually happened vs silently failing.

    Args:
        hours: Number of hours to look back (default: 24)

    Returns:
        Dict of {term_code: count_of_recently_scraped_courses}

    Raises:
        ValidationError: If no courses were scraped recently (suggests scraper failure)
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

    recent_by_term = {}

    for term in src.models.Term.select():
        count = (
            src.models.Course.select()
            .where(
                (src.models.Course.term == term)
                & (src.models.Course.last_scraped >= cutoff)
            )
            .count()
        )
        recent_by_term[term.code] = count

    total_recent = sum(recent_by_term.values())

    if total_recent == 0:
        raise ValidationError(
            f"No courses scraped in the last {hours} hours. "
            f"Scraper may have failed silently."
        )

    logger.info(
        "recent_scrapes_validated",
        hours=hours,
        total_recent=total_recent,
        by_term=recent_by_term,
    )

    return recent_by_term


def validate_term_isolation(
    recently_scraped_term: typing.Optional[str] = None,
    hours: int = 24,
) -> typing.Dict[str, typing.Any]:
    """
    Verify that scraping one term doesn't corrupt other terms.

    This is the KEY validation to catch CRN reuse bugs.

    Args:
        recently_scraped_term: Term code that was just scraped
        hours: Look back this many hours for "recent" scrapes

    Returns:
        Dict with validation results

    Raises:
        ValidationError: If other terms show recent scrape activity (corruption detected!)
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

    # Find courses scraped recently, grouped by term
    recent_by_term = {}

    for term in src.models.Term.select():
        count = (
            src.models.Course.select()
            .where(
                (src.models.Course.term == term)
                & (src.models.Course.last_scraped >= cutoff)
            )
            .count()
        )
        if count > 0:
            recent_by_term[term.code] = count

    # If we know which term was just scraped, verify ONLY that term has recent activity
    if recently_scraped_term:
        unexpected_terms = {
            term_code: count
            for term_code, count in recent_by_term.items()
            if term_code != recently_scraped_term
        }

        if unexpected_terms:
            raise ValidationError(
                f"🔴 CORRUPTION DETECTED! Scraped {recently_scraped_term}, but these "
                f"other terms also have recently updated courses: {unexpected_terms}. "
                f"This indicates CRN reuse is causing overwrites!"
            )

    logger.info(
        "term_isolation_validated",
        recently_scraped_term=recently_scraped_term,
        recent_by_term=recent_by_term,
    )

    return recent_by_term


def validate_crn_reuse_distribution() -> typing.Dict[str, int]:
    """
    Verify that CRNs are properly reused across terms (not overwritten).

    If we have Fall 2024 and Fall 2025, many CRNs should appear in BOTH terms.
    If CRNs only appear once, something is wrong.

    Returns:
        Dict with reuse statistics

    Raises:
        ValidationError: If CRN distribution suggests overwrites
    """
    import peewee

    # Count how many terms each CRN appears in
    crn_distribution = (
        src.models.Course.select(
            src.models.Course.crn,
            peewee.fn.COUNT(peewee.fn.DISTINCT(src.models.Course.term)).alias(
                "term_count"
            ),
        )
        .group_by(src.models.Course.crn)
    )

    distribution = {}
    for row in crn_distribution:
        count = row.term_count
        if count not in distribution:
            distribution[count] = 0
        distribution[count] += 1

    # Calculate statistics
    total_crns = sum(distribution.values())
    reused_crns = sum(
        count for term_count, count in distribution.items() if term_count > 1
    )
    reuse_rate = reused_crns / total_crns if total_crns > 0 else 0

    term_count = src.models.Term.select().count()

    # If we have 2+ terms, we expect significant CRN reuse
    if term_count >= 2 and reuse_rate < 0.10:
        raise ValidationError(
            f"🔴 SUSPICIOUS: Only {reuse_rate:.1%} of CRNs appear in multiple terms. "
            f"With {term_count} terms in database, we expect much higher reuse. "
            f"This suggests CRN overwrites are happening!"
        )

    logger.info(
        "crn_reuse_validated",
        total_crns=total_crns,
        reused_crns=reused_crns,
        reuse_rate=f"{reuse_rate:.1%}",
        distribution=distribution,
    )

    return {
        "total_crns": total_crns,
        "reused_crns": reused_crns,
        "reuse_rate": reuse_rate,
        "distribution": distribution,
    }


def validate_per_term_growth(
    baseline: typing.Optional[typing.Dict[str, int]] = None,
) -> typing.Dict[str, typing.Any]:
    """
    Validate that total course count grows or stays stable (never shrinks).

    Args:
        baseline: Previous course counts {term_code: count} from earlier scrape

    Returns:
        Dict with growth analysis

    Raises:
        ValidationError: If course counts decreased unexpectedly
    """
    current_counts = {}
    for term in src.models.Term.select():
        count = (
            src.models.Course.select()
            .where(src.models.Course.term == term)
            .count()
        )
        current_counts[term.code] = count

    if baseline:
        decreased_terms = []
        for term_code, old_count in baseline.items():
            new_count = current_counts.get(term_code, 0)
            if new_count < old_count * 0.95:  # Allow 5% tolerance for deletions
                decreased_terms.append(
                    {
                        "term": term_code,
                        "old_count": old_count,
                        "new_count": new_count,
                        "change": new_count - old_count,
                    }
                )

        if decreased_terms:
            raise ValidationError(
                f"🔴 COURSE COUNTS DECREASED! The following terms lost courses: "
                f"{decreased_terms}. This suggests corruption or deletion."
            )

    logger.info("per_term_growth_validated", current=current_counts, baseline=baseline)

    return {"current": current_counts, "baseline": baseline}


def run_all_validations(
    expected_counts: typing.Optional[typing.Dict[str, int]] = None,
    recently_scraped_term: typing.Optional[str] = None,
    baseline_counts: typing.Optional[typing.Dict[str, int]] = None,
) -> bool:
    """
    Run all validation checks.

    Args:
        expected_counts: OPTIONAL dict of {term_code: expected_course_count}
                        (only useful if we have external source of truth)
        recently_scraped_term: Term that was just scraped (validates isolation)
        baseline_counts: Previous course counts (validates no data loss)

    Returns:
        True if all validations pass

    Raises:
        ValidationError: If any validation fails
    """
    logger.info("running_all_validations")

    try:
        # 1. Course counts per term
        actual_counts = validate_term_course_counts(expected_counts)

        # 2. No orphaned courses
        validate_no_orphaned_courses()

        # 3. CRN uniqueness PER TERM (no duplicates within same term)
        validate_crn_uniqueness_per_term()

        # 4. CRN reuse ACROSS TERMS (should have many CRNs in multiple terms)
        validate_crn_reuse_distribution()

        # 5. Term isolation (scraping Term B doesn't corrupt Term A)
        validate_term_isolation(recently_scraped_term, hours=24)

        # 6. Per-term growth (counts never decrease)
        if baseline_counts:
            validate_per_term_growth(baseline_counts)

        # 7. Date alignment
        misaligned = validate_term_date_alignment()
        if misaligned:
            logger.warning(
                "some_courses_have_misaligned_dates",
                count=len(misaligned),
                examples=misaligned[:5],
            )

        # 8. Recent scrape activity
        validate_recent_scrapes(hours=24)

        logger.info(
            "all_validations_passed",
            total_courses=sum(actual_counts.values()),
            terms=len(actual_counts),
        )

        return True

    except ValidationError as e:
        logger.error("validation_failed", error=str(e))
        raise


def print_validation_report() -> None:
    """
    Print a human-readable validation report.

    This is useful for manual inspection after scraping.
    """
    print("\n" + "=" * 70)
    print("DATABASE VALIDATION REPORT")
    print("=" * 70 + "\n")

    try:
        # Course counts
        print("📊 COURSE COUNTS PER TERM")
        print("-" * 70)
        counts = validate_term_course_counts()
        total = sum(counts.values())
        for term_code, count in sorted(counts.items(), reverse=True):
            term = src.models.Term.get(src.models.Term.code == term_code)
            print(f"  {term.name:20s} ({term_code}): {count:5d} courses")
        print(f"\n  {'TOTAL':20s}           {total:5d} courses\n")

        # Orphaned courses
        print("🔗 FOREIGN KEY INTEGRITY")
        print("-" * 70)
        try:
            validate_no_orphaned_courses()
            print("  ✅ No orphaned courses found\n")
        except ValidationError as e:
            print(f"  ❌ {e}\n")
            raise

        # CRN uniqueness per term
        print("🔑 CRN UNIQUENESS PER TERM")
        print("-" * 70)
        try:
            validate_crn_uniqueness_per_term()
            print("  ✅ All (term, crn) combinations are unique\n")
        except ValidationError as e:
            print(f"  ❌ {e}\n")
            raise

        # CRN reuse across terms (KEY validation for corruption)
        print("🔄 CRN REUSE ACROSS TERMS")
        print("-" * 70)
        try:
            stats = validate_crn_reuse_distribution()
            print(f"  Total unique CRNs: {stats['total_crns']}")
            print(f"  CRNs appearing in 2+ terms: {stats['reused_crns']} ({stats['reuse_rate']:.1%})")
            print(f"  Distribution: {stats['distribution']}")
            term_count = src.models.Term.select().count()
            if term_count >= 2 and stats['reuse_rate'] < 0.10:
                print(f"  ⚠️  WARNING: Low reuse rate with {term_count} terms - possible overwrites!")
            else:
                print(f"  ✅ CRN reuse distribution looks healthy\n")
        except ValidationError as e:
            print(f"  ❌ {e}\n")
            raise

        # Term isolation
        print("🔒 TERM ISOLATION (scraping one term doesn't corrupt others)")
        print("-" * 70)
        try:
            recent = validate_term_isolation(recently_scraped_term=None, hours=24)
            if len(recent) == 0:
                print(f"  ℹ️  No courses scraped in last 24h (no recent activity to check)\n")
            elif len(recent) == 1:
                term_code = list(recent.keys())[0]
                print(f"  ✅ Only {term_code} has recent activity - no cross-contamination\n")
            else:
                print(f"  ⚠️  Multiple terms have recent activity: {recent}")
                print(f"     (This is OK if you scraped multiple terms, but could indicate overwrites)\n")
        except ValidationError as e:
            print(f"  ❌ {e}\n")
            raise

        # Date alignment
        print("📅 TERM DATE ALIGNMENT")
        print("-" * 70)
        try:
            misaligned = validate_term_date_alignment()
            if misaligned:
                print(f"  ⚠️  {len(misaligned)} courses have dates outside term range")
                print(f"     (This is OK if <10% of total)\n")
            else:
                print("  ✅ All course dates align with term dates\n")
        except ValidationError as e:
            print(f"  ❌ {e}\n")
            raise

        # Recent activity
        print("⏰ RECENT SCRAPE ACTIVITY (last 24h)")
        print("-" * 70)
        try:
            recent = validate_recent_scrapes(hours=24)
            total_recent = sum(recent.values())
            print(f"  {total_recent} courses scraped in last 24 hours")
            for term_code, count in sorted(recent.items(), reverse=True):
                if count > 0:
                    term = src.models.Term.get(src.models.Term.code == term_code)
                    print(f"    {term.name:20s}: {count:5d} courses")
            print()
        except ValidationError as e:
            print(f"  ❌ {e}\n")
            raise

        print("=" * 70)
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 70 + "\n")

    except ValidationError:
        print("=" * 70)
        print("❌ VALIDATION FAILED - SEE ERRORS ABOVE")
        print("=" * 70 + "\n")
        sys.exit(1)
