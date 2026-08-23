#!/usr/bin/env python3
"""Validate the marketplace and every plugin in it.

    python3 scripts/validate.py

Checks the rules that the Claude Code and Codex loaders enforce (or warn about)
before a user ever installs anything: manifest shape, name and version
agreement across the two hosts, referenced paths that exist, SKILL.md
frontmatter, and whether the generated catalogs are current.

Exits 1 when there is at least one error. Warnings never fail the run.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _marketplace as mp  # noqa: E402

# Marketplace names Anthropic reserves for official sources.
RESERVED_MARKETPLACE_NAMES = {
    "claude-code-marketplace", "claude-code-plugins", "claude-plugins-official",
    "claude-plugins-community", "claude-community", "anthropic-marketplace",
    "anthropic-plugins", "agent-skills", "anthropic-agent-skills",
    "knowledge-work-plugins", "life-sciences", "claude-for-legal",
    "claude-for-financial-services", "financial-services-plugins",
    "first-party-plugins", "healthcare", "org", "org-provisioned", "unknown",
}

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")

# Manifest fields whose values are paths inside the plugin, per host.
PATH_FIELDS = {
    mp.TARGET_CLAUDE: ("skills", "commands", "agents", "workflows", "outputStyles"),
    mp.TARGET_CODEX: ("skills",),
}
FILE_PATH_FIELDS = ("hooks", "mcpServers", "lspServers", "apps")

errors = []
warnings = []


def error(where, message):
    errors.append("{}: {}".format(where, message))


def warn(where, message):
    warnings.append("{}: {}".format(where, message))


def as_paths(value):
    """Manifest path fields accept a string or a list of strings."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def parse_frontmatter(text):
    """Minimal YAML frontmatter reader: flat `key: value` pairs only."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return None
    data = {}
    key = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        match = FRONTMATTER_KEY_RE.match(line)
        if match and not line.startswith((" ", "\t")):
            key = match.group(1)
            data[key] = match.group(2).strip().strip('"').strip("'")
        elif key:  # folded continuation line
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


def check_config(config):
    where = "marketplace.config.json"
    name = config.get("name")
    if not name:
        error(where, "`name` is required")
    else:
        if not mp.KEBAB_RE.match(name):
            error(where, "`name` must be kebab-case, got {!r}".format(name))
        if name.lower() in RESERVED_MARKETPLACE_NAMES:
            error(where, "`name` {!r} is reserved and will be rejected".format(name))
    owner = config.get("owner") or {}
    if not owner.get("name"):
        error(where, "`owner.name` is required by the Claude Code marketplace schema")
    if not config.get("description"):
        warn(where, "no `description`; users see it when browsing the marketplace")


def check_publish_metadata(plugin):
    where = "plugins/{}/{}".format(plugin.name, mp.PUBLISH_FILE)
    if not plugin.publish:
        warn(where, "missing; defaults to both targets, category Productivity")
        return
    for target in plugin.targets:
        if target not in mp.TARGETS:
            error(where, "unknown target {!r}; expected one of {}".format(
                target, ", ".join(mp.TARGETS)))
    if not plugin.publish.get("category"):
        warn(where, "no `category`; Codex entries fall back to Productivity")
    policy = ((plugin.publish.get("codex") or {}).get("policy") or {})
    installation = policy.get("installation")
    if installation and installation not in mp.INSTALLATION_POLICIES:
        error(where, "codex.policy.installation must be one of {}".format(
            ", ".join(mp.INSTALLATION_POLICIES)))
    authentication = policy.get("authentication")
    if authentication and authentication not in mp.AUTHENTICATION_POLICIES:
        error(where, "codex.policy.authentication must be one of {}".format(
            ", ".join(mp.AUTHENTICATION_POLICIES)))


def check_manifest(plugin, target, manifest_rel):
    manifest = plugin.manifest_for(target)
    where = "plugins/{}/{}".format(plugin.name, manifest_rel)
    if manifest is None:
        error("plugins/" + plugin.name,
              "declares target {!r} but {} is missing".format(target, manifest_rel))
        return
    if manifest.get("name") != plugin.name:
        error(where, "`name` is {!r} but the directory is {!r}; they must match".format(
            manifest.get("name"), plugin.name))
    if not manifest.get("description"):
        warn(where, "no `description`")
    version = manifest.get("version")
    if not version:
        warn(where, "no `version`; the resolved commit SHA is used instead")
    elif not mp.SEMVER_RE.match(str(version)):
        error(where, "`version` {!r} is not semver".format(version))

    for field in PATH_FIELDS[target] + FILE_PATH_FIELDS:
        value = manifest.get(field)
        if value is None or isinstance(value, dict):
            continue  # inline configuration, nothing to resolve on disk
        for rel in as_paths(value):
            if not rel.startswith("./") and rel not in (".", "./"):
                error(where, "`{}` path {!r} must start with ./".format(field, rel))
                continue
            if ".." in rel.split("/"):
                error(where, "`{}` path {!r} escapes the plugin root".format(field, rel))
                continue
            if not os.path.exists(os.path.join(plugin.path, rel)):
                error(where, "`{}` points at {!r}, which does not exist".format(field, rel))


def check_version_agreement(plugin):
    if plugin.claude is None or plugin.codex is None:
        return
    claude_version = plugin.claude.get("version")
    codex_version = plugin.codex.get("version")
    if claude_version != codex_version:
        error("plugins/" + plugin.name,
              "version differs between hosts: Claude {!r} vs Codex {!r}".format(
                  claude_version, codex_version))


def check_skills(plugin):
    skills_dir = os.path.join(plugin.path, "skills")
    if not os.path.isdir(skills_dir):
        return
    for name in sorted(os.listdir(skills_dir)):
        skill_dir = os.path.join(skills_dir, name)
        if name.startswith(".") or not os.path.isdir(skill_dir):
            continue
        where = "plugins/{}/skills/{}".format(plugin.name, name)
        skill_file = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_file):
            error(where, "skill directory has no SKILL.md")
            continue
        with open(skill_file, "r", encoding="utf-8") as handle:
            text = handle.read()
        front = parse_frontmatter(text)
        if front is None:
            error(where + "/SKILL.md", "missing or unterminated YAML frontmatter")
            continue
        skill_name = front.get("name")
        if not skill_name:
            error(where + "/SKILL.md", "frontmatter has no `name`")
        else:
            if skill_name != name:
                error(where + "/SKILL.md",
                      "`name` is {!r} but the directory is {!r}".format(skill_name, name))
            if not SKILL_NAME_RE.match(skill_name) or len(skill_name) > 64:
                error(where + "/SKILL.md",
                      "`name` must be lowercase alphanumeric and hyphens, max 64 chars")
        description = front.get("description")
        if not description:
            error(where + "/SKILL.md",
                  "frontmatter has no `description`; it is the only text the agent sees "
                  "before loading the skill")
        elif len(description) > 1024:
            error(where + "/SKILL.md", "`description` exceeds 1024 characters")


def check_codex_interface(plugin):
    if plugin.codex is None:
        return
    interface = plugin.codex.get("interface") or {}
    where = "plugins/{}/{}".format(plugin.name, mp.CODEX_MANIFEST)
    if not interface:
        warn(where, "no `interface` block; Codex falls back to bare manifest fields")
        return
    prompts = interface.get("defaultPrompt") or []
    if len(prompts) > 3:
        warn(where, "`interface.defaultPrompt` has {} entries; Codex uses the first 3".format(
            len(prompts)))
    for prompt in prompts:
        if len(prompt) > 128:
            warn(where, "a `defaultPrompt` entry is over 128 chars and will be truncated")
    for field in ("composerIcon", "logo", "logoDark"):
        rel = interface.get(field)
        if rel and not os.path.exists(os.path.join(plugin.path, rel)):
            error(where, "`interface.{}` points at {!r}, which does not exist".format(field, rel))
    for shot in interface.get("screenshots") or []:
        if not shot.startswith("./assets/") or not shot.endswith(".png"):
            error(where, "screenshots must be PNG files under ./assets/, got {!r}".format(shot))
        elif not os.path.exists(os.path.join(plugin.path, shot)):
            error(where, "screenshot {!r} does not exist".format(shot))


def check_docs(plugin):
    if not os.path.isfile(os.path.join(plugin.path, "README.md")):
        warn("plugins/" + plugin.name, "no README.md")


def check_generated_files(config, plugins):
    for path, text in mp.rendered_outputs(config, plugins):
        current = None
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                current = handle.read()
        if current != text:
            error(mp.relpath(path),
                  "out of date; run python3 scripts/sync_marketplaces.py")


def main():
    config = mp.load_config()
    plugins = mp.discover_plugins()

    check_config(config)
    if not plugins:
        warn("plugins/", "no plugins found")

    for plugin in plugins:
        if not mp.KEBAB_RE.match(plugin.name):
            error("plugins/" + plugin.name, "directory name must be kebab-case")
        check_publish_metadata(plugin)
        for target, manifest_rel in ((mp.TARGET_CLAUDE, mp.CLAUDE_MANIFEST),
                                     (mp.TARGET_CODEX, mp.CODEX_MANIFEST)):
            if target in plugin.targets:
                check_manifest(plugin, target, manifest_rel)
        check_version_agreement(plugin)
        check_skills(plugin)
        check_codex_interface(plugin)
        check_docs(plugin)

    check_generated_files(config, plugins)

    for message in warnings:
        print("warning  " + message)
    for message in errors:
        print("error    " + message)

    print("\n{} plugin(s), {} error(s), {} warning(s)".format(
        len(plugins), len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
