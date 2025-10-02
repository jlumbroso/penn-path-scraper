"""
Unit tests for Penn Courses API client.

Tests API interactions with mocked HTTP responses.
"""

import json
import pathlib
import typing
import unittest.mock

import pytest

import src.api_client
import src.types


# Load fixtures
FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


def load_fixture(filename: str) -> typing.Dict[str, typing.Any]:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


@pytest.fixture
def api_client() -> src.api_client.PennCoursesAPIClient:
    """Create API client instance for testing."""
    return src.api_client.PennCoursesAPIClient()


@pytest.fixture
def search_response() -> typing.Dict[str, typing.Any]:
    """Load search API response fixture."""
    return load_fixture("api_search_response.json")


@pytest.fixture
def details_response() -> typing.Dict[str, typing.Any]:
    """Load details API response fixture."""
    return load_fixture("api_details_response.json")


class TestPennCoursesAPIClient:
    """Tests for PennCoursesAPIClient class."""

    def test_client_initialization(self, api_client):
        """Test that client initializes properly."""
        assert api_client.base_url == "https://courses.upenn.edu/api/"
        assert api_client.timeout == 30

    def test_client_custom_timeout(self):
        """Test client with custom timeout."""
        client = src.api_client.PennCoursesAPIClient(timeout=60)
        assert client.timeout == 60

    @unittest.mock.patch("requests.post")
    def test_search_by_school(self, mock_post, api_client, search_response):
        """Test searching courses by school."""
        mock_post.return_value.json.return_value = search_response
        mock_post.return_value.raise_for_status = lambda: None

        result = api_client.search_by_school(term="202530", school_code="E")

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert "page=fose" in call_args[0][0]
        assert "route=search" in call_args[0][0]

        # Verify request body
        request_body = call_args[1]["json"]
        assert request_body["other"]["srcdb"] == "202530"
        assert request_body["criteria"][0]["field"] == "coll"
        assert request_body["criteria"][0]["value"] == "E"

        # Verify response parsing
        assert result["srcdb"] == "202530"
        assert result["count"] == 3
        assert len(result["results"]) == 3

    @unittest.mock.patch("requests.post")
    def test_search_by_keyword(self, mock_post, api_client, search_response):
        """Test searching courses by keyword."""
        mock_post.return_value.json.return_value = search_response
        mock_post.return_value.raise_for_status = lambda: None

        result = api_client.search_by_keyword(term="202530", keyword="lumbroso")

        # Verify request body
        call_args = mock_post.call_args
        request_body = call_args[1]["json"]
        assert request_body["criteria"][0]["field"] == "keyword"
        assert request_body["criteria"][0]["value"] == "lumbroso"

        # Verify response
        assert result["count"] == 3

    @unittest.mock.patch("requests.post")
    def test_get_course_details(self, mock_post, api_client, details_response):
        """Test getting detailed course information."""
        mock_post.return_value.json.return_value = details_response
        mock_post.return_value.raise_for_status = lambda: None

        result = api_client.get_course_details(
            term="202530",
            course_code="NETS 2130",
            crn="80595"
        )

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert "route=details" in call_args[0][0]

        # Verify request body
        request_body = call_args[1]["json"]
        assert request_body["srcdb"] == "202530"
        assert request_body["key"] == "crn:80595"
        assert request_body["group"] == "code:NETS 2130"

        # Verify response
        assert result["crn"] == "80595"
        assert result["code"] == "NETS 2130"
        assert "seats" in result

    @unittest.mock.patch("requests.post")
    def test_get_all_schools(self, mock_post, api_client, search_response):
        """Test getting courses for all schools in a term."""
        mock_post.return_value.json.return_value = search_response
        mock_post.return_value.raise_for_status = lambda: None

        results = list(api_client.get_all_schools(term="202530"))

        # Should be called once for each school (12 schools)
        assert mock_post.call_count == 12

        # Each result should be a (school_code, response) tuple
        assert len(results) == 12
        assert all(isinstance(r[0], str) for r in results)
        assert all(isinstance(r[1], dict) for r in results)

    @unittest.mock.patch("requests.post")
    def test_api_error_handling(self, mock_post, api_client):
        """Test handling of API errors."""
        # Simulate HTTP error
        mock_post.return_value.raise_for_status.side_effect = Exception("API Error")

        with pytest.raises(src.api_client.APIError) as exc_info:
            api_client.search_by_school(term="202530", school_code="E")

        assert "API Error" in str(exc_info.value)

    @unittest.mock.patch("requests.post")
    def test_json_decode_error(self, mock_post, api_client):
        """Test handling of invalid JSON responses."""
        mock_post.return_value.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_post.return_value.raise_for_status = lambda: None

        with pytest.raises(src.api_client.APIError) as exc_info:
            api_client.search_by_school(term="202530", school_code="E")

        assert "JSON" in str(exc_info.value)

    @unittest.mock.patch("requests.post")
    def test_timeout_error(self, mock_post, api_client):
        """Test handling of timeout errors."""
        import requests
        mock_post.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(src.api_client.APIError) as exc_info:
            api_client.search_by_school(term="202530", school_code="E")

        assert "timeout" in str(exc_info.value).lower()

    def test_rate_limiting(self, api_client):
        """Test that rate limiting is applied between requests."""
        import time

        # Mock successful requests
        with unittest.mock.patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"srcdb": "202530", "count": 0, "results": []}
            mock_post.return_value.raise_for_status = lambda: None

            # Set small rate limit delay for testing
            api_client.rate_limit_delay = 0.1

            start = time.time()
            api_client.search_by_school(term="202530", school_code="E")
            api_client.search_by_school(term="202530", school_code="W")
            elapsed = time.time() - start

            # Should take at least rate_limit_delay seconds
            assert elapsed >= 0.1

    @unittest.mock.patch("requests.post")
    def test_user_agent_rotation(self, mock_post, api_client):
        """Test that user agent is set in requests."""
        mock_post.return_value.json.return_value = {"srcdb": "202530", "count": 0, "results": []}
        mock_post.return_value.raise_for_status = lambda: None

        api_client.search_by_school(term="202530", school_code="E")

        # Verify user agent was set
        call_headers = mock_post.call_args[1]["headers"]
        assert "User-Agent" in call_headers
        assert len(call_headers["User-Agent"]) > 0


class TestAPIHelpers:
    """Tests for API helper functions."""

    def test_build_search_request_body(self):
        """Test building search request body."""
        body = src.api_client.build_search_request_body(
            term="202530",
            criteria={"field": "coll", "value": "E"}
        )

        assert body["other"]["srcdb"] == "202530"
        assert len(body["criteria"]) == 1
        assert body["criteria"][0]["field"] == "coll"
        assert body["criteria"][0]["value"] == "E"

    def test_build_details_request_body(self):
        """Test building details request body."""
        body = src.api_client.build_details_request_body(
            term="202530",
            course_code="CIS 1210",
            crn="12345"
        )

        assert body["srcdb"] == "202530"
        assert body["group"] == "code:CIS 1210"
        assert body["key"] == "crn:12345"
        assert body["userWithRolesStr"] == "!!!!!!"

    def test_get_current_term(self):
        """Test getting current term code."""
        import datetime

        # Mock current date
        with unittest.mock.patch("src.api_client.datetime") as mock_datetime:
            # Test Fall semester (August-December)
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 10, 15)
            term = src.api_client.get_current_term()
            assert term == "202530"  # Fall 2025

            # Test Spring semester (January-May)
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 3, 15)
            term = src.api_client.get_current_term()
            assert term == "202510"  # Spring 2025

            # Test Summer semester (June-July)
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 6, 15)
            term = src.api_client.get_current_term()
            assert term == "202520"  # Summer 2025

    def test_get_next_term(self):
        """Test getting next term code."""
        # After Fall comes Spring
        assert src.api_client.get_next_term("202530") == "202610"

        # After Spring comes Summer
        assert src.api_client.get_next_term("202510") == "202520"

        # After Summer comes Fall
        assert src.api_client.get_next_term("202520") == "202530"
