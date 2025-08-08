"""
This module tests the coverage report module.

Example use:
    source .venv/bin/activate
    pytest --cov=src/rattlesnake --cov-report=html --cov-report=xml --cov-report=term-misssing
"""

from pathlib import Path

import pytest

from rattlesnake.cicd.report_coverage import CoverageMetric, get_coverage_metrics


def test_get_coverage_metrics_simple():
    """Tests the coverage metrics calculation on a simple example."""
    cm = CoverageMetric(lines_valid=100, lines_covered=80)

    assert cm.lines_valid == 100
    assert cm.lines_covered == 80
    assert cm.coverage == 80.0


def test_get_coverage_metrics_valid_file():
    """Tests a correct coverage metrics are returns from a valid coverage file."""

    fin = Path(__file__).parent / "files" / "coverage_output_20250807_241800_UTC.xml"
    assert fin.is_file()
    result = get_coverage_metrics(fin)

    cm = CoverageMetric(lines_valid=10499, lines_covered=23)

    assert cm.lines_valid == 10499
    assert cm.lines_covered == 23
    assert cm.coverage == pytest.approx(
        0.2190684827126393, rel=1e-9
    )  # relative tolerance

    assert result.lines_valid == cm.lines_valid
    assert result.lines_covered == cm.lines_covered
    assert result.coverage == cm.coverage

    # Ensure the coverage percentage is calculated correctly
    assert result.coverage == (cm.lines_covered / cm.lines_valid * 100)


def test_get_coverage_metrics_bad_attributes():
    """Tests a correct coverage metrics are returns from an invalid coverage file."""

    fin = Path(__file__).parent / "files" / "coverage_bad_attributes.xml"
    assert fin.is_file()
    result = get_coverage_metrics(fin)

    expected = CoverageMetric(lines_valid=0, lines_covered=0)

    assert result.lines_valid == expected.lines_valid
    assert result.lines_covered == expected.lines_covered
    assert result.coverage == expected.coverage

    # Ensure the coverage percentage is 0.0 when there are no valid lines
    assert result.coverage == 0.0
