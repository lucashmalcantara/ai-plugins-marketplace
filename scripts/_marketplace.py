"""Shared helpers for the marketplace tooling.

Single source of truth for how plugins are discovered and how the two catalog
files are derived from them. Stdlib only, Python 3.9+.
"""

import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(REPO_ROOT, "marketplace.config.json")
PLUGINS_DIR = os.path.join(REPO_ROOT, "plugins")
CLAUDE_CATALOG = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")
CODEX_CATALOG = os.path.join(REPO_ROOT, ".agents", "plugins", "marketplace.json")
INDEX_FILE = os.path.join(REPO_ROOT, "PLUGINS.md")

CLAUDE_MANIFEST = os.path.join(".claude-plugin", "plugin.json")
CODEX_MANIFEST = os.path.join(".codex-plugin", "plugin.json")
PUBLISH_FILE = ".marketplace.json"

TARGET_CLAUDE = "claude-code"
TARGET_CODEX = "codex"
TARGETS = (TARGET_CLAUDE, TARGET_CODEX)

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")

# Codex marketplace policy values, per the Codex plugin spec.
INSTALLATION_POLICIES = ("NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT")
AUTHENTICATION_POLICIES = ("ON_INSTALL", "ON_USE")

# Metadata fields carried from a plugin manifest into a catalog entry.
SHARED_ENTRY_FIELDS = (
    "displayName",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def load_config():
    return read_json(CONFIG_PATH)


class Plugin(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.publish = {}
        self.claude = None
        self.codex = None

    @property
    def source_path(self):
        return "./plugins/" + self.name

    @property
    def targets(self):
        declared = self.publish.get("targets")
        return list(declared) if declared else list(TARGETS)

    def manifest_for(self, target):
        return self.claude if target == TARGET_CLAUDE else self.codex


def discover_plugins():
    """Return every plugin directory under plugins/, sorted by name."""
    if not os.path.isdir(PLUGINS_DIR):
        return []
    plugins = []
    for name in sorted(os.listdir(PLUGINS_DIR)):
        path = os.path.join(PLUGINS_DIR, name)
        if name.startswith(".") or not os.path.isdir(path):
            continue
        plugin = Plugin(name, path)
        publish_path = os.path.join(path, PUBLISH_FILE)
        if os.path.isfile(publish_path):
            plugin.publish = read_json(publish_path)
        claude_path = os.path.join(path, CLAUDE_MANIFEST)
        if os.path.isfile(claude_path):
            plugin.claude = read_json(claude_path)
        codex_path = os.path.join(path, CODEX_MANIFEST)
        if os.path.isfile(codex_path):
            plugin.codex = read_json(codex_path)
        plugins.append(plugin)
    return plugins


def build_claude_catalog(config, plugins):
    """Build .claude-plugin/marketplace.json (Claude Code marketplace schema)."""
    entries = []
    for plugin in plugins:
        if TARGET_CLAUDE not in plugin.targets or plugin.claude is None:
            continue
        manifest = plugin.claude
        entry = {"name": plugin.name, "source": plugin.source_path}
        for field in SHARED_ENTRY_FIELDS:
            if field in manifest:
                entry[field] = manifest[field]
        # `version` is deliberately omitted: when it is set in both places Claude
        # Code always uses the plugin.json value, so keeping it here only creates
        # a second copy that can drift.
        category = plugin.publish.get("category")
        if category:
            entry["category"] = category
        tags = plugin.publish.get("tags")
        if tags:
            entry["tags"] = list(tags)
        claude_opts = plugin.publish.get("claude") or {}
        if claude_opts.get("defaultEnabled") is False:
            entry["defaultEnabled"] = False
        entries.append(entry)

    catalog = {"name": config["name"]}
    if config.get("description"):
        catalog["description"] = config["description"]
    catalog["owner"] = config["owner"]
    catalog["metadata"] = {"pluginRoot": config.get("pluginRoot", "./plugins")}
    catalog["plugins"] = entries
    return catalog


def build_codex_catalog(config, plugins):
    """Build .agents/plugins/marketplace.json (Codex marketplace schema)."""
    entries = []
    for plugin in plugins:
        if TARGET_CODEX not in plugin.targets or plugin.codex is None:
            continue
        codex_opts = plugin.publish.get("codex") or {}
        policy = codex_opts.get("policy") or {}
        entry = {
            "name": plugin.name,
            "source": {"source": "local", "path": plugin.source_path},
            "policy": {
                "installation": policy.get("installation", "AVAILABLE"),
                "authentication": policy.get("authentication", "ON_INSTALL"),
            },
            "category": plugin.publish.get("category", "Productivity"),
        }
        if policy.get("products"):
            entry["policy"]["products"] = list(policy["products"])
        entries.append(entry)

    return {
        "name": config["name"],
        "interface": {"displayName": config.get("displayName", config["name"])},
        "plugins": entries,
    }


def build_index(config, plugins):
    """Build PLUGINS.md, the human-readable catalog."""
    lines = [
        "# Plugin index",
        "",
        "<!-- Generated by scripts/sync_marketplaces.py. Do not edit by hand. -->",
        "",
        "| Plugin | Version | Description | Claude Code | Codex |",
        "| --- | --- | --- | --- | --- |",
    ]
    for plugin in plugins:
        manifest = plugin.claude or plugin.codex or {}
        display = manifest.get("displayName") or plugin.name
        link = "[{}]({})".format(display, plugin.source_path)
        version = manifest.get("version", "—")
        description = (manifest.get("description") or "").replace("|", "\\|")
        claude_mark = "✅" if TARGET_CLAUDE in plugin.targets and plugin.claude else "—"
        codex_mark = "✅" if TARGET_CODEX in plugin.targets and plugin.codex else "—"
        lines.append("| {} | {} | {} | {} | {} |".format(
            link, version, description, claude_mark, codex_mark))
    if not plugins:
        lines.append("| _none yet_ | | | | |")
    lines += [
        "",
        "Install with `/plugin install <name>@{}` in Claude Code, or enable the plugin".format(
            config["name"]),
        "from `/plugins` in Codex. See the [README](./README.md) for the marketplace setup step.",
        "",
    ]
    return "\n".join(lines)


def rendered_outputs(config=None, plugins=None):
    """Return [(path, text), ...] for every generated file, as it should be on disk."""
    config = config if config is not None else load_config()
    plugins = plugins if plugins is not None else discover_plugins()
    return [
        (CLAUDE_CATALOG, dump_json(build_claude_catalog(config, plugins))),
        (CODEX_CATALOG, dump_json(build_codex_catalog(config, plugins))),
        (INDEX_FILE, build_index(config, plugins)),
    ]


def relpath(path):
    return os.path.relpath(path, REPO_ROOT)
