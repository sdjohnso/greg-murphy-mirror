#!/usr/bin/env python3 -u
"""
Orchestrator script for updating the Greg Murphy congressional data mirror.

Usage:
    python update_mirror.py full     # Full update (all data)
    python update_mirror.py daily    # Daily update (recent votes only)
"""

import sys
sys.stdout.reconfigure(line_buffering=True)

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent


def run_script(script_name: str) -> bool:
    """
    Run a Python script and return success status.

    Args:
        script_name: Name of script in scripts/ directory

    Returns:
        True if script succeeded, False otherwise
    """
    script_path = SCRIPTS_DIR / script_name
    print(f"\n{'='*60}")
    print(f"Running {script_name}")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "-u", str(script_path)],
            cwd=PROJECT_ROOT,
            check=True,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {script_name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to run {script_name}: {e}")
        return False


def update_last_updated(success: bool, update_type: str):
    """
    Update LAST_UPDATED.md with run status.

    Args:
        success: Whether the update succeeded
        update_type: Type of update (full or daily)
    """
    status = "Success" if success else "Failed"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# Last Updated

| Field | Value |
|-------|-------|
| **Timestamp** | {timestamp} |
| **Update Type** | {update_type} |
| **Status** | {status} |

## Update History

Updates run daily at 6 AM EST via GitHub Actions.

For manual updates, run:
```bash
python scripts/update_mirror.py full
```
"""

    path = PROJECT_ROOT / "LAST_UPDATED.md"
    with open(path, "w") as f:
        f.write(content)
    print(f"\nUpdated {path}")


def full_update() -> bool:
    """
    Run a full update: all pull scripts, metrics, and docs.

    Returns:
        True if all scripts succeeded
    """
    print("\n" + "=" * 60)
    print("FULL UPDATE")
    print("=" * 60)

    scripts = [
        "pull_member.py",
        "pull_votes.py",
        "pull_legislation.py",
        "generate_metrics.py",
        "generate_docs.py",
    ]

    success = True
    for script in scripts:
        if not run_script(script):
            success = False
            print(f"\nWARNING: {script} failed, continuing with remaining scripts...")

    return success


def daily_update() -> bool:
    """
    Run a daily update: votes, metrics, and docs.

    Skips member profile and legislation (rarely change).

    Returns:
        True if all scripts succeeded
    """
    print("\n" + "=" * 60)
    print("DAILY UPDATE")
    print("=" * 60)

    scripts = [
        "pull_votes.py",
        "generate_metrics.py",
        "generate_docs.py",
    ]

    success = True
    for script in scripts:
        if not run_script(script):
            success = False
            print(f"\nWARNING: {script} failed, continuing with remaining scripts...")

    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update the Greg Murphy congressional data mirror"
    )
    parser.add_argument(
        "update_type",
        choices=["full", "daily"],
        help="Type of update to run"
    )
    args = parser.parse_args()

    start_time = datetime.now()
    print(f"Starting {args.update_type} update at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if args.update_type == "full":
        success = full_update()
    else:
        success = daily_update()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("UPDATE COMPLETE")
    print("=" * 60)
    print(f"Status: {'SUCCESS' if success else 'FAILED'}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    update_last_updated(success, args.update_type)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
