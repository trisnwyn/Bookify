"""Tests for Phase 4 multi-platform skill packaging and platform adapters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bookify.errors import BookifyError
from bookify.toolchain import cli, skill_install
from helpers import ROOT


def test_portable_skill_tree_is_lightweight_and_platform_neutral() -> None:
    skill_dir = ROOT / "skills" / "bookify"
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file()

    text = skill_md.read_text()
    assert text.startswith("---\nname: bookify\n")
    assert "pdf-book-design" not in text
    assert ".config/opencode" not in text
    assert "sudo dnf" not in text

    total_bytes = sum(p.stat().st_size for p in skill_dir.rglob("*") if p.is_file())
    assert total_bytes < 120_000, f"portable skill too large: {total_bytes} bytes"
    for ref in ("checklist.md", "editorial.md", "limits.md", "modes-and-playbooks.md", "source-and-provenance.md", "visual-design.md"):
        assert (skill_dir / "references" / ref).is_file()
    for cmd in ("bookify.md", "bookify-source-faithful.md", "bookify-teachable-textbook.md"):
        assert (skill_dir / "commands" / cmd).is_file()


def test_claude_plugin_manifests_are_valid_and_point_to_existing_paths() -> None:
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["name"] == "bookify"
    for rel in plugin["skills"] + plugin["commands"]:
        assert (ROOT / rel).is_dir(), f"missing plugin path: {rel}"
    assert market["plugins"][0]["name"] == "bookify"


def test_skill_install_covers_all_five_platforms_safely(tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    res = skill_install.install_skill("all", scope="global", home=fake_home, engine=ROOT)
    assert res["ok"] is True
    assert len(res["results"]) == 5

    expected_dirs = [
        fake_home / ".claude" / "skills" / "bookify" / "SKILL.md",
        fake_home / ".agents" / "skills" / "bookify" / "SKILL.md",
        fake_home / ".config" / "opencode" / "skills" / "bookify" / "SKILL.md",
        fake_home / ".cursor" / "skills" / "bookify" / "SKILL.md",
        fake_home / ".gemini" / "config" / "skills" / "bookify" / "SKILL.md",
    ]
    for path in expected_dirs:
        assert path.is_file(), f"missing installed skill: {path}"
    assert (fake_home / ".claude" / "commands" / "bookify.md").is_file()
    assert (fake_home / ".config" / "opencode" / "commands" / "bookify-teachable-textbook.md").is_file()

    # Re-installing over an existing Bookify skill succeeds cleanly (upgrade path)
    upgrade = skill_install.install_skill("claude", scope="global", home=fake_home, engine=ROOT)
    assert upgrade["ok"] is True


def test_skill_install_refuses_to_clobber_unrelated_directory(tmp_path: Path) -> None:
    unrelated = tmp_path / "custom-dir"
    unrelated.mkdir()
    (unrelated / "notes.txt").write_text("do not delete me")

    with pytest.raises(BookifyError) as exc:
        skill_install.install_skill("cursor", target_override=unrelated, engine=ROOT)
    assert exc.value.code == "INPUT_INVALID"
    assert (unrelated / "notes.txt").is_file()


def test_cli_skill_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["skill", "list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    names = {row["platform"] for row in payload["platforms"]}
    assert {"claude", "codex", "opencode", "cursor", "antigravity", "agents"} <= names
