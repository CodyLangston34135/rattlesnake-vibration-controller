"""
This module is called by the pylint.yml to determine the badge color
based on the pylint score.  The module then appends BADGE_COLOR to the
GITHUB_ENV file so that it can be used later in the workflow.
"""

import os
import sys
from typing import Final

from rattlesnake.cicd.utilities import get_score_color

score = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0

COLOR: Final[str] = get_score_color(str(score))

# Export to GitHub environment
env_path = os.environ.get("GITHUB_ENV")
if env_path:
    with open(env_path, "a", encoding="utf-8") as f:
        f.write(f"BADGE_COLOR={COLOR}\n")
    print(f"    🎨 BADGE_COLOR={COLOR}")
else:
    print("    ⚠️ GITHUB_ENV is not set — failed to export BADGE_COLOR")
