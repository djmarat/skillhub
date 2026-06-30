# skillhub CLI v0.0.1
# Local-only: search/show/install/validate against registry/skills.jsonl
# No network calls. No payments. No domain.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import click
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "registry" / "skills.jsonl"
TRUST_CACHE_PATH = ROOT / "registry" / "trust.json"
INCOMING_PATH = ROOT / "incoming"  # pending submissions
import sys as _sys
_sys.path.insert(0, str(ROOT / "src"))
from skillhub.scan import scan_skill_dir  # noqa: E402


@dataclass
class Skill:
    name: str
    version: str
    description: str
    runtime: list[str]
    category: str | None
    tags: list[str]
    entry: dict
    trust: dict
    source_url: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Skill":
        return cls(
            name=d["name"],
            version=d["version"],
            description=d["description"],
            runtime=d.get("runtime", []),
            category=d.get("category"),
            tags=d.get("tags", []),
            entry=d.get("entry", {}),
            trust=d.get("trust", {}),
            source_url=d.get("_source"),
        )


def load_registry() -> list[Skill]:
    if not REGISTRY_PATH.exists():
        return []
    out: list[Skill] = []
    with REGISTRY_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(Skill.from_dict(d))
    return out


def trust_score(skill: Skill) -> float:
    # v0.0.1 baseline (kept as fallback). v0.2 priority is read from
    # registry/trust.json when present.
    score = 0.5
    if skill.trust.get("source") == "official":
        score += 0.3
    elif skill.trust.get("source") == "github":
        score += 0.1
    if skill.trust.get("security_passes", 0) > 0:
        score += 0.1
    if "hermes" in skill.runtime:
        score += 0.05
    return min(score, 1.0)


def _load_real_trust() -> dict[str, float]:
    """Read trust.json (v0.2 signals) if it exists."""
    if not TRUST_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(TRUST_CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return {}
    return {name: float(v.get("score", 0.0)) for name, v in data.items()}


def _score(skill: Skill, real_trust: dict[str, float]) -> float:
    """Prefer v0.2 real score when available; fall back to v0.0.1 baseline."""
    if skill.name in real_trust:
        return real_trust[skill.name]
    return trust_score(skill)


def _sort_key(skill: Skill, real_trust: dict[str, float]):
    return (0, -_score(skill, real_trust))


def render_table(skills: Iterable[Skill]) -> str:
    rows = [("NAME", "VERSION", "TRUST", "RUNTIMES", "DESCRIPTION")]
    skills_list = list(skills)
    real_trust = _load_real_trust()
    sorted_list = sorted(skills_list, key=lambda s: -_score(s, real_trust))
    for s in sorted_list:
        rows.append(
            (
                s.name,
                s.version,
                f"{_score(s, real_trust):.2f}",
                ",".join(s.runtime),
                s.description[:60] + ("…" if len(s.description) > 60 else ""),
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for i, row in enumerate(rows):
        line = "  ".join(c.ljust(widths[j]) for j, c in enumerate(row))
        out.append(line)
        if i == 0:
            out.append("  ".join("-" * w for w in widths))
    return "\n".join(out)


@click.group()
def cli() -> None:
    """skillhub — trusted skill marketplace for AI agents."""


@cli.command()
@click.argument("query", required=False)
@click.option("--runtime", "-r", multiple=True, help="Filter by runtime (hermes, claude-code, codex, cursor).")
@click.option("--category", "-c", help="Filter by category.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON, one record per line.")
def search(query: str | None, runtime: tuple[str, ...], category: str | None, as_json: bool) -> None:
    """Search local registry for skills matching QUERY."""
    skills = load_registry()
    if query:
        q = query.lower()
        skills = [
            s for s in skills
            if q in s.name.lower()
            or q in s.description.lower()
            or any(q in t.lower() for t in s.tags)
        ]
    if runtime:
        wanted = set(runtime)
        skills = [s for s in skills if wanted.intersection(s.runtime)]
    if category:
        skills = [s for s in skills if s.category == category]

    if as_json:
        real_trust = _load_real_trust()
        for s in skills:
            print(json.dumps({
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "runtime": s.runtime,
                "category": s.category,
                "tags": s.tags,
                "trust_score": _score(s, real_trust),
            }))
    elif not skills:
        click.echo("(no matching skills)")
    else:
        click.echo(render_table(skills))


@cli.command()
@click.argument("name")
def show(name: str) -> None:
    """Show full details for one skill."""
    real_trust = _load_real_trust()
    for s in load_registry():
        if s.name == name:
            d = {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "runtime": s.runtime,
                "category": s.category,
                "tags": s.tags,
                "entry": s.entry,
                "trust": s.trust,
                "trust_score": _score(s, real_trust),
            }
            click.echo(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
            return
    click.echo(f"skill not found: {name}", err=True)
    raise click.exceptions.Exit(1)


@cli.command()
@click.argument("name")
@click.option(
    "--runtime",
    "-r",
    required=True,
    type=click.Choice(["hermes", "claude-code", "codex", "cursor"]),
)
def install(name: str, runtime: str) -> None:
    """Install skill <NAME> into <RUNTIME>."""
    for s in load_registry():
        if s.name == name:
            _install_to_runtime(s, runtime)
            click.echo(f"installed {name}@{s.version} → {runtime}")
            return
    click.echo(f"skill not found: {name}", err=True)
    raise click.exceptions.Exit(1)


def _install_to_runtime(skill: Skill, runtime: str) -> None:
    """Transform universal manifest to runtime-specific layout."""
    home = Path.home()
    if runtime == "hermes":
        dst = home / ".hermes" / "skills" / skill.name
    elif runtime == "claude-code":
        dst = home / ".claude" / "skills" / skill.name
    elif runtime == "codex":
        dst = home / ".codex" / "skills" / skill.name
    elif runtime == "cursor":
        dst = home / ".cursor" / "skills" / skill.name
    else:
        raise ValueError(runtime)

    dst.mkdir(parents=True, exist_ok=True)
    # Drop the universal skill.yaml as the source of truth.
    (dst / "skill.yaml").write_text(yaml.safe_dump({
        "name": skill.name,
        "version": skill.version,
        "description": skill.description,
        "runtime": skill.runtime,
        "category": skill.category,
        "tags": skill.tags,
        "entry": skill.entry,
        "trust": skill.trust,
    }, sort_keys=False, allow_unicode=True))

    # Emit a minimal runtime-specific SKILL.md so the runtime can see it.
    (dst / "SKILL.md").write_text(
        f"# {skill.name}\n\n"
        f"> {skill.description}\n\n"
        f"**Version:** {skill.version}  \n"
        f"**Runtime:** {runtime}  \n"
        f"**Source:** skillhub (universal manifest)\n\n"
        f"## Usage\n\n"
        f"This skill is installed via `skillhub`. The universal manifest lives in `skill.yaml`.\n"
    )


def _validate_record(data: dict) -> list[str]:
    """Light schema check on a parsed skill record. Returns error strings."""
    errors: list[str] = []
    for key in ("name", "version", "description", "runtime", "entry"):
        if key not in data:
            errors.append(f"missing required field: {key}")
    name = data.get("name")
    if name and not str(name).replace("-", "").isalnum():
        errors.append("name must be kebab-case alphanumeric")
    if isinstance(data.get("runtime"), list) and not data["runtime"]:
        errors.append("runtime must be a non-empty list")
    description = data.get("description", "")
    if not description or len(str(description)) < 20:
        errors.append("description is missing or too short (< 20 chars)")
    entry = data.get("entry") or {}
    if entry.get("type") == "http" and not entry.get("url"):
        errors.append("entry.type=http requires entry.url")
    if entry.get("type") == "command" and not entry.get("command"):
        errors.append("entry.type=command requires entry.command")
    return errors


@cli.command(name="validate")
@click.argument("path", required=False, type=click.Path(exists=True, path_type=Path))
@click.option("--all", "validate_all", is_flag=True, help="Validate every record in registry/skills.jsonl.")
def validate_cmd(path: Path | None, validate_all: bool) -> None:
    """Validate a skill.yaml against the v0.1 schema (light check).

    Pass a path to a single file, OR --all to scan the whole registry.
    """
    if validate_all:
        skills = load_registry()
        valid = 0
        broken: list[tuple[str, list[str]]] = []
        for s in skills:
            errs = _validate_record({
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "runtime": s.runtime,
                "entry": s.entry,
            })
            if errs:
                broken.append((s.name, errs))
            else:
                valid += 1
        click.echo(f"validated {len(skills)} records: {valid} valid, {len(broken)} broken")
        if broken:
            click.echo("\nBroken records:")
            for name, errs in broken[:50]:
                click.echo(f"  {name}:")
                for e in errs:
                    click.echo(f"    - {e}")
            if len(broken) > 50:
                click.echo(f"  ... and {len(broken) - 50} more")
        return

    if path is None:
        click.echo("provide a path or use --all", err=True)
        raise click.exceptions.Exit(1)

    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        click.echo(f"invalid YAML: {e}", err=True)
        raise click.exceptions.Exit(1)

    errors = _validate_record(data)
    if errors:
        for e in errors:
            click.echo(f"  - {e}", err=True)
        raise click.exceptions.Exit(1)
    click.echo(f"ok: {data.get('name')}@{data.get('version')}")


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--skip-scan", is_flag=True, help="Skip the static security scan.")
def publish(path: Path, skip_scan: bool) -> None:
    """Validate, scan, and stage a skill for review.

    Emits incoming/<name>.json — open a PR with that file to add the skill.
    """
    skill_path = path / "skill.yaml" if path.is_dir() else path
    if not skill_path.exists():
        click.echo(f"skill.yaml not found at {skill_path}", err=True)
        raise click.exceptions.Exit(1)

    if not skip_scan:
        scan_dir = path if path.is_dir() else path.parent
        findings = scan_skill_dir(scan_dir)
        blocking = [f for f in findings if f["severity"] in ("critical", "high")]
        if blocking:
            click.echo(f"scan found {len(blocking)} blocking issues:", err=True)
            for f in blocking[:10]:
                click.echo(f"  - [{f['severity']}] {f['rule']} @ {f['location']}: {f['message']}", err=True)
            raise click.exceptions.Exit(1)

    try:
        data = yaml.safe_load(skill_path.read_text())
    except yaml.YAMLError as e:
        click.echo(f"invalid YAML: {e}", err=True)
        raise click.exceptions.Exit(1)

    errors = _validate_record(data)
    if errors:
        click.echo("validation failed:", err=True)
        for e in errors:
            click.echo(f"  - {e}", err=True)
        raise click.exceptions.Exit(1)

    INCOMING_PATH.mkdir(exist_ok=True)
    out = INCOMING_PATH / f"{data['name']}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    click.echo(f"staged: {out}")


if __name__ == "__main__":
    cli()
