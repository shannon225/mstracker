"""Local recovery helper. Run with --data-dir PATH user reset USERNAME via CLI internally."""
import argparse
from getpass import getpass
from pathlib import Path

from mstracker.cli import change_user, database_for, default_data_dir


def main():
    parser = argparse.ArgumentParser(description="Reset a named MSTracker account locally; no web recovery URL.")
    parser.add_argument("username")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    args = parser.parse_args()
    password = getpass("New password (12+ characters): ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match.")
    try:
        change_user(database_for(args.data_dir), args.username, "reset", password)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print("Password reset; existing sessions revoked. Disabled accounts remain disabled.")


if __name__ == "__main__":
    main()
