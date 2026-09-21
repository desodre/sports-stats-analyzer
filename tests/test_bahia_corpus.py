"""The Bahia corpus catalogs sources without claiming unverified rights or content."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "docs" / "bahia" / "source-catalog.json"


def test_full_match_candidate_is_linked_to_the_pilot_fixture():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    source = catalog["sources"][0]

    assert catalog["version"] == "bahia-source-catalog-v1"
    assert source["source_id"] == "youtube:q0MIJVd_9U4"
    assert source["match"] == {
        "football_data_match_id": 554816,
        "cbf_match_id": 831968,
        "description": "Remo 4–1 Bahia",
    }
    assert source["metadata"]["duration_s"] == 13219
    assert source["content"]["match_content_start_s"] == 1 * 3600 + 2 * 60 + 57


def test_video_rights_and_user_reported_timing_remain_unreviewed():
    source = json.loads(CATALOG.read_text(encoding="utf-8"))["sources"][0]

    assert source["rights_status"] == "unreviewed"
    assert source["content"]["match_content_start_basis"] == "user_reported"
    assert source["content"]["timing_review_status"] == "unreviewed"
    assert source["local_file"] is None
    assert source["sha256"] is None
