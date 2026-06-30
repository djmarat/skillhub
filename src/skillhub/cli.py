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
    # v0.0.1 — naive, just for ordering.
    # Real formula later: install_success_rate + recency + scan_pass + ...
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


def render_table(skills: Iterable[Skill]) -> str:
    rows = [("NAME", "VERSION", "TRUST", "RUNTIMES", "DESCRIPTION")]
    for s in sorted(skills, key=lambda x: -trust_score(x)):
        rows.append(
            (
                s.name,
                s.version,
                f"{trust_score(s):.2f}",
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
        for s in skills:
            print(json.dumps({
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "runtime": s.runtime,
                "category": s.category,
                "tags": s.tags,
                "trust_score": trust_score(s),
            }))
    elif not skills:
        click.echo("(no matching skills)")
    else:
        click.echo(render_table(skills))


@cli.command()
@click.argument("name")
def show(name: str) -> None:
    """Show full details for one skill."""
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
                "trust_score": trust_score(s),
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


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def validate(path: Path) -> None:
    """Validate a skill.yaml against the v0.1 schema (light check)."""
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        click.echo(f"invalid YAML: {e}", err=True)
        raise click.exceptions.Exit(1)

    for key in ("name", "version", "description", "runtime", "entry"):
        if key not in data:
            errors.append(f"missing required field: {key}")
    if data.get("name") and not str(data["name"]).replace("-", "").isalnum():
        errors.append("name must be kebab-case alphanumeric")
    if isinstance(data.get("runtime"), list) and not data["runtime"]:
        errors.append("runtime must be a non-empty list")

    if errors:
        for e in errors:
            click.echo(f"  - {e}", err=True)
        raise click.exceptions.Exit(1)
    click.echo(f"ok: {data.get('name')}@{data.get('version')}")


if __name__ == "__main__":
    cli()
