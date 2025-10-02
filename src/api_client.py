"""
API client for Penn Courses catalog (courses.upenn.edu).

Provides a clean interface for querying the undocumented API.
"""

import datetime
import time
import typing

import fake_useragent
import requests
import structlog

import src.types


logger = structlog.get_logger(__name__)


class APIError(Exception):
    """Exception raised for API-related errors."""

    pass


class PennCoursesAPIClient:
    """
    Client for Penn Courses API.

    Handles HTTP requests, rate limiting, error handling, and user agent rotation.
    """

    def __init__(
        self,
        base_url: str = "https://courses.upenn.edu/api/",
        timeout: int = 30,
        rate_limit_delay: float = 0.5,
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL for API
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests in seconds (for politeness)
        """
        self.base_url = base_url
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay

        # User agent rotation for better success rate
        self.ua = fake_useragent.UserAgent()

        # Track last request time for rate limiting
        self._last_request_time: typing.Optional[float] = None

        logger.info(
            "api_client_initialized",
            base_url=base_url,
            timeout=timeout,
            rate_limit_delay=rate_limit_delay,
        )

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limit."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                logger.debug("rate_limit_wait", sleep_time=sleep_time)
                time.sleep(sleep_time)

    def _make_request(
        self,
        endpoint: str,
        json_body: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        """
        Make a POST request to the API.

        Args:
            endpoint: API endpoint (query string)
            json_body: Request body

        Returns:
            JSON response as dict

        Raises:
            APIError: If request fails
        """
        self._wait_for_rate_limit()

        url = f"{self.base_url}?{endpoint}"

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.ua.random,
        }

        logger.debug(
            "api_request",
            url=url,
            body_size=len(str(json_body)),
        )

        try:
            response = requests.post(
                url,
                json=json_body,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self._last_request_time = time.time()

            data = response.json()

            logger.debug(
                "api_response",
                status_code=response.status_code,
                response_size=len(response.text),
            )

            return data

        except requests.Timeout as e:
            logger.error("api_timeout", error=str(e))
            raise APIError(f"Request timeout: {e}")

        except requests.RequestException as e:
            logger.error("api_request_error", error=str(e))
            raise APIError(f"API request failed: {e}")

        except ValueError as e:
            # JSON decode error
            logger.error("json_decode_error", error=str(e))
            raise APIError(f"Invalid JSON response: {e}")

        except Exception as e:
            # Catch any other errors and wrap them
            logger.error("api_unknown_error", error=str(e))
            raise APIError(f"API Error: {e}")

    def search_by_school(
        self,
        term: str,
        school_code: str,
    ) -> src.types.APISearchResponse:
        """
        Search for courses by school/college.

        Args:
            term: Term code (e.g., "202530")
            school_code: School code (e.g., "E" for Engineering)

        Returns:
            APISearchResponse with results

        Raises:
            APIError: If request fails
        """
        endpoint = f"page=fose&route=search&coll={school_code}"
        body = build_search_request_body(
            term=term,
            criteria={"field": "coll", "value": school_code},
        )

        logger.info(
            "search_by_school",
            term=term,
            school_code=school_code,
        )

        response = self._make_request(endpoint, body)

        # Type cast to APISearchResponse
        return typing.cast(src.types.APISearchResponse, response)

    def search_by_keyword(
        self,
        term: str,
        keyword: str,
    ) -> src.types.APISearchResponse:
        """
        Search for courses by keyword (instructor, course name, etc.).

        Args:
            term: Term code
            keyword: Search keyword

        Returns:
            APISearchResponse with results

        Raises:
            APIError: If request fails
        """
        endpoint = f"page=fose&route=search&keyword={keyword}"
        body = build_search_request_body(
            term=term,
            criteria={"field": "keyword", "value": keyword},
        )

        logger.info(
            "search_by_keyword",
            term=term,
            keyword=keyword,
        )

        response = self._make_request(endpoint, body)

        return typing.cast(src.types.APISearchResponse, response)

    def get_course_details(
        self,
        term: str,
        course_code: str,
        crn: str,
        matched_crns: typing.Optional[str] = None,
    ) -> src.types.APICourseDetails:
        """
        Get detailed information for a specific course section.

        Args:
            term: Term code
            course_code: Course code (e.g., "CIS 1210")
            crn: Course Reference Number
            matched_crns: Comma-separated list of related CRNs (optional)

        Returns:
            APICourseDetails with full course information

        Raises:
            APIError: If request fails
        """
        endpoint = "page=fose&route=details"
        body = build_details_request_body(
            term=term,
            course_code=course_code,
            crn=crn,
            matched_crns=matched_crns,
        )

        logger.info(
            "get_course_details",
            term=term,
            course_code=course_code,
            crn=crn,
        )

        response = self._make_request(endpoint, body)

        return typing.cast(src.types.APICourseDetails, response)

    def get_all_schools(
        self,
        term: str,
    ) -> typing.Iterator[typing.Tuple[str, src.types.APISearchResponse]]:
        """
        Get courses for all schools in a term.

        Args:
            term: Term code

        Yields:
            Tuples of (school_code, APISearchResponse)

        Raises:
            APIError: If any request fails
        """
        logger.info("get_all_schools", term=term, school_count=len(src.types.SCHOOLS))

        for school in src.types.SCHOOLS:
            school_code = school["code"]

            logger.debug(
                "fetching_school",
                term=term,
                school_code=school_code,
                school_name=school["name"],
            )

            response = self.search_by_school(term=term, school_code=school_code)

            yield (school_code, response)


# =============================================================================
# Helper Functions
# =============================================================================


def build_search_request_body(
    term: str,
    criteria: typing.Dict[str, str],
) -> typing.Dict[str, typing.Any]:
    """
    Build request body for search endpoint.

    Args:
        term: Term code
        criteria: Search criteria dict with "field" and "value"

    Returns:
        Request body dict
    """
    return {
        "other": {
            "srcdb": term,
        },
        "criteria": [criteria],
    }


def build_details_request_body(
    term: str,
    course_code: str,
    crn: str,
    matched_crns: typing.Optional[str] = None,
) -> typing.Dict[str, typing.Any]:
    """
    Build request body for details endpoint.

    Args:
        term: Term code
        course_code: Course code (e.g., "CIS 1210")
        crn: Course Reference Number
        matched_crns: Comma-separated list of related CRNs

    Returns:
        Request body dict
    """
    return {
        "group": f"code:{course_code}",
        "key": f"crn:{crn}",
        "srcdb": term,
        "matched": matched_crns or f"crn:{crn}",
        "userWithRolesStr": "!!!!!!",
    }


def get_current_term() -> str:
    """
    Get the current academic term code based on today's date.

    Returns:
        Term code (e.g., "202530" for Fall 2025)
    """
    now = datetime.datetime.now()
    year = now.year
    month = now.month

    # Determine semester
    # Spring: January-May (months 1-5)
    # Summer: June-July (months 6-7)
    # Fall: August-December (months 8-12)

    if 1 <= month <= 5:
        semester = "10"  # Spring
    elif 6 <= month <= 7:
        semester = "20"  # Summer
    else:  # 8-12
        semester = "30"  # Fall

    return f"{year}{semester}"


def get_next_term(term: str) -> str:
    """
    Get the next term code after the given term.

    Args:
        term: Current term code (e.g., "202530")

    Returns:
        Next term code

    Examples:
        >>> get_next_term("202530")  # Fall 2025
        "202610"  # Spring 2026

        >>> get_next_term("202510")  # Spring 2025
        "202520"  # Summer 2025
    """
    year = int(term[:4])
    semester = term[4:]

    if semester == "30":  # Fall -> Spring of next year
        return f"{year + 1}10"
    elif semester == "10":  # Spring -> Summer
        return f"{year}20"
    elif semester == "20":  # Summer -> Fall
        return f"{year}30"
    else:
        raise ValueError(f"Invalid semester code: {semester}")


def get_active_terms() -> typing.List[str]:
    """
    Get currently active terms (current and next).

    This is useful for scraping advance registration data.

    Returns:
        List of term codes [current_term, next_term]
    """
    current = get_current_term()
    next_term = get_next_term(current)

    return [current, next_term]
