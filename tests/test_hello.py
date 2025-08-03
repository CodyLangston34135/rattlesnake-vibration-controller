"""
This is a minimum working example of a test framework.

Example use:
    source .venv/bin/activate
    pytest tests/test_hello.py -v
    pytest tests/test_hello.py::test_greet -v
    pytest --cov=src/rattlesnake --cov-report=xml --cov-report=html --cov-report=term-missing
"""

# import pytest

from rattlesnake import hello


def test_greet():
    """Test the gret function."""
    assert hello.greet("World") == "Hello, World!"
