#!/usr/bin/env python3
"""Persist NOTE_KEEPER_VAULT so the vault resolves from any directory.

Planning and writing are separate on purpose: this is the only part of the
plugin that touches a file outside the vault, so nothing is written until a
plan has been shown and approved. Stdlib only, Python 3.9+.
"""

import os
import shlex
import shutil
import tempfile

ENV_VAR = "NOTE_KEEPER_VAULT"
CONFIG_FILE = ".note-keeper.json"

BLOCK_START = "# >>> Note Keeper Plugin (managed) >>>"
BLOCK_END = "# <<< Note Keeper Plugin (managed) <<<"

# Only zsh is written to. Every other shell is told what to add by hand, which
# is safer than guessing at a startup file the user may not even source.
SUPPORTED_SHELL = "zsh"


class Unsupported(Exception):
    """Raised when asked to write on a target that has no supported flow."""


def _validate(vault):
    """Resolve the vault path, refusing anything that cannot be persisted."""
    if "\x00" in vault:
        raise ValueError("vault path contains a null byte")
    if "\n" in vault or "\r" in vault:
        raise ValueError("vault path contains a line break")

    root = os.path.abspath(os.path.expanduser(vault))
    if not os.path.exists(root):
        raise ValueError("{!r} does not exist".format(root))
    if not os.path.isdir(root):
        raise ValueError("{!r} is not a directory".format(root))
    if not os.path.isfile(os.path.join(root, CONFIG_FILE)):
        raise ValueError(
            "{!r} is not a vault: no {} in it".format(root, CONFIG_FILE))
    return root


def _quote(path):
    """Quote a path for a shell startup file, always visibly."""
    quoted = shlex.quote(path)
    # shlex leaves an ordinary path bare; quote it anyway so the line reads the
    # same whatever the path looks like.
    return quoted if quoted != path else "'{}'".format(path)


def _export_line(root):
    return "export {}={}".format(ENV_VAR, _quote(root))


def _block(root):
    return "{}\n{}\n{}".format(BLOCK_START, _export_line(root), BLOCK_END)


def _target(platform, shell, is_wsl):
    """Which flow applies here: the zsh startup file, or nothing."""
    # WSL is Linux as far as a shell startup file is concerned, so it is checked
    # before the platform name, which reads as linux there anyway.
    if not is_wsl and platform.startswith("win"):
        return None, "unsupported platform: {}".format(platform)
    name = os.path.basename(shell or "")
    if name != SUPPORTED_SHELL:
        return None, "unsupported shell: {}".format(name or "unknown")
    return SUPPORTED_SHELL, SUPPORTED_SHELL


def _find_block(lines):
    """The inclusive line range of the managed block, or None."""
    start = end = None
    for number, line in enumerate(lines):
        if line.strip() == BLOCK_START:
            start = number
        elif line.strip() == BLOCK_END and start is not None:
            end = number
            break
    return None if start is None or end is None else (start, end)


def _current_value(path):
    """The vault already recorded in the managed block, if there is one."""
    if not os.path.isfile(path):
        return None
    with open(path) as handle:
        lines = handle.read().splitlines()
    span = _find_block(lines)
    if span is None:
        return None
    for line in lines[span[0]:span[1] + 1]:
        stripped = line.strip()
        if stripped.startswith("export {}=".format(ENV_VAR)):
            _, _, value = stripped.partition("=")
            parsed = shlex.split(value)
            if parsed:
                return parsed[0]
    return None


def _manual(root, shell_file):
    return (
        "Add this line to {} by hand, then open a new terminal:\n\n"
        "    {}".format(shell_file, _export_line(root)))


def plan(vault, home=None, platform=None, shell=None, is_wsl=None):
    """Describe what making `vault` the default would change. Writes nothing."""
    import sys

    root = _validate(vault)
    home = os.path.expanduser("~") if home is None else home
    platform = sys.platform if platform is None else platform
    shell = os.environ.get("SHELL") if shell is None else shell
    is_wsl = _detect_wsl() if is_wsl is None else is_wsl

    flow, reason = _target(platform, shell, is_wsl)
    if flow is None:
        return {
            "vault": root,
            "supported": False,
            "reason": reason,
            "file": None,
            "current": None,
            "conflict": False,
            "action": "manual",
            "manual": _manual(root, "your shell's startup file"),
        }

    rc = os.path.join(home, ".zshrc")
    current = _current_value(rc)
    if current is None:
        action = "create"
    elif current == root:
        action = "unchanged"
    else:
        action = "update"

    return {
        "vault": root,
        "supported": True,
        "reason": reason,
        "file": rc,
        "block": _block(root),
        "current": current,
        "conflict": current is not None and current != root,
        "action": action,
        "manual": _manual(root, rc),
        "activate": "source {}".format(rc),
    }


def _detect_wsl():
    try:
        with open("/proc/version") as handle:
            return "microsoft" in handle.read().lower()
    except OSError:
        return False


def apply(plan_dict):
    """Write the plan. Only ever touches the managed block."""
    if not plan_dict.get("supported"):
        raise Unsupported(plan_dict.get("reason", "no supported flow here"))

    path = plan_dict["file"]
    block = plan_dict["block"]

    existed = os.path.isfile(path)
    lines = []
    if existed:
        with open(path) as handle:
            lines = handle.read().splitlines()

    span = _find_block(lines)
    if span is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block.splitlines())
    else:
        lines[span[0]:span[1] + 1] = block.splitlines()

    _write(path, "\n".join(lines) + "\n", existed)
    return {"file": path, "action": plan_dict["action"], "written": True}


def _write(path, content, existed):
    """Replace the file atomically, keeping the permissions it had."""
    directory = os.path.dirname(path) or "."
    handle, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(content)
        if existed:
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
