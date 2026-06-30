"""scan.py — basic static security scan for skill entries.

Heuristic checks aimed at catching the top accidental-danger patterns
without an LLM:

- Python: `eval`, `exec`, `os.system`, `subprocess` with shell=True
- Bash: `curl | sh`, `wget | bash`, `rm -rf /`, unverified downloads
- Generic: hard-coded secrets, .env references

Pure AST / regex — fast, no network. Returns list of findings as
dicts: {rule_id, severity, location, message}.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


FINDINGS: list[dict] = []


def _add(rule: str, sev: str, loc: str, msg: str) -> None:
    FINDINGS.append({"rule": rule, "severity": sev, "location": loc, "message": msg})


def scan_python(path: Path, source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        _add("python-parse-error", "high", str(path), f"not valid Python: {e}")
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("eval", "exec", "compile"):
                _add("py-danger-builtin", "high", f"{path}:{node.lineno}",
                     f"use of {name}() can execute arbitrary code")
            if name == "system" or name == "popen":
                _add("py-os-call", "medium", f"{path}:{node.lineno}",
                     f"os.{name}() is shell-injection-prone")
            if isinstance(func, ast.Attribute) and func.attr in ("call", "run", "Popen"):
                full = ast.unparse(func)
                if "subprocess" in full or "Popen" in full:
                    # Check for shell=True kwarg
                    has_shell = any(
                        isinstance(kw.value, ast.Constant) and kw.value.value is True
                        for kw in node.keywords
                        if kw.arg == "shell"
                    )
                    if has_shell:
                        _add("py-shell-true", "high", f"{path}:{node.lineno}",
                             "subprocess call with shell=True")
    # Secret patterns
    secret_re = re.compile(r"(?i)(api[_-]?key|secret|token|password)[\"':= ]+([a-z0-9_\-]{8,})")
    for m in secret_re.finditer(source):
        _add("secret-pattern", "high", f"{path}:{source[:m.start()].count(chr(10))+1}",
             "possible hard-coded secret")


def scan_bash(path: Path, source: str) -> None:
    if re.search(r"curl[^|]*\|\s*(sh|bash|sudo)", source):
        _add("bash-curl-pipe", "high", str(path),
             "curl piped to shell — unverified download pattern")
    if re.search(r"rm\s+-rf\s+/(\s|$|\")", source):
        _add("bash-rm-rf-root", "critical", str(path),
             "rm -rf / would wipe the system")
    if re.search(r"wget[^|]*\|\s*(sh|bash|sudo)", source):
        _add("bash-wget-pipe", "high", str(path), "wget | bash pattern")


def scan_text(path: Path, source: str) -> None:
    """Generic checks for any file kind."""
    secret_re = re.compile(r"(?i)(api[_-]?key|secret|token|password)[\"':= ]+([a-z0-9_\-]{16,})")
    for m in secret_re.finditer(source):
        _add("secret-pattern", "high", f"{path}", "possible hard-coded secret")


def scan_skill_dir(skill_dir: Path) -> list[dict]:
    """Scan every Python/sh/script file under skill_dir. Returns findings."""
    FINDINGS.clear()
    if not skill_dir.exists() or not skill_dir.is_dir():
        _add("scan-error", "high", str(skill_dir), "not a directory")
        return list(FINDINGS)
    for p in skill_dir.rglob("*"):
        if not p.is_file():
            continue
        try:
            content = p.read_text(errors="ignore")
        except Exception:
            continue
        name = p.name.lower()
        if name.endswith(".py"):
            scan_python(p, content)
        elif name.endswith((".sh", ".bash")):
            scan_bash(p, content)
        else:
            scan_text(p, content)
    return list(FINDINGS)
