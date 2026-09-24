"""Command line for AnonBroadcast.

Author: Aziel Eliab.
"""

from __future__ import annotations

import argparse
import sys

from anonbroadcast import VERSION
from anonbroadcast.render import RenderError, render_mp4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anon-broadcast",
        description="Render a local communique MP4 from text.",
    )
    parser.add_argument("--version", action="store_true", help="Print the package version and exit.")
    sub = parser.add_subparsers(dest="command")
    render = sub.add_parser("render", help="Write an MP4 and a SHA-256 receipt.")
    render.add_argument("-o", "--out", default="communique.mp4", help="Output MP4 path.")
    source = render.add_mutually_exclusive_group()
    source.add_argument("-t", "--text", help="Note text.")
    source.add_argument("-f", "--file", help="Read the note from a UTF-8 file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(VERSION)
        return 0
    if args.command != "render":
        parser.print_help(sys.stderr)
        return 2
    if args.text is not None:
        text = args.text
    elif args.file is not None:
        try:
            text = open(args.file, encoding="utf-8").read()
        except OSError as exc:
            print(f"Could not read the note file. {exc.strerror or exc}", file=sys.stderr)
            return 2
    else:
        if sys.stdin.isatty():
            print("Pass --text, --file, or pipe the note on stdin.", file=sys.stderr)
            return 2
        text = sys.stdin.read()
    try:
        receipt = render_mp4(text, args.out)
    except RenderError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    print(f"Wrote {args.out}")
    print(f"SHA-256 {receipt['sha256']}")
    return 0
