#!/usr/bin/env python3
"""
Convenience script for running Black formatter on the project.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=False):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        return result
    except subprocess.SubprocessError as e:
        print(f"Error running command '{cmd}': {e}")
        sys.exit(1)


def check_formatting():
    """Check if files need formatting."""
    print("🔍 Checking code formatting with Black...")
    result = run_command("uv run black --check --diff .")

    if result.returncode == 0:
        print("✅ All files are properly formatted!")
        return True
    else:
        print(
            "❌ Some files need formatting. Run 'python scripts/format.py --fix' to fix them."
        )
        return False


def format_code():
    """Format all Python files with Black."""
    print("🎨 Formatting code with Black...")
    result = run_command("uv run black .")

    if result.returncode == 0:
        print("✅ Code formatting complete!")
        return True
    else:
        print("❌ Formatting failed!")
        return False


def show_help():
    """Show help message."""
    help_text = """
Black Formatter Utility

Usage:
    python scripts/format.py [--check|--fix|--help]

Options:
    --check     Check if files need formatting (default)
    --fix       Format all Python files
    --help      Show this help message

Examples:
    python scripts/format.py              # Check formatting
    python scripts/format.py --check      # Check formatting
    python scripts/format.py --fix        # Format all files
    """
    print(help_text.strip())


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if not args or "--check" in args:
        success = check_formatting()
        sys.exit(0 if success else 1)
    elif "--fix" in args:
        success = format_code()
        sys.exit(0 if success else 1)
    elif "--help" in args or "-h" in args:
        show_help()
        sys.exit(0)
    else:
        print(f"Unknown argument: {args[0]}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
