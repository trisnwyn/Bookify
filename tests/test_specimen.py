"""Task 5: the specimen manuscript, its photograph and the font manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from bookify.manuscript import model

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"


def _blocks(manuscript: model.Manuscript) -> list[dict]:
    return [block for section in manuscript.sections for block in section["blocks"]]


def test_specimen_validates() -> None:
    manuscript = model.load(SPECIMEN)

    assert manuscript.id == "specimen-book"
    assert manuscript.revision == 1
    assert len(manuscript.sections) == 2


def test_specimen_contains_every_required_element() -> None:
    manuscript = model.load(SPECIMEN)
    blocks = _blocks(manuscript)
    types = {block["type"] for block in blocks}

    assert {"paragraph", "lead", "definition", "example", "case", "assessment", "list", "quote"} <= types
    assert {"table", "equation", "chart", "diagram", "illustration"} <= types

    texts = " ".join(
        block.get("text", "") + block.get("caption", "") + block.get("definition", "")
        for block in blocks
    )
    assert "Tiếng Việt" in texts and "ế ộ ữ" in texts
    assert "日本語" in texts
    assert "—" in texts and "→" in texts and "≤" in texts

    equation = next(block for block in blocks if block["type"] == "equation")
    assert equation["typst"].startswith("overline(x)")

    first_section = manuscript.sections[0]
    assert first_section["kicker"] and first_section["standfirst"]

    xrefs = [block for block in blocks if "{ref:" in block.get("text", "")]
    assert xrefs, "specimen must exercise a cross-reference"


def test_specimen_chart_is_marked_synthetic_and_noted() -> None:
    manuscript = model.load(SPECIMEN)
    chart = next(block for block in _blocks(manuscript) if block["type"] == "chart")

    assert chart["chart"]["verification"] == "synthetic"
    assert chart["confidence"] == "inferred"
    assert chart["note"]
    assert chart["chart"]["notes"]


def test_specimen_diagram_is_marked_synthetic_and_noted() -> None:
    manuscript = model.load(SPECIMEN)
    diagram = next(block for block in _blocks(manuscript) if block["type"] == "diagram")

    assert "synthetic" in diagram["caption"].lower()
    assert diagram["confidence"] == "inferred"
    assert diagram["note"]


def test_photograph_record_is_complete_and_verified() -> None:
    record_path = ROOT / "assets" / "illustrations" / "photo-1" / "record.yaml"
    record = yaml.safe_load(record_path.read_text())

    for field in ("path", "originUrl", "creator", "licence", "credit", "caption", "alt", "kind"):
        assert record.get(field), f"missing {field}"
    assert record["kind"] == "contemporary_photograph"
    assert record["rightsStatus"] == "verified"
    assert record["originUrl"].startswith("https://commons.wikimedia.org/wiki/File:")
    assert "public domain" in record["licence"].lower()

    image = ROOT / record["path"]
    assert image.is_file()
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    assert record["sha256"] == digest


def test_font_manifest_covers_every_vendored_face() -> None:
    manifest = yaml.safe_load((ROOT / "assets" / "fonts" / "fonts.yaml").read_text())
    files = [entry["path"] for family in manifest["families"] for entry in family["files"]]

    assert {family["family"] for family in manifest["families"]} == {
        "Spectral",
        "Noto Serif CJK JP",
        "STIX Two Math",
    }
    for relative in files:
        assert (ROOT / relative).is_file(), f"missing font file: {relative}"
    assert set(manifest["scripts"]) == {"latin-vietnamese", "japanese", "maths"}
    assert all(family.get("licence") for family in manifest["families"])
