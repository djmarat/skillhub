import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from skillhub.cli import (
    Skill,
    load_registry,
    render_table,
    trust_score,
)


def test_load_registry_returns_at_least_20():
    skills = load_registry()
    assert len(skills) >= 20
    assert all(isinstance(s, Skill) for s in skills)


def test_all_skills_have_required_fields():
    for s in load_registry():
        assert s.name and "-" in s.name or s.name.replace("-", "").isalnum()
        assert s.version
        assert s.description
        assert isinstance(s.runtime, list) and s.runtime
        assert 0.0 <= trust_score(s) <= 1.0


def test_search_json_contains_expected_keys():
    skills = load_registry()
    out = render_table(skills)
    assert "NAME" in out
    assert "VERSION" in out


def test_trust_official_higher_than_community():
    skills = {s.name: s for s in load_registry()}
    official = skills["pdf-md"]
    community = skills["git-summary"]
    assert trust_score(official) > trust_score(community)
