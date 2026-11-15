"""Task 61: external per-book workspace, read-only engine and legacy compatibility."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.publish import typst_driver
from bookify.toolchain.cli import main

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"
ENGINE_ASSET_DIRS = ("typst", "assets/fonts", "vendor/typst", "tools")
ENGINE_FILES = ("toolchain.lock.json",)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in names:
        path = root / name
        if path.is_file():
            hashes[name] = _digest(path)
    return hashes


def engine_snapshot() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in ENGINE_ASSET_DIRS:
        base = ROOT / name
        for path in sorted(base.rglob("*")):
            if path.is_file():
                hashes[path.relative_to(ROOT).as_posix()] = _digest(path)
    hashes.update(_hashes(ROOT, ENGINE_FILES))
    return hashes


def _specimen_workspace(path: Path) -> Path:
    """A public-safe book workspace holding the specimen manuscript and its asset."""
    if path.exists():
        return path
    path.mkdir(parents=True)
    shutil.copyfile(SPECIMEN, path / "book.yaml")
    shutil.copytree(
        ROOT / "assets" / "illustrations" / "photo-1",
        path / "assets" / "illustrations" / "photo-1",
    )
    return path


def _small_manuscript(path: Path, *, title: str) -> Path:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "small-book",
        "metadata": {"title": title, "languages": ["en"]},
        "sections": [
            {
                "id": "sec-one",
                "title": "One",
                "blocks": [
                    {
                        "id": "b-one",
                        "type": "paragraph",
                        "text": "A short, source-grounded paragraph for an isolated workspace.",
                        "sourceAnchors": [{"sourceId": "source-slug", "page": 1}],
                    }
                ],
            }
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _specimen_workspace(tmp_path_factory.mktemp("skill-workspace") / "book")


@pytest.fixture(scope="module")
def built(workspace: Path) -> typst_driver.BuildResult:
    return typst_driver.build(
        workspace / "book.yaml",
        workspace / "dist" / "book.pdf",
        workspace / "build" / "book",
        offline=True,
        workspace=workspace,
    )


def test_external_workspace_build_writes_only_inside_the_workspace(workspace: Path, built: typst_driver.BuildResult) -> None:
    assert built.pdf == (workspace / "dist" / "book.pdf").resolve()
    assert built.pdf.is_file()
    # Phase 2 layout correction: corrected leading reflows the specimen to 5.
    # Bookify v2 D4: designed cover + chapter opener reflow the specimen to 6.
    assert built.report["pdf"]["pages"] == 6
    assert built.report["offline"] is True
    assert (workspace / "build" / "book" / "build-report.json").is_file()
    assert built.report["pdf"]["path"] == str((workspace / "dist" / "book.pdf").resolve())
    staged = workspace / "build" / "book" / "typst-root"
    assert not (staged / "typst" / "templates" / "book.typ").exists()
    assert (staged / "typst").is_dir() and (staged / "engine-assets" / "fonts").is_dir()
    assert all(entry["path"].startswith("/figures/") for entry in built.report["figures"])


def test_workspace_build_matches_legacy_layout_and_text(workspace: Path, built: typst_driver.BuildResult) -> None:
    legacy_out = ROOT / ".cache" / "skill-workspace-legacy" / "specimen.pdf"
    legacy = typst_driver.build(
        SPECIMEN,
        legacy_out,
        ROOT / ".cache" / "skill-workspace-legacy" / "book",
        offline=True,
    )
    new_text = subprocess.run(
        ["pdftotext", "-layout", str(built.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    old_text = subprocess.run(
        ["pdftotext", "-layout", str(legacy.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout

    assert new_text == old_text
    assert built.report["pdf"]["pages"] == legacy.report["pdf"]["pages"]
    assert [item["page"] for item in built.report["placements"]] == [
        item["page"] for item in legacy.report["placements"]
    ]


def test_engine_tree_is_read_only_across_a_workspace_build(workspace: Path, built: typst_driver.BuildResult) -> None:
    before = engine_snapshot()
    second = typst_driver.build(
        workspace / "book.yaml",
        workspace / "dist" / "book-rebuild.pdf",
        workspace / "build" / "book-rebuild",
        offline=True,
        workspace=workspace,
    )

    assert engine_snapshot() == before
    assert second.report["pdf"]["sha256"] == built.report["pdf"]["sha256"]


def test_workspace_figures_and_design_checks_use_engine_fonts(workspace: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([
        "figures", "render",
        "--workspace", str(workspace),
        "--manuscript", str(workspace / "book.yaml"),
        "--out", str(workspace / "build" / "figures"),
        "--json",
    ]) == 0
    figures = json.loads(capsys.readouterr().out)
    assert {entry["kind"] for entry in figures["figures"]} == {"chart", "diagram"}
    assert all((workspace / "build" / "figures") in Path(entry["path"]).parents for entry in figures["figures"])

    assert main([
        "design", "check",
        "--workspace", str(workspace),
        "--manuscript", str(workspace / "book.yaml"),
        "--json",
    ]) == 0
    design = json.loads(capsys.readouterr().out)
    assert design["ok"] is True


def test_workspace_manuscript_check_and_env_fallback(workspace: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([
        "manuscript", "check",
        "--workspace", str(workspace),
        "--manuscript", str(workspace / "book.yaml"),
        "--json",
    ]) == 0
    flag = json.loads(capsys.readouterr().out)
    assert flag["workspace"] == str(workspace.resolve())

    monkeypatch.setenv("BOOKIFY_WORKSPACE", str(workspace))
    assert main(["manuscript", "check", "--manuscript", str(workspace / "book.yaml"), "--json"]) == 0
    environment = json.loads(capsys.readouterr().out)
    assert environment["workspace"] == str(workspace.resolve())


def test_workspace_build_and_pages_are_verifyable(workspace: Path, built: typst_driver.BuildResult) -> None:
    previous = workspace / "dist" / "book-rebuild.pdf"
    if not previous.is_file():
        typst_driver.build(
            workspace / "book.yaml",
            previous,
            workspace / "build" / "book-rebuild",
            offline=True,
            workspace=workspace,
        )
    pages = workspace / "build" / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftoppm", "-png", "-r", "50", str(built.pdf), str(pages / "page")], check=True)
    sheet = workspace / "build" / "contact.png"
    subprocess.run(
        ["magick", "montage", *[str(path) for path in sorted(pages.glob("page-*.png"))], "-tile", "3x", str(sheet)],
        check=True,
    )
    build_report = json.loads((workspace / "build" / "book" / "build-report.json").read_text())
    decisions = {
        warning["id"]: "Checked the rendered page; the density is deliberate."
        for warning in build_report.get("readability", {}).get("warnings", [])
    }
    # This short fixture has no level-2/3 heading; rhythm reports both bands as
    # unmeasured and the review must answer them.
    decisions.update(
        {
            "rhythm:unmeasured:h2": "The fixture has no level-2 heading; the band is measured in the design fixture.",
            "rhythm:unmeasured:h3": "The fixture has no level-3 heading; the band is pinned by the design fixture.",
        }
    )
    (workspace / "build" / "review-notes.json").write_text(json.dumps(decisions))
    assert main([
        "verify",
        "--workspace", str(workspace),
        "--pdf", str(built.pdf),
        "--manuscript", str(workspace / "book.yaml"),
        "--previous-pdf", str(workspace / "dist" / "book-rebuild.pdf"),
        "--build-report", str(workspace / "build" / "book" / "build-report.json"),
        "--contact-sheet", str(sheet),
        "--reviewed-by", "agent",
        "--reviewed-at", "2026-11-12T00:00:00+00:00",
        "--review-notes", str(workspace / "build" / "review-notes.json"),
        "--report", str(workspace / "build" / "verify.json"),
        "--json",
    ]) == 0
    report = json.loads((workspace / "build" / "verify.json").read_text())
    assert report["gate"] == "pass"
    assert report["pins"]["typst"]


def test_build_directory_outside_the_workspace_fails(workspace: Path) -> None:
    with pytest.raises(BookifyError) as error:
        typst_driver.build(
            workspace / "book.yaml",
            workspace / "dist" / "escape.pdf",
            ROOT / ".cache" / "outside-build",
            offline=True,
            workspace=workspace,
        )

    assert error.value.code == "BUILD_FAILED"
    assert "workspace" in error.value.message


def test_output_pdf_outside_the_workspace_fails(workspace: Path) -> None:
    with pytest.raises(BookifyError) as error:
        typst_driver.build(
            workspace / "book.yaml",
            ROOT / ".cache" / "outside.pdf",
            workspace / "build" / "book",
            offline=True,
            workspace=workspace,
        )

    assert error.value.code == "BUILD_FAILED"


def test_symlinked_build_directory_cannot_escape_the_workspace(workspace: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace / "build" / "escape-link"
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BookifyError) as error:
        typst_driver.build(
            workspace / "book.yaml",
            workspace / "dist" / "escape-link.pdf",
            link / "book",
            offline=True,
            workspace=workspace,
        )

    assert error.value.code == "BUILD_FAILED"


def test_workspace_inside_the_engine_is_refused(tmp_path: Path) -> None:
    inside_engine = ROOT / ".cache" / "workspace-inside-engine"
    inside_engine.mkdir(parents=True, exist_ok=True)
    manuscript = _small_manuscript(tmp_path / "book.yaml", title="Refused")

    with pytest.raises(BookifyError) as error:
        typst_driver.build(manuscript, tmp_path / "x.pdf", tmp_path / "build", offline=True, workspace=inside_engine)

    assert error.value.code == "INPUT_INVALID"
    assert "engine" in error.value.message


def test_manuscript_outside_the_workspace_is_refused(tmp_path: Path, workspace: Path) -> None:
    stray = _small_manuscript(tmp_path / "book.yaml", title="Stray")

    with pytest.raises(BookifyError) as error:
        model.load(stray, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "workspace" in error.value.message


def test_verify_report_outside_the_workspace_is_refused(workspace: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([
        "verify",
        "--workspace", str(workspace),
        "--pdf", str(workspace / "dist" / "book.pdf"),
        "--manuscript", str(workspace / "book.yaml"),
        "--report", str(tmp_path / "verify.json"),
        "--json",
    ]) == 3
    assert "BUILD_FAILED" in capsys.readouterr().err


def test_two_workspaces_share_no_mutable_state(tmp_path: Path) -> None:
    first = tmp_path / "book-a"
    second = tmp_path / "book-b"
    for workspace in (first, second):
        workspace.mkdir(parents=True)
        _small_manuscript(workspace / "book.yaml", title=f"Book {workspace.name}")
        (workspace / "authoring").mkdir()
        (workspace / "authoring" / "record.json").write_text('{"mode": "source-faithful"}')
    second_before = _hashes(second, ("book.yaml", "authoring/record.json"))

    typst_driver.build(
        first / "book.yaml",
        first / "dist" / "book.pdf",
        first / "build" / "book",
        offline=True,
        workspace=first,
    )

    assert _hashes(second, ("book.yaml", "authoring/record.json")) == second_before
    assert not (second / "build").exists()
    assert not (second / "dist").exists()

    typst_driver.build(
        second / "book.yaml",
        second / "dist" / "book.pdf",
        second / "build" / "book",
        offline=True,
        workspace=second,
    )
    first_report = json.loads((first / "build" / "book" / "build-report.json").read_text())
    second_report = json.loads((second / "build" / "book" / "build-report.json").read_text())
    assert first_report["pdf"]["path"] == str((first / "dist" / "book.pdf").resolve())
    assert second_report["pdf"]["path"] == str((second / "dist" / "book.pdf").resolve())
    assert first_report["pdf"]["sha256"] != second_report["pdf"]["sha256"]

    shutil.rmtree(first / "build")
    assert (first / "book.yaml").is_file()
    assert (first / "authoring" / "record.json").is_file()
    assert (second / "build" / "book" / "build-report.json").is_file()


def test_legacy_root_discovery_is_unchanged() -> None:
    manuscript = model.load(SPECIMEN)

    assert manuscript.root == ROOT
    assert manuscript.engine == ROOT
    assert manuscript.workspace is None
    loaded = model.load(SPECIMEN, root=ROOT)
    assert loaded.root == ROOT


def test_legacy_build_arguments_keep_working(tmp_path: Path) -> None:
    result = typst_driver.build(
        SPECIMEN,
        tmp_path / "specimen.pdf",
        ROOT / ".cache" / "skill-workspace-legacy-args" / "book",
        offline=True,
    )

    assert result.pdf.is_file()
    assert result.report["pdf"]["pages"] == 6
