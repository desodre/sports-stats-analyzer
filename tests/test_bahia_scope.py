"""The Bahia pilot scope is a versioned, auditable input to later phases."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "docs" / "bahia" / "pilot-2026.json"
SCHEMA = ROOT / "docs" / "bahia" / "evidence.schema.json"


def test_bahia_pilot_has_balanced_unique_finished_matches():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    matches = catalog["matches"]

    assert catalog["version"] == "bahia-pilot-2026-v1"
    assert catalog["scope"]["pilot_size"] == 10
    assert len(matches) == 10
    assert len({match["football_data_match_id"] for match in matches}) == 10
    assert len({match["cbf_match_id"] for match in matches}) == 10
    assert {match["status"] for match in matches} == {"FINISHED"}
    assert Counter(match["venue_role"] for match in matches) == {"home": 5, "away": 5}
    assert Counter(match["result"]["outcome"] for match in matches) == {
        "win": 4,
        "draw": 3,
        "loss": 3,
    }

    for match in matches:
        assert match["cbf_url"].endswith(f"/{match['cbf_match_id']}")


def test_bahia_identity_preserves_ambiguity_and_excludes_bahia_de_feira():
    focus = json.loads(CATALOG.read_text(encoding="utf-8"))["focus_team"]

    assert focus["football_data"]["team_id"] == 1777
    assert focus["cbf"]["primary_team_id"] == 61377
    assert focus["cbf"]["identity_status"] == "candidate_by_fixture_linkage"
    assert focus["cbf"]["historical_unresolved_ids"] == [20006]
    assert focus["cbf"]["excluded_ids"] == [21878]


def test_evidence_schema_requires_provenance_content_and_review_state():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    required = set(schema["required"])
    assert {"match", "source", "content", "confidence", "review_status", "limitations"} <= required
    rights = schema["properties"]["source"]["properties"]["rights_status"]["enum"]
    assert "unreviewed" in rights
    assert "permitted" in rights
    assert "prohibited" in rights
    assert schema["properties"]["entities"]["properties"]["focus_team_id"] == {"const": 1777}
