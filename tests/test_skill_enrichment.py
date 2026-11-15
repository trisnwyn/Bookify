"""Task 60: enrichment permission, citation and no-invention guards."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from bookify.authoring import record
from bookify.errors import BookifyError
from bookify.manuscript import model

SOURCE_ID = "source-slug"
BOOK_ID = "skill-book"
NOTE_SHA = hashlib.sha256(b"note bytes").hexdigest()


def _manuscript(path: Path, *, example: bool = False) -> Path:
    blocks_one: list[dict] = [
        {
            "id": "b-one",
            "type": "paragraph",
            "text": "First page text.",
            "sourceAnchors": [{"sourceId": SOURCE_ID, "page": 1}],
        }
    ]
    if example:
        blocks_one.append(
            {
                "id": "b-example",
                "type": "example",
                "title": "Worked example",
                "text": "A worked example retained from the source.",
                "sourceAnchors": [{"sourceId": SOURCE_ID, "page": 1}],
            }
        )
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": BOOK_ID,
        "metadata": {"title": "Enrichment fixture", "languages": ["en"]},
        "sections": [
            {"id": "sec-one", "title": "One", "blocks": blocks_one},
            {
                "id": "sec-two",
                "title": "Two",
                "blocks": [
                    {
                        "id": "b-two",
                        "type": "paragraph",
                        "text": "Second page text.",
                        "sourceAnchors": [{"sourceId": SOURCE_ID, "page": 2}],
                    }
                ],
            },
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


def _record(manuscript_path: Path, **overrides) -> dict:
    data: dict = {
        "schemaVersion": "1.0",
        "bookId": BOOK_ID,
        "mode": "source-faithful",
        "source": {
            "id": SOURCE_ID,
            "sha256": "a" * 64,
            "pages": 2,
            "intakeManifest": "intake/manifest.json",
        },
        "enrichment": {"requested": False, "permission": None, "sources": []},
        "coverage": [
            {"sourceId": SOURCE_ID, "page": 1, "status": "covered", "blockIds": ["b-one"], "reason": None},
            {"sourceId": SOURCE_ID, "page": 2, "status": "covered", "blockIds": ["b-two"], "reason": None},
        ],
        "derivations": [
            {
                "kind": "heading",
                "blockIds": ["b-one"],
                "anchors": [{"sourceId": SOURCE_ID, "page": 1}],
                "citation": None,
                "decision": "Heading derived from the page's own topic sentence.",
            }
        ],
        "manuscriptSha256": hashlib.sha256(manuscript_path.read_bytes()).hexdigest(),
        "manuscriptRevision": 1,
    }
    data.update(overrides)
    return data


def _validate(data: dict, manuscript_path: Path) -> record.Record:
    return record.validate(data, manuscript=model.load(manuscript_path))


def _fails(data: dict, manuscript_path: Path) -> BookifyError:
    with pytest.raises(BookifyError) as error:
        _validate(data, manuscript_path)
    assert error.value.code == "INPUT_INVALID"
    assert error.value.locator is not None
    return error.value


def _external_record(manuscript_path: Path, **overrides) -> dict:
    data = _record(
        manuscript_path,
        mode="teachable",
        enrichment={
            "requested": True,
            "permission": "User asked for note.md in the final section only.",
            "sources": [
                {
                    "citation": "Harbour Notes (2024), note.md",
                    "locator": "file:note.md",
                    "localSha256": NOTE_SHA,
                    "creator": "Harbour Notes",
                    "accessed": "2026-11-12",
                }
            ],
        },
        derivations=[
            {
                "kind": "external",
                "blockIds": ["b-two"],
                "anchors": [],
                "citation": "Harbour Notes (2024), note.md",
                "decision": "Final section cites the permissioned note; nothing else was added.",
            }
        ],
    )
    data.update(overrides)
    return data


def test_teachable_accepts_permissioned_cited_enrichment(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    loaded = _validate(_external_record(manuscript), manuscript)

    assert loaded.enrichment["requested"] is True
    assert loaded.enrichment["sources"][0]["citation"] == "Harbour Notes (2024), note.md"


@pytest.mark.parametrize(
    "enrichment",
    [
        {"requested": True, "permission": None, "sources": []},
        {"requested": False, "permission": "User allowed one note.", "sources": []},
        {
            "requested": False,
            "permission": None,
            "sources": [{"citation": "Harbour Notes (2024)", "locator": "file:note.md"}],
        },
    ],
)
def test_strict_rejects_any_enrichment(tmp_path: Path, enrichment: dict) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript, enrichment=enrichment)

    error = _fails(data, manuscript)

    assert "enrichment" in error.message.lower() or "external" in error.message.lower()


def test_teachable_rejects_external_material_without_permission(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _external_record(manuscript)
    data["enrichment"]["permission"] = None

    error = _fails(data, manuscript)

    assert "permission" in error.message


def test_teachable_rejects_permission_without_a_request(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _external_record(manuscript)
    data["enrichment"] = {
        "requested": False,
        "permission": "User allowed one note.",
        "sources": [{"citation": "Harbour Notes (2024)", "locator": "file:note.md"}],
    }

    error = _fails(data, manuscript)

    assert "enrichment" in error.message.lower()


def test_teachable_rejects_external_derivation_without_citation(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _external_record(manuscript)
    data["derivations"][0]["citation"] = None

    error = _fails(data, manuscript)

    assert "citation" in error.message


def test_teachable_rejects_an_unknown_citation(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _external_record(manuscript)
    data["derivations"][0]["citation"] = "Some other book"

    error = _fails(data, manuscript)

    assert "Some other book" in error.message


def test_teachable_rejects_an_unused_enrichment_source(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _external_record(manuscript)
    data["enrichment"]["sources"].append({"citation": "Second note (2025)", "locator": "file:second.md"})

    error = _fails(data, manuscript)

    assert "Second note (2025)" in error.message


@pytest.mark.parametrize(
    "source",
    [
        {"citation": "Harbour Notes (2024), note.md", "localSha256": "not-a-hash"},
        {"citation": "Note with neither locator nor hash"},
        {"citation": "", "locator": "file:note.md"},
    ],
)
def test_enrichment_source_needs_citation_and_a_stable_locator(tmp_path: Path, source: dict) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _external_record(manuscript)
    data["enrichment"]["sources"] = [dict(source)]

    _fails(data, manuscript)


def test_teachable_accepts_permission_without_used_sources(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(
        manuscript,
        mode="teachable",
        enrichment={"requested": True, "permission": "User allowed note.md; it was not needed.", "sources": []},
    )

    loaded = _validate(data, manuscript)

    assert loaded.enrichment["requested"] is True


def test_permission_is_not_permission_to_invent_a_teaching_example(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", example=True)
    data = _external_record(manuscript)
    data["derivations"].append(
        {
            "kind": "example",
            "blockIds": ["b-example"],
            "anchors": [],
            "citation": None,
            "decision": "Invented a worked example with new numbers.",
        }
    )

    error = _fails(data, manuscript)

    assert "b-example" in error.message or "anchor" in error.message


def test_teachable_teaching_kind_is_anchored_to_the_source(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", example=True)
    data = _external_record(manuscript)
    data["derivations"].append(
        {
            "kind": "example",
            "blockIds": ["b-example"],
            "anchors": [{"sourceId": SOURCE_ID, "page": 1}],
            "citation": None,
            "decision": "Worked example derives from the page's own distinction; no new fact.",
        }
    )

    loaded = _validate(data, manuscript)

    assert any(item["kind"] == "example" for item in loaded.derivations)
