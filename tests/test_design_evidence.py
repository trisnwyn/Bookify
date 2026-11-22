"""Tracked design evidence and the spec reconciliation.

`build/` is ignored, so the accepted proof sources are copied into
`docs/design/proofs/` and hashed here. These tests fail if the evidence is
deleted, edited or drifts from its recorded hashes, and they pin the spec text
that supersedes the retired cover and opener.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOFS = ROOT / "docs" / "design" / "proofs"
COVER = ROOT / "typst" / "cover.typ"
TEMPLATE = ROOT / "typst" / "templates" / "book.typ"
SPEC = ROOT / "SPEC-design-system.md"
MAP = ROOT / "docs" / "design-map.md"
LAYOUT = ROOT / "docs" / "design" / "textbook-layout.md"

HASH = re.compile(r"^([0-9a-f]{64})  (\S+)$", re.MULTILINE)


def _recorded_hashes() -> dict[str, str]:
    text = (PROOFS / "README.md").read_text(encoding="utf-8")
    block = text.split("Hashes of these tracked copies (SHA-256):", 1)[1]
    block = block.split("```", 2)[1]
    return {name: digest for digest, name in HASH.findall(block)}


def test_tracked_proofs_are_present_and_match_their_hashes() -> None:
    recorded = _recorded_hashes()

    assert set(recorded) == {
        "a1/README.md",
        "a1/a1-proof.measure.json",
        "a1/a1-proof.gaps.json",
        "a1/a1-proof.typ",
        "a2/README.md",
        "a2/measure.json",
        "a2/measure.py",
        "a2/proof.typ",
        "cover/INDEX.md",
        "cover/README-a.md",
        "cover/README-b.md",
        "cover/part-a-measure.py",
        "cover/part-a.json",
        "cover/part-a.typ",
        "cover/part-b-measure.py",
        "cover/part-b.json",
        "cover/part-b.typ",
    }
    for name, expected in recorded.items():
        path = PROOFS / name
        assert path.is_file(), name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"{name} changed without updating docs/design/proofs/README.md"


def test_cover_module_defines_all_seven_compositions() -> None:
    cover = COVER.read_text(encoding="utf-8")

    for index in range(1, 8):
        assert f"cover-{index}: cover-{index}" in cover
        assert f"#let cover-{index}(" in cover
    assert 'panic("unknown cover composition' in cover
    # Artwork is a record path or nothing; no drawing stands in for it.
    assert "art-field" in cover
    assert "burst(" not in cover, "the proof burst must not be reproduced as cover art"


def test_template_dispatches_the_selected_cover_and_the_new_heading() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")

    assert 'render-cover(doc.metadata, doc.cover)' in template
    assert "Chapter " in template and 'prefix + " " + it.body' in template
    assert "cover-index" not in template and "ledger" not in template
    assert "section-columns(" in template and "preset-branch(" in template


def test_spec_and_map_record_the_supersession() -> None:
    spec = " ".join(SPEC.read_text(encoding="utf-8").split())
    design_map = " ".join(MAP.read_text(encoding="utf-8").split())
    layout = " ".join(LAYOUT.read_text(encoding="utf-8").split())

    assert "Amendment — production layout integration" in spec
    assert "cover-1" in spec and "cover-7" in spec and "engine-fallback" in spec
    assert "Chapter 1: Title" in spec
    assert "15.30" in spec and "blank line" in spec
    assert "cover-1" in design_map and "docs/design/proofs/" in design_map
    assert "`encoded+proof`" in design_map
    assert "Q2" in layout and "open" in layout
    assert "docs/design/proofs/" in layout
