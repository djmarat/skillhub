#!/usr/bin/env python3
"""check_entry_commands.py — health-check every entry in the registry.

For each skill record:
- entry.type == "command": take the first token, check via shutil.which
- entry.type == "http":     HEAD request, time it
- entry.type == "python":   check python on PATH
- entry.type == "node":     check node on PATH

Writes registry/health.json with results, and prints a summary.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "skills.jsonl"
HEALTH = ROOT / "registry" / "health.json"


def _check_command(entry: dict) -> dict:
    cmd = entry.get("command", "").strip()
    if not cmd:
        return {"ok": False, "reason": "no command field"}
    exe = cmd.split()[0]
    on_path = shutil.which(exe) is not None
    return {
        "ok": on_path,
        "executable": exe,
        "on_path": on_path,
        "command": cmd,
        "reason": None if on_path else f"executable '{exe}' not on PATH",
    }


def _check_http(entry: dict) -> dict:
    url = entry.get("url", "").strip()
    if not url:
        return {"ok": False, "reason": "no url field"}
    try:
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "skillhub-healthcheck/0.1",
        })
        with urllib.request.urlopen(req, timeout=5) as r:
            return {
                "ok": r.status < 400,
                "status": r.status,
                "url": url,
                "reason": None if r.status < 400 else f"HTTP {r.status}",
            }
    except Exception as e:
        # Try GET (some servers reject HEAD)
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return {
                    "ok": r.status < 400,
                    "status": r.status,
                    "url": url,
                    "reason": None if r.status < 400 else f"HTTP {r.status}",
                }
        except Exception as e2:
            return {
                "ok": False,
                "url": url,
                "reason": f"unreachable: {type(e).__name__}",
            }


def _check_python(entry: dict) -> dict:
    on_path = shutil.which("python3") is not None or shutil.which("python") is not None
    return {
        "ok": on_path,
        "reason": None if on_path else "python not on PATH",
    }


def _check_node(entry: dict) -> dict:
    on_path = shutil.which("node") is not None
    return {
        "ok": on_path,
        "reason": None if on_path else "node not on PATH",
    }


def _check_skill(record: dict) -> dict:
    entry = record.get("entry") or {}
    etype = entry.get("type")
    if etype == "command":
        result = _check_command(entry)
    elif etype == "http":
        result = _check_http(entry)
    elif etype == "python":
        result = _check_python(entry)
    elif etype == "node":
        result = _check_node(entry)
    else:
        result = {"ok": False, "reason": f"unknown entry.type: {etype}"}
    return result


def main() -> int:
    if not REGISTRY.exists():
        print(f"registry not found: {REGISTRY}", file=sys.stderr)
        return 1
    records: list[dict] = []
    with REGISTRY.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    print(f"checking {len(records)} records...", file=sys.stderr)

    results: dict[str, dict] = {}
    by_status: dict[str, list[str]] = {"ok": [], "broken": [], "unknown": []}

    start = time.time()
    for i, r in enumerate(records):
        name = r.get("name", f"#{i}")
        result = _check_skill(r)
        results[name] = result
        if result["ok"]:
            by_status["ok"].append(name)
        elif result.get("reason") and "unknown" in str(result.get("reason", "")):
            by_status["unknown"].append(name)
        else:
            by_status["broken"].append(name)
        # progress
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            print(f"  {i+1}/{len(records)} ({elapsed:.1f}s)", file=sys.stderr)

    HEALTH.write_text(json.dumps({
        "checked_at": time.time(),
        "total": len(records),
        "ok": len(by_status["ok"]),
        "broken": len(by_status["broken"]),
        "unknown": len(by_status["unknown"]),
        "results": results,
    }, indent=2))

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Total: {len(records)} records in {elapsed:.1f}s")
    print(f"  ok:     {len(by_status['ok'])}")
    print(f"  broken: {len(by_status['broken'])}")
    print(f"  unknown:{len(by_status['unknown'])}")
    print(f"\nhealth written to {HEALTH}")

    # Print first 10 broken for quick inspection
    if by_status["broken"]:
        print(f"\n--- first 10 broken ---")
        for n in by_status["broken"][:10]:
            r = results[n]
            print(f"  {n:35}  {r.get('reason', '')}")
    if by_status["unknown"]:
        print(f"\n--- first 5 unknown ---")
        for n in by_status["unknown"][:5]:
            r = results[n]
            print(f"  {n:35}  {r.get('reason', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
