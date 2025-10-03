"""
Course scraper orchestrator.

Coordinates API client and persistence layer to scrape Penn course data.
Handles error recovery, progress tracking, and enrollment snapshots.
"""

import datetime
import typing

import structlog

import src.api_client
import src.models
import src.persistence
import src.types

# Initialize structured logger
logger = structlog.get_logger()


# =============================================================================
# Result Types
# =============================================================================

class SchoolScrapeResult(typing.TypedDict):
    """Result of scraping a single school."""
    school_code: str
    term: str
    courses_found: int
    courses_saved: int
    errors_count: int
    error_details: typing.List[str]
    duration_seconds: float


class TermScrapeResult(typing.TypedDict):
    """Result of scraping a single term."""
    term: str
    school_results: typing.List[SchoolScrapeResult]
    total_courses_found: int
    total_courses_saved: int
    total_errors: int
    duration_seconds: float


# =============================================================================
# Main Scraper Class
# =============================================================================

class CourseScraper:
    """
    Orchestrates scraping of Penn course catalog.

    Coordinates API client and database persistence with error handling,
    logging, and progress tracking.
    """

    def __init__(
        self,
        api_client: src.api_client.PennCoursesAPIClient,
        db_path: str,
    ):
        """
        Initialize scraper.

        Args:
            api_client: Configured API client for Penn Courses
            db_path: Path to SQLite database
        """
        self.api_client = api_client
        self.db_path = db_path
        self.logger = logger.bind(component="scraper")

    def scrape_term(
        self,
        term: str,
        schools: typing.Optional[typing.List[str]] = None,
        create_snapshots: bool = True,
    ) -> TermScrapeResult:
        """
        Scrape all courses for a term.

        Args:
            term: Term code (e.g., "202530")
            schools: List of school codes to scrape (None = all schools)
            create_snapshots: Whether to create enrollment snapshots

        Returns:
            TermScrapeResult with aggregated statistics
        """
        start_time = datetime.datetime.now()

        self.logger.info("scrape_term_start", term=term, schools=schools)

        # Ensure term exists in database
        ensure_term_exists(term)

        # Determine which schools to scrape
        if schools is None:
            schools = [school["code"] for school in src.types.SCHOOLS]

        # Scrape each school
        school_results: typing.List[SchoolScrapeResult] = []
        for school_code in schools:
            try:
                result = self.scrape_school(
                    term=term,
                    school_code=school_code,
                    create_snapshots=create_snapshots,
                )
                school_results.append(result)
            except Exception as e:
                self.logger.error(
                    "scrape_school_failed",
                    term=term,
                    school_code=school_code,
                    error=str(e),
                )
                # Add error result
                school_results.append({
                    "school_code": school_code,
                    "term": term,
                    "courses_found": 0,
                    "courses_saved": 0,
                    "errors_count": 1,
                    "error_details": [str(e)],
                    "duration_seconds": 0.0,
                })

        # Aggregate results
        duration = (datetime.datetime.now() - start_time).total_seconds()

        result: TermScrapeResult = {
            "term": term,
            "school_results": school_results,
            "total_courses_found": sum(r["courses_found"] for r in school_results),
            "total_courses_saved": sum(r["courses_saved"] for r in school_results),
            "total_errors": sum(r["errors_count"] for r in school_results),
            "duration_seconds": duration,
        }

        self.logger.info(
            "scrape_term_complete",
            term=term,
            courses_found=result["total_courses_found"],
            courses_saved=result["total_courses_saved"],
            errors=result["total_errors"],
            duration=duration,
        )

        return result

    def scrape_school(
        self,
        term: str,
        school_code: str,
        create_snapshots: bool = True,
    ) -> SchoolScrapeResult:
        """
        Scrape all courses for a school in a term.

        Args:
            term: Term code (e.g., "202530")
            school_code: School code (e.g., "E" for Engineering)
            create_snapshots: Whether to create enrollment snapshots

        Returns:
            SchoolScrapeResult with statistics
        """
        start_time = datetime.datetime.now()

        self.logger.info(
            "scrape_school_start",
            term=term,
            school_code=school_code,
        )

        # Search for courses in this school
        try:
            search_result = self.api_client.search_by_school(
                term=term,
                school_code=school_code,
            )
        except Exception as e:
            self.logger.error(
                "search_failed",
                term=term,
                school_code=school_code,
                error=str(e),
            )
            raise

        courses_found = search_result["count"]
        courses_saved = 0
        errors: typing.List[str] = []

        # Process each course
        for course_summary in search_result["results"]:
            try:
                self._process_course(
                    course_code=course_summary["code"],
                    crn=course_summary["crn"],
                    term=term,
                    create_snapshot=create_snapshots,
                )
                courses_saved += 1
            except Exception as e:
                error_msg = f"Failed to process {course_summary['code']} (CRN {course_summary['crn']}): {e}"
                errors.append(error_msg)
                self.logger.warning(
                    "course_process_failed",
                    term=term,
                    school_code=school_code,
                    course_code=course_summary["code"],
                    crn=course_summary["crn"],
                    error=str(e),
                )

        duration = (datetime.datetime.now() - start_time).total_seconds()

        result: SchoolScrapeResult = {
            "school_code": school_code,
            "term": term,
            "courses_found": courses_found,
            "courses_saved": courses_saved,
            "errors_count": len(errors),
            "error_details": errors,
            "duration_seconds": duration,
        }

        self.logger.info(
            "scrape_school_complete",
            term=term,
            school_code=school_code,
            courses_found=courses_found,
            courses_saved=courses_saved,
            errors=len(errors),
            duration=duration,
        )

        return result

    def _process_course(
        self,
        course_code: str,
        crn: str,
        term: str,
        create_snapshot: bool = True,
    ) -> None:
        """
        Process a single course: fetch details, transform, save, snapshot.

        Args:
            course_code: Course code (e.g., "CIS 1210")
            crn: Course Reference Number
            term: Term code
            create_snapshot: Whether to create enrollment snapshot
        """
        # Fetch detailed course data
        api_details = self.api_client.get_course_details(
            term=term,
            course_code=course_code,
            crn=crn,
        )

        # Transform API data to CourseDict
        course_dict = src.persistence.api_details_to_course_dict(api_details)

        # Save to database
        course = src.persistence.save_course(course_dict)

        # Create enrollment snapshot if requested
        if create_snapshot:
            src.persistence.create_enrollment_snapshot(
                course=course,
                timestamp=datetime.datetime.now(),
            )


# =============================================================================
# Helper Functions
# =============================================================================

def ensure_term_exists(term_code: str) -> src.models.Term:
    """
    Ensure term exists in database, creating if necessary.

    Args:
        term_code: Term code (e.g., "202530")

    Returns:
        Term model instance
    """
    term_name = src.types.format_term_code(term_code)

    term, created = src.models.Term.get_or_create(
        code=term_code,
        defaults={"name": term_name},
    )

    if created:
        logger.info("term_created", code=term_code, name=term_name)

    return term
