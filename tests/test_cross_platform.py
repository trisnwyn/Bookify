"""Tests for Phase 3 cross-platform Typst installer, sandbox tiers, portable doctor, and Pillow contact sheet."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest
import yaml
from PIL import Image

from bookify.figures import contact_sheet
from bookify.publish import typst_driver
from bookify.toolchain import cli, doctor, typst_install
from helpers import ROOT


def test_platform_normalization_covers_linux_macos_windows() -> None:
    assert typst_install.normalized_platform("linux", "x86_64") == ("linux", "x86_64")
    assert typst_install.normalized_platform("linux", "aarch64") == ("linux", "aarch64")
    assert typst_install.normalized_platform("darwin", "arm64") == ("darwin", "arm64")
    assert typst_install.normalized_platform("darwin", "x86_64") == ("darwin", "x86_64")
    assert typst_install.normalized_platform("win32", "AMD64") == ("win32", "x86_64")
    assert typst_install.binary_name("win32") == "typst.exe"
    assert typst_install.binary_name("darwin") == "typst"
    for key in (("linux", "x86_64"), ("linux", "aarch64"), ("darwin", "arm64"), ("darwin", "x86_64"), ("win32", "x86_64")):
        assert key in typst_install.PLATFORM_ARCHIVES


def test_install_typst_from_local_tar_archive(tmp_path: Path) -> None:
    src_bin = ROOT / "tools" / "typst" / "typst"
    archive = tmp_path / "typst-test.tar"
    with tarfile.open(archive, "w") as tf:
        tf.add(src_bin, arcname="typst-0.15.1/typst")

    res = typst_install.install_typst(from_archive=archive, cache_root=tmp_path / "bin")
    assert res["ok"] is True
    assert res["status"] == "installed"
    assert "0.15.1" in str(res["version"])
    installed = Path(str(res["path"]))
    assert installed.is_file()

    res2 = typst_install.install_typst(from_archive=archive, cache_root=tmp_path / "bin")
    assert res2["status"] == "already-installed"


def test_env_isolated_sandbox_builds_byte_identically_without_bwrap(tmp_path: Path) -> None:
    book_yaml = tmp_path / "book.yaml"
    book_yaml.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "portable-sandbox-test",
                "metadata": {"title": "Portable Sandbox Build", "languages": ["en"]},
                "sections": [
                    {
                        "id": "sec-1",
                        "title": "Portable Build",
                        "level": 1,
                        "blocks": [
                            {"id": "b-1", "type": "paragraph", "text": "Compiled without bwrap using local env isolation."},
                            {"id": "b-eq", "type": "equation", "typst": "e^(i pi) + 1 = 0", "caption": "Euler identity."},
                        ],
                    }
                ],
            },
            sort_keys=False,
        )
    )
    pdf_a = tmp_path / "a.pdf"
    pdf_b = tmp_path / "b.pdf"
    res_a = typst_driver.build(book_yaml, pdf_a, tmp_path / "build-a", offline=True, sandbox="none")
    res_b = typst_driver.build(book_yaml, pdf_b, tmp_path / "build-b", offline=True, sandbox="none")
    assert res_a.report["sandbox"]["mode"] == "env-isolated"
    assert res_a.report["sandbox"]["bwrap"] is False
    assert pdf_a.read_bytes() == pdf_b.read_bytes()


def test_portable_doctor_mode_passes_without_strict_venv_pin() -> None:
    report = doctor.run(ROOT, strict=False)
    assert report.ok, report.summary()


def test_pillow_contact_sheet_builds_without_imagemagick(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    for idx in range(1, 6):
        img = Image.new("RGB", (300, 420), (255, 255, 255))
        img.save(pages_dir / f"page-{idx}.png")
    out_png = tmp_path / "contact.png"
    rc = cli.main(["figures", "contact-sheet", "--pages-dir", str(pages_dir), "--out", str(out_png), "--cols", "3", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["pages"] == 5
    assert payload["columns"] == 3
    assert payload["rows"] == 2
    assert out_png.is_file()
    with Image.open(out_png) as sheet:
        assert sheet.size == tuple(payload["size"])
