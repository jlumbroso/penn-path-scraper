"""
HTML and JSON parsing functions for Penn course catalog data.

Parses HTML fields from the API responses into structured data.
"""

import datetime
import json
import re
import typing

import bs4

import src.types


def parse_seats(html: str) -> src.types.ParsedSeatsDict:
    """
    Parse enrollment data from HTML seats field.

    Args:
        html: HTML string like:
            '<strong>Maximum Enrollment:</strong> <span class="seats_max">50</span> /
             <strong>Seats Avail:</strong> <span class="seats_avail">2</span>'

    Returns:
        ParsedSeatsDict with max_enrollment, seats_available, and enrolled.
        All fields will be None if seats data is unavailable (e.g., cancelled,
        full, or historical courses).

    Note:
        This function does NOT raise exceptions. Empty HTML returns None values
        rather than fabricating 0 or -1 sentinel values.
    """
    # Handle empty seats HTML (cancelled, full, or historical courses)
    if not html or not html.strip():
        return src.types.ParsedSeatsDict(
            max_enrollment=None,
            seats_available=None,
            enrolled=None,
        )

    soup = bs4.BeautifulSoup(html, "html.parser")

    # Find seats_max and seats_avail spans
    max_span = soup.find("span", class_="seats_max")
    avail_span = soup.find("span", class_="seats_avail")

    if not max_span or not avail_span:
        raise ValueError(f"Could not find seats information in HTML: {html}")

    try:
        max_enrollment = int(max_span.get_text().strip())
        seats_available = int(avail_span.get_text().strip())
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Could not parse enrollment numbers: {e}")

    enrolled = max_enrollment - seats_available

    return src.types.ParsedSeatsDict(
        max_enrollment=max_enrollment,
        seats_available=seats_available,
        enrolled=enrolled,
    )


def parse_meeting_html(html: str) -> typing.List[src.types.ParsedMeetingDict]:
    """
    Parse meeting time and location from HTML.

    Args:
        html: HTML string like:
            '<div class="meet">TR 5:15pm-6:44pm
             <span class="meet-room-202530"> in
             <a href="..." target="_blank">TOWN 217</a></span>
             <span class="meet-dates"> (8/26 to 12/8)</span></div>'

    Returns:
        List of ParsedMeetingDict (can be multiple meetings per section)

    Note:
        Returns empty list for TBA or courses with no specific meeting times.
    """
    if not html or not html.strip():
        return []

    soup = bs4.BeautifulSoup(html, "html.parser")
    meetings = []

    # Find all div.meet elements
    meet_divs = soup.find_all("div", class_="meet")

    for meet_div in meet_divs:
        # Get the text content
        text = meet_div.get_text().strip()

        # Skip TBA
        if text == "TBA" or "TBA" in text:
            continue

        # Check for online courses (e.g., "Meets Online 8/25 to 12/7")
        online_pattern = r"Meets\s+Online\s+(\d+/\d+)\s+to\s+(\d+/\d+)"
        online_match = re.search(online_pattern, text)

        if online_match:
            # This is an online course - extract dates
            start_str, end_str = online_match.groups()

            # Parse dates
            current_year = datetime.datetime.now().year
            start_month, start_day = map(int, start_str.split("/"))
            end_month, end_day = map(int, end_str.split("/"))

            # Heuristic: if start month > end month, course spans year boundary
            if start_month > end_month:
                start_year = current_year
                end_year = current_year + 1
            else:
                start_year = current_year
                end_year = current_year

            start_date = f"{start_year}-{start_month:02d}-{start_day:02d}"
            end_date = f"{end_year}-{end_month:02d}-{end_day:02d}"

            # Create meeting dict for online course (no specific days/times)
            meeting: src.types.ParsedMeetingDict = {
                "days": "",  # No specific meeting days
                "start_time": "",  # No specific start time
                "end_time": "",  # No specific end time
                "room_code": "Online",
                "room_url": None,
                "start_date": start_date,
                "end_date": end_date,
            }
            meetings.append(meeting)
            continue

        # Extract day/time pattern (e.g., "TR 5:15pm-6:44pm")
        # Pattern: letters followed by time range
        pattern = r"([MTWRFSU]+)\s+(\d{1,2}):(\d{2})([ap]m)-(\d{1,2}):(\d{2})([ap]m)"
        match = re.search(pattern, text)

        if not match:
            # No valid meeting pattern found
            continue

        days, start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = match.groups()

        # Convert to 24-hour time
        start_hour_int = int(start_hour)
        end_hour_int = int(end_hour)

        if start_ampm == "pm" and start_hour_int != 12:
            start_hour_int += 12
        elif start_ampm == "am" and start_hour_int == 12:
            start_hour_int = 0

        if end_ampm == "pm" and end_hour_int != 12:
            end_hour_int += 12
        elif end_ampm == "am" and end_hour_int == 12:
            end_hour_int = 0

        start_time = f"{start_hour_int:02d}:{start_min}"
        end_time = f"{end_hour_int:02d}:{end_min}"

        # Extract room info
        room_code = None
        room_url = None

        room_span = meet_div.find("span", class_=re.compile(r"meet-room-\d+"))
        if room_span:
            room_link = room_span.find("a")
            if room_link:
                room_code = room_link.get_text().strip()
                room_url = room_link.get("href")

        # Extract dates
        start_date = None
        end_date = None

        dates_span = meet_div.find("span", class_="meet-dates")
        if dates_span:
            dates_text = dates_span.get_text().strip()
            # Pattern: (8/26 to 12/8)
            dates_match = re.search(r"\((\d+/\d+)\s+to\s+(\d+/\d+)\)", dates_text)
            if dates_match:
                start_str, end_str = dates_match.groups()
                # Parse dates - need to infer year from term
                # For now, assume current/next year
                current_year = datetime.datetime.now().year

                start_month, start_day = map(int, start_str.split("/"))
                end_month, end_day = map(int, end_str.split("/"))

                # Heuristic: if start month > end month, course spans year boundary
                if start_month > end_month:
                    start_year = current_year
                    end_year = current_year + 1
                else:
                    start_year = current_year
                    end_year = current_year

                start_date = f"{start_year:04d}-{start_month:02d}-{start_day:02d}"
                end_date = f"{end_year:04d}-{end_month:02d}-{end_day:02d}"

        meetings.append(
            src.types.ParsedMeetingDict(
                days=days,
                start_time=start_time,
                end_time=end_time,
                room_code=room_code,
                room_url=room_url,
                start_date=start_date or "",
                end_date=end_date or "",
            )
        )

    return meetings


def parse_instructor_html(html: str) -> typing.List[src.types.InstructorDict]:
    """
    Parse instructor information from HTML.

    Args:
        html: HTML string like:
            '<div class="instructor-detail">Jeremie Lumbroso</div>'

    Returns:
        List of InstructorDict
    """
    if not html or not html.strip():
        return []

    soup = bs4.BeautifulSoup(html, "html.parser")
    instructors = []

    # Find all instructor-detail divs
    instructor_divs = soup.find_all("div", class_="instructor-detail")

    for div in instructor_divs:
        name = div.get_text().strip()
        if name:
            instructors.append(src.types.InstructorDict(name=name))

    return instructors


def parse_meeting_times(json_str: str) -> typing.List[typing.Dict[str, str]]:
    """
    Parse meetingTimes JSON field.

    Args:
        json_str: JSON string like:
            '[{"meet_day":"1","start_time":"1715","end_time":"1844"}]'

    Returns:
        List of dicts with day, day_abbr, start_time, end_time

    Raises:
        ValueError: If JSON is invalid
    """
    if not json_str or not json_str.strip():
        return []

    try:
        times = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if not isinstance(times, list):
        return []

    result = []
    for time in times:
        day_code = time["meet_day"]
        start_time_raw = time["start_time"]
        end_time_raw = time["end_time"]

        # Convert day code to name
        day_name = src.types.DAY_CODES.get(day_code, "Unknown")
        day_abbr = src.types.DAY_ABBREVIATIONS.get(day_code, "?")

        # Format times (from "1715" to "17:15")
        if len(start_time_raw) == 4:
            start_time = f"{start_time_raw[:2]}:{start_time_raw[2:]}"
        else:
            # Handle 3-digit times (e.g., "900" -> "09:00")
            start_time = f"0{start_time_raw[0]}:{start_time_raw[1:]}"

        if len(end_time_raw) == 4:
            end_time = f"{end_time_raw[:2]}:{end_time_raw[2:]}"
        else:
            end_time = f"0{end_time_raw[0]}:{end_time_raw[1:]}"

        result.append(
            {
                "day": day_name,
                "day_abbr": day_abbr,
                "start_time": start_time,
                "end_time": end_time,
            }
        )

    return result


def parse_linked_crns(crn_str: str) -> typing.List[str]:
    """
    Parse comma-separated CRN string into list.

    Args:
        crn_str: Comma-separated CRNs like "61969,61970" or empty string

    Returns:
        List of CRN strings
    """
    if not crn_str or not crn_str.strip():
        return []

    # Split by comma and strip whitespace
    crns = [crn.strip() for crn in crn_str.split(",")]

    # Filter out empty strings
    return [crn for crn in crns if crn]
