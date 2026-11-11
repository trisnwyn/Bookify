"""Contract tests for the manuscript schema, semantic rules and rights records."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from bookify.errors import BookifyError
from bookify.manuscript import model, schema
from bookify.toolchain.cli import main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "schemas" / "examples"
NEGATIVE = EXAMPLES / "negative"
COMPOSITION = NEGATIVE / "composition"

NEGATIVE_CASES = {
    "unknown-field.yaml": "SCHEMA_INVALID",
    "duplicate-id.yaml": "SCHEMA_INVALID",
    "dangling-xref.yaml": "XREF_MISSING",
    "unreadable-without-note.yaml": "SCHEMA_INVALID",
    "unreadable-prose-content.yaml": "SCHEMA_INVALID",
    "unreadable-diagram-content.yaml": "SCHEMA_INVALID",
    "guessed-unreadable.yaml": "SCHEMA_INVALID",
    "incomplete-chart-matrix.yaml": "SCHEMA_INVALID",
    "orphan-diagram-edge.yaml": "SCHEMA_INVALID",
    "equation-injection.yaml": "SCHEMA_INVALID",
    "missing-licence.yaml": "RIGHTS_INCOMPLETE",
    "unsupported-version.yaml": "SCHEMA_INVALID",
}

COMPOSITION_CASES = {
    "side-without-companion.yaml",
    "full-with-companion.yaml",
    "composition-on-chart.yaml",
    "non-adjacent-companion.yaml",
    "non-prose-companion.yaml",
    "duplicate-companion.yaml",
    "over-cap-companion.yaml",
    "label-prefixed-companion.yaml",
}


def test_example_specimen_validates() -> None:
    manuscript = model.load(EXAMPLES / "specimen.yaml")

    assert manuscript.id == "minimal-specimen"
    assert manuscript.revision == 1
    assert len(manuscript.sections) == 2
    assert manuscript.block_ids >= {"b-chart", "b-diagram", "b-table"}


@pytest.mark.parametrize("name, code", sorted(NEGATIVE_CASES.items()))
def test_negative_fixtures_fail_with_named_code(name: str, code: str) -> None:
    with pytest.raises(BookifyError) as error:
        model.load(NEGATIVE / name)

    assert error.value.code == code, f"{name}: {error.value.code} ({error.value.message})"


def test_chart_null_requires_a_note(tmp_path: Path) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    chart = data["sections"][0]["blocks"][2]["chart"]
    chart["values"] = [[72], [None], [58]]

    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data))

    with pytest.raises(BookifyError) as error:
        model.load(target)
    assert error.value.code == "SCHEMA_INVALID"


def _chart(data: dict) -> dict:
    return next(
        block["chart"] for section in data["sections"] for block in section["blocks"] if block["type"] == "chart"
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_chart_values_must_be_finite(tmp_path: Path, value: float) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    _chart(data)["values"] = [[value], [64], [58]]

    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data))

    with pytest.raises(BookifyError) as error:
        model.load(target)
    assert error.value.code == "SCHEMA_INVALID"
    assert "non-finite" in error.value.message


def test_chart_axis_must_have_min_below_max(tmp_path: Path) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    _chart(data)["axis"] = {"min": 100, "max": 0}

    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data))

    with pytest.raises(BookifyError) as error:
        model.load(target)
    assert error.value.code == "SCHEMA_INVALID"
    assert "min must be below max" in error.value.message


def test_chart_value_outside_the_axis_is_rejected(tmp_path: Path) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    _chart(data)["values"] = [[150], [64], [58]]
    _chart(data)["axis"] = {"min": 0, "max": 100}

    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data))

    with pytest.raises(BookifyError) as error:
        model.load(target)
    assert error.value.code == "SCHEMA_INVALID"
    assert "outside axis" in error.value.message


@pytest.mark.parametrize("source", ['x $ y', 'x \\# y', "x \\\\ y"])
def test_equation_source_is_math_only(tmp_path: Path, source: str) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    data["sections"][0]["blocks"].append({"id": "b-eq", "type": "equation", "typst": source})

    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data))

    with pytest.raises(BookifyError) as error:
        model.load(target)
    assert error.value.code == "SCHEMA_INVALID"
    assert "equation contains" in error.value.message



def test_unreadable_blocks_of_every_kind_reject_invented_payload(tmp_path: Path) -> None:
    blocks = {
        "paragraph": {"text": "Guessed text."},
        "quote": {"text": "Guessed quotation."},
        "list": {"items": ["Guessed item."]},
        "table": {"caption": "Guessed table.", "header": ["A"], "rows": [["1"]]},
        "equation": {"typst": "x + y"},
        "diagram": {
            "caption": "Guessed figure.",
            "diagram": {
                "preset": "process",
                "nodes": [{"id": "n-a", "label": "A"}, {"id": "n-b", "label": "B"}],
                "edges": [{"from": "n-a", "to": "n-b"}],
            },
        },
        "illustration": {"caption": "Guessed photograph.", "illustrationId": "photo-1"},
    }

    for kind, payload in blocks.items():
        data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
        data["sections"][0]["blocks"].append(
            {"id": f"b-unreadable-{kind}", "type": kind, "confidence": "unreadable",
             "note": "The source could not be read.", **payload}
        )
        target = tmp_path / f"{kind}.yaml"
        target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

        with pytest.raises(BookifyError) as error:
            model.load(target, root=ROOT)

        assert error.value.code == "SCHEMA_INVALID", f"{kind}: {error.value.message}"
        assert "unreadable" in error.value.message, f"{kind}: {error.value.message}"


def test_unresolved_block_with_a_note_is_the_allowed_uncertainty_form(tmp_path: Path) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    data["sections"][0]["blocks"].append(
        {"id": "b-unresolved", "type": "unresolved", "confidence": "unreadable",
         "note": "The page was not readable."}
    )
    target = tmp_path / "unresolved.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    manuscript = model.load(target, root=ROOT)

    block = manuscript.sections[0]["blocks"][-1]
    assert block["type"] == "unresolved" and block["note"].startswith("The page was not readable")


def test_table_rows_must_match_header_width(tmp_path: Path) -> None:
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    data["sections"][1]["blocks"][0]["rows"].append(["Cedar"])

    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data))

    with pytest.raises(BookifyError) as error:
        model.load(target)
    assert error.value.code == "SCHEMA_INVALID"


def test_illustration_record_is_checked_and_hashed(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "assets", tmp_path / "assets")
    data = yaml.safe_load((EXAMPLES / "specimen.yaml").read_text())
    data["sections"][0]["blocks"].append({"id": "b-photo", "type": "illustration", "illustrationId": "photo-1"})
    (tmp_path / "manuscript.yaml").write_text(yaml.safe_dump(data))

    record = tmp_path / "assets" / "illustrations" / "photo-1" / "record.yaml"
    payload = yaml.safe_load(record.read_text())
    payload["sha256"] = "0" * 64
    record.write_text(yaml.safe_dump(payload))

    with pytest.raises(BookifyError) as error:
        model.load(tmp_path / "manuscript.yaml")
    assert error.value.code == "RIGHTS_INCOMPLETE"


def test_schema_document_is_closed() -> None:
    document = schema.load_document()

    assert document["additionalProperties"] is False
    assert "unevaluatedProperties" in document["$defs"]["block"]
    assert document["$defs"]["chartBlock"]["properties"]["chart"]["additionalProperties"] is False


def _composition_manuscript(tmp_path: Path, blocks: list[dict], name: str = "composition") -> Path:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": name,
        "metadata": {"title": "Composition", "languages": ["en"]},
        "sections": [{"id": "sec-a", "title": "Composition", "blocks": blocks}],
    }
    target = tmp_path / f"{name}.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return target


def _photo(block_id: str = "b-photo", **composition) -> dict:
    block = {"id": block_id, "type": "illustration", "illustrationId": "photo-1"}
    if composition:
        block["composition"] = composition
    return block


def test_side_composition_with_an_adjacent_prose_companion_validates(tmp_path: Path) -> None:
    target = _composition_manuscript(
        tmp_path,
        [
            _photo(preset="side-left", companion="b-text"),
            {"id": "b-text", "type": "paragraph", "text": "Short companion prose."},
        ],
    )

    manuscript = model.load(target, root=ROOT)

    block = manuscript.sections[0]["blocks"][0]
    assert block["composition"] == {"preset": "side-left", "companion": "b-text"}


def test_absent_or_full_composition_validates_without_a_companion(tmp_path: Path) -> None:
    absent = model.load(_composition_manuscript(tmp_path, [_photo()], "absent"), root=ROOT)
    full = model.load(
        _composition_manuscript(tmp_path, [_photo(preset="full")], "explicit-full"), root=ROOT
    )

    assert "composition" not in absent.sections[0]["blocks"][0]
    assert full.sections[0]["blocks"][0]["composition"] == {"preset": "full"}


def test_old_manuscripts_still_validate_without_a_composition() -> None:
    for path in (
        ROOT / "content" / "specimen.yaml",
        ROOT / "fixtures" / "synthetic-trial.yaml",
    ):
        manuscript = model.load(path)
        assert manuscript.revision >= 1
        for section in manuscript.sections:
            for block in section["blocks"]:
                assert "composition" not in block, f"{path.name}: {block['id']} gained a composition"

    catalogue = model.load(ROOT / "content" / "catalogue.yaml")
    assert catalogue.revision == 2
    composed = [
        block["composition"]
        for section in catalogue.sections
        for block in section["blocks"]
        if "composition" in block
    ]
    assert {entry["preset"] for entry in composed} == {"full", "side-left", "side-right"}


def test_companion_cap_is_520_collapsed_characters(tmp_path: Path) -> None:
    at_cap = _composition_manuscript(
        tmp_path,
        [
            _photo(preset="side-left", companion="b-text"),
            {"id": "b-text", "type": "paragraph", "text": "x" * 520},
        ],
        "at-cap",
    )
    over_cap = _composition_manuscript(
        tmp_path,
        [
            _photo(preset="side-left", companion="b-text"),
            {"id": "b-text", "type": "paragraph", "text": "x" * 521},
        ],
        "over-cap",
    )

    model.load(at_cap, root=ROOT)
    with pytest.raises(BookifyError) as error:
        model.load(over_cap, root=ROOT)
    assert error.value.code == "SCHEMA_INVALID"
    assert "520" in error.value.message


def test_companion_notes_and_titles_count_towards_the_cap(tmp_path: Path) -> None:
    target = _composition_manuscript(
        tmp_path,
        [
            _photo(preset="side-right", companion="b-text"),
            {
                "id": "b-text",
                "type": "example",
                "title": "A title",
                "text": "x" * 500,
                "note": "A note of twenty-one",
            },
        ],
        "note-over-cap",
    )

    with pytest.raises(BookifyError) as error:
        model.load(target, root=ROOT)
    assert error.value.code == "SCHEMA_INVALID"
    assert "520" in error.value.message


@pytest.mark.parametrize("name", sorted(COMPOSITION_CASES))
def test_composition_negative_fixtures_fail_with_schema_invalid(name: str) -> None:
    with pytest.raises(BookifyError) as error:
        model.load(COMPOSITION / name)

    assert error.value.code == "SCHEMA_INVALID", f"{name}: {error.value.code} ({error.value.message})"


def test_cli_check_reports_success(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["manuscript", "check", "--manuscript", str(EXAMPLES / "specimen.yaml"), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["sections"] == 2


def test_cli_check_reports_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["manuscript", "check", "--manuscript", str(NEGATIVE / "dangling-xref.yaml"), "--json"]) == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == "XREF_MISSING"


def test_cli_schema_prints_the_normative_document(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["manuscript", "schema"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["$id"] == "https://bookify.local/schemas/manuscript.schema.json"
