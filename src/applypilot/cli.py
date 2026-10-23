"""Command-line entry point."""

import argparse

from applypilot import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="ApplyPilot Local job search workspace")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
