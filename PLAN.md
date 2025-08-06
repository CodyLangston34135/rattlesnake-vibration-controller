# Pylint Report Refactoring Plan

This document outlines the plan to refactor and improve the `pylint_report.py` script and its associated tests. Each item in this list represents an atomic change that can be committed individually.

1.  **Refactor for Testability**: Modify `pylint_report.py` to remove calls to `sys.exit()` from all functions except `main()`. Functions should raise exceptions instead, making them easier to test.

2.  **Expand Test Coverage**: Add comprehensive unit tests for `pylint_report.py` to `tests/test_pylint_report.py`. This includes testing file I/O operations (with mocking), report parsing logic, and HTML generation.

3.  **Create Shared Utilities**: Create a new module `src/rattlesnake/cicd/cicd_utils.py` and move the `get_score_color` function into it. Update `pylint_report.py` and `pylint_badge_color.py` to use this shared function.

4.  **Switch to JSON Input**: Modify the `.github/workflows/pylint.yml` workflow to have `pylint` generate a JSON report. This provides a more stable and machine-readable input format.

5.  **Refactor to Parse JSON**: Update `pylint_report.py` to parse the JSON report instead of the raw text output. This will simplify the parsing logic and make it more robust against changes in `pylint`'s text formatting.

6.  **Update Tests for JSON**: Modify the tests in `tests/test_pylint_report.py` to use sample JSON data as fixtures, aligning them with the new JSON-based parsing approach.

7.  **Optimize Regular Expressions**: Pre-compile the regular expressions used in the script to improve performance and code clarity.

8.  **Final Code Cleanup**: Perform a final review of the code, add or update docstrings, and ensure all changes adhere to the project's coding standards.
