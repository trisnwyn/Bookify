"""Contract tests for the canonical multi-platform Bookify skill (`skills/bookify/`)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "bookify" / "SKILL.md"
REFERENCES = ROOT / "skills" / "bookify" / "references"
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
    assert fields["name"] == "bookify"
    assert fields["description"]
    line_count = len(SKILL.read_text(encoding="utf-8").splitlines())
    assert line_count <= 200, f"entry is not compact: {line_count} lines"


def test_entry_documents_three_commands_for_two_modes() -> None:
    text = flat(SKILL)
    for command in ("/bookify", "/bookify-source-faithful", "/bookify-teachable-textbook"):
        assert command in text
    assert "source-faithful" in text and "teachable" in text
    assert "default alias" in text
    assert "never ask which mode" in text


def test_entry_links_every_progressive_guide_and_the_files_exist() -> None:
    text = SKILL.read_text(encoding="utf-8")
    for name in GUIDES:
        assert f"references/{name}.md" in text, f"entry does not link {name}"
        assert (REFERENCES / f"{name}.md").is_file(), f"missing guide {name}.md"


def test_entry_documents_workspace_record_and_user_non_burden() -> None:
    text = flat(SKILL)
    assert "authoring/record.json" in text
    assert "never ask the user to edit yaml" in text
    assert "responsespace" in text
    assert "fillspace" in text


def test_entry_has_no_private_or_platform_locked_leaks() -> None:
    text = flat(SKILL)
    for absent in (
        "content/catalogue.yaml",
        "content/specimen.yaml",
        "fixtures/synthetic-trial.yaml",
        "pdf-book-design",
        ".config/opencode",
        "sudo dnf",
        "all rights reserved",
        "proprietary",
        "private trial",
        str(Path.home()).lower(),
    ):
        assert absent not in text, f"unexpected leak in SKILL.md: {absent!r}"


def test_checklist_and_visual_guide_preserve_core_contracts() -> None:
    checklist = CHECKLIST.read_text(encoding="utf-8")
    guide = " ".join((REFERENCES / "visual-design.md").read_text(encoding="utf-8").split())
    for term in ("cover-1", "cover-7", "engine-fallback", "Chapter 1: Title", "1.1 a)", "centred"):
        assert term in guide, f"visual guide lacks {term!r}"
    for term in ("Chapter n: Title", "blank line", "engine-fallback", "artwork: absent", "1.1 a)"):
        assert term in checklist, f"checklist lacks {term!r}"


def test_mode_playbook_defines_both_contracts_and_enrichment_permission() -> None:
    text = flat(MODES)
    assert "source-faithful" in text and "teachable" in text
    assert "not a third mode" in text or "no third mode" in text
    assert "outside enrichment" in text
    assert "explicit" in text and "permission" in text
    assert "citation" in text
    assert "conflict" in text and "one brief resolution" in text
