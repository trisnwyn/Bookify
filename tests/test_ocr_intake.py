"""OCR core intake: determinism, confidence, regions and failure modes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from helpers import ROOT
from bookify.errors import BookifyError
from bookify.intake import changes, manifest, ocr

FIXTURE = ROOT / "fixtures" / "ocr-capability" / "fixture.pdf"
DEV_ENGINE = ROOT / "tools" / "ocr" / "tesseract"
DEV_TESSDATA = ROOT / "vendor" / "ocr" / "tessdata"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _options(**overrides) -> ocr.OcrOptions:
    return ocr.OcrOptions(enabled=True, tesseract=DEV_ENGINE, tessdata=DEV_TESSDATA, **overrides)


@pytest.fixture(scope="module")
def intake(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict, Path]:
    previous = os.environ.get("BOOKIFY_OCR_ALLOW_DEV")
    os.environ["BOOKIFY_OCR_ALLOW_DEV"] = "1"
    out = tmp_path_factory.mktemp("ocr-intake")
    try:
        data = manifest.build(FIXTURE, out, ocr_options=_options())
    finally:
        if previous is None:
            os.environ.pop("BOOKIFY_OCR_ALLOW_DEV", None)
        else:
            os.environ["BOOKIFY_OCR_ALLOW_DEV"] = previous
    return data, out


def test_double_intake_is_byte_identical(intake: tuple[dict, Path], tmp_path: Path) -> None:
    first, first_out = intake
    previous = os.environ.get("BOOKIFY_OCR_ALLOW_DEV")
    os.environ["BOOKIFY_OCR_ALLOW_DEV"] = "1"
    try:
        second = manifest.build(FIXTURE, tmp_path, ocr_options=_options())
    finally:
        if previous is None:
            os.environ.pop("BOOKIFY_OCR_ALLOW_DEV", None)
        else:
            os.environ["BOOKIFY_OCR_ALLOW_DEV"] = previous

    assert first == second
    assert _sha(first_out / "manifest.json") == _sha(tmp_path / "manifest.json")
    for relative in (
        "ocr/page-001-region-01.tsv",
        "ocr/page-001-region-01.txt",
        "ocr/page-002-region-01.tsv",
        "ocr/page-002-region-01.txt",
        "ocr/page-003-region-01.tsv",
        "ocr/page-003-region-01.txt",
    ):
        assert _sha(first_out / relative) == _sha(tmp_path / relative), relative
    # The run log carries timings and must not be part of the manifest hash.
    assert "runlog" not in (first_out / "manifest.json").read_text()


def test_pin_change_invalidates_and_is_reported(intake: tuple[dict, Path], tmp_path: Path) -> None:
    first, _out = intake
    previous = os.environ.get("BOOKIFY_OCR_ALLOW_DEV")
    os.environ["BOOKIFY_OCR_ALLOW_DEV"] = "1"
    try:
        second = manifest.build(
            FIXTURE,
            tmp_path,
            ocr_options=_options(min_region_area_pt2=50_000.0),
        )
    finally:
        if previous is None:
            os.environ.pop("BOOKIFY_OCR_ALLOW_DEV", None)
        else:
            os.environ["BOOKIFY_OCR_ALLOW_DEV"] = previous

    diff = changes.diff(first, second)
    assert diff["ocrChangedPages"] == [1, 2, 3]
    assert first["ocr"]["pinSha256"] != second["ocr"]["pinSha256"]


def test_agreement_accepts_good_and_rejects_low_quality(intake: tuple[dict, Path]) -> None:
    data, _out = intake
    pages = {page["page"]: page for page in data["pages"]}

    good = pages[2]["ocr"]
    degraded = pages[3]["ocr"]

    assert good["status"] == "applied"
    assert good["agreement"] >= 0.98
    assert good["machineRead"] is True
    assert degraded["status"] == "below_threshold"
    assert degraded["agreement"] < 0.90
    assert degraded["eligibleLineCount"] == 0
    assert "agreement" in degraded["reason"]

    # The bands are applied per line and per region, and a high mean alone is
    # not enough: the capability proof measured agreement 0.8927 with mean 90.95.
    assert ocr.band_for(90.95, 0.0293, 0.8927) == "below_threshold"
    assert ocr.band_for(95.95, 0.0049, 0.9902) == "adequate"
    assert ocr.band_for(95.14, 0.0141, None) == "below_threshold"


def test_image_only_page_is_machine_read_or_unresolved(intake: tuple[dict, Path]) -> None:
    data, out = intake
    pages = {page["page"]: page for page in data["pages"]}

    readable = pages[2]
    assert readable["isImageOnly"] is True
    assert readable["charCount"] == 0
    assert readable["ocr"]["scope"] == "page"
    assert readable["ocr"]["status"] == "applied"
    assert readable["ocr"]["machineRead"] is True
    assert "Cash receipts journal" in (out / readable["ocr"]["textPath"]).read_text()

    degraded = pages[3]
    assert degraded["isImageOnly"] is True
    assert degraded["ocr"]["status"] == "below_threshold"
    assert degraded["ocr"]["wordCount"] > 0
    lines = [line for region in degraded["ocr"]["regions"] for line in region["lines"]]
    assert lines and all(line["eligible"] is False for line in lines)
    assert degraded["ocr"]["reason"]


def test_region_table_is_extracted_from_a_prose_page(intake: tuple[dict, Path]) -> None:
    data, out = intake
    page = next(item for item in data["pages"] if item["page"] == 1)
    record = page["ocr"]

    assert page["isImageOnly"] is False
    assert record["scope"] == "images"
    assert record["status"] == "applied"
    assert len(record["regions"]) == 1
    region = record["regions"][0]
    assert region["bbox"][0] > 40 and region["bbox"][2] < 560
    assert region["machineRead"] is True
    assert region["confidence"]["mean"] >= 90

    rows = ocr.reconstruct_table((out / region["tsvPath"]).read_bytes())
    flattened = [" | ".join(row) for row in rows]
    assert any("Cash at bank" in row and "12,480.00" in row for row in flattened)
    assert any("Totals" in row and "65,485.50" in row for row in flattened)

    # The prose page's text layer does not carry the table body.
    page_text = (out / "pages" / "page-001.txt").read_text()
    assert "12,480.00" not in page_text


def test_missing_engine_is_a_named_input_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("BOOKIFY_TESSERACT", raising=False)
    monkeypatch.delenv("BOOKIFY_TESSDATA", raising=False)
    monkeypatch.delenv("BOOKIFY_OCR_ALLOW_DEV", raising=False)
    original = shutil.which

    def no_tesseract(name: str) -> str | None:
        if name == "tesseract":
            return None
        return original(name)

    monkeypatch.setattr(shutil, "which", no_tesseract)

    with pytest.raises(BookifyError) as error:
        ocr.resolve(ocr.OcrOptions(enabled=True))
    assert error.value.code == "INPUT_INVALID"
    assert "OCR_ENGINE_MISSING" in error.value.message
    assert "dnf install tesseract" in error.value.message

    # The setup failure happens before a page is written.
    with pytest.raises(BookifyError) as error:
        manifest.build(
            FIXTURE,
            tmp_path,
            ocr_options=ocr.OcrOptions(enabled=True),
        )
    assert error.value.code == "INPUT_INVALID"
    assert not (tmp_path / "manifest.json").exists()


def test_changed_only_skips_with_the_same_source_and_pin(
    intake: tuple[dict, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _data, out = intake
    monkeypatch.setenv("BOOKIFY_OCR_ALLOW_DEV", "1")
    monkeypatch.setenv("BOOKIFY_TESSERACT", str(DEV_ENGINE))
    monkeypatch.setenv("BOOKIFY_TESSDATA", str(DEV_TESSDATA))
    from bookify.toolchain.cli import main

    assert main(["intake", "--source", str(FIXTURE), "--out", str(out), "--changed-only", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] is True
    assert payload["ocrChangedPages"] == []


def test_no_ocr_records_a_baseline_instead_of_silence(tmp_path: Path) -> None:
    built = manifest.build(FIXTURE, tmp_path, ocr_options=ocr.OcrOptions(enabled=False))
    statuses = {page["page"]: page["ocr"]["status"] for page in built["pages"]}

    assert statuses == {1: "skipped", 2: "skipped", 3: "skipped", 4: "not_required"}
    assert built["pages"][0]["ocr"]["skipReason"] == "disabled_by_flag"


@pytest.mark.skipif(not Path("/usr/bin/bwrap").is_file(), reason="bwrap is required for the sandbox proof")
def test_offline_sandbox_produces_the_same_measurement(tmp_path: Path) -> None:
    previous = os.environ.get("BOOKIFY_OCR_ALLOW_DEV")
    os.environ["BOOKIFY_OCR_ALLOW_DEV"] = "1"
    try:
        online = ocr.analyse_source(
            FIXTURE,
            tmp_path / "online",
            [(2, "")],
            _options(offline=False, allow_unsandboxed=True),
        )
        sandboxed = ocr.analyse_source(
            FIXTURE, tmp_path / "sandboxed", [(2, "")], _options(offline=True)
        )
    finally:
        if previous is None:
            os.environ.pop("BOOKIFY_OCR_ALLOW_DEV", None)
        else:
            os.environ["BOOKIFY_OCR_ALLOW_DEV"] = previous

    assert online["pages"][2]["agreement"] == sandboxed["pages"][2]["agreement"]
    assert online["pages"][2]["regions"][0]["tsvSha256"] == sandboxed["pages"][2]["regions"][0]["tsvSha256"]


def test_vie_is_pinned_but_opt_in() -> None:
    previous = os.environ.get("BOOKIFY_OCR_ALLOW_DEV")
    os.environ["BOOKIFY_OCR_ALLOW_DEV"] = "1"
    vietnamese = None
    try:
        english = ocr.resolve(_options())
        vietnamese = ocr.resolve(_options(lang="eng+vie"))
    finally:
        if previous is None:
            os.environ.pop("BOOKIFY_OCR_ALLOW_DEV", None)
        else:
            os.environ["BOOKIFY_OCR_ALLOW_DEV"] = previous

    assert vietnamese is not None
    assert [model["lang"] for model in english.identity.data] == ["eng"]
    assert [model["lang"] for model in vietnamese.identity.data] == ["eng", "vie"]
    assert english.identity.pin_sha256 != vietnamese.identity.pin_sha256
    with pytest.raises(BookifyError):
        ocr.resolve(_options(lang="jpn"))


def test_changed_only_ocr_reanalyzes_a_previous_no_ocr_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """C2: an existing --no-ocr manifest must not suppress a later --ocr run."""
    from bookify.toolchain.cli import main

    manifest.build(FIXTURE, tmp_path, ocr_options=ocr.OcrOptions(enabled=False))
    monkeypatch.setenv("BOOKIFY_OCR_ALLOW_DEV", "1")
    monkeypatch.setenv("BOOKIFY_TESSERACT", str(DEV_ENGINE))
    monkeypatch.setenv("BOOKIFY_TESSDATA", str(DEV_TESSDATA))

    assert main(["intake", "--source", str(FIXTURE), "--out", str(tmp_path), "--changed-only", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] is False
    assert payload["ocr"]["statuses"]["applied"] == 2
    rebuilt = json.loads((tmp_path / "manifest.json").read_text())
    assert rebuilt["ocr"]["pinSha256"]
    assert any(page["ocr"]["status"] == "applied" for page in rebuilt["pages"])


def test_changed_only_no_ocr_removes_stale_ocr_records(
    intake: tuple[dict, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """C2: switching a record back to --no-ocr must rebuild, not keep OCR text."""
    _data, out = intake
    monkeypatch.setenv("BOOKIFY_OCR_ALLOW_DEV", "1")
    from bookify.toolchain.cli import main

    assert main(["intake", "--source", str(FIXTURE), "--out", str(out), "--changed-only", "--no-ocr", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] is False
    rebuilt = json.loads((out / "manifest.json").read_text())
    assert "ocr" not in rebuilt
    assert all(page["ocr"]["status"] in {"skipped", "not_required"} for page in rebuilt["pages"])
    assert not list((out / "ocr").glob("page-*-region-*.tsv"))


def test_intake_extraction_is_sandboxed_and_logged(tmp_path: Path) -> None:
    """C3: offline is the default and the run log records the actual state."""
    source = manifest.build(FIXTURE, tmp_path, ocr_options=ocr.OcrOptions(enabled=False))
    assert source["pageCount"] == 4
    runlog = [
        json.loads(line)
        for line in (tmp_path / "ocr" / "runlog.jsonl").read_text().splitlines()
        if line
    ]
    extract_record = runlog[0]
    assert extract_record["phase"] == "extract"
    assert extract_record["sandbox"]["offline"] is True
    assert extract_record["sandbox"]["sandboxed"] is True
    assert "--unshare-net" in extract_record["sandbox"]["argv"]


def _runlog(out: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (out / "ocr" / "runlog.jsonl").read_text().splitlines()
        if line
    ]


def test_cli_default_intake_is_sandboxed_and_allow_unsandboxed_changes_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """M4b/C3: the CLI, not only the library default, wires the sandbox."""
    if not Path("/usr/bin/bwrap").is_file():
        pytest.skip("bwrap is required to observe the sandboxed argv")
    from bookify.toolchain.cli import main

    default_out = tmp_path / "default"
    assert main(
        [
            "intake", "--source", str(FIXTURE), "--out", str(default_out),
            "--changed-only", "--no-ocr", "--json",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] is False
    record = next(item for item in _runlog(default_out) if item["phase"] == "extract")
    assert record["sandbox"]["offline"] is True
    assert record["sandbox"]["sandboxed"] is True
    assert record["sandbox"]["unsandboxedExplicit"] is False
    assert Path(record["sandbox"]["argv"][0]).name == "bwrap"
    assert "--unshare-net" in record["sandbox"]["argv"]
    assert "--die-with-parent" in record["sandbox"]["argv"]

    explicit_out = tmp_path / "explicit"
    assert main(
        [
            "intake", "--source", str(FIXTURE), "--out", str(explicit_out),
            "--changed-only", "--no-ocr", "--allow-unsandboxed", "--json",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] is False
    explicit = next(item for item in _runlog(explicit_out) if item["phase"] == "extract")
    assert explicit["sandbox"]["offline"] is False
    assert explicit["sandbox"]["sandboxed"] is False
    assert explicit["sandbox"]["unsandboxedExplicit"] is True
    assert explicit["sandbox"]["argv"] == []


def test_cli_sandbox_default_fails_closed_without_bwrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """M4b/C3: the default is the sandbox even when bwrap is missing."""
    from bookify.toolchain.cli import main

    monkeypatch.setattr("bookify.intake.sandbox.bwrap_path", lambda: None)
    assert main(["intake", "--source", str(FIXTURE), "--out", str(tmp_path), "--no-ocr", "--json"]) == 3
    error = json.loads(capsys.readouterr().err)
    assert error["code"] == "BUILD_FAILED"
    assert "allow-unsandboxed" in error["message"]
    assert not (tmp_path / "manifest.json").exists()

    assert main(
        [
            "intake", "--source", str(FIXTURE), "--out", str(tmp_path / "pass"),
            "--no-ocr", "--allow-unsandboxed", "--json",
        ]
    ) == 0
    record = next(item for item in _runlog(tmp_path / "pass") if item["phase"] == "extract")
    assert record["sandbox"]["offline"] is False
    assert record["sandbox"]["unsandboxedExplicit"] is True


def test_unsandboxed_intake_requires_the_explicit_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """C3: a missing sandbox fails closed unless the caller opts in."""
    monkeypatch.setattr("bookify.intake.sandbox.bwrap_path", lambda: None)
    with pytest.raises(BookifyError) as error:
        manifest.build(
            FIXTURE,
            tmp_path,
            ocr_options=ocr.OcrOptions(enabled=False, offline=True),
        )
    assert error.value.code == "BUILD_FAILED"
    assert "allow-unsandboxed" in error.value.message

    built = manifest.build(
        FIXTURE,
        tmp_path,
        ocr_options=ocr.OcrOptions(enabled=False, offline=False, allow_unsandboxed=True),
    )
    assert built["pageCount"] == 4
    record = json.loads((tmp_path / "ocr" / "runlog.jsonl").read_text().splitlines()[0])
    assert record["sandbox"]["offline"] is False
    assert record["sandbox"]["unsandboxedExplicit"] is True


def test_extraction_timeout_is_source_unreadable() -> None:
    """C3: a hanging extractor is killed by the per-command timeout."""
    import subprocess as sp

    from bookify.intake import sandbox

    def hang(*_args: object, **_kwargs: object):
        raise sp.TimeoutExpired(["pdftotext"], 0.1)

    previous = sandbox.subprocess.run
    sandbox.subprocess.run = hang  # type: ignore[assignment]
    try:
        with pytest.raises(BookifyError) as error:
            sandbox.run(
                ["pdftotext", "source.pdf", "-"],
                sandbox.SandboxPolicy(offline=False, allow_unsandboxed=True, timeout=0.1),
            )
    finally:
        sandbox.subprocess.run = previous  # type: ignore[assignment]
    assert error.value.code == "SOURCE_UNREADABLE"
    assert "timeout" in error.value.message


def test_source_caps_are_enforced_before_extraction(tmp_path: Path) -> None:
    """C4: page and byte caps fail fast, with --no-ocr too, and name the limit."""
    from bookify.intake import caps

    huge = tmp_path / "huge.pdf"
    huge.write_bytes(b"%PDF-1.4\n")
    with huge.open("r+b") as handle:
        handle.truncate(caps.CAP_PDF_BYTES + 1)
    with pytest.raises(BookifyError) as error:
        manifest.build(huge, tmp_path / "huge-out", ocr_options=ocr.OcrOptions(enabled=False))
    assert error.value.code == "INPUT_INVALID"
    assert str(caps.CAP_PDF_BYTES) in error.value.message
    assert "bytes" in error.value.locator
    assert not (tmp_path / "huge-out" / "manifest.json").exists()

    many = _synthetic_pdf(tmp_path / "many.pdf", caps.CAP_PAGES + 2)
    with pytest.raises(BookifyError) as error:
        manifest.build(many, tmp_path / "many-out", ocr_options=ocr.OcrOptions(enabled=False))
    assert error.value.code == "INPUT_INVALID"
    assert str(caps.CAP_PAGES) in error.value.message
    assert "pages" in error.value.locator
    assert not (tmp_path / "many-out" / "manifest.json").exists()


def _synthetic_pdf(path: Path, pages: int) -> Path:
    """A tiny valid PDF with many empty pages (same content object)."""
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + index} 0 R" for index in range(pages))
    objects.append(f"<< /Type /Pages /Count {pages} /Kids [{kids}] >>".encode())
    content = b"<< /Length 0 >>\nstream\n\nendstream"
    content_object = 3 + pages
    for index in range(pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_object} 0 R >>".encode()
        )
    objects.append(content)
    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode()
    output += b"0000000000 65535 f \n"
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(output))
    return path


def test_small_image_on_a_text_page_is_recorded_too_small(tmp_path: Path) -> None:
    """R2: a 72x48 placement is skipped with reason, never upscaled into text."""
    from helpers import compile_typ

    source = compile_typ(
        '#set page(paper: "a4", margin: 40pt)\n'
        "This page carries a short text layer and a tiny logo-like image.\n"
        '#image("/assets/illustrations/photo-1/original.jpg", width: 72pt, height: 48pt)\n',
        "ocr-too-small",
    )
    built = manifest.build(source, tmp_path, ocr_options=_options())
    record = built["pages"][0]["ocr"]
    assert record["status"] == "skipped"
    assert record["skipReason"] == "too_small"
    assert record["tooSmallRegions"]
    assert record["tooSmallRegions"][0]["reason"] == "too_small"


def test_path_shim_resolves_as_the_system_path_with_a_distinct_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C5: a PATH resolution test, not a claim that a distro package was used.

    The shim script execs the pinned development binary; the manifest therefore
    records `engine.source: "path"` and the shim's own hash. This proves the
    resolution order and the pin boundary, not a system package's bytes.
    """
    bin_dir = tmp_path / "pathbin"
    bin_dir.mkdir()
    shim = bin_dir / "tesseract"
    shim.write_text(f'#!/bin/sh\nexec "{DEV_ENGINE}" "$@"\n')
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.delenv("BOOKIFY_TESSERACT", raising=False)
    monkeypatch.setenv("BOOKIFY_TESSDATA", str(DEV_TESSDATA))
    monkeypatch.delenv("BOOKIFY_OCR_ALLOW_DEV", raising=False)

    resolved = ocr.resolve(ocr.OcrOptions(enabled=True))
    assert resolved.identity.source == "path"
    assert resolved.identity.development_only is False
    assert resolved.identity.binary_sha256 == hashlib.sha256(shim.read_bytes()).hexdigest()

    previous = os.environ.get("BOOKIFY_OCR_ALLOW_DEV")
    os.environ["BOOKIFY_OCR_ALLOW_DEV"] = "1"
    try:
        development = ocr.resolve(_options())
    finally:
        if previous is None:
            os.environ.pop("BOOKIFY_OCR_ALLOW_DEV", None)
        else:
            os.environ["BOOKIFY_OCR_ALLOW_DEV"] = previous
    assert development.identity.development_only is True
    assert resolved.identity.pin_sha256 != development.identity.pin_sha256

    second = bin_dir / "tesseract"
    second.write_text(f'#!/bin/sh\n# same version, different bytes\nexec "{DEV_ENGINE}" "$@"\n')
    second.chmod(0o755)
    changed = ocr.resolve(ocr.OcrOptions(enabled=True))
    assert changed.identity.pin_sha256 != resolved.identity.pin_sha256
