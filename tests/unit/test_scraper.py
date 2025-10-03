"""
Unit tests for course scraper orchestrator.

Tests coordination of API client and persistence layer with mocked dependencies.
"""

import datetime
import typing

import pytest

import src.api_client
import src.models
import src.scraper
import src.types


@pytest.fixture
def mock_api_client(mocker):
    """Create mocked API client."""
    client = mocker.Mock(spec=src.api_client.PennCoursesAPIClient)
    return client


@pytest.fixture
def mock_db(mocker):
    """Mock database operations."""
    # Mock the persistence functions
    mocker.patch("src.persistence.initialize_database")
    mocker.patch("src.persistence.save_course")
    mocker.patch("src.persistence.create_enrollment_snapshot")
    mocker.patch("src.models.Term.get_or_create")
    mocker.patch("src.models.School.get_or_create")
    mocker.patch("src.models.ScrapeLog.create")
    return mocker


class TestCourseScraper:
    """Tests for CourseScraper class."""

    def test_scraper_initialization(self, mock_api_client):
        """Test scraper initializes with API client and database path."""
        scraper = src.scraper.CourseScraper(
            api_client=mock_api_client,
            db_path=":memory:"
        )

        assert scraper.api_client == mock_api_client
        assert scraper.db_path == ":memory:"

    def test_scrape_school_calls_api_and_persists(self, mock_api_client, mock_db, mocker):
        """Test scraping a single school fetches courses and saves them."""
        # Mock API search response
        mock_api_client.search_by_school.return_value = {
            "srcdb": "202530",
            "count": 2,
            "results": [
                {"code": "CIS 1210", "crn": "12345"},
                {"code": "CIS 1200", "crn": "12346"},
            ]
        }

        # Mock API details response
        mock_api_client.get_course_details.return_value = {
            "code": "CIS 1210",
            "crn": "12345",
            "srcdb": "202530",
            "section": "001",
            "title": "Data Structures",
            "schedule_type": "Lecture",
            "status_new": "Active",
            "isCancelled": "",
            "seats": '<strong>Maximum Enrollment:</strong> <span class="seats_max">100</span> / <strong>Seats Avail:</strong> <span class="seats_avail">10</span>',
            "meeting_html": "",
            "instructordetail_html": "",
            "linked_crns": "",
            "hours_html": "1",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "description": "",
        }

        # Mock term existence
        mock_term = mocker.Mock()
        mock_term.code = "202530"
        mocker.patch("src.models.Term.get_or_create", return_value=(mock_term, False))

        scraper = src.scraper.CourseScraper(
            api_client=mock_api_client,
            db_path=":memory:"
        )

        result = scraper.scrape_school(term="202530", school_code="E")

        # Verify API was called
        mock_api_client.search_by_school.assert_called_once_with(
            term="202530",
            school_code="E"
        )

        # Verify we got details for courses
        assert mock_api_client.get_course_details.call_count == 2

        # Verify result
        assert result["school_code"] == "E"
        assert result["term"] == "202530"
        assert result["courses_found"] == 2
        assert result["courses_saved"] >= 0

    def test_scrape_school_handles_api_errors(self, mock_api_client, mock_db, mocker):
        """Test scraping continues on API errors."""
        # Mock API search response with 2 courses
        mock_api_client.search_by_school.return_value = {
            "srcdb": "202530",
            "count": 2,
            "results": [
                {"code": "CIS 1210", "crn": "12345"},
                {"code": "CIS 1200", "crn": "12346"},
            ]
        }

        # First course succeeds, second fails
        mock_api_client.get_course_details.side_effect = [
            {
                "code": "CIS 1210",
                "crn": "12345",
                "srcdb": "202530",
                "section": "001",
                "title": "Data Structures",
                "schedule_type": "Lecture",
                "status_new": "Active",
                "isCancelled": "",
                "seats": '<strong>Maximum Enrollment:</strong> <span class="seats_max">100</span> / <strong>Seats Avail:</strong> <span class="seats_avail">10</span>',
                "meeting_html": "",
                "instructordetail_html": "",
                "linked_crns": "",
                "hours_html": "1",
                "start_date": "2025-08-26",
                "end_date": "2025-12-08",
                "description": "",
            },
            src.api_client.APIError("Network error")
        ]

        mock_term = mocker.Mock()
        mock_term.code = "202530"
        mocker.patch("src.models.Term.get_or_create", return_value=(mock_term, False))

        scraper = src.scraper.CourseScraper(
            api_client=mock_api_client,
            db_path=":memory:"
        )

        result = scraper.scrape_school(term="202530", school_code="E")

        # Should process both, but only one succeeds
        assert result["courses_found"] == 2
        assert result["errors_count"] == 1

    def test_scrape_term_scrapes_all_schools(self, mock_api_client, mock_db, mocker):
        """Test scraping a term processes all schools."""
        # Mock search returning empty results for all schools
        mock_api_client.search_by_school.return_value = {
            "srcdb": "202530",
            "count": 0,
            "results": []
        }

        mock_term = mocker.Mock()
        mock_term.code = "202530"
        mocker.patch("src.models.Term.get_or_create", return_value=(mock_term, False))

        scraper = src.scraper.CourseScraper(
            api_client=mock_api_client,
            db_path=":memory:"
        )

        result = scraper.scrape_term(term="202530")

        # Should call API for all 12 schools
        assert mock_api_client.search_by_school.call_count == 12

        # Verify result
        assert result["term"] == "202530"
        assert len(result["school_results"]) == 12

    def test_scrape_term_with_specific_schools(self, mock_api_client, mock_db, mocker):
        """Test scraping only specific schools."""
        mock_api_client.search_by_school.return_value = {
            "srcdb": "202530",
            "count": 0,
            "results": []
        }

        mock_term = mocker.Mock()
        mock_term.code = "202530"
        mocker.patch("src.models.Term.get_or_create", return_value=(mock_term, False))

        scraper = src.scraper.CourseScraper(
            api_client=mock_api_client,
            db_path=":memory:"
        )

        result = scraper.scrape_term(term="202530", schools=["E", "W"])

        # Should only call API for specified schools
        assert mock_api_client.search_by_school.call_count == 2
        assert len(result["school_results"]) == 2

    def test_create_enrollment_snapshots_optional(self, mock_api_client, mock_db, mocker):
        """Test enrollment snapshot creation can be disabled."""
        mock_api_client.search_by_school.return_value = {
            "srcdb": "202530",
            "count": 1,
            "results": [{"code": "CIS 1210", "crn": "12345"}]
        }

        mock_api_client.get_course_details.return_value = {
            "code": "CIS 1210",
            "crn": "12345",
            "srcdb": "202530",
            "section": "001",
            "title": "Data Structures",
            "schedule_type": "Lecture",
            "status_new": "Active",
            "isCancelled": "",
            "seats": '<strong>Maximum Enrollment:</strong> <span class="seats_max">100</span>',
            "meeting_html": "",
            "instructordetail_html": "",
            "linked_crns": "",
            "hours_html": "1",
            "start_date": "2025-08-26",
            "end_date": "2025-12-08",
            "description": "",
        }

        mock_term = mocker.Mock()
        mock_term.code = "202530"
        mocker.patch("src.models.Term.get_or_create", return_value=(mock_term, False))

        # Mock snapshot creation
        mock_create_snapshot = mocker.patch("src.persistence.create_enrollment_snapshot")

        scraper = src.scraper.CourseScraper(
            api_client=mock_api_client,
            db_path=":memory:"
        )

        # Scrape without snapshots
        scraper.scrape_school(
            term="202530",
            school_code="E",
            create_snapshots=False
        )

        # Should not create snapshots
        mock_create_snapshot.assert_not_called()


class TestScraperHelpers:
    """Tests for scraper helper functions."""

    def test_ensure_term_exists_creates_term(self, mocker):
        """Test ensuring term exists creates it if needed."""
        mock_term = mocker.Mock()
        mock_term.code = "202530"

        mock_get_or_create = mocker.patch(
            "src.models.Term.get_or_create",
            return_value=(mock_term, True)
        )

        result = src.scraper.ensure_term_exists("202530")

        mock_get_or_create.assert_called_once()
        assert result.code == "202530"
