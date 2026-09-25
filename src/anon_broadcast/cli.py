"""Status command for the AnonBroadcast download.

The command tells a person that this package is not ready, and names the
next step from the repository description. It does not render video.
"""

from __future__ import annotations

import json
import sys
import textwrap

from anon_broadcast import AUTHOR

PROG = "anon-broadcast"
SUMMARY = "This package is not ready yet."
NEXT_STEP = (
    "When it ships, the next step will be the local renderer named in the "
    "repository description: text in, TTS voice, desk reel, metadata-culled "
    "MP4, and a SHA-256 receipt. That renderer is not in this package."
)
VERSION_LABEL = "unreleased"


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    want_json, version, error = _parse(argv)
    if error == "help":
        _out(_help_text())
        return 0
    if error:
        _fail(want_json, error)
        return 2
    if version:
        _print_version(want_json)
        return 0
    _print_welcome(want_json)
    return 0


def _parse(argv: list[str]) -> tuple[bool, bool, str | None]:
    """Return (want_json, want_version, error). error == 'help' means show help."""
    want_json = False
    want_version = False
    positionals: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            return False, False, "help"
        if arg == "--json":
            want_json = True
        elif arg == "--version":
            want_version = True
        elif arg == "--":
            positionals.extend(argv[i + 1 :])
            break
        elif arg.startswith("-"):
            return want_json, False, f'Unknown option "{arg}".'
        else:
            positionals.append(arg)
        i += 1
    if positionals:
        return want_json, False, f'Unknown command "{positionals[0]}".'
    return want_json, want_version, None


def _print_welcome(want_json: bool) -> None:
    if want_json:
        _out(
            json.dumps(
                {
                    "name": PROG,
                    "author": AUTHOR,
                    "ready": False,
                    "summary": SUMMARY,
                    "next_step": NEXT_STEP,
                    "suggestions": [f"{PROG} --help", f"{PROG} --json"],
                },
                indent=2,
            )
            + "\n"
        )
        return
    _out(
        "\n".join(
            [
                "AnonBroadcast",
                f"Author: {AUTHOR}",
                "",
                SUMMARY,
                "",
                textwrap.fill(NEXT_STEP, width=72),
                "",
                "Next:",
                f"  {PROG} --help",
                f"  {PROG} --json",
                "",
            ]
        )
    )


def _print_version(want_json: bool) -> None:
    if want_json:
        _out(
            json.dumps(
                {"name": PROG, "author": AUTHOR, "version": VERSION_LABEL},
                indent=2,
            )
            + "\n"
        )
        return
    _out(f"{PROG} {VERSION_LABEL}\n")


def _help_text() -> str:
    return "\n".join(
        [
            f"{PROG} — status for this download",
            "",
            "Usage:",
            f"  {PROG} [--json]",
            f"  {PROG} --help",
            "",
            f"Author: {AUTHOR}",
            "",
            "This package is not ready yet. With no arguments, the command",
            "says so and names the next step for when a release ships.",
            "",
            "Options:",
            "  -h, --help    Show this help and exit",
            "  --json        Print the status as JSON",
            '  --version     Print "unreleased" and exit',
            "",
            "Examples:",
            f"  {PROG}",
            f"  {PROG} --json",
            "",
        ]
    )


def _fail(want_json: bool, reason: str) -> None:
    next_step = f"Try: {PROG} --help"
    if want_json:
        _out(
            json.dumps(
                {
                    "name": PROG,
                    "author": AUTHOR,
                    "ready": False,
                    "ok": False,
                    "error": reason,
                    "next": next_step,
                },
                indent=2,
            )
            + "\n"
        )
        return
    _err(f"{reason} {next_step}\n")


def _out(text: str) -> None:
    sys.stdout.write(text)


def _err(text: str) -> None:
    sys.stderr.write(text)
