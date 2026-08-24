#!/usr/bin/env python3
"""Tests for the note-keeper scripts.

    python3 -m unittest discover -s plugins/note-keeper/scripts -p 'test_*.py'

Stdlib only, no fixtures on disk: every test builds a throwaway vault in a temp
directory and cleans it up.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vault  # noqa: E402
from generate_index import (  # noqa: E402
    extract_relationships,
    extract_tags,
    format_line,
    render_index,
    scan,
    write_index,
)

VAULT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.py")
INDEX_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_index.py")


class _VaultCase(unittest.TestCase):
    """Base with a throwaway vault helper; each vault is cleaned up automatically."""

    def _vault(self, notes=None, config=None, marker=True):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "notes"))
        for name, body in (notes or {}).items():
            with open(os.path.join(root, "notes", name), "w", encoding="utf-8") as handle:
                handle.write(body)
        if marker:
            with open(os.path.join(root, vault.CONFIG_FILE), "w", encoding="utf-8") as handle:
                json.dump(config or {}, handle)
        return root

    def _read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class TestExtractTags(unittest.TestCase):
    def test_inline_tags(self):
        self.assertEqual(extract_tags("texto #post-pricing e #data"), ["post-pricing", "data"])

    def test_heading_is_not_a_tag(self):
        self.assertEqual(extract_tags("# Título\ncorpo"), [])

    def test_nested_tags(self):
        self.assertEqual(extract_tags("veja #post-pricing/custos"), ["post-pricing/custos"])

    def test_tags_in_code_are_ignored(self):
        self.assertEqual(extract_tags("`#nope` e ```\n#tambem-nao\n``` mas #sim"), ["sim"])

    def test_url_fragment_is_not_a_tag(self):
        self.assertEqual(extract_tags("[x](https://e.com/a#secao)"), [])

    def test_duplicates_collapse_keeping_order(self):
        self.assertEqual(extract_tags("#a #b #a"), ["a", "b"])


class TestExtractRelationships(unittest.TestCase):
    def test_angle_bracketed_destination_with_spaces(self):
        self.assertEqual(
            extract_relationships("veja [Seller Agreements](<Seller Agreements.md>)"),
            ["Seller Agreements"])

    def test_plain_destination(self):
        self.assertEqual(extract_relationships("[Go](Go.md)"), ["Go"])

    def test_non_markdown_targets_are_skipped(self):
        self.assertEqual(extract_relationships("[site](https://example.com)"), [])

    def test_attachment_paths_are_reduced_to_the_filename(self):
        self.assertEqual(extract_relationships("[x](<../notes/Outra Nota.md>)"), ["Outra Nota"])

    def test_a_markdown_attachment_is_not_a_relationship(self):
        # An Excalidraw drawing is a .md file living in _attachments/. A note
        # embedding one references an asset, not a note — counted as a
        # relationship it points at a note that will never exist.
        self.assertEqual(
            extract_relationships("[Diagrama](<../_attachments/desenho.excalidraw.md>)"), [])

    def test_links_in_code_are_ignored(self):
        self.assertEqual(extract_relationships("`[x](Y.md)`"), [])

    def test_duplicates_collapse_keeping_order(self):
        self.assertEqual(extract_relationships("[a](A.md) [b](B.md) [a2](A.md)"), ["A", "B"])

    def test_percent_encoded_destination_is_decoded(self):
        # What Obsidian writes for a spaced filename. Left encoded, the
        # relationship lands under "Note%201" and no backlink search finds it.
        self.assertEqual(extract_relationships("[Note 1](Note%201.md)"), ["Note 1"])

    def test_decomposed_and_composed_titles_agree(self):
        # macOS hands filenames back decomposed; a link typed into a note body
        # arrives composed. Both name "Técnica" and must yield one title.
        composed = extract_relationships("[x](<" + unicodedata.normalize("NFC", "Técnica") + ".md>)")
        decomposed = extract_relationships("[x](<" + unicodedata.normalize("NFD", "Técnica") + ".md>)")
        self.assertEqual(composed, decomposed)
        self.assertEqual(composed, [unicodedata.normalize("NFC", "Técnica")])

    def test_percent_encoded_and_bracketed_forms_agree(self):
        encoded = extract_relationships("[x](Repasse%20de%20Custos.md)")
        bracketed = extract_relationships("[x](<Repasse de Custos.md>)")
        self.assertEqual(encoded, bracketed)
        self.assertEqual(encoded, ["Repasse de Custos"])

    def test_encoded_and_bracketed_links_to_one_note_collapse(self):
        self.assertEqual(
            extract_relationships("[a](<Note 1.md>) e [b](Note%201.md)"), ["Note 1"])


class TestRenderSeparators(unittest.TestCase):
    def test_relationships_are_separated_so_a_comma_in_a_title_survives(self):
        # "Preposições in, on e at" is a legal filename. Joined with ", " the
        # list reads back as three different notes.
        line = format_line({
            "title": "Inglês", "path": "notes/Inglês.md", "summary": "hub",
            "tags": [], "relationships": ["Preposições in, on e at", "Often"]})
        self.assertIn("relationships: Preposições in, on e at / Often", line)
        self.assertEqual(
            line.split("relationships: ")[1].split(" / "),
            ["Preposições in, on e at", "Often"])


class TestRender(unittest.TestCase):
    def test_line_carries_summary_tags_and_relationships(self):
        line = format_line({
            "title": "Repasse Custos",
            "path": "notes/Repasse Custos.md",
            "summary": "Resumo",
            "tags": ["custos"],
            "relationships": ["Fury"],
        })
        self.assertEqual(
            line,
            "- [Repasse Custos](<../notes/Repasse Custos.md>) — Resumo "
            "· tags: custos · relationships: Fury")

    def test_line_omits_empty_sections(self):
        line = format_line({
            "title": "Go", "path": "notes/Go.md", "summary": "Resumo",
            "tags": [], "relationships": [],
        })
        self.assertEqual(line, "- [Go](<../notes/Go.md>) — Resumo")

    def test_entries_are_alphabetical_case_insensitive(self):
        rendered = render_index([
            {"title": "zeta", "path": "notes/zeta.md", "summary": "z"},
            {"title": "Alpha", "path": "notes/Alpha.md", "summary": "a"},
        ])
        self.assertLess(rendered.index("[Alpha]"), rendered.index("[zeta]"))

    def test_empty_vault_renders_only_the_header(self):
        self.assertNotIn("\n- ", render_index([]))


class TestFindVault(_VaultCase):
    def test_env_var_wins(self):
        root = self._vault()
        other = self._vault()
        self.assertEqual(
            vault.find_vault(start=other, env={vault.ENV_VAR: root}),
            os.path.abspath(root))

    def test_env_var_pointing_nowhere_is_an_error(self):
        with self.assertRaises(vault.VaultNotFound):
            vault.find_vault(env={vault.ENV_VAR: "/nonexistent/vault"})

    def test_marker_found_in_an_ancestor(self):
        root = self._vault()
        deep = os.path.join(root, "notes")
        self.assertEqual(vault.find_vault(start=deep, env={}), os.path.abspath(root))

    def test_bare_notes_folder_is_enough(self):
        root = self._vault(marker=False)
        self.assertEqual(vault.find_vault(start=root, env={}), os.path.abspath(root))

    def test_marker_outranks_a_nearer_notes_folder(self):
        # A repository that merely contains notes/ must not shadow the real,
        # marked vault further up the tree.
        root = self._vault()
        nested = os.path.join(root, "projects", "app")
        os.makedirs(os.path.join(nested, "notes"))
        self.assertEqual(vault.find_vault(start=nested, env={}), os.path.abspath(root))

    def test_no_vault_anywhere_raises(self):
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        # /tmp has no vault marker above it on any supported platform.
        with self.assertRaises(vault.VaultNotFound):
            vault.find_vault(start=empty, env={})


class TestDescribeAndInit(_VaultCase):
    def test_defaults_when_unconfigured(self):
        info = vault.describe(self._vault(config={}))
        self.assertEqual(info["language"], "pt-BR")
        self.assertEqual(info["timezone"], "-03:00")

    def test_config_overrides_defaults(self):
        info = vault.describe(self._vault(config={"language": "en", "timezone": "+01:00"}))
        self.assertEqual(info["language"], "en")
        self.assertEqual(info["timezone"], "+01:00")

    def test_blank_values_fall_back_to_defaults(self):
        info = vault.describe(self._vault(config={"language": "   "}))
        self.assertEqual(info["language"], "pt-BR")

    def test_missing_folders_are_reported(self):
        info = vault.describe(self._vault())
        self.assertIn("_templates", info["missing"])
        self.assertNotIn("notes", info["missing"])

    def test_init_creates_the_layout(self):
        target = os.path.join(tempfile.mkdtemp(), "vault")
        self.addCleanup(shutil.rmtree, os.path.dirname(target), ignore_errors=True)
        root, created = vault.init_vault(target)
        self.assertEqual(vault.describe(root)["missing"], [])
        self.assertIn(vault.CONFIG_FILE, created)
        self.assertTrue(os.path.isfile(os.path.join(root, "_templates", "Base.md")))

    def test_init_is_idempotent(self):
        target = self._vault()
        vault.init_vault(target)
        _, created = vault.init_vault(target)
        self.assertEqual(created, [])


class TestScan(_VaultCase):
    def test_scan_reports_tags_and_relationships(self):
        root = self._vault({"Go.md": "sobre #go e [Fury](<Fury.md>)"})
        entry = scan(root)[0]
        self.assertEqual(entry["title"], "Go")
        self.assertEqual(entry["path"], "notes/Go.md")
        self.assertEqual(entry["tags"], ["go"])
        self.assertEqual(entry["relationships"], ["Fury"])
        self.assertTrue(entry["needs_summary"])

    def test_an_accented_filename_matches_a_link_to_it(self):
        # The note is on disk under a decomposed name (what macOS stores) and
        # another note links to it composed. Title and relationship must be
        # equal strings, or every backlink to an accented note is invisible.
        root = self._vault({
            unicodedata.normalize("NFD", "Patrícia") + ".md": "ficha",
            "Railda.md": "sobrinha [Patrícia](<" + unicodedata.normalize("NFC", "Patrícia") + ".md>)",
        })
        entries = {e["title"]: e for e in scan(root)}
        self.assertIn(unicodedata.normalize("NFC", "Patrícia"), entries)
        self.assertEqual(entries["Railda"]["relationships"],
                         [unicodedata.normalize("NFC", "Patrícia")])

    def test_non_markdown_files_are_ignored(self):
        root = self._vault({"Go.md": "x"})
        with open(os.path.join(root, "notes", "image.png"), "wb") as handle:
            handle.write(b"\x89PNG")
        self.assertEqual([e["title"] for e in scan(root)], ["Go"])

    def test_missing_notes_folder_is_a_clean_error(self):
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        with self.assertRaises(SystemExit):
            scan(empty)


class TestWriteIndex(_VaultCase):
    def test_write_renders_and_caches(self):
        root = self._vault({"Go.md": "corpo #go"})
        write_index(root, {"notes/Go.md": "Resumo do Go"})
        self.assertIn("- [Go](<../notes/Go.md>) — Resumo do Go",
                      self._read(os.path.join(root, vault.INDEX_FILE)))
        cache = json.loads(self._read(os.path.join(root, vault.CACHE_FILE)))
        self.assertEqual(cache["notes/Go.md"]["summary"], "Resumo do Go")

    def test_unchanged_notes_reuse_the_cached_summary(self):
        root = self._vault({"Go.md": "corpo"})
        write_index(root, {"notes/Go.md": "Resumo"})
        entry = scan(root)[0]
        self.assertFalse(entry["needs_summary"])
        self.assertEqual(entry["summary"], "Resumo")
        write_index(root)  # no summaries supplied — the cache covers it
        self.assertIn("Resumo", self._read(os.path.join(root, vault.INDEX_FILE)))

    def test_edited_note_needs_a_new_summary(self):
        root = self._vault({"Go.md": "corpo"})
        write_index(root, {"notes/Go.md": "Resumo"})
        with open(os.path.join(root, "notes", "Go.md"), "w", encoding="utf-8") as handle:
            handle.write("corpo diferente")
        self.assertTrue(scan(root)[0]["needs_summary"])
        with self.assertRaises(SystemExit):
            write_index(root)

    def test_summary_keyed_by_the_wrong_path_does_not_satisfy_the_write(self):
        root = self._vault({"Go.md": "corpo"})
        with self.assertRaises(SystemExit):
            write_index(root, {"Go.md": "Resumo"})

    def test_deleted_note_drops_out_of_the_cache(self):
        root = self._vault({"Go.md": "a", "Fury.md": "b"})
        write_index(root, {"notes/Go.md": "ra", "notes/Fury.md": "rb"})
        os.remove(os.path.join(root, "notes", "Fury.md"))
        write_index(root)
        cache = json.loads(self._read(os.path.join(root, vault.CACHE_FILE)))
        self.assertNotIn("notes/Fury.md", cache)
        self.assertNotIn("Fury", self._read(os.path.join(root, vault.INDEX_FILE)))


class TestInspect(_VaultCase):
    def test_missing_folder_reports_everything_as_missing(self):
        report = vault.inspect_path(os.path.join(tempfile.mkdtemp(), "nope"))
        self.assertFalse(report["exists"])
        self.assertFalse(report["is_vault"])
        self.assertIn("notes", report["missing"])

    def test_existing_vault_is_recognised(self):
        report = vault.inspect_path(self._vault({"Go.md": "corpo"}))
        self.assertTrue(report["is_vault"])
        self.assertTrue(report["configured"])
        self.assertEqual(report["notes"], 1)

    def test_root_docs_are_not_loose_notes(self):
        root = self._vault()
        for name in ("README.md", "CONTRIBUTING.md"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
                handle.write("# doc\n")
        self.assertEqual(vault.inspect_path(root)["loose_markdown"], [])

    def test_loose_markdown_is_found_including_subfolders(self):
        root = self._vault()
        os.makedirs(os.path.join(root, "inbox"))
        for rel in ("Solta.md", os.path.join("inbox", "Outra.md")):
            with open(os.path.join(root, rel), "w", encoding="utf-8") as handle:
                handle.write("x\n")
        self.assertEqual(vault.inspect_path(root)["loose_markdown"],
                         ["Solta.md", os.path.join("inbox", "Outra.md")])

    def test_notes_and_support_folders_are_not_loose(self):
        root = self._vault({"Go.md": "corpo"})
        os.makedirs(os.path.join(root, "_templates"), exist_ok=True)
        with open(os.path.join(root, "_templates", "Base.md"), "w", encoding="utf-8") as h:
            h.write("## x\n")
        self.assertEqual(vault.inspect_path(root)["loose_markdown"], [])


class TestObsidian(_VaultCase):
    def _plugins(self, root, data):
        os.makedirs(os.path.join(root, vault.OBSIDIAN_DIR), exist_ok=True)
        path = os.path.join(root, vault.OBSIDIAN_DIR, "core-plugins.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        return path

    def test_plan_changes_nothing_on_disk(self):
        root = self._vault()
        self.assertTrue(vault.obsidian_plan(root))
        self.assertFalse(os.path.isdir(os.path.join(root, vault.OBSIDIAN_DIR)))

    def test_markdown_links_are_forced_on(self):
        # Left at its default Obsidian writes [[wikilinks]], which the note
        # format forbids — this is the load-bearing setting.
        keys = {c["key"]: c["to"] for c in vault.obsidian_plan(self._vault())}
        self.assertIs(keys["useMarkdownLinks"], True)
        self.assertEqual(keys["attachmentFolderPath"], "_attachments")
        self.assertEqual(keys["newFileFolderPath"], "notes")
        # Not "shortest": that writes a bare filename only Obsidian's own index
        # can resolve, so an attachment embed points at notes/<file> and breaks
        # in every other Markdown reader.
        self.assertEqual(keys["newLinkFormat"], "relative")

    def test_configure_then_replan_is_empty(self):
        root = self._vault()
        vault.configure_obsidian(root)
        self.assertEqual(vault.obsidian_plan(root), [])

    def test_existing_app_settings_are_merged_not_replaced(self):
        root = self._vault()
        os.makedirs(os.path.join(root, vault.OBSIDIAN_DIR))
        app = os.path.join(root, vault.OBSIDIAN_DIR, "app.json")
        with open(app, "w", encoding="utf-8") as handle:
            json.dump({"theme": "obsidian", "userIgnoreFilters": ["private/"]}, handle)
        vault.configure_obsidian(root)
        with open(app, encoding="utf-8") as handle:
            merged = json.load(handle)
        self.assertEqual(merged["theme"], "obsidian")
        self.assertEqual(merged["userIgnoreFilters"], ["private/", "_sessions/"])

    def test_core_plugins_is_never_authored_from_scratch(self):
        # A file holding only `templates` would read as "every other core
        # plugin is off"; Obsidian enables Templates by default anyway.
        root = self._vault()
        vault.configure_obsidian(root)
        self.assertFalse(os.path.isfile(
            os.path.join(root, vault.OBSIDIAN_DIR, "core-plugins.json")))

    def test_existing_core_plugins_map_keeps_its_other_entries(self):
        root = self._vault()
        path = self._plugins(root, {"graph": True, "templates": False})
        vault.configure_obsidian(root)
        with open(path, encoding="utf-8") as handle:
            plugins = json.load(handle)
        self.assertEqual(plugins, {"graph": True, "templates": True})

    def test_legacy_core_plugins_list_is_appended_to(self):
        root = self._vault()
        path = self._plugins(root, ["file-explorer", "graph"])
        vault.configure_obsidian(root)
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), ["file-explorer", "graph", "templates"])

    def test_a_file_with_nothing_to_change_is_not_rewritten(self):
        # Rewriting core-plugins.json to change none of its thirty entries is
        # churn in the user's diff, and contradicts "merged, never replaced".
        root = self._vault()
        path = self._plugins(root, {"graph": True, "templates": True})
        before = self._read(path)
        stamp = os.stat(path).st_mtime_ns
        vault.configure_obsidian(root)
        self.assertEqual(self._read(path), before)
        self.assertEqual(os.stat(path).st_mtime_ns, stamp)

    def test_configuring_twice_rewrites_nothing_the_second_time(self):
        root = self._vault()
        vault.configure_obsidian(root)
        app = os.path.join(root, vault.OBSIDIAN_DIR, "app.json")
        stamp = os.stat(app).st_mtime_ns
        self.assertEqual(vault.configure_obsidian(root), [])
        self.assertEqual(os.stat(app).st_mtime_ns, stamp)

    def test_unreadable_config_does_not_crash_the_plan(self):
        root = self._vault()
        os.makedirs(os.path.join(root, vault.OBSIDIAN_DIR))
        with open(os.path.join(root, vault.OBSIDIAN_DIR, "app.json"), "w") as handle:
            handle.write("{ not json")
        self.assertTrue(vault.obsidian_plan(root))


class TestHostAgnostic(unittest.TestCase):
    """The scripts must not know which agent host is running them.

    Host knowledge belongs in one line of each SKILL.md, where a fallback can
    be written; a script that reached for CLAUDE_PLUGIN_ROOT or PLUGIN_ROOT
    would push that knowledge into the implementation and break on a host that
    exports neither. See the plugin README, "Host portability".
    """

    MODULES = (VAULT_SCRIPT, INDEX_SCRIPT)

    def test_no_host_variables_are_read(self):
        for path in self.MODULES:
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            for name in ("CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"):
                self.assertNotIn(name, source, "{} references {}".format(
                    os.path.basename(path), name))

    def test_only_the_plugin_s_own_variable_is_read(self):
        self.assertEqual(vault.ENV_VAR, "NOTE_KEEPER_VAULT")

    def test_scripts_locate_themselves(self):
        # generate_index.py imports vault.py as a sibling, so it must derive its
        # own directory rather than rely on the caller's cwd or sys.path.
        with open(INDEX_SCRIPT, encoding="utf-8") as handle:
            self.assertIn("__file__", handle.read())


class TestCommandLine(_VaultCase):
    def _run(self, script, args, env=None):
        environment = dict(os.environ)
        environment.pop(vault.ENV_VAR, None)
        environment.update(env or {})
        return subprocess.run(
            [sys.executable, script] + args,
            capture_output=True, text=True, env=environment)

    def test_vault_script_prints_the_resolved_vault(self):
        root = self._vault()
        result = self._run(VAULT_SCRIPT, ["--root", root])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["root"], os.path.abspath(root))

    def test_vault_script_fails_cleanly_with_no_vault(self):
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        result = self._run(VAULT_SCRIPT, ["--root", empty])
        self.assertEqual(result.returncode, 1)
        self.assertIn(vault.ENV_VAR, result.stderr)

    def test_index_script_scan_and_write(self):
        root = self._vault({"Go.md": "corpo #go"})
        scanned = self._run(INDEX_SCRIPT, ["--root", root, "scan"])
        self.assertEqual(scanned.returncode, 0, scanned.stderr)
        self.assertTrue(json.loads(scanned.stdout)[0]["needs_summary"])

        summaries = os.path.join(root, "summaries.json")
        with open(summaries, "w", encoding="utf-8") as handle:
            json.dump({"notes/Go.md": "Resumo do Go"}, handle)
        written = self._run(INDEX_SCRIPT, ["--root", root, "write", "--summaries", summaries])
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertIn("Resumo do Go", self._read(os.path.join(root, vault.INDEX_FILE)))

    def test_index_script_resolves_the_vault_from_the_environment(self):
        root = self._vault({"Go.md": "corpo"})
        result = self._run(INDEX_SCRIPT, ["scan"], env={vault.ENV_VAR: root})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["title"], "Go")


if __name__ == "__main__":
    unittest.main()
