"""
CLI/crobat_cli.py

Entry point for the crobat command-line tool.

Usage
-----
    # Run with config.ini defaults:
    python CLI/crobat_cli.py

    # Override any parameter:
    python CLI/crobat_cli.py --pair BTC-USD --duration 30 --range 10 --sides bid,ask --filetype csv

    # Prompt for each parameter (shows current default, Enter to accept):
    python CLI/crobat_cli.py --interactive
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crobat.config import recording_defaults
from crobat.recorder import L2Recorder, SnapshotTimeoutError
from crobat.filesave import clear_output_dir

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_VALID_SIDES     = {"bid", "ask", "signed"}
_VALID_FILETYPES = {"csv", "pkl", "xlsx"}


def _parse_csv_list(value: str, valid: set, label: str) -> list[str]:
    """Split a comma-separated string, strip whitespace, and validate each item."""
    items = [s.strip() for s in value.split(",") if s.strip()]
    if not items:
        print(f"Error: at least one {label} is required.", file=sys.stderr)
        sys.exit(2)
    unknown = set(items) - valid
    if unknown:
        print(
            f"Error: unknown {label}: {', '.join(sorted(unknown))}. "
            f"Valid options: {', '.join(sorted(valid))}",
            file=sys.stderr,
        )
        sys.exit(2)
    return items


def _prompt_with_default(prompt: str, default: str) -> str:
    """Prompt the user, showing the current default. Returns default on empty input."""
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw if raw else default


# ---------------------------------------------------------------------------
# Settings object
# ---------------------------------------------------------------------------

class _Settings:
    """Plain container passed to L2_Update."""

    def __init__(self, currency_pair, position_range, recording_duration,
                 sides, filetype, output_dir):
        self.currency_pair      = currency_pair
        self.position_range     = position_range
        self.recording_duration = recording_duration
        self.sides              = sides
        self.filetype           = filetype
        self.output_dir         = output_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crobat_cli.py",
        description=(
            "Connect to Coinbase and record L2 order book data.\n\n"
            "Settings are read from config.ini by default. "
            "Any flag overrides the corresponding config value. "
            "Use --interactive to be prompted for each parameter before the session starts."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pair",        default=None, help="Currency pair, e.g. XRP-USD")
    parser.add_argument("--duration",    default=None, type=int,
                        help="Recording duration in seconds")
    parser.add_argument("--range",       default=None, type=int, dest="position_range",
                        help="Order book depth (number of price levels per side)")
    parser.add_argument("--sides",       default=None,
                        help="Comma-separated sides to record: bid,ask,signed")
    parser.add_argument("--filetype",    default=None,
                        help="Comma-separated output formats: csv,pkl,xlsx")
    parser.add_argument("--output-dir",  default="runs", dest="output_dir",
                        help="Directory where output files are written (default: runs)")
    parser.add_argument("--clear-runs",  action="store_true", default=False,
                        dest="clear_runs",
                        help="Delete all existing files in the output directory before recording")
    parser.add_argument("--interactive", action="store_true", default=False,
                        help="Prompt for each parameter (Enter to accept the shown default)")
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    defaults = recording_defaults()

    # Resolve each parameter: CLI flag > config.ini default
    d_pair     = args.pair          or defaults.get("currency_pair",      "XRP-USD")
    d_duration = args.duration      or defaults.get("recording_duration", 10)
    d_range    = args.position_range or defaults.get("position_range",    5)
    d_sides    = args.sides         or ",".join(defaults.get("sides",    ["bid", "ask", "signed"]))
    d_filetype = args.filetype      or ",".join(defaults.get("filetype", ["csv"]))
    output_dir = args.output_dir

    if args.interactive:
        print("Press Enter to accept the value shown in brackets.\n")
        d_pair     = _prompt_with_default("Currency pair",             d_pair)
        d_duration = _prompt_with_default("Recording duration (secs)", str(d_duration))
        d_range    = _prompt_with_default("Position range (depth)",    str(d_range))
        d_sides    = _prompt_with_default("Sides (bid,ask,signed)",    d_sides)
        d_filetype = _prompt_with_default("File types (csv,pkl,xlsx)", d_filetype)
        output_dir = _prompt_with_default("Output directory",          output_dir)

    # Validate and coerce types
    try:
        d_duration = int(d_duration)
        if d_duration <= 0:
            raise ValueError
    except ValueError:
        print("Error: --duration must be a positive integer.", file=sys.stderr)
        sys.exit(2)

    try:
        d_range = int(d_range)
        if d_range <= 0:
            raise ValueError
    except ValueError:
        print("Error: --range must be a positive integer.", file=sys.stderr)
        sys.exit(2)

    sides_list    = _parse_csv_list(d_sides,    _VALID_SIDES,     "--sides")
    filetype_list = _parse_csv_list(d_filetype, _VALID_FILETYPES, "--filetype")

    settings = _Settings(
        currency_pair      = d_pair,
        position_range     = d_range,
        recording_duration = d_duration,
        sides              = sides_list,
        filetype           = filetype_list,
        output_dir         = output_dir,
    )

    print(f"\nRecording session")
    print(f"  Pair:      {settings.currency_pair}")
    print(f"  Duration:  {settings.recording_duration}s")
    print(f"  Depth:     {settings.position_range} levels")
    print(f"  Sides:     {', '.join(settings.sides)}")
    print(f"  Output:    {', '.join(settings.filetype)}  ->  {output_dir}\n")

    if args.clear_runs:
        deleted = clear_output_dir(output_dir)
        print(f"  Cleared {deleted} file(s) from {output_dir}\n")

    try:
        recorder = L2Recorder(settings)
        recorder.start()
    except SnapshotTimeoutError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
