#!/usr/bin/env python3
"""Regenerate the marketplace catalogs and the plugin index from plugins/.

    python3 scripts/sync_marketplaces.py            # write the catalogs
    python3 scripts/sync_marketplaces.py --check    # fail if they are stale

The catalogs are committed to the repository because that is what Claude Code
and Codex fetch when a user adds the marketplace; this script keeps them from
drifting away from the plugin manifests.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _marketplace as mp  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if a generated file on disk is stale",
    )
    args = parser.parse_args()

    stale = []
    written = []
    for path, text in mp.rendered_outputs():
        current = None
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                current = handle.read()
        if current == text:
            continue
        if args.check:
            stale.append(mp.relpath(path))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        written.append(mp.relpath(path))

    if args.check:
        if stale:
            print("Generated files are out of date:")
            for path in stale:
                print("  " + path)
            print("\nRun: python3 scripts/sync_marketplaces.py")
            return 1
        print("Generated files are up to date.")
        return 0

    if written:
        for path in written:
            print("wrote " + path)
    else:
        print("Generated files already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
