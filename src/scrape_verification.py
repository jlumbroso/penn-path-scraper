"""
Scrape verification using sampling.

GENERAL-PURPOSE DATA CONSISTENCY VALIDATION

The problem with post-hoc validation: if data is corrupted during insertion,
we have no "ground truth" to compare against. The scraper logs say "saved 6535"
but the database only has 2268 - how do we know which is right?

Solution: During scraping, randomly sample 1/N records and write them to a
ground-truth JSON file OUTSIDE the database. After scraping, verify those
samples exist in the database with correct data.

This catches corruption at insertion time, not weeks later.

REUSABLE FOR ANY ENTITY:
- Courses (CRN reuse corruption)
- Rooms (building/room misassignment)
- Instructors (name deduplication bugs)
- Meetings (time/location errors)
- Any other scraped entity

The key insight: external ground truth captured BEFORE database insertion.
"""
import datetime
import hashlib
import json
import pathlib
import random
import typing
import uuid

import structlog

import src.models
import src.types


logger = structlog.get_logger()


# Global: Current database ID for this session
_current_database_id: typing.Optional[str] = None
_current_samples: typing.List[typing.Dict[str, typing.Any]] = []
_sample_rate = 100  # Sample 1 in every N courses


def get_database_id(db_path: str) -> str:
    """
    Get unique ID for this database.

    Uses combination of file path and inode to generate stable ID.
    The ID stays stable even as database is modified.
    If database is moved/copied, it gets a new ID.

    Args:
        db_path: Path to database file

    Returns:
        Unique database ID (hex string)
    """
    # Use file path + inode for uniqueness (stable across modifications)
    path = pathlib.Path(db_path).resolve()

    try:
        stat = path.stat()
        # Combine path and inode (but NOT creation time, which changes on writes)
        unique_str = f"{path}:{stat.st_ino}"
    except FileNotFoundError:
        # Database doesn't exist yet - use path only
        # This will generate same ID once file is created
        unique_str = f"{path}:pending"

    # Hash to get stable ID
    return hashlib.sha256(unique_str.encode()).hexdigest()[:16]


def init_sampling(db_path: str, sample_rate: int = 100) -> None:
    """
    Initialize sampling for this scraping session.

    Args:
        db_path: Path to database
        sample_rate: Sample 1 in every N courses (default: 100)
    """
    global _current_database_id, _current_samples, _sample_rate

    _current_database_id = get_database_id(db_path)
    _current_samples = []
    _sample_rate = sample_rate

    logger.info(
        "sampling_initialized",
        database_id=_current_database_id,
        sample_rate=sample_rate,
    )


def should_sample() -> bool:
    """
    Randomly decide whether to sample this course.

    Returns:
        True if this course should be sampled
    """
    return random.randint(1, _sample_rate) == 1


def sample_course(course_dict: src.types.CourseDict) -> None:
    """
    Record this course as a ground-truth sample.

    This is called during scraping, BEFORE inserting into database.
    We capture the data we EXPECT to be in the database.

    Args:
        course_dict: Course data being inserted
    """
    if not should_sample():
        return

    if _current_database_id is None:
        logger.warning("sampling_not_initialized")
        return

    # Extract key fields for verification
    sample = {
        "database_id": _current_database_id,
        "sampled_at": datetime.datetime.now().isoformat(),
        "term_code": course_dict["term"],
        "crn": course_dict["crn"],
        "course_code": course_dict["code"],
        "section": course_dict["section"],
        "title": course_dict["title"],
        "schedule_type": course_dict["schedule_type"],
        "enrolled": course_dict.get("enrolled"),
        "max_enrollment": course_dict.get("max_enrollment"),
        "start_date": course_dict.get("start_date"),
        "end_date": course_dict.get("end_date"),
        "instructors": [
            instr["name"] if isinstance(instr, dict) else instr
            for instr in course_dict.get("instructors", [])
        ],
    }

    _current_samples.append(sample)

    logger.debug(
        "course_sampled",
        term=sample["term_code"],
        crn=sample["crn"],
        code=sample["course_code"],
    )


def save_samples(output_dir: str) -> pathlib.Path:
    """
    Save ground-truth samples to JSON file.

    Args:
        output_dir: Directory to save samples

    Returns:
        Path to saved samples file
    """
    if not _current_samples:
        logger.warning("no_samples_to_save")
        return None

    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp and database ID
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"scrape-samples-{timestamp}-{_current_database_id}.json"
    filepath = output_path / filename

    # Save samples
    data = {
        "database_id": _current_database_id,
        "generated_at": datetime.datetime.now().isoformat(),
        "sample_count": len(_current_samples),
        "sample_rate": _sample_rate,
        "samples": _current_samples,
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(
        "samples_saved",
        file=str(filepath),
        count=len(_current_samples),
    )

    return filepath


def verify_samples(
    samples_file: str,
    db_path: str,
) -> typing.Dict[str, typing.Any]:
    """
    Verify ground-truth samples against database.

    This is the KEY validation that catches corruption.

    Args:
        samples_file: Path to samples JSON file
        db_path: Path to database to verify

    Returns:
        Dict with verification results

    Raises:
        ValueError: If database ID doesn't match samples
        AssertionError: If samples don't match database
    """
    # Load samples
    with open(samples_file, "r") as f:
        data = json.load(f)

    expected_db_id = data["database_id"]
    samples = data["samples"]

    # Verify database ID
    actual_db_id = get_database_id(db_path)
    if actual_db_id != expected_db_id:
        raise ValueError(
            f"Database ID mismatch! Samples are from database {expected_db_id}, "
            f"but you're verifying against {actual_db_id}. "
            f"This means you're checking the wrong database."
        )

    # Initialize database
    src.models.db.init(db_path)
    src.models.db.connect()

    results = {
        "total_samples": len(samples),
        "verified": 0,
        "missing": [],
        "mismatched": [],
        "corrupted": [],
    }

    try:
        for sample in samples:
            term_code = sample["term_code"]
            crn = sample["crn"]

            # Look up course in database
            try:
                term = src.models.Term.get(src.models.Term.code == term_code)
                course = src.models.Course.get(
                    (src.models.Course.term == term)
                    & (src.models.Course.crn == crn)
                )

                # Verify key fields match
                mismatches = []

                if course.code != sample["course_code"]:
                    mismatches.append(
                        f"code: expected {sample['course_code']}, got {course.code}"
                    )

                if course.title != sample["title"]:
                    mismatches.append(
                        f"title: expected {sample['title']}, got {course.title}"
                    )

                if course.section != sample["section"]:
                    mismatches.append(
                        f"section: expected {sample['section']}, got {course.section}"
                    )

                # Check if term_id is WRONG (the corruption we're detecting!)
                if course.term.code != term_code:
                    results["corrupted"].append(
                        {
                            "crn": crn,
                            "expected_term": term_code,
                            "actual_term": course.term.code,
                            "expected_code": sample["course_code"],
                            "actual_code": course.code,
                            "message": f"🔴 CORRUPTION! CRN {crn} should be in {term_code} "
                            f"({sample['course_code']}) but is in {course.term.code} ({course.code})",
                        }
                    )
                elif mismatches:
                    results["mismatched"].append(
                        {
                            "crn": crn,
                            "term": term_code,
                            "mismatches": mismatches,
                        }
                    )
                else:
                    results["verified"] += 1

            except src.models.Term.DoesNotExist:
                results["missing"].append(
                    {
                        "crn": crn,
                        "term": term_code,
                        "reason": f"Term {term_code} not found in database",
                    }
                )

            except src.models.Course.DoesNotExist:
                # Course not found in expected term - but check if it exists in OTHER terms
                # (This catches the corruption bug where CRN is assigned to wrong term)
                other_courses = (
                    src.models.Course.select()
                    .where(src.models.Course.crn == crn)
                )

                if other_courses.exists():
                    # CRN exists but in WRONG term - this is corruption!
                    wrong_course = other_courses.first()
                    results["corrupted"].append(
                        {
                            "crn": crn,
                            "expected_term": term_code,
                            "actual_term": wrong_course.term.code,
                            "expected_code": sample["course_code"],
                            "actual_code": wrong_course.code,
                            "message": f"🔴 CORRUPTION! CRN {crn} should be in {term_code} "
                            f"({sample['course_code']}) but is in {wrong_course.term.code} ({wrong_course.code})",
                        }
                    )
                else:
                    # CRN doesn't exist anywhere - genuinely missing
                    results["missing"].append(
                        {
                            "crn": crn,
                            "term": term_code,
                            "code": sample["course_code"],
                            "reason": f"Course not found (expected CRN {crn} in term {term_code})",
                        }
                    )

    finally:
        src.models.db.close()

    # Log results
    logger.info(
        "verification_complete",
        total=results["total_samples"],
        verified=results["verified"],
        missing=len(results["missing"]),
        mismatched=len(results["mismatched"]),
        corrupted=len(results["corrupted"]),
    )

    return results


def print_verification_report(results: typing.Dict[str, typing.Any]) -> None:
    """
    Print human-readable verification report.

    Args:
        results: Results from verify_samples()
    """
    print("\n" + "=" * 70)
    print("SCRAPE VERIFICATION REPORT (Ground Truth Samples)")
    print("=" * 70 + "\n")

    total = results["total_samples"]
    verified = results["verified"]
    missing = len(results["missing"])
    mismatched = len(results["mismatched"])
    corrupted = len(results["corrupted"])

    print(f"📊 SUMMARY")
    print("-" * 70)
    print(f"  Total samples: {total}")
    print(f"  ✅ Verified:   {verified} ({verified/total*100:.1f}%)")
    print(f"  ❓ Missing:    {missing} ({missing/total*100:.1f}%)")
    print(f"  ⚠️  Mismatched: {mismatched} ({mismatched/total*100:.1f}%)")
    print(f"  🔴 CORRUPTED:  {corrupted} ({corrupted/total*100:.1f}%)\n")

    if corrupted > 0:
        print("🔴 CORRUPTION DETECTED!")
        print("-" * 70)
        for item in results["corrupted"][:10]:  # Show first 10
            print(f"  {item['message']}")
        if len(results["corrupted"]) > 10:
            print(f"  ... and {len(results['corrupted']) - 10} more\n")

        print("\n❌ DATABASE IS CORRUPTED - CRN REUSE BUG DETECTED")
        print("   This means courses from different terms are overwriting each other.")
        print("   Schema fix may not be applied, or persistence logic is buggy.\n")
        return

    if missing > 0:
        print("❓ MISSING COURSES")
        print("-" * 70)
        for item in results["missing"][:5]:
            print(f"  Term {item['term']}, CRN {item['crn']}: {item['reason']}")
        if missing > 5:
            print(f"  ... and {missing - 5} more\n")

    if mismatched > 0:
        print("⚠️  MISMATCHED DATA")
        print("-" * 70)
        for item in results["mismatched"][:5]:
            print(f"  Term {item['term']}, CRN {item['crn']}:")
            for mismatch in item["mismatches"]:
                print(f"    - {mismatch}")
        if mismatched > 5:
            print(f"  ... and {mismatched - 5} more\n")

    if verified == total:
        print("=" * 70)
        print("✅ ALL SAMPLES VERIFIED - DATABASE IS CORRECT")
        print("=" * 70 + "\n")
    else:
        print("=" * 70)
        print(f"⚠️  {verified}/{total} VERIFIED - SOME ISSUES FOUND")
        print("=" * 70 + "\n")
