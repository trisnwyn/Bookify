"""Task 60: durable authoring record, mode contracts and provenance checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from bookify.authoring import record
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.toolchain.cli import main

SOURCE_ID = "source-slug"
BOOK_ID = "skill-book"


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(workspace: Path) -> list[tuple[str, str]]:
    return sorted(
        (path.relative_to(workspace).as_posix(), _file_digest(path))
        for path in workspace.rglob("*")
        if path.is_file()
    )


def _manuscript(
    path: Path,
    *,
    first_page: int = 1,
    second_page: int = 2,
    example: bool = False,
    unresolved: bool = False,
    bare: bool = False,
) -> Path:
    first: dict = {"id": "b-one", "type": "paragraph", "text": "First page text."}
    if not bare:
        first["sourceAnchors"] = [{"sourceId": SOURCE_ID, "page": first_page}]
    blocks_one: list[dict] = [first]
    if example:
        blocks_one.append(
            {
                "id": "b-example",
                "type": "example",
                "title": "Worked example",
                "text": "A worked example retained from the source.",
                "sourceAnchors": [{"sourceId": SOURCE_ID, "page": first_page}],
            }
        )
    if unresolved:
        blocks_one.append({"id": "b-gap", "type": "unresolved", "note": "Label is illegible."})
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": BOOK_ID,
        "metadata": {"title": "Record fixture", "languages": ["en"]},
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
                        "sourceAnchors": [{"sourceId": SOURCE_ID, "page": second_page}],
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


def _validate(data: dict, manuscript_path: Path | None = None) -> record.Record:
    manuscript = model.load(manuscript_path) if manuscript_path is not None else None
    return record.validate(data, manuscript=manuscript)


def _fails(data: dict, manuscript_path: Path, code: str = "INPUT_INVALID") -> BookifyError:
    with pytest.raises(BookifyError) as error:
        _validate(data, manuscript_path)
    assert error.value.code == code
    assert error.value.locator is not None
    assert "record.json" in error.value.locator
    return error.value


def test_valid_strict_record_reports_its_contract(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)

    loaded = record.validate(data, manuscript=model.load(manuscript))

    assert loaded.mode == "source-faithful"
    assert loaded.book_id == BOOK_ID
    assert loaded.pages == 2
    assert loaded.manuscript_revision == 1
    assert loaded.source_sha256 == "a" * 64
    summary = loaded.summary()
    assert summary["coverage"] == {"covered": 2, "merged": 0, "excluded": 0}
    assert summary["mode"] == "source-faithful"


def test_teachable_reorganisation_and_teaching_record_validates(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", first_page=2, second_page=1, example=True)
    data = _record(
        manuscript,
        mode="teachable",
        coverage=[
            {"sourceId": SOURCE_ID, "page": 1, "status": "covered", "blockIds": ["b-two"], "reason": None},
            {"sourceId": SOURCE_ID, "page": 2, "status": "covered", "blockIds": ["b-one", "b-example"], "reason": None},
        ],
        derivations=[
            {
                "kind": "reorder",
                "blockIds": ["b-two"],
                "anchors": [{"sourceId": SOURCE_ID, "page": 1}],
                "citation": None,
                "decision": "Opening example moved first as a teaching hook.",
            },
            {
                "kind": "example",
                "blockIds": ["b-example"],
                "anchors": [{"sourceId": SOURCE_ID, "page": 2}],
                "citation": None,
                "decision": "Worked example derived from the recorded distinction; no new fact.",
            },
        ],
        uncertainty=[],
        decisions=[{"id": "d-001", "kind": "reorder", "decision": "Reordered for a teachable opening."}],
    )

    loaded = _validate(data, manuscript)

    assert loaded.mode == "teachable"
    assert [item["kind"] for item in loaded.derivations] == ["reorder", "example"]


@pytest.mark.parametrize("mode", ["study-guide", "workbook", "Source-Faithful", ""])
def test_only_two_modes_exist(tmp_path: Path, mode: str) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    error = _fails(_record(manuscript, mode=mode), manuscript)

    assert "source-faithful" in error.message


def test_record_schema_version_is_one(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    _fails(_record(manuscript, schemaVersion="2.0"), manuscript)


def test_unknown_top_level_field_is_rejected(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    _fails(_record(manuscript, pipeline={"steps": []}), manuscript)


def test_unknown_derivation_kind_is_rejected(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"][0]["kind"] = "rewritten"

    _fails(data, manuscript)


def test_derivation_needs_a_decision(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"][0]["decision"] = "  "

    _fails(data, manuscript)


def test_derivation_anchor_must_be_inside_the_source(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"][0]["anchors"] = [{"sourceId": SOURCE_ID, "page": 3}]

    _fails(data, manuscript)


def test_strict_rejects_external_derivation(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"].append(
        {
            "kind": "external",
            "blockIds": ["b-two"],
            "anchors": [],
            "citation": "Harbour Notes (2024)",
            "decision": "Added a note from an outside source.",
        }
    )

    error = _fails(data, manuscript)

    assert "external" in error.message


def test_strict_rejects_reordering(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"][0]["kind"] = "reorder"

    error = _fails(data, manuscript)

    assert "order" in error.message


def test_strict_rejects_teaching_kind_without_retention(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"][0]["kind"] = "explain"

    error = _fails(data, manuscript)

    assert "retained" in error.message


def test_strict_accepts_retained_teaching_kind(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["derivations"][0].update(kind="explain", retained=True)

    loaded = _validate(data, manuscript)

    assert loaded.derivations[0]["retained"] is True


def test_strict_rejects_a_teaching_block_absent_from_the_source(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", example=True)

    error = _fails(_record(manuscript), manuscript)

    assert "b-example" in error.message


def test_strict_accepts_a_teaching_block_retained_from_the_source(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", example=True)
    data = _record(manuscript)
    data["derivations"].append(
        {
            "kind": "example",
            "blockIds": ["b-example"],
            "retained": True,
            "anchors": [{"sourceId": SOURCE_ID, "page": 1}],
            "citation": None,
            "decision": "Worked example is present in the source and retained verbatim.",
        }
    )

    loaded = _validate(data, manuscript)

    assert any(item["kind"] == "example" for item in loaded.derivations)


def test_strict_rejects_non_monotonic_page_anchors(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", first_page=2, second_page=1)

    error = _fails(_record(manuscript), manuscript)

    assert "order" in error.message


def test_strict_order_includes_derivation_anchors(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", first_page=1, second_page=1, bare=True)
    data = _record(manuscript)
    # b-one has no manuscript anchor; its only provenance is a page-2
    # derivation, while b-two anchors page 1. The effective order is 2 → 1.
    data["derivations"][0]["anchors"] = [{"sourceId": SOURCE_ID, "page": 2}]

    error = _fails(data, manuscript)

    assert "order" in error.message


def test_teachable_allows_source_reordering(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", first_page=2, second_page=1)

    loaded = _validate(_record(manuscript, mode="teachable"), manuscript)

    assert loaded.mode == "teachable"


def test_coverage_must_name_every_page_once(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    duplicate = _record(manuscript)
    duplicate["coverage"][1]["page"] = 1
    duplicate["coverage"][1]["blockIds"] = ["b-two"]
    _fails(duplicate, manuscript)

    missing = _record(manuscript)
    missing["coverage"] = missing["coverage"][:1]
    _fails(missing, manuscript)


def test_coverage_must_be_in_ascending_page_order(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["coverage"] = list(reversed(data["coverage"]))

    _fails(data, manuscript)


@pytest.mark.parametrize("status", ["merged", "excluded"])
def test_non_covered_status_needs_a_reason(tmp_path: Path, status: str) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["coverage"][1].update(status=status, reason=" ")

    _fails(data, manuscript)


def test_covered_page_needs_a_block(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["coverage"][1]["blockIds"] = []

    _fails(data, manuscript)


def test_coverage_block_ids_must_exist(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["coverage"][1]["blockIds"] = ["b-unknown"]

    error = _fails(data, manuscript)

    assert "b-unknown" in error.message


def test_a_block_anchored_to_an_excluded_page_is_rejected(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["coverage"][1].update(status="excluded", blockIds=[], reason="Duplicate page dropped.")

    error = _fails(data, manuscript)

    assert "b-two" in error.message


def test_unreadable_block_needs_a_recorded_uncertainty(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", unresolved=True)
    data = _record(manuscript)
    data["coverage"][0]["blockIds"] = ["b-one", "b-gap"]

    error = _fails(data, manuscript)

    assert "b-gap" in error.message


def test_uncertainty_records_an_unreadable_block(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", unresolved=True)
    data = _record(manuscript)
    data["coverage"][0]["blockIds"] = ["b-one", "b-gap"]
    data["uncertainty"] = [
        {"sourceId": SOURCE_ID, "page": 1, "blockId": "b-gap", "note": "Label is illegible; left unresolved."}
    ]

    loaded = _validate(data, manuscript)

    assert loaded.uncertainty[0]["blockId"] == "b-gap"


def test_uncertainty_cannot_mark_a_readable_block_unreadable(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["uncertainty"] = [
        {"sourceId": SOURCE_ID, "page": 1, "blockId": "b-one", "note": "Claims the paragraph was unreadable."}
    ]

    error = _fails(data, manuscript)

    assert "b-one" in error.message


def test_uncertainty_note_is_required(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    data = _record(manuscript)
    data["uncertainty"] = [{"sourceId": SOURCE_ID, "page": 1, "blockId": None, "note": ""}]

    _fails(data, manuscript)


def test_a_block_without_provenance_is_rejected(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", bare=True)
    data = _record(manuscript)
    data["derivations"] = []

    error = _fails(data, manuscript)

    assert "b-one" in error.message


def test_a_recorded_derivation_gives_a_block_provenance(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml", bare=True)
    data = _record(manuscript)
    data["derivations"][0]["blockIds"] = ["b-one"]

    loaded = _validate(data, manuscript)

    assert loaded.derivations[0]["blockIds"] == ["b-one"]


def test_manuscript_hash_must_match_the_stored_manuscript(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    error = _fails(_record(manuscript, manuscriptSha256="b" * 64), manuscript)

    assert "manuscript" in error.message.lower()


def test_manuscript_revision_must_match(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    _fails(_record(manuscript, manuscriptRevision=2), manuscript)


def test_book_id_must_match_the_manuscript(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")

    _fails(_record(manuscript, bookId="other-book"), manuscript)


def test_record_round_trips_through_a_file(tmp_path: Path) -> None:
    manuscript = _manuscript(tmp_path / "book.yaml")
    path = tmp_path / "authoring" / "record.json"
    path.parent.mkdir()
    path.write_text(json.dumps(_record(manuscript), indent=2))

    loaded = record.load(path, manuscript=model.load(manuscript))

    assert loaded.path == path
    assert loaded.mode == "source-faithful"


def test_record_file_must_be_json(tmp_path: Path) -> None:
    path = tmp_path / "record.json"
    path.write_text("{not json")

    with pytest.raises(BookifyError) as error:
        record.load(path)

    assert error.value.code == "INPUT_INVALID"


def test_check_cross_checks_the_intake_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "book"
    manuscript = _manuscript(workspace / "book.yaml")
    manifest = {
        "schemaVersion": "1.0",
        "sourceId": SOURCE_ID,
        "sourceName": "source.pdf",
        "sourceSha256": "a" * 64,
        "pageCount": 2,
        "pages": [],
    }
    (workspace / "intake").mkdir(parents=True)
    (workspace / "intake" / "manifest.json").write_text(json.dumps(manifest))
    record_path = workspace / "authoring" / "record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(json.dumps(_record(manuscript)))

    payload = record.check(record_path, manuscript_path=manuscript, workspace=workspace)

    assert payload["ok"] is True
    assert payload["source"]["pages"] == 2
    assert payload["manuscript"]["revision"] == 1
    assert payload["workspace"] == str(workspace.resolve())

    manifest["sourceSha256"] = "c" * 64
    (workspace / "intake" / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(BookifyError) as error:
        record.check(record_path, manuscript_path=manuscript, workspace=workspace)
    assert error.value.code == "INPUT_INVALID"


def test_check_refuses_a_record_outside_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "book"
    manuscript = _manuscript(workspace / "book.yaml")
    stray = tmp_path / "elsewhere" / "record.json"
    stray.parent.mkdir(parents=True)
    stray.write_text(json.dumps(_record(manuscript)))

    with pytest.raises(BookifyError) as error:
        record.check(stray, manuscript_path=manuscript, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "workspace" in error.value.message


def test_check_cross_checks_the_source_file(tmp_path: Path) -> None:
    workspace = tmp_path / "book"
    manuscript = _manuscript(workspace / "book.yaml")
    record_path = workspace / "authoring" / "record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(json.dumps(_record(manuscript)))
    source = tmp_path / "source.bin"
    source.write_bytes(b"a real source file whose hash is not the recorded one")

    with pytest.raises(BookifyError) as error:
        record.check(record_path, manuscript_path=manuscript, source_path=source)

    assert error.value.code == "INPUT_INVALID"
    assert "source.sha256" in (error.value.locator or "")


def test_cli_contract_check_reports_the_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "book"
    manuscript = _manuscript(workspace / "book.yaml")
    (workspace / "intake").mkdir(parents=True)
    (workspace / "intake" / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "sourceId": SOURCE_ID,
                "sourceName": "source.pdf",
                "sourceSha256": "a" * 64,
                "pageCount": 2,
                "pages": [],
            }
        )
    )
    record_path = workspace / "authoring" / "record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(json.dumps(_record(manuscript)))

    assert main(["author", "contract", "check", "--workspace", str(workspace), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["mode"] == "source-faithful"
    assert payload["workspace"] == str(workspace.resolve())
    assert payload["coverage"] == {"covered": 2, "merged": 0, "excluded": 0}


def test_cli_contract_check_rejects_mode_leakage(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "book"
    manuscript = _manuscript(workspace / "book.yaml")
    record_path = workspace / "authoring" / "record.json"
    record_path.parent.mkdir(parents=True)
    data = _record(
        manuscript,
        enrichment={"requested": True, "permission": "User allowed one note.", "sources": []},
    )
    record_path.write_text(json.dumps(data))

    assert main(["author", "contract", "check", "--workspace", str(workspace), "--json"]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["code"] == "INPUT_INVALID"
    assert "record.json" in error["locator"]


def test_check_writes_nothing(tmp_path: Path) -> None:
    workspace = tmp_path / "book"
    manuscript = _manuscript(workspace / "book.yaml")
    record_path = workspace / "authoring" / "record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(json.dumps(_record(manuscript)))
    before = _tree(workspace)

    record.check(record_path, manuscript_path=manuscript)

    assert _tree(workspace) == before
