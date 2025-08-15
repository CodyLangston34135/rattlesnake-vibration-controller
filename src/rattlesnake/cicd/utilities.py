#!/usr/bin/env python3
"""
Utilities for CICD processes.
"""

from datetime import datetime
import pytz


def get_score_color(pylint_score: str) -> str:
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
    # The format of the input timestamp
    input_format: str = "%Y%m%d_%H%M%S_%Z"

    # Convert the input string to a datetime object
    utc_datetime: datetime = datetime.strptime(short, input_format)
    # The datetime object is naive, so we make it timezone-aware
    utc_now: datetime = pytz.utc.localize(utc_datetime)

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
