"""
Gets the coverage percentage from a coverage.xml file and determines the
color for a badge. It then writes the coverage and color to the GitHub
environment file.
"""

import xml.etree.ElementTree as ET
import os
import sys

from rattlesnake.cicd.utilities import get_score_color_coverage


def get_coverage_and_color(coverage_file: str):
    """
    Parses a coverage.xml file to get the coverage percentage and determines
    the badge color.

    Args:
        coverage_file: The path to the coverage.xml file.
    """
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        coverage = float(root.attrib["line-rate"]) * 100  # overwrite with real coverage
    except Exception:
        # yes all exceptions should be caught here
        coverage = 0.0

    print(f"Coverage: {coverage:.1f}%")

    color = get_score_color_coverage(str(coverage))

    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as f:
            f.write(f"COVERAGE={coverage:.1f}\n")
            f.write(f"BADGE_COLOR_COV={color}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_coverage_and_color(sys.argv[1])
    else:
        print("Usage: python coverage_badge_color.py <path_to_coverage.xml>")
        sys.exit(1)
