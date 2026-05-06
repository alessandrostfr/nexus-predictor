"""Small local helper to verify the backend environment.

Run it with the virtual environment active:

    python scripts/check_environment.py
"""

import sys


def main() -> None:
    """Print a simple Python version check."""
    print("Python executable:", sys.executable)
    print("Python version:", sys.version)
    print("Environment check completed.")


if __name__ == "__main__":
    main()
