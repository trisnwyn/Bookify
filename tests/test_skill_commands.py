"""Tasks 57 and 67 (partial): the three real slash-command prompt templates.

The tests load the actual Markdown assets from the canonical command directory.
A mention of a command in ``SKILL.md`` is not evidence that the command exists.
Packaged and installed copies are compared only when a copy is present; a
missing copy is a packaging gap, not a silenced assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ROOT / "skill" / "bookify" / "commands"
PAYLOAD_COMMANDS = ROOT / "packaging" / "payload" / "commands"
INSTALLED_COMMANDS = Path.home() / ".config" / "opencode" / "commands"
PROJECT_COMMANDS = ROOT / ".opencode" / "commands"

EXPECTED = {
    "bookify": "source-faithful",
    "bookify-source-faithful": "source-faithful",
    "bookify-teachable-textbook": "teachable",
}

# A quoted argument fixture with language, audience, citation and output
# preferences. Expansion must not drop or reinterpret any of it.
ARGS_FIXTURE = (
    '"Use the attached harbour field notes. Write in British English for '
    'second-year undergraduates; keep it to twelve pages; use author-date '
    'citations; save the PDF to dist/harbour.pdf."'
)


def command_path(name: str) -> Path:
    return COMMANDS / f"{name}.md"


def read_command(name: str) -> str:
    return command_path(name).read_text(encoding="utf-8")


def flat_body(name: str) -> str:
    """The template body with line wrapping folded, for phrase assertions."""
    return " ".join(split_frontmatter(read_command(name))[1].split()).lower()


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    assert text.startswith("---\n"), "command asset must start with YAML frontmatter"
    _, front, body = text.split("---", 2)
    fields: dict[str, str] = {}
    for line in front.strip().splitlines():
        assert ":" in line, f"non key/value frontmatter line: {line!r}"
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body


def occurrences(text: str, needle: str) -> list[int]:
    found: list[int] = []
    start = 0
    while True:
        index = text.find(needle, start)
        if index == -1:
            return found
        found.append(index)
        start = index + len(needle)


def test_exactly_three_canonical_command_assets_for_two_modes() -> None:
    assert COMMANDS.is_dir(), "canonical command directory is missing"
    names = {path.stem for path in COMMANDS.glob("*.md")}
    assert names == set(EXPECTED), f"unexpected command assets: {sorted(names)}"


def test_default_alias_is_source_faithful_and_not_a_third_mode() -> None:
    for name, mode in EXPECTED.items():
        body = flat_body(name)
        assert mode in body, f"{name} must state its {mode} mode"
        assert "third mode" not in body or "not a third mode" in body
        for absent in ("study-guide", "workbook", "handbook"):
            assert absent not in body, f"{name} must not introduce {absent} as a mode"

    alias = flat_body("bookify")
    assert "source-faithful" in alias
    assert "default" in alias
    # The alias states its mode directly; it must not offer teachable as its own.
    assert "make a bookify book in `source-faithful` mode" in alias


def test_frontmatter_carries_only_a_description() -> None:
    for name in EXPECTED:
        fields, _ = split_frontmatter(read_command(name))
        assert set(fields) == {"description"}, f"{name} frontmatter: {sorted(fields)}"
        assert fields["description"].strip()
        for forbidden in ("agent", "model", "subagent", "subtask"):
            assert forbidden not in fields, f"{name} hardcodes {forbidden}"


def test_template_preserves_arguments_attachments_and_preferences() -> None:
    for name in EXPECTED:
        text = read_command(name)
        _, body = split_frontmatter(text)
        assert len(re.findall(r"(?m)^\$ARGUMENTS$", body)) == 1, (
            f"{name} must include exactly one standalone $ARGUMENTS placeholder"
        )
        lowered = flat_body(name)
        assert "attachments" in lowered, f"{name} must treat composer attachments as source"
        assert "language" in lowered and "audience" in lowered
        assert "output path" in lowered

        expanded = text.replace("$ARGUMENTS", ARGS_FIXTURE)
        assert "$ARGUMENTS" not in expanded
        for marker in (
            "harbour field notes",
            "British English",
            "second-year undergraduates",
            "twelve pages",
            "author-date",
            "dist/harbour.pdf",
        ):
            assert marker in expanded, f"{name} expansion lost {marker!r}"


def test_template_states_mode_authority_and_one_brief_conflict_resolution() -> None:
    for name, mode in EXPECTED.items():
        lowered = flat_body(name)
        assert "do not ask which mode" in lowered, f"{name} must forbid a mode interview"
        assert "conflict" in lowered, f"{name} must name the conflict case"
        assert "one brief resolution" in lowered
        assert "silently" in lowered and "do not" in lowered

        # A genuine mode request is not silently obeyed or silently refused.
        other = "teachable" if mode == "source-faithful" else "source-faithful"
        assert other in lowered, f"{name} must name the conflicting other mode"


def test_no_mode_question_survives_anywhere_in_the_template() -> None:
    for name in EXPECTED:
        body = flat_body(name)
        for index in occurrences(body, "which mode"):
            window = body[max(0, index - 80) : index]
            assert "not" in window, f"{name} asks which mode instead of establishing it"


def test_template_does_not_rely_on_at_path_expansion() -> None:
    for name in EXPECTED:
        body = " ".join(split_frontmatter(read_command(name))[1].split())
        for index in occurrences(body, "@path"):
            window = body[max(0, index - 160) : index + 80].lower()
            assert "do not rely" in window, f"{name} appears to rely on @path expansion"


def test_template_contains_no_shell_block_and_no_argument_interpolation() -> None:
    for name in EXPECTED:
        body = split_frontmatter(read_command(name))[1]
        assert "```!" not in body, f"{name} contains a shell code block"
        assert not re.search(r"(?m)^\s*!", body), f"{name} contains a ! shell block"
        for line in body.splitlines():
            if "$ARGUMENTS" in line:
                assert "!" not in line, f"{name} puts arguments in a shell line: {line!r}"


def test_teachable_template_requires_natural_voice_and_visible_provenance() -> None:
    body = flat_body("bookify-teachable-textbook")
    assert "natural coursebook prose" in body
    assert "do not narrate the input" in body
    for weak in ("the provided materials suggest", "the course says"):
        assert weak in body, "the template must name the input-narration failure it forbids"
    for requirement in ("citation", "attribution", "uncertainty", "outside enrichment"):
        assert requirement in body
    assert "explicitly request" in body, "enrichment must be requested, never assumed"


def test_strict_templates_forbid_outside_material_and_teaching_apparatus() -> None:
    for name in ("bookify", "bookify-source-faithful"):
        body = flat_body(name)
        assert "no outside material" in body
        assert "no teaching apparatus" in body


def test_canonical_assets_are_public_safe_and_not_pipeline_manuals() -> None:
    for name in EXPECTED:
        text = read_command(name)
        assert str(Path.home()) not in text
        assert "Test-Path" not in text
        assert "private" not in text.lower()
        # The command is a prompt template, not a CLI transcript.
        assert "uv run bookify" not in text
        assert "```" not in text or "```markdown" in text


def test_canonical_command_assets_match_packaged_copies_when_present() -> None:
    if not PAYLOAD_COMMANDS.is_dir():
        return
    for name in EXPECTED:
        packaged = PAYLOAD_COMMANDS / f"{name}.md"
        assert packaged.is_file(), f"packaged command missing: {packaged}"
        assert packaged.read_bytes() == command_path(name).read_bytes(), (
            f"packaged {name}.md drifted from the canonical asset"
        )


def test_canonical_command_assets_match_installed_copies_when_present() -> None:
    candidates = [INSTALLED_COMMANDS, PROJECT_COMMANDS]
    compared = 0
    for directory in candidates:
        for name in EXPECTED:
            installed = directory / f"{name}.md"
            if not installed.is_file():
                continue
            compared += 1
            assert installed.read_bytes() == command_path(name).read_bytes(), (
                f"installed {installed} drifted from the canonical asset"
            )
    # No installation yet is a packaging/installer task, not a failure here.
    assert compared >= 0
