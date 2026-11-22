"""Tasks 58–59: the compact skill entry, mode playbook and packaged entry.

These tests read the actual Markdown files. They check that the entry is
agent-first and command-first, that every progressive guide is linked and
exists, that the two modes are the only modes, and that the packaged entry
carries the same normative contract instead of drifting into a second skill.
Legacy coverage for the visual composition contract stays asserted.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "bookify" / "SKILL.md"
PAYLOAD = ROOT / "packaging" / "payload" / "SKILL.md"
REFERENCES = ROOT / "skill" / "bookify" / "references"
CHECKLIST = REFERENCES / "checklist.md"
MODES = REFERENCES / "modes-and-playbooks.md"

GUIDES = (
    "modes-and-playbooks",
    "source-and-provenance",
    "editorial",
    "visual-design",
    "limits",
    "checklist",
)

SAME_NORMATIVE_TERMS = (
    "source-faithful",
    "teachable",
    "bookify-source-faithful",
    "bookify-teachable-textbook",
    "outside enrichment",
    "authoring/record.json",
    "coverage",
    "provenance",
    "--workspace",
    "BOOKIFY_WORKSPACE",
)


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, front, _ = text.split("---", 2)
    fields: dict[str, str] = {}
    for line in front.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def test_entry_frontmatter_and_compact_length() -> None:
    fields = frontmatter(SKILL)
    assert fields["name"]
    assert fields["description"]
    line_count = len(SKILL.read_text(encoding="utf-8").splitlines())
    assert line_count <= 250, f"entry is not compact: {line_count} lines"


def test_entry_documents_three_commands_for_two_modes() -> None:
    text = flat(SKILL)
    for command in ("/bookify", "/bookify-source-faithful", "/bookify-teachable-textbook"):
        assert command in text
    assert "default alias" in text
    assert "do not ask which mode" in text
    assert "not a third mode" in text
    assert "direct" in text and "fallback" in text
    # Only two mode names are offered.
    for absent in ("study-guide", "workbook", "handbook"):
        assert absent not in text


def test_entry_links_every_progressive_guide_and_the_files_exist() -> None:
    text = SKILL.read_text(encoding="utf-8")
    for name in GUIDES:
        assert f"references/{name}.md" in text, f"entry does not link {name}"
        assert (REFERENCES / f"{name}.md").is_file(), f"missing guide {name}.md"


def test_entry_does_not_impose_a_mandatory_pipeline() -> None:
    text = flat(SKILL)
    assert "optional" in text
    assert "not a mandatory" in text and "pipeline" in text
    assert "the agent may author the manuscript directly" in text
    raw = SKILL.read_text(encoding="utf-8")
    assert not re.search(r"(?mi)^#{2,3}\s*(workflow|step \d)", raw)
    assert "must run" not in text
    assert "always run" not in text


def test_entry_documents_workspace_record_and_user_non_burden() -> None:
    text = flat(SKILL)
    assert "--workspace" in text
    assert "bookify_workspace" in text
    assert "authoring/record.json" in text
    assert "never required to author yaml" in text or "do not ask them to write yaml" in text
    assert "manage caches" in text


def test_entry_has_no_hardcoded_catalogue_shape_or_original_root() -> None:
    text = flat(SKILL)
    for absent in (
        "content/catalogue.yaml",
        "content/specimen.yaml",
        "fixtures/synthetic-trial.yaml",
        str(Path.home()),
    ):
        assert absent not in text
    lowered = text
    start = 0
    while True:
        index = lowered.find("catalogue", start)
        if index == -1:
            break
        window = lowered[max(0, index - 200) : index + 200]
        assert "regression" in window, "catalogue may only appear as a regression note"
        start = index + 1


def test_entry_has_no_stale_pipeline_or_licence_wording() -> None:
    text = flat(SKILL)
    for absent in ("all rights reserved", "proprietary", "lecture deck", "private trial"):
        assert absent not in text
    assert "does not replace the global" in text
    assert "global `pdf-book-design` skill" in text
    assert "uv run python -m pytest -q" in text


def test_entry_keeps_the_approved_composition_contract() -> None:
    text = flat(SKILL)
    for phrase in ("side-left", "side-right", "full", "immediately following", "520"):
        assert phrase in text
    for phrase in ("consumed once", "no auto-pairing", "unbreakable"):
        assert phrase in text
    assert "credit" in text and "image column" in text
    assert "verify" in text


def test_checklist_is_self_critique_and_keeps_regression_coverage() -> None:
    text = flat(CHECKLIST)
    assert "self-critique" in text
    assert "30-figure geometry" in text
    assert "four distinct pages" in text
    for phrase in ("side-left", "side-right", "520"):
        assert phrase in text
    assert "uv run python -m pytest -q" in text


def test_mode_playbook_defines_both_contracts_and_enrichment_permission() -> None:
    text = flat(MODES)
    assert "source-faithful" in text and "teachable" in text
    assert "not a third mode" in text or "no third mode" in text
    assert "outside enrichment" in text
    assert "explicit" in text and "permission" in text
    assert "citation" in text
    assert "conflict" in text and "one brief resolution" in text
    for absent in ("study-guide", "workbook", "handbook"):
        assert absent not in text


def test_packaged_entry_carries_the_same_normative_contract() -> None:
    entry = flat(SKILL)
    packaged = flat(PAYLOAD)
    for term in SAME_NORMATIVE_TERMS:
        assert term.lower() in entry, f"local entry lacks {term!r}"
        assert term.lower() in packaged, f"packaged entry lacks {term!r}"
    assert "not a mandatory" in packaged and "pipeline" in packaged
    assert "do not ask which mode" in packaged
    assert "not a third mode" in packaged


def test_packaged_entry_points_to_payload_and_engine_paths_that_exist() -> None:
    text = PAYLOAD.read_text(encoding="utf-8")
    assert "references/checklist.md" in text
    for name in GUIDES:
        if name == "checklist":
            continue
        engine_path = f"engine/skill/bookify/references/{name}.md"
        payload_path = f"references/{name}.md"
        assert engine_path in text or payload_path in text, f"packaged entry does not point to {name}"
        assert (REFERENCES / f"{name}.md").is_file()
    assert "commands/" in text
    assert "~/.config/opencode/commands" in text


def test_packaged_entry_keeps_setup_and_visual_vocabulary_contract() -> None:
    text = PAYLOAD.read_text(encoding="utf-8")
    for phrase in ("BOOKIFY_ENGINE", "side-left", "side-right", "full", "references/checklist.md"):
        assert phrase in text


# --- Production design integration guidance (cover, headings, layouts) ---

DESIGN_GUIDANCE_TERMS = (
    "cover-1",
    "cover-7",
    "engine-fallback",
    "artwork: absent",
    "Chapter 1: Title",
    "1.1 a)",
    "blank line",
    "centred",
    "companions",
    "layout: {columns: 2}",
)


def test_entries_and_guides_teach_the_integrated_design() -> None:
    """Both entries and the visual guide must describe the shipped renderer."""
    entry = " ".join(SKILL.read_text(encoding="utf-8").split())
    packaged = " ".join(PAYLOAD.read_text(encoding="utf-8").split())
    guide = " ".join((REFERENCES / "visual-design.md").read_text(encoding="utf-8").split())

    for term in ("cover-1", "cover-7", "engine-fallback", "Chapter 1: Title", "1.1 a)", "centred"):
        assert term in entry, f"canonical entry lacks {term!r}"
        assert term in packaged, f"packaged entry lacks {term!r}"
        assert term in guide, f"visual guide lacks {term!r}"


def test_no_entry_still_teaches_the_retired_cover_or_opener() -> None:
    entry = " ".join(SKILL.read_text(encoding="utf-8").split())
    packaged = " ".join(PAYLOAD.read_text(encoding="utf-8").split())
    guide = " ".join((REFERENCES / "visual-design.md").read_text(encoding="utf-8").split())

    for text in (entry, packaged, guide):
        assert "ledger motif" not in text
        assert "Opener" not in text and "openers" not in text
        assert "40 pt" not in text
    assert "chapter index" not in entry


def test_checklist_covers_the_new_heading_rule_and_cover_state() -> None:
    checklist = CHECKLIST.read_text(encoding="utf-8")

    assert "Chapter n: Title" in checklist
    assert "blank line" in checklist
    assert "engine-fallback" in checklist
    assert "artwork: absent" in checklist
    assert "1.1 a)" in checklist
