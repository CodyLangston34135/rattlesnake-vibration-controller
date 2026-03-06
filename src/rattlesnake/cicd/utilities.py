#!/usr/bin/env python3
"""
Utilities for CICD processes.
"""

import re
from datetime import datetime

import pytz


def get_score_color_lint(pylint_score: str) -> str:
    """
    Determine color based on pylint score.

    Args:
        pylint_score: The pylint score as string, e.g., "8.5", "7.0", etc.

    Returns:
        Hex color code for the score, as a string.
    """
    try:
        score_val: float = float(pylint_score)
        if score_val >= 8.0:
            return "brightgreen"
        elif score_val >= 6.0:
            return "yellow"
        elif score_val >= 4.0:
            return "orange"
        else:
            return "red"
    except ValueError:
        return "gray"


def get_score_color_coverage(coverage_score: str) -> str:
    """
    Determines the color based on a pytest coverage score.

    Args:
        coverage_score:  The coverage score as a string, e.g., "92.5"

    Returns:
        The color for the badge as a string.
    """
    try:
        score_val: float = float(coverage_score)
        if score_val >= 90:
            return "brightgreen"
        elif score_val >= 80:
            return "green"
        elif score_val >= 70:
            return "yellow"
        elif score_val >= 60:
            return "orange"
        else:
            return "red"
    except ValueError:
        return "gray"


def get_timestamp() -> str:
    """
    Get formatted timestamp with UTC, EST, and MST times.

    Returns:
        Formatted timestamp string
    """
    # Get the current UTC time
    utc_now: datetime = datetime.now(pytz.utc)

    # Define the time zones
    timezone_est: pytz.BaseTzInfo = pytz.timezone("America/New_York")
    timezone_mst: pytz.BaseTzInfo = pytz.timezone("America/Denver")

    # Convert UTC time to EST and MST
    est_now: datetime = utc_now.astimezone(timezone_est)
    mst_now: datetime = utc_now.astimezone(timezone_mst)

    # Format the output
    df: str = "%Y-%m-%d %H:%M:%S "  # Date format
    utc: str = utc_now.strftime(df + "UTC")
    est: str = est_now.strftime(df + "EST")
    mst: str = mst_now.strftime(df + "MST")

    # Combine the formatted times
    timestamp: str = f"{utc} ({est} / {mst})"

    return timestamp


def extend_timestamp(short: str) -> str:
    """
    Given a timestamp string from CI/CD in the form of
    20250815_211112_UTC, extend the timestamp to include EST and MST times
    and return the extended string, so it look like, for example,
    2025-08-15 21:11:12 UTC (2025-08-15 17:11:12 EST / 2025-08-15 15:11:12 MST)

    Args:
        short: the UTC bash string, for example: 20250815_211112_UTC

    Returns:
        Extended timestamp, for example
        2025-08-15 21:11:12 UTC (2025-08-15 17:11:12 EST / 2025-08-15 15:11:12 MST)
    """
    # Regex pattern to match the required format: YYYYMMDD_HHMMSS_TZ
    # The timezone abbreviation must be 'UTC', 'GMT', or 'Z'
    pattern: re.Pattern = re.compile(r"^(\d{8})_(\d{6})_(UTC|GMT|Z)$")
    match = pattern.match(short)

    if not match:
        raise ValueError(
            f"Invalid timestamp format: '{short}'. "
            f"Expected format is YYYYMMDD_HHMMSS_TZ, where TZ is one of UTC, GMT, or Z."
        )

    # Extract the date and time parts from the regex match
    date_part, time_part, _ = match.groups()

    # Combine the parts into a format that can be parsed by datetime
    datetime_str: str = f"{date_part}_{time_part}_UTC"
    input_format: str = "%Y%m%d_%H%M%S_%Z"

    # Convert the input string to a datetime object
    utc_datetime: datetime = datetime.strptime(datetime_str, input_format)

    # Make the datetime object timezone-aware
    utc_now: datetime = pytz.utc.localize(utc_datetime)

    # Define the time zones
    timezone_est: pytz.BaseTzInfo = pytz.timezone("America/New_York")
    timezone_mst: pytz.BaseTzInfo = pytz.timezone("America/Denver")

    # Convert UTC time to EST and MST
    est_now: datetime = utc_now.astimezone(timezone_est)
    mst_now: datetime = utc_now.astimezone(timezone_mst)

    # Format the output
    df: str = "%Y-%m-%d %H:%M:%S"  # Date format without trailing space
    utc: str = utc_now.strftime(df)
    est: str = est_now.strftime(df)
    mst: str = mst_now.strftime(df)

    # Use timezone abbreviations from the datetime objects
    utc_tz_abbr: str = utc_now.strftime("%Z")
    # est_tz_abbr: str = est_now.strftime("%Z")
    est_tz_abbr: str = "EST"
    # mst_tz_abbr: str = mst_now.strftime("%Z")
    mst_tz_abbr: str = "MST"

    # Combine the formatted times
    timestamp: str = f"{utc} {utc_tz_abbr} ({est} {est_tz_abbr} / {mst} {mst_tz_abbr})"

    return timestamp


def write_report(html_content: str, output_file: str) -> None:
    """
    Write HTML content to file.

    Args:
        html_content: The HTML content to write
        output_file: Path for the output HTML file

    Raises:
        IOError: If the file cannot be written.
    """
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
    except IOError as e:
        raise IOError(f'Error writing output file "{output_file}": {e}') from e
