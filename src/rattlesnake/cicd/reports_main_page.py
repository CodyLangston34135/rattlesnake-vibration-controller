"""
Generates the main landing page for the code quality reports.
"""

import argparse
import sys
from typing import Final

from rattlesnake.cicd.utilities import get_timestamp

HTML_TEMPLATE: Final[str] = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rattlesnake Code Quality Reports</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f6f8fa;
        }}
        .container {{
            max-width: 800px; margin: 0 auto;
        }}
        .header {{
            background: white; padding: 30px; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 30px; text-align: center;
        }}
        .report-card {{
            background: white; padding: 20px; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;
        }}
        .report-card h3 {{
            margin-top: 0; color: #0366d6;
        }}
        .report-link {{
            background: #0366d6; color: white; padding: 10px 20px;
            text-decoration: none; border-radius: 6px; display: inline-block;
        }}
        .report-link:hover {{
            background: #0256cc;
        }}
        .badge {{
            margin: 10px 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Rattlesnake Code Quality</h1>
            <!--
            <p>Automated code quality analysis for the Rattlesnake vibration controller</p>
            <div class="badge">
                <img src="https://github.com/{github_repo}/raw/dev/badges/pylint.svg" alt="Pylint Score">
            </div>
            <div class="badge">
                <img src="https://github.com/{github_repo}/raw/dev/badges/coverage.svg" alt="Coverage">
            </div>
            -->
        </div>

        <div class="report-card">
            <h3>📊 Pylint Report</h3>
            <p>Static code analysis results showing code quality metrics, style compliance, and potential issues.</p>
            <p><strong>Latest Score:</strong> {pylint_score}/10</p>
            <p><strong>Last Updated:</strong> {formatted_time}</p>
            <a href="./reports/pylint/" class="report-link">Pylint Report</a>
        </div>

        <div class="report-card">
            <h3>🔗 Quick Links</h3>
            <p>
                <a href="https://github.com/{github_repo}" class="report-link">GitHub Repository</a>
                <a href="https://github.com/{github_repo}/actions" class="report-link">GitHub Actions</a>
                <a href="https://github.com/{github_repo}/releases" class="report-link">Releases</a>
            </p>
        </div>
    </div>
</body>
</html>
"""


def get_report_html(github_repo: str, pylint_score: str) -> str:
    """Generates the HTML for the reports landing page.

    Args:
        github_repo: The name of the GitHub repository (e.g., 'user/repo').
        pylint_score: The pylint score.

    Returns:
        The generated HTML content as a string.
    """
    formatted_time: str = get_timestamp()

    return HTML_TEMPLATE.format(
        github_repo=github_repo,
        pylint_score=pylint_score,
        formatted_time=formatted_time,
    )


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


def run_reports_main_page(
    github_repo: str, pylint_score: str, output_file: str
) -> None:
    """
    Main function to create HTML report.

    Args:
        github_repo: The name of the GitHub repository (e.g., 'user/repo').
        pylint_score: The pylint score.
        output_file: Path for the generated HTML report
    """
    html_content: str = get_report_html(
        github_repo=github_repo, pylint_score=pylint_score
    )
    write_report(html_content, output_file)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description="Generate the main reports page.")
    parser.add_argument(
        "--github_repo",
        type=str,
        required=True,
        help="The GitHub repository in the format 'owner/repo-name'.",
    )
    parser.add_argument(
        "--pylint_score",
        type=str,
        required=True,
        help="The Pylint score.",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
        help="The path to the output HTML file.",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args: argparse.Namespace = parse_arguments()
    try:
        run_reports_main_page(
            github_repo=args.github_repo,
            pylint_score=args.pylint_score,
            output_file=args.output_file,
        )
        print(f"✅ GitHub Pages reports main page generated: {args.output_file}")
    except IOError as e:
        print(f"❌ I/O error occurred: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
