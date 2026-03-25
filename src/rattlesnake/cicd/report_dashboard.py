"""
Generates the root index.html dashboard for GitHub Pages.
"""

import argparse
import os


def generate_dashboard_html(github_repo: str) -> str:
    """
    Generate the HTML content for the dashboard.

    Args:
        github_repo: GitHub repository name (owner/repo)

    Returns:
        HTML string
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rattlesnake Vibration Controller - Reports</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; background-color: #f6f8fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ background-color: #f1f1f1; margin: 10px 0; padding: 15px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }}
        .badge {{ font-weight: bold; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }}
        .badge-main {{ background-color: #0366d6; color: white; }}
        .badge-dev {{ background-color: #f66a0a; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Rattlesnake Vibration Controller - CI/CD Hub</h1>
        <p>Access the latest documentation and quality reports for both the stable and development versions.</p>
        
        <h2>🚀 Released (<a href="https://github.com/{github_repo}/tree/main?tab=readme-ov-file">Main Branch</a>)</h2>
        <ul>
            <li><a href="main/book/jupyter/index.html">User's Manual (work in progress)</a> <span class="badge badge-main">stable</span></li>
            <li><a href="main/reports/lint/index.html">Lint Report (work in progress)</a> <img src="main/badges/lint.svg" alt="Lint Score" style="vertical-align: middle; margin-left: 10px;"></li>
            <li><a href="main/reports/coverage/index.html">Coverage Report (work in progress)</a> <img src="main/badges/coverage.svg" alt="Coverage" style="vertical-align: middle; margin-left: 10px;"></li>
        </ul>

        <h2>🛠️ Development (<a href="https://github.com/{github_repo}/tree/dev?tab=readme-ov-file">Dev Branch</a>)</h2>
        <ul>
            <li><a href="dev/book/jupyter/index.html">User's Manual</a> <span class="badge badge-dev">latest</span></li>
            <li><a href="dev/reports/lint/index.html">Lint Report</a> <img src="dev/badges/lint.svg" alt="Lint Score" style="vertical-align: middle; margin-left: 10px;"></li>
            <li><a href="dev/reports/coverage/index.html">Coverage Report</a> <img src="dev/badges/coverage.svg" alt="Coverage" style="vertical-align: middle; margin-left: 10px;"></li>
        </ul>
    </div>
</body>
</html>"""


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate CI/CD dashboard index.html")
    parser.add_argument(
        "--github_repo", required=True, help="GitHub repository (owner/repo)"
    )
    parser.add_argument("--output_file", required=True, help="Output HTML file path")
    args = parser.parse_args()

    html = generate_dashboard_html(args.github_repo)

    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard generated: {args.output_file}")


if __name__ == "__main__":
    main()
