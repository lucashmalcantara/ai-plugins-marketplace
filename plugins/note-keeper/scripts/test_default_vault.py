#!/usr/bin/env python3
"""Tests for persisting NOTE_KEEPER_VAULT as the user's default vault."""

import os
import shlex
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import default_vault  # noqa: E402


class _Case(unittest.TestCase):
    """A real vault and a real home directory, both thrown away afterwards."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.vault = self._make_vault("vault")

    def _cleanup(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_vault(self, name):
        root = os.path.join(self.tmp, name)
        os.makedirs(os.path.join(root, "notes"))
        with open(os.path.join(root, ".note-keeper.json"), "w") as handle:
            handle.write("{}\n")
        return root

    def _rc(self):
        return os.path.join(self.home, ".zshrc")

    def _read_rc(self):
        with open(self._rc()) as handle:
            return handle.read()

    def _plan(self, vault=None, **kwargs):
        kwargs.setdefault("home", self.home)
        kwargs.setdefault("platform", "darwin")
        kwargs.setdefault("shell", "/bin/zsh")
        kwargs.setdefault("is_wsl", False)
        return default_vault.plan(vault or self.vault, **kwargs)

    def _exported_value(self):
        """The path a shell would actually see, parsed rather than string-matched."""
        for line in self._read_rc().splitlines():
            if line.startswith("export NOTE_KEEPER_VAULT="):
                _, _, value = line.partition("=")
                return shlex.split(value)[0]
        raise AssertionError("no export line in {}".format(self._rc()))


class TestPlatformRouting(_Case):
    def test_zsh_on_macos_is_supported(self):
        plan = self._plan()
        self.assertTrue(plan["supported"])
        self.assertEqual(plan["file"], self._rc())

    def test_wsl_uses_the_shell_flow(self):
        plan = self._plan(platform="linux", is_wsl=True)
        self.assertTrue(plan["supported"])
        self.assertEqual(plan["file"], self._rc())

    def test_bash_is_unsupported_and_names_the_shell(self):
        plan = self._plan(shell="/bin/bash")
        self.assertFalse(plan["supported"])
        self.assertIn("bash", plan["reason"])

    def test_windows_is_unsupported(self):
        plan = self._plan(platform="win32", shell=None)
        self.assertFalse(plan["supported"])
        self.assertIn("win32", plan["reason"])

    def test_unsupported_platform_still_explains_how_to_do_it_by_hand(self):
        plan = self._plan(platform="win32", shell=None)
        self.assertIn("NOTE_KEEPER_VAULT", plan["manual"])
        self.assertIn(self.vault, plan["manual"])


class TestPlanWritesNothing(_Case):
    def test_plan_does_not_create_the_rc_file(self):
        self._plan()
        self.assertFalse(os.path.exists(self._rc()))

    def test_plan_does_not_touch_an_existing_rc_file(self):
        with open(self._rc(), "w") as handle:
            handle.write("alias ll='ls -la'\n")
        self._plan()
        self.assertEqual(self._read_rc(), "alias ll='ls -la'\n")


class TestApply(_Case):
    def test_writes_the_managed_block_creating_the_file(self):
        default_vault.apply(self._plan())
        self.assertEqual(self._exported_value(), self.vault)

    def test_keeps_unrelated_lines_untouched(self):
        with open(self._rc(), "w") as handle:
            handle.write("alias ll='ls -la'\nexport EDITOR=vim\n")
        default_vault.apply(self._plan())
        body = self._read_rc()
        self.assertIn("alias ll='ls -la'", body)
        self.assertIn("export EDITOR=vim", body)

    def test_running_twice_does_not_duplicate_the_block(self):
        default_vault.apply(self._plan())
        default_vault.apply(self._plan())
        self.assertEqual(self._read_rc().count(default_vault.BLOCK_START), 1)

    def test_a_new_path_replaces_the_old_value(self):
        default_vault.apply(self._plan())
        other = self._make_vault("other")
        default_vault.apply(self._plan(vault=other))
        self.assertEqual(self._exported_value(), other)
        self.assertEqual(self._read_rc().count(default_vault.BLOCK_START), 1)

    def test_preserves_file_permissions(self):
        with open(self._rc(), "w") as handle:
            handle.write("# mine\n")
        os.chmod(self._rc(), 0o600)
        default_vault.apply(self._plan())
        mode = stat.S_IMODE(os.stat(self._rc()).st_mode)
        self.assertEqual(mode, 0o600)

    def test_refuses_to_write_on_an_unsupported_target(self):
        plan = self._plan(platform="win32", shell=None)
        with self.assertRaises(default_vault.Unsupported):
            default_vault.apply(plan)
        self.assertFalse(os.path.exists(self._rc()))


class TestConflict(_Case):
    def test_reports_the_existing_value_as_a_conflict(self):
        default_vault.apply(self._plan())
        other = self._make_vault("other")
        plan = self._plan(vault=other)
        self.assertTrue(plan["conflict"])
        self.assertEqual(plan["current"], self.vault)

    def test_the_same_path_again_is_not_a_conflict(self):
        default_vault.apply(self._plan())
        plan = self._plan()
        self.assertFalse(plan["conflict"])
        self.assertEqual(plan["action"], "unchanged")

    def test_a_first_run_is_not_a_conflict(self):
        plan = self._plan()
        self.assertFalse(plan["conflict"])
        self.assertIsNone(plan["current"])
        self.assertEqual(plan["action"], "create")


class TestPathValidation(_Case):
    def test_accepts_a_path_containing_spaces(self):
        spaced = self._make_vault("my notes vault")
        default_vault.apply(self._plan(vault=spaced))
        self.assertEqual(self._exported_value(), spaced)

    def test_accepts_a_path_containing_a_single_quote(self):
        quoted = self._make_vault("lucas's vault")
        default_vault.apply(self._plan(vault=quoted))
        self.assertEqual(self._exported_value(), quoted)

    def test_rejects_a_path_that_does_not_exist(self):
        with self.assertRaises(ValueError):
            self._plan(vault=os.path.join(self.tmp, "nowhere"))

    def test_rejects_a_file(self):
        target = os.path.join(self.tmp, "afile")
        with open(target, "w") as handle:
            handle.write("x")
        with self.assertRaises(ValueError):
            self._plan(vault=target)

    def test_rejects_a_directory_that_is_not_a_vault(self):
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        with self.assertRaises(ValueError):
            self._plan(vault=plain)

    def test_rejects_a_newline_in_the_path(self):
        with self.assertRaises(ValueError):
            self._plan(vault=self.vault + "\nexport EVIL=1")

    def test_rejects_a_null_byte_in_the_path(self):
        with self.assertRaises(ValueError):
            self._plan(vault=self.vault + "\x00")

    def test_resolves_a_relative_path_to_an_absolute_one(self):
        plan = self._plan(vault=os.path.relpath(self.vault, os.getcwd()))
        self.assertEqual(plan["vault"], self.vault)


class TestCommandLine(_Case):
    """The skill reaches this through vault.py, so the subcommand is the contract."""

    SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.py")

    def _run(self, args):
        import subprocess
        environment = dict(os.environ)
        environment["HOME"] = self.home
        environment["SHELL"] = "/bin/zsh"
        return subprocess.run(
            [sys.executable, self.SCRIPT, "default"] + args,
            capture_output=True, text=True, env=environment)

    def test_prints_a_plan_and_writes_nothing(self):
        import json
        result = self._run([self.vault])
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["vault"], self.vault)
        self.assertEqual(payload["action"], "create")
        self.assertFalse(os.path.exists(self._rc()))

    def test_apply_writes_the_block(self):
        result = self._run([self.vault, "--apply"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._exported_value(), self.vault)

    def test_reports_an_invalid_path_without_a_traceback(self):
        result = self._run([os.path.join(self.tmp, "nowhere")])
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("nowhere", result.stderr)


if __name__ == "__main__":
    unittest.main()
