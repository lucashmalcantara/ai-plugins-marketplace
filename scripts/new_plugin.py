#!/usr/bin/env python3
"""Scaffold a new plugin from templates/plugin-template.

    python3 scripts/new_plugin.py my-plugin \
        --display-name "My Plugin" \
        --description "One sentence on what it does."

Creates plugins/<name>/ with both host manifests, one starter skill, docs, and
publication metadata, then regenerates the catalogs.
"""

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _marketplace as mp  # noqa: E402

TEMPLATE_DIR = os.path.join(mp.REPO_ROOT, "templates", "plugin-template")
TEXT_SUFFIXES = (".json", ".md")


def titleize(name):
    return " ".join(part.capitalize() for part in name.split("-"))


def substitute(text, replacements):
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="plugin name in kebab-case")
    parser.add_argument("--display-name", help="human-readable name (default: derived from name)")
    parser.add_argument("--description", default="TODO: one sentence on what this plugin does.")
    parser.add_argument("--skill", help="name of the starter skill (default: the plugin name)")
    parser.add_argument("--category", default="Productivity", help="marketplace category")
    parser.add_argument(
        "--targets",
        default=",".join(mp.TARGETS),
        help="comma-separated hosts to publish to (default: both)",
    )
    args = parser.parse_args()

    name = args.name
    if not mp.KEBAB_RE.match(name):
        print("error: plugin name must be kebab-case, got {!r}".format(name))
        return 1

    targets = [target.strip() for target in args.targets.split(",") if target.strip()]
    for target in targets:
        if target not in mp.TARGETS:
            print("error: unknown target {!r}; expected one of {}".format(
                target, ", ".join(mp.TARGETS)))
            return 1

    destination = os.path.join(mp.PLUGINS_DIR, name)
    if os.path.exists(destination):
        print("error: plugins/{} already exists".format(name))
        return 1

    config = mp.load_config()
    owner = config.get("owner") or {}
    skill_name = args.skill or name
    replacements = {
        "PLUGIN_NAME": name,
        "PLUGIN_DISPLAY_NAME": args.display_name or titleize(name),
        "PLUGIN_DESCRIPTION": args.description,
        "AUTHOR_NAME": owner.get("name", ""),
        "AUTHOR_URL": owner.get("url", ""),
        "REPO_URL": config.get("repository", ""),
        "example-skill": skill_name,
    }

    shutil.copytree(TEMPLATE_DIR, destination)
    example_skill = os.path.join(destination, "skills", "example-skill")
    if skill_name != "example-skill" and os.path.isdir(example_skill):
        os.rename(example_skill, os.path.join(destination, "skills", skill_name))

    for root, _dirs, files in os.walk(destination):
        for filename in files:
            if not filename.endswith(TEXT_SUFFIXES):
                continue
            path = os.path.join(root, filename)
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(substitute(text, replacements))

    publish_path = os.path.join(destination, mp.PUBLISH_FILE)
    publish = mp.read_json(publish_path)
    publish["targets"] = targets
    publish["category"] = args.category
    publish["tags"] = []
    if mp.TARGET_CLAUDE not in targets:
        publish.pop("claude", None)
    if mp.TARGET_CODEX not in targets:
        publish.pop("codex", None)
    with open(publish_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(publish, indent=2, ensure_ascii=False) + "\n")

    if mp.TARGET_CLAUDE not in targets:
        shutil.rmtree(os.path.join(destination, ".claude-plugin"))
    if mp.TARGET_CODEX not in targets:
        shutil.rmtree(os.path.join(destination, ".codex-plugin"))
        shutil.rmtree(os.path.join(destination, "assets"), ignore_errors=True)

    for path, text in mp.rendered_outputs():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    print("Created plugins/{}".format(name))
    print("Next:")
    print("  1. write plugins/{}/skills/{}/SKILL.md".format(name, skill_name))
    print("  2. fill in the manifests and README.md")
    print("  3. python3 scripts/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
