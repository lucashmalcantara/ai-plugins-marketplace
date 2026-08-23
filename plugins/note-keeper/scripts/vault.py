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


# --- Obsidian ---------------------------------------------------------------
#
# Obsidian is optional: a viewer over the same folder, never a dependency. It
# stores per-vault settings as JSON under .obsidian/ and writes only the keys
# that differ from its defaults, so an untouched app.json is `{}` and merging
# into it is safe.

OBSIDIAN_DIR = ".obsidian"

# Settings that make Obsidian agree with the note format instead of fighting it.
# useMarkdownLinks and newLinkFormat are the load-bearing pair: left at their
# defaults Obsidian writes [[wikilinks]], which the note format forbids.
OBSIDIAN_APP = {
    "attachmentFolderPath": FOLDERS["attachments"],
    "useMarkdownLinks": True,
    "newLinkFormat": "shortest",
    "newFileLocation": "folder",
    "newFileFolderPath": FOLDERS["notes"],
}
# Keeps capture buffers out of search and the graph without hiding the folder.
OBSIDIAN_IGNORE = FOLDERS["sessions"] + "/"
OBSIDIAN_TEMPLATES = {"folder": FOLDERS["templates"]}
TEMPLATES_PLUGIN = "templates"

VAULT_DOCS = ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "LICENSE.md")


def _read_json(path, fallback):
    if not os.path.isfile(path):
        return fallback
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (ValueError, OSError):
        return fallback


def _change(path, key, before, after):
    return {"file": path, "key": key, "from": before, "to": after}


def obsidian_plan(root):
    """Settings Obsidian would need changed, without touching anything."""
    root = os.path.abspath(os.path.expanduser(root))
    changes = []

    app_rel = os.path.join(OBSIDIAN_DIR, "app.json")
    app = _read_json(os.path.join(root, app_rel), {})
    for key, value in OBSIDIAN_APP.items():
        if app.get(key) != value:
            changes.append(_change(app_rel, key, app.get(key), value))
    ignores = app.get("userIgnoreFilters") or []
    if OBSIDIAN_IGNORE not in ignores:
        changes.append(_change(app_rel, "userIgnoreFilters",
                               list(ignores), list(ignores) + [OBSIDIAN_IGNORE]))

    # core-plugins.json is the one file here that is a complete list rather than
    # a set of overrides: writing a fresh one holding only `templates` would
    # read as "every other core plugin is off". Obsidian enables Templates by
    # default anyway, so when the file is absent the right move is to leave it
    # for Obsidian to write.
    plugins_rel = os.path.join(OBSIDIAN_DIR, "core-plugins.json")
    plugins_path = os.path.join(root, plugins_rel)
    if os.path.isfile(plugins_path):
        plugins = _read_json(plugins_path, {})
        # Obsidian used a list of enabled plugin ids before moving to a map;
        # both shapes are still found in the wild.
        if isinstance(plugins, list):
            enabled = TEMPLATES_PLUGIN in plugins
        else:
            enabled = bool(plugins.get(TEMPLATES_PLUGIN))
        if not enabled:
            changes.append(_change(plugins_rel, TEMPLATES_PLUGIN, enabled, True))

    templates_rel = os.path.join(OBSIDIAN_DIR, "templates.json")
    templates = _read_json(os.path.join(root, templates_rel), {})
    for key, value in OBSIDIAN_TEMPLATES.items():
        if templates.get(key) != value:
            changes.append(_change(templates_rel, key, templates.get(key), value))

    return changes


def _write_json(path, data):
    # Key order is preserved rather than sorted: these are the user's files, and
    # reordering thirty plugin entries to change none of them is pure churn in
    # their diff.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def configure_obsidian(root):
    """Apply obsidian_plan(root).

    Only files the plan actually changes are rewritten, and each is merged into
    rather than replaced — an untouched setting keeps its value and its place.
    """
    root = os.path.abspath(os.path.expanduser(root))
    changes = obsidian_plan(root)
    touched = {change["file"] for change in changes}

    app_rel = os.path.join(OBSIDIAN_DIR, "app.json")
    if app_rel in touched:
        app_path = os.path.join(root, app_rel)
        app = _read_json(app_path, {})
        app.update(OBSIDIAN_APP)
        ignores = list(app.get("userIgnoreFilters") or [])
        if OBSIDIAN_IGNORE not in ignores:
            ignores.append(OBSIDIAN_IGNORE)
        app["userIgnoreFilters"] = ignores
        _write_json(app_path, app)

    # The plan only lists this file when it exists and Templates is off, so
    # reaching here can neither author it from scratch nor rewrite it for nothing.
    plugins_rel = os.path.join(OBSIDIAN_DIR, "core-plugins.json")
    if plugins_rel in touched:
        plugins_path = os.path.join(root, plugins_rel)
        plugins = _read_json(plugins_path, {})
        if isinstance(plugins, list):
            if TEMPLATES_PLUGIN not in plugins:
                plugins.append(TEMPLATES_PLUGIN)
        else:
            plugins[TEMPLATES_PLUGIN] = True
        _write_json(plugins_path, plugins)

    templates_rel = os.path.join(OBSIDIAN_DIR, "templates.json")
    if templates_rel in touched:
        templates_path = os.path.join(root, templates_rel)
        templates = _read_json(templates_path, {})
        templates.update(OBSIDIAN_TEMPLATES)
        _write_json(templates_path, templates)

    return changes


def loose_markdown(root):
    """Markdown outside notes/ that a setup run would have to account for.

    Vault docs at the root (README.md and friends) are documentation, not
    notes, so they stay where they are and are not reported.
    """
    root = os.path.abspath(os.path.expanduser(root))
    skip = set(FOLDERS.values())
    found = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(
            name for name in dirs
            if not name.startswith(".") and os.path.join(
                os.path.relpath(current, root), name).lstrip("./") not in skip)
        rel_dir = os.path.relpath(current, root)
        if rel_dir != "." and rel_dir.split(os.sep)[0] in skip:
            continue
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            if rel_dir == "." and name in VAULT_DOCS:
                continue
            found.append(os.path.join(rel_dir, name) if rel_dir != "." else name)
    return found


def inspect_path(path):
    """Classify a folder for setup. Read-only: this never creates anything."""
    path = os.path.abspath(os.path.expanduser(path))
    report = {"path": path, "exists": os.path.isdir(path)}
    if not report["exists"]:
        report.update(empty=True, is_vault=False, configured=False,
                      missing=sorted(FOLDERS.values()), notes=0,
                      loose_markdown=[], is_git=False,
                      obsidian={"present": False, "changes": obsidian_plan(path)})
        return report

    entries = [name for name in os.listdir(path) if name != ".DS_Store"]
    report["empty"] = not entries
    report["is_vault"] = looks_like_vault(path)
    report["configured"] = os.path.isfile(os.path.join(path, CONFIG_FILE))
    report["missing"] = sorted(
        folder for folder in FOLDERS.values()
        if not os.path.isdir(os.path.join(path, folder)))
    notes_dir = os.path.join(path, FOLDERS["notes"])
    report["notes"] = len([
        name for name in os.listdir(notes_dir) if name.endswith(".md")
    ]) if os.path.isdir(notes_dir) else 0
    report["loose_markdown"] = loose_markdown(path)
    report["is_git"] = os.path.isdir(os.path.join(path, ".git"))
    report["obsidian"] = {
        "present": os.path.isdir(os.path.join(path, OBSIDIAN_DIR)),
        "changes": obsidian_plan(path),
    }
    return report


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="start resolution here instead of the working directory")
    sub = parser.add_subparsers(dest="cmd")

    inspect = sub.add_parser("inspect", help="report what is at a path, changing nothing")
    inspect.add_argument("path", nargs="?", default=".")

    init = sub.add_parser("init", help="create the vault layout")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--obsidian", action="store_true",
                      help="also point Obsidian at the layout")
    init.add_argument("--dry-run", action="store_true",
                      help="report what would change, and write nothing")

    obsidian = sub.add_parser("obsidian", help="point Obsidian at an existing layout")
    obsidian.add_argument("path", nargs="?", default=".")
    obsidian.add_argument("--dry-run", action="store_true",
                          help="report what would change, and write nothing")

    args = parser.parse_args(argv)

    if args.cmd == "inspect":
        print(json.dumps(inspect_path(args.path), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "obsidian":
        target = os.path.abspath(os.path.expanduser(args.path))
        changes = obsidian_plan(target) if args.dry_run else configure_obsidian(target)
        print(json.dumps({"root": target, "dry_run": args.dry_run,
                          "obsidian_changes": changes}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "init":
        if args.dry_run:
            report = inspect_path(args.path)
            report["would_create"] = report["missing"] + (
                [] if report["configured"] else [CONFIG_FILE])
            report["dry_run"] = True
            if not args.obsidian:
                report["obsidian"]["changes"] = []
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        root, created = init_vault(args.path)
        payload = describe(root)
        payload["created"] = created
        payload["obsidian_changes"] = configure_obsidian(root) if args.obsidian else []
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
