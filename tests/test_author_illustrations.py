"""Task 19: selections are recorded before pagination, reused, and carry rights."""

from __future__ import annotations

from pathlib import Path

from helpers import ROOT
from bookify.authoring import illustrations


def test_selection_is_recorded_before_pagination(tmp_path: Path) -> None:
    store = tmp_path / "selections.json"

    record = illustrations.select(store, "sec-reading-a-sample", "photo-1", "Recognition: a formal welcome in context.")

    assert record["reused"] is False
    assert record["selectedBeforePagination"] is True
    assert record["reason"].startswith("Recognition")
    assert illustrations.load(store) == [
        {
            "sectionId": "sec-reading-a-sample",
            "illustrationId": "photo-1",
            "reason": "Recognition: a formal welcome in context.",
            "selectedBeforePagination": True,
        }
    ]


def test_repeating_a_selection_reuses_it_without_search(tmp_path: Path) -> None:
    store = tmp_path / "selections.json"
    first = illustrations.select(store, "sec-reading-a-sample", "photo-1", "Recognition.")
    second = illustrations.select(store, "sec-reading-a-sample", "photo-1", "A different reason.")

    assert second["reused"] is True
    assert second["reason"] == first["reason"]
    assert len(illustrations.load(store)) == 1


def test_no_quota_is_applied(tmp_path: Path) -> None:
    store = tmp_path / "selections.json"
    for illustration in ("photo-1", "photo-a", "photo-b"):
        illustrations.select(store, "sec-reading-a-sample", illustration, "Relevant to the section.")

    assert len(illustrations.load(store)) == 3


def test_status_preserves_rights_status(tmp_path: Path) -> None:
    store = tmp_path / "selections.json"
    illustrations.select(store, "sec-one", "photo-1", "Recognition.")
    illustrations.select(store, "sec-one", "photo-c", "Context, rights unresolved.")
    illustrations.select(store, "sec-one", "photo-missing", "Candidate not yet sourced.")

    rows = {row["illustrationId"]: row for row in illustrations.status(store, ROOT)}

    assert rows["photo-1"]["rightsStatus"] == "verified"
    assert rows["photo-c"]["rightsStatus"] == "unconfirmed"
    assert rows["photo-missing"]["rightsStatus"] == "unconfirmed"
    assert all(row["licence"] for row in rows.values())
