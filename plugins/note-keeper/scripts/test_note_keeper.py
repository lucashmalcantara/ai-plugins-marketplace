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

    def test_links_in_code_are_ignored(self):
        self.assertEqual(extract_relationships("`[x](Y.md)`"), [])

    def test_duplicates_collapse_keeping_order(self):
        self.assertEqual(extract_relationships("[a](A.md) [b](B.md) [a2](A.md)"), ["A", "B"])


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
