#!/usr/bin/env python3
"""
Utilities for CICD processes.
"""

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
