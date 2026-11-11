"""Task 46: one composition unit in normalization, the report and deferral."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from bookify.manuscript import model
from bookify.publish import illustrations, normalize, report

ROOT = Path(__file__).resolve().parents[1]
# Captured from the pre-composition implementation; these manuscripts have no
# composition field, so their normalized document must not change at all.
SPECIMEN_NORMALIZED_SHA256 = "c06c4893dc3539988d68bae501b8ad7b0e5452f198f3cb87c4ecc4d31f630c82"
SYNTHETIC_TRIAL_NORMALIZED_SHA256 = "a5adbb8315f5a8fae62d4d49bc14654ba28c923cfc8d2a838152a96b0bb18447"


def _manuscript(tmp_path: Path, blocks: list[dict], name: str = "composition") -> model.Manuscript:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": {"title": "Composition fixture", "languages": ["en", "vi", "ja"]},
        "sections": [{"id": "sec-a", "title": "Composition", "blocks": blocks}],
    }
    target = tmp_path / f"{name}.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return model.load(target, root=ROOT)


def _photo(block_id: str, record: str, **composition) -> dict:
    block = {"id": block_id, "type": "illustration", "illustrationId": record}
    if composition:
        block["composition"] = composition
    return block


def _document(manuscript: model.Manuscript) -> normalize.Document:
    paths = {
        block["id"]: "unused.svg"
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    }
    return normalize.build(manuscript, paths, draft=True)


def _blocks(document: normalize.Document) -> list[dict]:
    return [block for section in document.data["sections"] for block in section["blocks"]]


def _entry(document: normalize.Document, block_id: str) -> dict:
    return next(block for block in _blocks(document) if block["id"] == block_id)


def test_side_left_emits_the_companion_once_inside_the_illustration(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            _photo("b-photo", "photo-1", preset="side-left", companion="b-photo-text"),
            {
                "id": "b-photo-text",
                "type": "paragraph",
                "text": "COMPANION-MARKER short prose immediately after the illustration.",
            },
        ],
    )

    document = _document(manuscript)
    blocks = _blocks(document)

    assert [block["id"] for block in blocks if block["type"] == "illustration"] == ["b-photo"]
    assert "b-photo-text" not in [block["id"] for block in blocks], "the companion was rendered twice"
    entry = _entry(document, "b-photo")
    assert entry["composition"] == "side-left"
    assert entry["companion"]["id"] == "b-photo-text"
    assert entry["companion"]["type"] == "paragraph"
    assert entry["companion"]["text"].startswith("COMPANION-MARKER")
    assert json.dumps(document.data).count("COMPANION-MARKER") == 1


def test_side_right_and_definition_companions_keep_their_own_fields(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            _photo("b-photo", "hist-1", preset="side-right", companion="b-def"),
            {
                "id": "b-def",
                "type": "definition",
                "term": "Protocol",
                "definition": "The agreed order of an encounter.",
                "note": "A recorded note.",
            },
        ],
    )

    entry = _entry(_document(manuscript), "b-photo")

    assert entry["composition"] == "side-right"
    assert entry["companion"] == {
        "id": "b-def",
        "type": "definition",
        "term": "Protocol",
        "definition": "The agreed order of an encounter.",
        "note": "A recorded note.",
    }


def test_full_composition_has_no_companion_and_one_block(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path, [_photo("b-photo", "art-1", preset="full")])

    document = _document(manuscript)

    assert [block["id"] for block in _blocks(document)] == ["b-photo"]
    assert _entry(document, "b-photo")["composition"] == "full"
    assert "companion" not in _entry(document, "b-photo")


def test_labels_are_built_before_the_companion_is_consumed(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            {
                "id": "b-chart",
                "type": "chart",
                "caption": "A chart.",
                "chart": {
                    "kind": "grouped_bar",
                    "categories": ["A"],
                    "series": [{"id": "s", "label": "Series"}],
                    "values": [[1]],
                    "axis": {"unit": "index", "min": 0, "max": 2},
                    "source": {"sourceId": "fixture", "page": 1},
                    "verification": "verified",
                },
            },
            _photo("b-photo", "photo-1", preset="side-left", companion="b-text"),
            {
                "id": "b-text",
                "type": "paragraph",
                "text": "Shown as {ref:b-chart} and referenced by {ref:b-text}.",
            },
            {
                "id": "b-tail",
                "type": "paragraph",
                "text": "The pair above is {ref:b-photo}.",
            },
        ],
    )

    document = _document(manuscript)
    entry = _entry(document, "b-photo")

    assert entry["label"] == "Photograph 1"
    assert entry["companion"]["text"] == "Shown as Figure 1 and referenced by §1."
    assert _entry(document, "b-tail")["text"] == "The pair above is Photograph 1."


def test_illustration_numbering_is_unchanged_by_a_composition(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            _photo("b-photo-a", "photo-1", preset="side-left", companion="b-text"),
            {"id": "b-text", "type": "paragraph", "text": "First companion."},
            _photo("b-photo-b", "hist-1"),
        ],
    )

    document = _document(manuscript)

    assert _entry(document, "b-photo-a")["label"] == "Photograph 1"
    assert _entry(document, "b-photo-b")["label"] == "Photograph 2"


def test_specimen_and_synthetic_trial_normalized_documents_are_unchanged() -> None:
    for label, path, expected in (
        ("specimen", ROOT / "content" / "specimen.yaml", SPECIMEN_NORMALIZED_SHA256),
        (
            "synthetic-trial",
            ROOT / "fixtures" / "synthetic-trial.yaml",
            SYNTHETIC_TRIAL_NORMALIZED_SHA256,
        ),
    ):
        manuscript = model.load(path)
        document = _document(manuscript)
        raw = json.dumps(document.data, sort_keys=True, ensure_ascii=False)
        assert hashlib.sha256(raw.encode()).hexdigest() == expected, label
        assert "composition" not in raw and "companion" not in raw


def test_composition_entries_record_the_page_and_deferral(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            _photo("b-photo-a", "photo-1", preset="side-left", companion="b-text"),
            {"id": "b-text", "type": "paragraph", "text": "First companion."},
            _photo("b-photo-b", "hist-1", preset="side-right", companion="b-text-b"),
            {"id": "b-text-b", "type": "paragraph", "text": "Second companion."},
        ],
    )
    document = _document(manuscript)
    numbered = {"Photograph 1": 4, "Photograph 2": 4}

    entries = report.composition_entries(document.data, numbered)

    assert entries == [
        {
            "blockId": "b-photo-a",
            "preset": "side-left",
            "companionId": "b-text",
            "page": 4,
            "deferred": False,
        },
        {
            "blockId": "b-photo-b",
            "preset": "side-right",
            "companionId": "b-text-b",
            "page": 4,
            "deferred": False,
        },
    ]


def test_a_composition_defers_as_one_unit_never_the_companion(tmp_path: Path) -> None:
    manuscript = _manuscript(
        tmp_path,
        [
            _photo("b-photo-a", "photo-1", preset="side-left", companion="b-text"),
            {"id": "b-text", "type": "paragraph", "text": "First companion."},
            _photo("b-photo-b", "hist-1", preset="side-right", companion="b-text-b"),
            {"id": "b-text-b", "type": "paragraph", "text": "Second companion."},
        ],
    )
    document = _document(manuscript)

    deferred = illustrations.defer_later(document.data, {4: ["photo-1", "hist-1"]})

    assert deferred == ["hist-1"]
    entry = _entry(document, "b-photo-b")
    assert entry["pagebreak"] is True
    assert "pagebreak" not in entry["companion"]
    assert document.data["illustrations"][1]["pagebreak"] is True
