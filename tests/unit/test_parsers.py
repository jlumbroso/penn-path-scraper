"""
Unit tests for HTML parsing functions.

Tests parsing of enrollment, meeting, and instructor data from HTML fields
returned by the Penn courses API.
"""

import pytest

import src.parsers


class TestParseSeats:
    """Tests for parsing enrollment/seats HTML."""

    def test_parse_seats_with_available(self):
        """Test parsing when seats are available."""
        html = (
            '<strong>Maximum Enrollment:</strong> <span class="seats_max">50</span> / '
            '<strong>Seats Avail:</strong> <span class="seats_avail">2</span>'
        )

        result = src.parsers.parse_seats(html)

        assert result["max_enrollment"] == 50
        assert result["seats_available"] == 2
        assert result["enrolled"] == 48

    def test_parse_seats_full_class(self):
        """Test parsing when class is full."""
        html = (
            '<strong>Maximum Enrollment:</strong> <span class="seats_max">80</span> / '
            '<strong>Seats Avail:</strong> <span class="seats_avail">0</span>'
        )

        result = src.parsers.parse_seats(html)

        assert result["max_enrollment"] == 80
        assert result["seats_available"] == 0
        assert result["enrolled"] == 80

    def test_parse_seats_large_class(self):
        """Test parsing for large enrollment numbers."""
        html = (
            '<strong>Maximum Enrollment:</strong> <span class="seats_max">250</span> / '
            '<strong>Seats Avail:</strong> <span class="seats_avail">15</span>'
        )

        result = src.parsers.parse_seats(html)

        assert result["max_enrollment"] == 250
        assert result["seats_available"] == 15
        assert result["enrolled"] == 235

    def test_parse_seats_empty_string(self):
        """Test parsing empty HTML returns None values."""
        result = src.parsers.parse_seats("")

        assert result["max_enrollment"] is None
        assert result["seats_available"] is None
        assert result["enrolled"] is None

    def test_parse_seats_malformed_html(self):
        """Test parsing malformed HTML."""
        html = "<strong>Maximum Enrollment:</strong> 50"

        with pytest.raises(ValueError):
            src.parsers.parse_seats(html)


class TestParseMeetingHTML:
    """Tests for parsing meeting time and location HTML."""

    def test_parse_meeting_with_room(self):
        """Test parsing meeting with room information."""
        html = (
            '<div class="meet">TR 1:45pm-3:14pm'
            '<span class="meet-room-202530"> in '
            '<a href="https://www.facilities.upenn.edu/maps/locations/walnut-street-3401" '
            'target="_blank">WLNT 401B</a></span>'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
        )

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 1
        meeting = result[0]

        assert meeting["days"] == "TR"
        assert meeting["start_time"] == "13:45"
        assert meeting["end_time"] == "15:14"
        assert meeting["room_code"] == "WLNT 401B"
        assert "walnut-street-3401" in meeting["room_url"]
        assert meeting["start_date"] == "2025-08-26"
        assert meeting["end_date"] == "2025-12-08"

    def test_parse_meeting_towne_building(self):
        """Test parsing meeting in Towne building."""
        html = (
            '<div class="meet">TR 5:15pm-6:44pm'
            '<span class="meet-room-202530"> in '
            '<a href="https://www.facilities.upenn.edu/maps/locations/towne-building" '
            'target="_blank">TOWN 217</a></span>'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
        )

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 1
        meeting = result[0]

        assert meeting["days"] == "TR"
        assert meeting["start_time"] == "17:15"
        assert meeting["end_time"] == "18:44"
        assert meeting["room_code"] == "TOWN 217"

    def test_parse_meeting_friday_recitation(self):
        """Test parsing Friday recitation."""
        html = (
            '<div class="meet">F 10:15am-11:44am'
            '<span class="meet-room-202530"> in '
            '<a href="https://www.facilities.upenn.edu/maps/locations/moore-school-building" '
            'target="_blank">MOOR 216</a></span>'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
        )

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 1
        meeting = result[0]

        assert meeting["days"] == "F"
        assert meeting["start_time"] == "10:15"
        assert meeting["end_time"] == "11:44"
        assert meeting["room_code"] == "MOOR 216"

    def test_parse_meeting_mwf(self):
        """Test parsing MWF meeting pattern."""
        html = (
            '<div class="meet">MWF 9:00am-9:59am'
            '<span class="meet-room-202530"> in '
            '<a href="https://www.facilities.upenn.edu/maps/locations/levine-hall" '
            'target="_blank">LEVI 101</a></span>'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
        )

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 1
        meeting = result[0]

        assert meeting["days"] == "MWF"
        assert meeting["start_time"] == "09:00"
        assert meeting["end_time"] == "09:59"

    def test_parse_meeting_tba(self):
        """Test parsing TBA (no specific meeting time)."""
        html = '<div class="meet">TBA</div>'

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 0  # TBA means no specific meetings

    def test_parse_meeting_multiple_meetings(self):
        """Test parsing multiple meeting times."""
        html = (
            '<div class="meet">TR 1:45pm-3:14pm'
            '<span class="meet-room-202530"> in '
            '<a href="https://www.facilities.upenn.edu/maps/locations/towne-building" '
            'target="_blank">TOWN 217</a></span>'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
            '<div class="meet">F 10:00am-11:59am'
            '<span class="meet-room-202530"> in '
            '<a href="https://www.facilities.upenn.edu/maps/locations/moore-school-building" '
            'target="_blank">MOOR 100</a></span>'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
        )

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 2
        assert result[0]["days"] == "TR"
        assert result[1]["days"] == "F"

    def test_parse_meeting_no_room(self):
        """Test parsing meeting without room information."""
        html = (
            '<div class="meet">TR 1:45pm-3:14pm'
            '<span class="meet-dates"> (8/26 to 12/8)</span></div>'
        )

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 1
        meeting = result[0]

        assert meeting["days"] == "TR"
        assert meeting["room_code"] is None
        assert meeting["room_url"] is None

    def test_parse_meeting_online_course(self):
        """Test parsing online course with 'Meets Online' pattern."""
        html = '<div class="meet">Meets Online 8/25 to 12/7</div>'

        result = src.parsers.parse_meeting_html(html)

        assert len(result) == 1
        meeting = result[0]

        # Online courses have no specific days/times
        assert meeting["days"] == ""
        assert meeting["start_time"] == ""
        assert meeting["end_time"] == ""

        # But they should have "Online" as room_code and dates
        assert meeting["room_code"] == "Online"
        assert meeting["room_url"] is None
        assert "2025-08-25" in meeting["start_date"] or "2024-08-25" in meeting["start_date"]
        assert "2025-12-07" in meeting["end_date"] or "2024-12-07" in meeting["end_date"]


class TestParseInstructorHTML:
    """Tests for parsing instructor information from HTML."""

    def test_parse_single_instructor(self):
        """Test parsing single instructor."""
        html = '<div class="instructor-detail">Jeremie Lumbroso</div>'

        result = src.parsers.parse_instructor_html(html)

        assert len(result) == 1
        assert result[0]["name"] == "Jeremie Lumbroso"

    def test_parse_instructor_with_initial(self):
        """Test parsing instructor with abbreviated first name."""
        html = '<div class="instructor-detail">J. Lumbroso</div>'

        result = src.parsers.parse_instructor_html(html)

        assert len(result) == 1
        assert result[0]["name"] == "J. Lumbroso"

    def test_parse_instructor_team(self):
        """Test parsing 'Team' instructor."""
        html = '<div class="instructor-detail">Team</div>'

        result = src.parsers.parse_instructor_html(html)

        assert len(result) == 1
        assert result[0]["name"] == "Team"

    def test_parse_instructor_staff(self):
        """Test parsing 'Staff' instructor."""
        html = '<div class="instructor-detail">Staff</div>'

        result = src.parsers.parse_instructor_html(html)

        assert len(result) == 1
        assert result[0]["name"] == "Staff"

    def test_parse_multiple_instructors(self):
        """Test parsing multiple instructors."""
        html = (
            '<div class="instructor-detail">John Smith</div>'
            '<div class="instructor-detail">Jane Doe</div>'
        )

        result = src.parsers.parse_instructor_html(html)

        assert len(result) == 2
        assert result[0]["name"] == "John Smith"
        assert result[1]["name"] == "Jane Doe"

    def test_parse_instructor_empty(self):
        """Test parsing empty instructor HTML."""
        html = ""

        result = src.parsers.parse_instructor_html(html)

        assert len(result) == 0


class TestParseMeetingTimes:
    """Tests for parsing meetingTimes JSON field."""

    def test_parse_meeting_times_tr(self):
        """Test parsing Tuesday/Thursday meeting times."""
        json_str = '[{"meet_day":"1","start_time":"1345","end_time":"1514"},{"meet_day":"3","start_time":"1345","end_time":"1514"}]'

        result = src.parsers.parse_meeting_times(json_str)

        assert len(result) == 2
        assert result[0]["day"] == "Monday"
        assert result[0]["day_abbr"] == "M"
        assert result[0]["start_time"] == "13:45"
        assert result[0]["end_time"] == "15:14"

        assert result[1]["day"] == "Wednesday"
        assert result[1]["day_abbr"] == "W"

    def test_parse_meeting_times_friday(self):
        """Test parsing Friday meeting time."""
        json_str = '[{"meet_day":"4","start_time":"1015","end_time":"1144"}]'

        result = src.parsers.parse_meeting_times(json_str)

        assert len(result) == 1
        assert result[0]["day"] == "Thursday"
        assert result[0]["day_abbr"] == "R"
        assert result[0]["start_time"] == "10:15"
        assert result[0]["end_time"] == "11:44"

    def test_parse_meeting_times_empty(self):
        """Test parsing empty meeting times."""
        json_str = '[]'

        result = src.parsers.parse_meeting_times(json_str)

        assert len(result) == 0

    def test_parse_meeting_times_invalid_json(self):
        """Test parsing invalid JSON."""
        json_str = 'not valid json'

        with pytest.raises(ValueError):
            src.parsers.parse_meeting_times(json_str)


class TestParseLinkedCRNs:
    """Tests for parsing linked CRNs."""

    def test_parse_single_linked_crn(self):
        """Test parsing single linked CRN."""
        crn_str = "61970"

        result = src.parsers.parse_linked_crns(crn_str)

        assert result == ["61970"]

    def test_parse_multiple_linked_crns(self):
        """Test parsing multiple linked CRNs."""
        crn_str = "61969,61970,61975"

        result = src.parsers.parse_linked_crns(crn_str)

        assert result == ["61969", "61970", "61975"]

    def test_parse_empty_linked_crns(self):
        """Test parsing empty linked CRNs."""
        crn_str = ""

        result = src.parsers.parse_linked_crns(crn_str)

        assert result == []

    def test_parse_linked_crns_with_spaces(self):
        """Test parsing linked CRNs with spaces."""
        crn_str = "61969, 61970, 61975"

        result = src.parsers.parse_linked_crns(crn_str)

        assert result == ["61969", "61970", "61975"]
