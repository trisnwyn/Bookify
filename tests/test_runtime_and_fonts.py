"""Tests for Phase 2 runtime path decoupling and optional CJK font pack."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bookify import runtime
from bookify.errors import BookifyError
from bookify.publish import typst_driver
from bookify.toolchain import cli, fonts
from helpers import ROOT


def test_runtime_engine_root_finds_checkout_and_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert runtime.engine_root() == ROOT
    fake = tmp_path / "engine"
    (fake / "typst").mkdir(parents=True)
    (fake / "schemas").mkdir(parents=True)
    monkeypatch.setenv(runtime.ENGINE_ENV, str(fake))
    assert runtime.engine_root() == fake.resolve()


def test_runtime_rejects_invalid_engine_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(runtime.ENGINE_ENV, str(tmp_path))
    with pytest.raises(BookifyError) as exc:
        runtime.engine_root()
    assert exc.value.code == "INPUT_INVALID"


def test_cjk_font_install_verifies_hash_and_rejects_corrupt_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.ttc"
    bad.write_bytes(b"not a real font")
    with pytest.raises(BookifyError) as exc:
        fonts.install_cjk(target_dir=tmp_path / "cache", from_file=bad)
    assert exc.value.code == "FONT_MISSING"
    assert "mismatch" in exc.value.message

    source_cjk = ROOT / fonts.CJK_FONT_RELATIVE
    if source_cjk.is_file():
        res = fonts.install_cjk(target_dir=tmp_path / "cache", from_file=source_cjk)
        assert res["ok"] is True
        assert (tmp_path / "cache" / fonts.CJK_FONT_FILENAME).is_file()
        again = fonts.install_cjk(target_dir=tmp_path / "cache", from_file=source_cjk)
        assert again["status"] == "already-installed"


def test_standalone_book_builds_outside_repo_without_workspace_flag(tmp_path: Path) -> None:
    book_yaml = tmp_path / "book.yaml"
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "standalone-test",
        "metadata": {"title": "Standalone Directory Build", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-one",
                "title": "Standalone",
                "level": 1,
                "blocks": [{"id": "b-1", "type": "paragraph", "text": "Built outside the engine checkout."}],
            }
        ],
    }
    book_yaml.write_text(yaml.safe_dump(data, sort_keys=False))
    out_pdf = tmp_path / "out.pdf"
    result = typst_driver.build(book_yaml, out_pdf, tmp_path / "build", offline=True)
    assert out_pdf.is_file()
    assert result.report["pdf"]["pages"] >= 3


def test_standalone_relative_paths_resolve_from_cwd_not_doubled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sub = tmp_path / "books" / "demo"
    sub.mkdir(parents=True)
    book_yaml = sub / "book.yaml"
    book_yaml.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "relative-cwd-test",
                "metadata": {"title": "Relative Path Build", "languages": ["en"]},
                "sections": [
                    {
                        "id": "sec-one",
                        "title": "Relative",
                        "level": 1,
                        "blocks": [{"id": "b-1", "type": "paragraph", "text": "Relative path resolution check."}],
                    }
                ],
            },
            sort_keys=False,
        )
    )
    monkeypatch.chdir(tmp_path)
    result = typst_driver.build(Path("books/demo/book.yaml"), Path("books/demo/out.pdf"), Path("books/demo/build"), offline=True)
    assert result.pdf == (sub / "out.pdf").resolve()
    assert (sub / "out.pdf").is_file()


def test_cli_fonts_status_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["fonts", "status", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"pack": "cjk"' in out
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
