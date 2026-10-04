import sys
from pathlib import Path


# -------------------------------------------------
# PROJECT ROOT CONFIGURATION
# -------------------------------------------------

# Get the directory containing this conftest.py file.
PROJECT_ROOT = Path(__file__).resolve().parent


# -------------------------------------------------
# PYTHON IMPORT PATH
# -------------------------------------------------

# Make sure the project root is available to Python
# when pytest imports test modules.
#
# This allows imports such as:
#
# from healing.healing_engine import heal_locator

project_root_string = str(PROJECT_ROOT)

if project_root_string not in sys.path:
    sys.path.insert(0, project_root_string)