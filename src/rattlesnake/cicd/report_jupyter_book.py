#!/usr/bin/env python3
"""
Jupyter Book Metadata Generator

This module updates the Jupyter Book configuration file (myst.yml) with
CI/CD metadata (timestamp, branch, commit hash).
"""

import argparse
import sys
from rattlesnake.cicd.utilities import extend_timestamp


def generate_footer_md(
    timestamp_ext: str, run_id: str, ref_name: str, github_sha: str, github_repo: str
) -> str:
    """
    Generate a Markdown snippet with CI/CD metadata.

    Args:
        timestamp_ext: Formatted timestamp string
        run_id: GitHub Actions run ID
        ref_name: Git reference name (branch)
        github_sha: GitHub commit SHA
        github_repo: GitHub repository name

    Returns:
        Markdown string formatted for the primary_sidebar_footer block
    """
    # Use 6-space indentation as found in myst.yml for the block content
    indent: str = "      "
    return (
        f"\n"
        f"{indent}---\n"
        f"{indent}**Generated:** {timestamp_ext}\n"
        f"{indent}**Run ID:** [{run_id}](https://github.com/{github_repo}/actions/runs/{run_id})\n"
        f"{indent}**Branch:** [{ref_name}](https://github.com/{github_repo}/tree/{ref_name})\n"
        f"{indent}**Commit:** [{github_sha[:7]}](https://github.com/{github_repo}/commit/{github_sha})\n"
        f"{indent}**Repository:** [{github_repo}](https://github.com/{github_repo})\n"
    )


def update_myst_file(file_path: str, footer_md: str) -> None:
    """
    Append metadata footer to the myst.yml file.

    Args:
        file_path: Path to the myst.yml file
        footer_md: Markdown snippet to append

    Raises:
        FileNotFoundError: If myst.yml is not found
        IOError: If writing to the file fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "primary_sidebar_footer: |" not in content:
            print(f"Warning: 'primary_sidebar_footer: |' not found in {file_path}")
            return

        # Simple append to the end of the file since primary_sidebar_footer is the last part
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(footer_md)

    except FileNotFoundError as e:
        raise FileNotFoundError(f'File not found: "{file_path}"') from e
    except IOError as e:
        raise IOError(f'Error updating file "{file_path}": {e}') from e


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Inject CI/CD metadata into myst.yml",
    )
    parser.add_argument("--myst_file", required=True, help="Path to myst.yml")
    parser.add_argument(
        "--timestamp", required=True, help="UTC timestamp, e.g., 20240101_120000_UTC"
    )
    parser.add_argument("--run_id", required=True, help="GitHub Actions run ID")
    parser.add_argument("--ref_name", required=True, help="Git branch name")
    parser.add_argument("--github_sha", required=True, help="GitHub commit SHA")
    parser.add_argument("--github_repo", required=True, help="GitHub repository name")

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args: argparse.Namespace = parse_arguments()
    try:
        timestamp_ext: str = extend_timestamp(args.timestamp)
        footer_md: str = generate_footer_md(
            timestamp_ext,
            args.run_id,
            args.ref_name,
            args.github_sha,
            args.github_repo,
        )
        update_myst_file(args.myst_file, footer_md)
        print(f"✅ Successfully updated Jupyter Book metadata in {args.myst_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
