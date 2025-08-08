"""This module extracts key coverage metrics from a coverage output file."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageMetric:
    """Represents coverage metrics for a codebase.

    Attributes:
        lines_valid (int): The total number of valid lines in the codebase.
        lines_covered (int): The number of lines that are covered by tests.
        coverage (float): The coverage percentage, calculated as
            (lines_covered / lines_valid) * 100. Defaults to 0.0.
    """

    lines_valid: int = 0
    lines_covered: int = 0

    @property
    def coverage(self) -> float:
        """
        Calculates the coverage percentage.

        The coverage is calculated as `(lines_covered / lines_valid) * 100`.
        Returns 0.0 if `lines_valid` is zero to prevent division by zero errors.
        """

        return (
            (self.lines_covered / self.lines_valid * 100)
            if self.lines_valid > 0
            else 0.0
        )


def get_coverage_metrics(coverage_file: Path) -> CoverageMetric:
    """
    Gets the lines-valid, lines-covered, and coverage percentage as
    a list strings.
    """

    cm = CoverageMetric()

    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        lines_valid = int(root.attrib["lines-valid"])
        lines_covered = int(root.attrib["lines-covered"])
        _coverage = (
            float(root.attrib["line-rate"]) * 100
        )  # not used because we calculate it ourselves
        cm = CoverageMetric(
            lines_valid=lines_valid,
            lines_covered=lines_covered,
        )  # overwrite default
    except:
        print("No valid attributes found.")

    return cm

    # # Determine badge color based on coverage
    # if coverage >= 90:
    #     color = "brightgreen"
    # elif coverage >= 80:
    #     color = "green"
    # elif coverage >= 70:
    #     color = "yellow"
    # elif coverage >= 60:
    #     color = "orange"
    # else:
    #     color = "red"
