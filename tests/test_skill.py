"""Task 51: the local skill documents the visual-layout contract and commands."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "bookify" / "SKILL.md"
CHECKLIST = ROOT / "skill" / "bookify" / "references" / "checklist.md"


def test_skill_documents_composition_presets_and_adjacency() -> None:
    text = SKILL.read_text()

    for phrase in ("side-left", "side-right", "full", "immediately following", "520"):
        assert phrase in text
    assert "consumed once" in text
    assert "no auto-pairing" in text
    assert "unbreakable" in text
    assert "credit" in text and "image column" in text
    assert "verify" in text


def test_skill_keeps_the_local_global_skill_boundary_and_working_test_command() -> None:
    text = SKILL.read_text()

    assert "does not replace the global" in text
    assert "uv run python -m pytest -q" in text
    assert "global `pdf-book-design` skill" in text


def test_checklist_covers_side_compositions_and_the_geometry_gate() -> None:
    text = CHECKLIST.read_text()

    for phrase in (
        "side-left",
        "side-right",
        "520",
        "four distinct pages",
        "30-figure geometry",
        "uv run python -m pytest -q",
    ):
        assert phrase in text
