#!/usr/bin/env python3
"""Resolve the note-keeper vault and its settings.

    python3 vault.py                 # print the resolved vault as JSON
    python3 vault.py --root <path>   # resolve from an explicit starting point
    python3 vault.py init <path>     # create a new vault at <path>

Every note-keeper skill starts by running this so it knows where the vault is
before touching a file. Stdlib only, Python 3.9+.
"""

import argparse
import json
import os
import sys

CONFIG_FILE = ".note-keeper.json"
ENV_VAR = "NOTE_KEEPER_VAULT"

# The vault layout is a convention, not a setting: skills refer to these folders
# by name, so they are the same in every vault.
FOLDERS = {
    "notes": "notes",
    "attachments": "_attachments",
    "templates": "_templates",
    "sessions": "_sessions",
    "index_dir": ".index",
}
INDEX_FILE = os.path.join(FOLDERS["index_dir"], "INDEX.md")
CACHE_FILE = os.path.join(FOLDERS["index_dir"], "cache.json")

# Only the prose settings are configurable — they affect what gets written, not
# where it lives. The defaults match the vault this plugin was extracted from.
DEFAULTS = {
    "language": "pt-BR",
    "timezone": "-03:00",
}

BASE_TEMPLATE = "## Contexto\n\n## Detalhes\n\n## Referências\n"


class VaultNotFound(Exception):
    pass


def read_config(root):
    """Read <root>/.note-keeper.json, tolerating its absence."""
    path = os.path.join(root, CONFIG_FILE)
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def looks_like_vault(path):
    """A directory is a vault if it is marked as one, or holds notes/."""
    return (os.path.isfile(os.path.join(path, CONFIG_FILE))
            or os.path.isdir(os.path.join(path, FOLDERS["notes"])))


def _ancestors(start):
    current = os.path.abspath(start)
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            return
        current = parent


def find_vault(start=None, env=None):
    """Resolve the vault root.

    In order: $NOTE_KEEPER_VAULT, then the nearest ancestor of `start` marked
    with .note-keeper.json, then the nearest ancestor holding a notes/ folder.
    """
    env = os.environ if env is None else env
    override = (env.get(ENV_VAR) or "").strip()
    if override:
        root = os.path.abspath(os.path.expanduser(override))
        if not os.path.isdir(root):
            raise VaultNotFound(
                "{} points at {!r}, which is not a directory".format(ENV_VAR, root))
        return root

    start = os.getcwd() if start is None else start
    # A marked vault wins over a bare notes/ folder anywhere up the tree, so a
    # repository that happens to contain notes/ never shadows the real vault.
    for probe in (
        lambda path: os.path.isfile(os.path.join(path, CONFIG_FILE)),
        lambda path: os.path.isdir(os.path.join(path, FOLDERS["notes"])),
    ):
        for candidate in _ancestors(start):
            if probe(candidate):
                return candidate

    raise VaultNotFound(
        "no vault found from {!r}: set {} to the vault path, or run "
        "`python3 vault.py init <path>` to create one".format(
            os.path.abspath(start), ENV_VAR))


def describe(root):
    """Everything a skill needs to know about a vault, as plain data."""
    config = read_config(root)
    info = {"root": root}
    for key, folder in FOLDERS.items():
        info[key] = os.path.join(root, folder)
    info["index_file"] = os.path.join(root, INDEX_FILE)
    info["cache_file"] = os.path.join(root, CACHE_FILE)
    for key, default in DEFAULTS.items():
        value = config.get(key)
        info[key] = value if isinstance(value, str) and value.strip() else default
    info["configured"] = os.path.isfile(os.path.join(root, CONFIG_FILE))
    info["missing"] = sorted(
        folder for folder in FOLDERS.values()
        if not os.path.isdir(os.path.join(root, folder)))
    return info


def init_vault(root):
    """Create the vault layout at `root`, leaving anything already there alone."""
    root = os.path.abspath(os.path.expanduser(root))
    created = []
    for folder in FOLDERS.values():
        path = os.path.join(root, folder)
        if not os.path.isdir(path):
            os.makedirs(path)
            created.append(folder)
    config_path = os.path.join(root, CONFIG_FILE)
    if not os.path.isfile(config_path):
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(DEFAULTS, indent=2, ensure_ascii=False) + "\n")
        created.append(CONFIG_FILE)
    template_path = os.path.join(root, FOLDERS["templates"], "Base.md")
    if not os.path.isfile(template_path):
        with open(template_path, "w", encoding="utf-8") as handle:
            handle.write(BASE_TEMPLATE)
        created.append(os.path.join(FOLDERS["templates"], "Base.md"))
    return root, created


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="start resolution here instead of the working directory")
    sub = parser.add_subparsers(dest="cmd")
    init = sub.add_parser("init", help="create a new vault")
    init.add_argument("path", nargs="?", default=".")
    args = parser.parse_args(argv)

    if args.cmd == "init":
        root, created = init_vault(args.path)
        payload = describe(root)
        payload["created"] = created
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    try:
        root = find_vault(args.root)
    except VaultNotFound as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    print(json.dumps(describe(root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
