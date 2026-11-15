"""Task 67: command-driven acceptance for the two modes from one source.

The tests load the actual canonical command assets (a ``SKILL.md`` mention is
not evidence that an entry exists), expand them with the public-safe invocation
fixture, and run ``bookify.authoring.record.check`` over the two real
same-source books. Negative cases mutate temporary copies only; tracked
artifacts are never changed.

The two books are portable external-workspace examples. Their tracked location
is inside the engine tree, where legacy root discovery resolves the repository
root for the strict book's book-local ``plate-1`` illustration, and workspace
mode refuses a path inside the engine tree by design. The same-source checks
therefore run on byte-identical temporary copies with the manuscript path and no
workspace (the record fields are asserted identical first). The teachable book,
which has no illustration record, is additionally checked at its tracked path.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from bookify.authoring import record
from bookify.errors import BookifyError

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ROOT / "skill" / "bookify" / "commands"
PAYLOAD_COMMANDS = ROOT / "packaging" / "payload" / "commands"
INSTALLED_COMMANDS = Path.home() / ".config" / "opencode" / "commands"
PROJECT_COMMANDS = ROOT / ".opencode" / "commands"
CONTENT = ROOT / "content" / "agent-skill"
SOURCE_FIXTURE = ROOT / "fixtures" / "agent-skill" / "source.pdf"
INVOCATIONS = ROOT / "fixtures" / "agent-skill" / "invocations.json"

SOURCE_SHA256 = "2c751d32ba89126b996db5045814e6ed2dc03468f0785ba74c3d28077f4ae1be"
MODES = ("source-faithful", "teachable")
EXPECTED = {
    "bookify": "source-faithful",
    "bookify-source-faithful": "source-faithful",
    "bookify-teachable-textbook": "teachable",
}
TEACHING_KINDS = {"explain", "example", "assessment", "glossary"}
TEACHING_BLOCK_KINDS = {
    "definition": "glossary",
    "example": "example",
    "assessment": "assessment",
    "case": "explain",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_text(name: str) -> str:
    return (COMMANDS / f"{name}.md").read_text(encoding="utf-8")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    assert text.startswith("---\n"), "command asset must start with YAML frontmatter"
    _, front, body = text.split("---", 2)
    fields: dict[str, str] = {}
    for line in front.strip().splitlines():
        assert ":" in line, f"non key/value frontmatter line: {line!r}"
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body


def flat_body(name: str) -> str:
    return " ".join(split_frontmatter(command_text(name))[1].split()).lower()


def expand(case: dict) -> str:
    _, body = split_frontmatter(command_text(case["command"]))
    assert len(re.findall(r"(?m)^\$ARGUMENTS$", body)) == 1
    expanded = re.sub(r"(?m)^\$ARGUMENTS$", lambda _match: case["arguments"], body)
    assert len(re.findall(r"(?m)^\$ARGUMENTS$", expanded)) == 0
    return expanded


def occurrences(text: str, needle: str) -> list[int]:
    found: list[int] = []
    start = 0
    while True:
        index = text.find(needle, start)
        if index == -1:
            return found
        found.append(index)
        start = index + len(needle)


def invocations() -> dict:
    return json.loads(INVOCATIONS.read_text(encoding="utf-8"))


def cases() -> list[dict]:
    return list(invocations()["cases"])


def mode_question(text: str) -> bool:
    """True when a sentence asks the user to choose a mode."""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if re.search(r"\bwhich mode\b", sentence, re.IGNORECASE):
            if "?" in sentence:
                return True
            if not re.search(r"\b(not|never|no)\b", sentence, re.IGNORECASE):
                return True
    return False


# ---------------------------------------------------------------------------
# Command assets and invocation expansion
# ---------------------------------------------------------------------------


def test_invocation_fixture_is_public_safe_and_covers_three_entries() -> None:
    data = invocations()
    assert data["schemaVersion"] == "1.0"
    assert data["source"]["path"] == "fixtures/agent-skill/source.pdf"
    assert data["source"]["sha256"] == SOURCE_SHA256
    assert data["source"]["pages"] == 6

    listed = cases()
    assert {case["command"] for case in listed} == set(EXPECTED)
    assert {case["expect"]["mode"] for case in listed} == set(MODES)
    for case in listed:
        assert case["id"] and case["arguments"]
        assert case["expect"]["mode"] == EXPECTED[case["command"]]
        assert case["attachments"] == ["source.pdf"], (
            f"{case['id']} must record the same composer source attachment"
        )
        assert case["expect"]["preserved"], f"{case['id']} must record preserved text"
        if case["expect"]["conflict"]:
            assert case["expect"]["otherEntry"] in (
                "/bookify-source-faithful",
                "/bookify-teachable-textbook",
            )

    assert {path.stem for path in COMMANDS.glob("*.md")} == set(EXPECTED)
    raw = INVOCATIONS.read_text(encoding="utf-8")
    assert "/home/" not in raw and "~/" not in raw and "C:\\" not in raw
    assert "http://" not in raw and "https://" not in raw
    assert "source.pdf" in raw and "harbour" in raw


def test_default_alias_maps_to_source_faithful_and_adds_no_third_mode() -> None:
    # Three entries, two modes: the alias is a mapping, not another mode.
    assert len(EXPECTED) == 3
    assert set(EXPECTED.values()) == set(MODES)
    assert EXPECTED["bookify"] == "source-faithful"

    alias = flat_body("bookify")
    assert "default alias" in alias
    assert "establishes `source-faithful`" in alias
    assert "establishes `teachable`" not in alias
    assert alias.count("establishes `") == 1


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["id"])
def test_each_invocation_expands_from_its_actual_command_asset(case: dict) -> None:
    fields, body = split_frontmatter(command_text(case["command"]))
    assert set(fields) == {"description"}, f"{case['command']} frontmatter: {sorted(fields)}"
    assert fields["description"].strip()
    for forbidden in ("agent", "model", "subagent", "subtask"):
        assert forbidden not in fields, f"{case['command']} hardcodes {forbidden}"

    assert len(re.findall(r"(?m)^\$ARGUMENTS$", body)) == 1

    expanded = expand(case)
    assert case["arguments"] in expanded, "the argument text must survive verbatim"
    for marker in case["expect"]["preserved"]:
        assert marker.lower() in expanded.lower(), f"{case['id']} expansion lost {marker!r}"
    assert "treat the user's composer attachments as the supplied source" in (
        " ".join(expanded.split()).lower()
    )


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["id"])
def test_entry_command_establishes_its_mode_without_a_mode_question(case: dict) -> None:
    body = flat_body(case["command"])
    mode = case["expect"]["mode"]

    assert f"establishes `{mode}`" in body
    assert "do not ask which mode" in body
    for offer in ("which mode would you like", "choose a mode", "select a mode"):
        assert offer not in body

    for index in occurrences(body, "which mode"):
        window = body[max(0, index - 60) : index]
        assert re.search(r"\b(not|never|no)\b", window), (
            f"{case['command']} asks which mode instead of establishing it"
        )

    assert not mode_question(expand(case))


@pytest.mark.parametrize(
    "case",
    [case for case in cases() if case["expect"]["conflict"]],
    ids=lambda case: case["id"],
)
def test_conflicting_mode_argument_gets_one_brief_resolution(case: dict) -> None:
    body = flat_body(case["command"])
    mode = case["expect"]["mode"]
    other_entry = case["expect"]["otherEntry"]
    other_mode = "teachable" if mode == "source-faithful" else "source-faithful"

    # The entry still establishes its own mode; the other mode is an alternative
    # entry, never a silent switch.
    assert f"establishes `{mode}`" in body
    assert f"establishes `{other_mode}`" not in body

    # A genuine conflict: the argument asks for the other mode.
    assert other_mode in case["arguments"].lower()

    # Exactly one brief resolution, naming the alternative entry.
    assert body.count("one brief resolution") == 1
    assert other_entry in body
    assert "do not switch modes silently" in body

    expanded = expand(case)
    assert "one brief resolution" in expanded
    assert other_entry in expanded

    # The argument text itself is not rewritten into a mode override.
    assert case["arguments"] in expanded


def test_command_assets_have_no_shell_interpolation_or_at_path_dependence() -> None:
    for name in EXPECTED:
        _, body = split_frontmatter(command_text(name))
        assert "```!" not in body, f"{name} contains a shell code block"
        assert not re.search(r"(?m)^\s*!", body), f"{name} contains a ! shell line"
        for line in body.splitlines():
            if "$ARGUMENTS" in line:
                assert "!" not in line, f"{name} puts arguments in a shell line: {line!r}"

        assert "@path" in body.lower(), f"{name} must warn about @path"
        for index in occurrences(body.lower(), "@path"):
            window = " ".join(body[max(0, index - 160) : index].split()).lower()
            assert re.search(r"do not\s+rely", window), (
                f"{name} appears to rely on @path expansion"
            )

    # Argument text is prompt text: substitution is literal, never shell input.
    for case in cases():
        expanded = expand(case)
        assert case["arguments"] in expanded
        assert not re.search(r"(?m)^\s*!", expanded), (
            f"{case['id']} expanded into a shell-looking line"
        )


@pytest.mark.parametrize("directory", [INSTALLED_COMMANDS, PROJECT_COMMANDS], ids=["global", "project"])
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_installed_command_copy_matches_canonical_when_present(directory: Path, name: str) -> None:
    installed = directory / f"{name}.md"
    if not installed.is_file():
        pytest.skip(f"no installed copy at {installed}")
    assert installed.read_bytes() == (COMMANDS / f"{name}.md").read_bytes(), (
        f"installed {installed} drifted from the canonical asset"
    )


def test_packaged_command_copy_matches_canonical_when_present() -> None:
    if not PAYLOAD_COMMANDS.is_dir():
        pytest.skip("no packaged command directory")
    for name in EXPECTED:
        packaged = PAYLOAD_COMMANDS / f"{name}.md"
        assert packaged.is_file(), f"packaged command missing: {packaged}"
        assert packaged.read_bytes() == (COMMANDS / f"{name}.md").read_bytes()


# ---------------------------------------------------------------------------
# Same-source books through the public record API
# ---------------------------------------------------------------------------


def portable_copy(mode: str, tmp_path: Path) -> Path:
    """Copy one book to a temp root with no pyproject above it.

    The copy is asserted byte-identical to the tracked record and manuscript, so
    the check exercises the approved artifacts, not a rewritten fixture.
    """
    source = CONTENT / mode
    target = tmp_path / mode
    shutil.copytree(source, target)
    for relative in ("authoring/record.json", "book.yaml"):
        assert (target / relative).read_bytes() == (source / relative).read_bytes()
    return target


def check_copy(mode: str, tmp_path: Path) -> tuple[Path, dict]:
    target = portable_copy(mode, tmp_path)
    payload = record.check(
        target / "authoring" / "record.json",
        manuscript_path=target / "book.yaml",
        source_path=SOURCE_FIXTURE,
    )
    return target, payload


def record_data(target: Path) -> dict:
    return json.loads((target / "authoring" / "record.json").read_text(encoding="utf-8"))


def manuscript_data(target: Path) -> dict:
    return yaml.safe_load((target / "book.yaml").read_text(encoding="utf-8"))


def blocks(manuscript: dict) -> list[dict]:
    return [block for section in manuscript["sections"] for block in section["blocks"]]


def test_source_fixture_hash_is_unchanged() -> None:
    assert sha256_file(SOURCE_FIXTURE) == SOURCE_SHA256


@pytest.mark.parametrize("mode", MODES)
def test_same_source_record_passes_its_mode_contract(mode: str, tmp_path: Path) -> None:
    target, payload = check_copy(mode, tmp_path)

    assert payload["ok"] is True
    assert payload["mode"] == mode
    assert payload["workspace"] is None
    assert payload["source"] == {
        "id": "source",
        "sha256": SOURCE_SHA256,
        "pages": 6,
        "intakeManifest": "intake/manifest.json",
    }
    assert payload["coverage"] == {"covered": 6, "merged": 0, "excluded": 0}
    assert payload["enrichment"] == {"requested": False, "permission": None, "sources": 0}
    assert payload["uncertainty"] == 1
    assert payload["derivations"]["total"] > 0

    data = record_data(target)
    assert data["schemaVersion"] == "1.0"
    assert data["mode"] == mode
    assert data["source"]["sha256"] == SOURCE_SHA256
    assert [entry["page"] for entry in data["coverage"]] == [1, 2, 3, 4, 5, 6]
    assert data["manuscriptSha256"] == payload["manuscript"]["sha256"]
    assert data["manuscriptRevision"] == payload["manuscript"]["revision"]


def test_strict_record_has_no_mode_leakage(tmp_path: Path) -> None:
    target, _ = check_copy("source-faithful", tmp_path)
    data = record_data(target)
    derivations = data["derivations"]
    kinds = {entry["kind"] for entry in derivations}

    assert "external" not in kinds
    assert "reorder" not in kinds
    assert data["enrichment"]["requested"] is False
    assert data["enrichment"]["permission"] is None
    assert data["enrichment"]["sources"] == []

    for entry in derivations:
        assert entry["citation"] is None
        if entry["kind"] in TEACHING_KINDS:
            assert entry.get("retained") is True, (
                f"strict teaching kind {entry['kind']} must be retained source content"
            )

    # Every teaching block in the manuscript is source content named by a
    # retained derivation of the matching kind.
    retained = {entry["kind"] for entry in derivations if entry.get("retained") is True}
    for block in blocks(manuscript_data(target)):
        expected = TEACHING_BLOCK_KINDS.get(block["type"])
        if expected is not None:
            assert expected in retained, f"{block['id']} has no retained source derivation"

    # Strict order: source-anchor pages never move backwards in document order.
    anchor_pages = [
        anchor["page"]
        for block in blocks(manuscript_data(target))
        for anchor in block.get("sourceAnchors", [])
    ]
    assert anchor_pages == sorted(anchor_pages)


def test_teachable_record_restructures_without_outside_material(tmp_path: Path) -> None:
    target, _ = check_copy("teachable", tmp_path)
    data = record_data(target)
    derivations = data["derivations"]
    kinds = {entry["kind"] for entry in derivations}

    assert "reorder" in kinds, "teachable mode must record its reorganisation"
    assert {"explain", "example", "assessment"} <= kinds
    assert "external" not in kinds
    assert data["enrichment"]["requested"] is False
    assert data["enrichment"]["sources"] == []

    for entry in derivations:
        assert entry["citation"] is None
        assert entry["anchors"], f"{entry['kind']} derivation lost its source anchors"
        assert entry["decision"].strip()
    assert any(decision.get("kind") == "reorder" for decision in data["decisions"])


@pytest.mark.parametrize("mode", MODES)
def test_unreadable_plate_is_recorded_as_uncertainty(mode: str, tmp_path: Path) -> None:
    target, payload = check_copy(mode, tmp_path)
    data = record_data(target)
    assert payload["uncertainty"] == len(data["uncertainty"]) == 1

    entry = data["uncertainty"][0]
    assert entry["sourceId"] == "source"
    assert entry["page"] == 6
    assert entry["note"].strip()

    by_id = {block["id"]: block for block in blocks(manuscript_data(target))}
    assert entry["blockId"] in by_id
    named = by_id[entry["blockId"]]
    assert named["type"] == "unresolved" or named.get("confidence") == "unreadable"


def test_tracked_teachable_record_checks_with_manuscript_and_no_workspace() -> None:
    payload = record.check(
        CONTENT / "teachable" / "authoring" / "record.json",
        manuscript_path=CONTENT / "teachable" / "book.yaml",
        source_path=SOURCE_FIXTURE,
    )
    assert payload["ok"] is True
    assert payload["mode"] == "teachable"
    assert payload["workspace"] is None
    assert payload["coverage"] == {"covered": 6, "merged": 0, "excluded": 0}


# ---------------------------------------------------------------------------
# Negative contracts on temporary copies
# ---------------------------------------------------------------------------


def mutate_copy(mode: str, tmp_path: Path, mutate) -> tuple[Path, Path]:
    target = portable_copy(mode, tmp_path)
    record_path = target / "authoring" / "record.json"
    data = record_data(target)
    mutate(data)
    record_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return target, record_path


def rejected(target: Path, record_path: Path) -> BookifyError:
    with pytest.raises(BookifyError) as error:
        record.check(record_path, manuscript_path=target / "book.yaml")
    assert error.value.code == "INPUT_INVALID"
    assert error.value.locator is not None
    assert str(record_path) in error.value.locator
    return error.value


def test_strict_record_with_reorder_is_rejected(tmp_path: Path) -> None:
    def add_reorder(data: dict) -> None:
        data["derivations"].append(
            {
                "kind": "reorder",
                "blockIds": ["b-s1-body"],
                "anchors": [{"sourceId": "source", "page": 1}],
                "citation": None,
                "decision": "Acceptance negative: a strict record may not reorder source content.",
            }
        )

    target, record_path = mutate_copy("source-faithful", tmp_path, add_reorder)
    error = rejected(target, record_path)

    assert "derivations[" in error.locator
    assert error.locator.endswith(".kind")
    assert "order" in error.message.lower() or "reorder" in error.message.lower()


def test_strict_record_with_external_enrichment_is_rejected(tmp_path: Path) -> None:
    def add_enrichment(data: dict) -> None:
        data["enrichment"] = {
            "requested": True,
            "permission": "The user allowed one public note.",
            "sources": [{"citation": "Public note (2026), note.md", "locator": "file:note.md"}],
        }

    target, record_path = mutate_copy("source-faithful", tmp_path, add_enrichment)
    error = rejected(target, record_path)

    assert "enrichment" in error.locator or "enrichment" in error.message.lower()
    assert "source-faithful" in error.message.lower()


def test_teachable_record_with_uncited_enrichment_is_rejected(tmp_path: Path) -> None:
    def declare_unused_source(data: dict) -> None:
        data["enrichment"] = {
            "requested": True,
            "permission": "The user allowed one public note.",
            "sources": [{"citation": "Public note (2026), note.md", "locator": "file:note.md"}],
        }

    target, record_path = mutate_copy("teachable", tmp_path, declare_unused_source)
    error = rejected(target, record_path)

    assert "enrichment.sources[0]" in error.locator
    assert "never cited" in error.message.lower()
