"""Version information for pdfdiff-turbo API."""
import os
from pathlib import Path

# Try to read version from VERSION file in project root
VERSION_FILE = Path(__file__).parent.parent.parent / "VERSION"

try:
    with open(VERSION_FILE, "r") as f:
        __version__ = f.read().strip()
except FileNotFoundError:
    __version__ = "0.0.0"

# Expose version
API_VERSION = __version__
