"""OCR provenance: machine-read marking, region anchors and verification."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

from helpers import ROOT, SPECIMEN
from bookify.authoring import record as author_record
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.publish import typst_driver
from bookify.verify import runner as verify_runner
from bookify.verify.checks import machine_read, ocr_free

SOURCE_ID = "ocr-source"
SOURCE_SHA = "a" * 64
CROSS_CHECK = "arithmetic opening+movement=closing"
NOTE = "Reconstructed from an image by OCR; values are machine-read and unverified."
DEV_ENGINE = ROOT / "tools" / "ocr" / "tesseract"
DEV_TESSDATA = ROOT / "vendor" / "ocr" / "tessdata"
OCR_FIXTURE = ROOT / "fixtures" / "ocr-capability" / "fixture.pdf"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _manuscript(*, machine: bool = True, verified: bool = False, digits: bool = True) -> dict[str, Any]:
    block: dict[str, Any] = {
        "id": "t-balances",
        "type": "table",
        "caption": "Selected balances",
        "header": ["Account", "Closing"],
        "rows": [["Cash at bank", "12,480.00"]] if digits else [["Cash at bank", "nil"]],
        "confidence": "verified" if verified else "inferred",
        "note": NOTE,
        "sourceAnchors": [{"sourceId": SOURCE_ID, "page": 1, "region": 1}],
    }
    if machine:
        block["machineRead"] = {
            "region": 1,
            "method": "ocr-table-v1",
            "confidence": 95.02,
            "crossCheckedBy": CROSS_CHECK,
        }
    return {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "ocr-book",
        "metadata": {"title": "OCR book", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-balances",
                "title": "Balances",
                "blocks": [block],
            }
        ],
    }


def _manifest() -> dict[str, Any]:
    engine = {
        "name": "tesseract",
        "version": "5.5.3",
        "source": "development-copy",
        "developmentOnly": True,
        "binary": "tesseract",
        "binarySha256": "b" * 64,
        "oem": 1,
        "pagePsm": 3,
        "regionPsm": 6,
        "threads": 1,
        "models": [{"lang": "eng", "sha256": "c" * 64}],
    }
    return {
        "schemaVersion": "1.0",
        "sourceId": SOURCE_ID,
        "sourceName": "ocr.pdf",
        "sourceSha256": SOURCE_SHA,
        "pageCount": 2,
        "ocr": {"pinSha256": "d" * 64},
        "pages": [
            {
                "page": 1,
                "textSha256": "e" * 64,
                "charCount": 20,
                "isImageOnly": False,
                "images": [],
                "ocr": {
                    "status": "applied",
                    "scope": "images",
                    "engine": engine,
                    "machineRead": True,
                    "pinSha256": "d" * 64,
                    "regions": [
                        {
                            "index": 1,
                            "bbox": [56.72, 222.89, 539.22, 483.16],
                            "band": "adequate",
                            "confidence": {"mean": 95.02, "minLine": 95.02, "lowConfidenceShare": 0.0},
                            "agreement": 1.0,
                            "eligibleLineCount": 1,
                            "lineCount": 1,
                            "wordCount": 4,
                            "machineRead": True,
                            "lines": [
                                {
                                    "index": 1,
                                    "text": "Cash at bank 12,480.00",
                                    "confidence": 95.02,
                                    "agreement": 1.0,
                                    "band": "adequate",
                                    "eligible": True,
                                }
                            ],
                        }
                    ],
                },
            },
            {
                "page": 2,
                "textSha256": "f" * 64,
                "charCount": 0,
                "isImageOnly": True,
                "images": [],
                "ocr": {
                    "status": "below_threshold",
                    "scope": "page",
                    "engine": engine,
                    "machineRead": True,
                    "pinSha256": "d" * 64,
                    "regions": [
                        {
                            "index": 1,
                            "bbox": [0.0, 0.0, 595.28, 841.89],
                            "band": "below_threshold",
                            "confidence": {"mean": 43.25, "minLine": 31.0, "lowConfidenceShare": 0.76},
                            "agreement": 0.6667,
                            "eligibleLineCount": 0,
                            "lineCount": 2,
                            "wordCount": 3,
                            "machineRead": True,
                            "lines": [
                                {
                                    "index": 1,
                                    "text": "Memo of receipts",
                                    "confidence": 43.25,
                                    "agreement": 0.6667,
                                    "band": "below_threshold",
                                    "eligible": False,
                                }
                            ],
                        }
                    ],
                },
            },
        ],
    }


def _coverage() -> list[dict[str, Any]]:
    return [
        {
            "sourceId": SOURCE_ID,
            "page": 1,
            "status": "covered",
            "blockIds": ["t-balances"],
            "reason": None,
            "basis": "ocr",
            "ocrRegions": [1],
            "ocrStatus": "applied",
        },
        {
            "sourceId": SOURCE_ID,
            "page": 2,
            "status": "excluded",
            "blockIds": [],
            "reason": "OCR below threshold; image unresolved",
            "basis": "ocr",
            "ocrRegions": [1],
            "ocrStatus": "below_threshold",
        },
    ]


def _derivation() -> dict[str, Any]:
    return {
        "kind": "ocr",
        "blockIds": ["t-balances"],
        "anchors": [{"sourceId": SOURCE_ID, "page": 1, "region": 1}],
        "decision": "Reconstructed the table from the image region.",
        "retained": True,
        "method": "ocr-table-v1",
        "crossCheck": CROSS_CHECK,
    }


def _workspace(
    tmp_path: Path,
    *,
    mutate_manuscript: Callable[[dict[str, Any]], None] | None = None,
    mutate_manifest: Callable[[dict[str, Any]], None] | None = None,
    mutate_record: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[Path, Path, Path]:
    workspace = tmp_path / "book"
    workspace.mkdir()
    data = _manuscript()
    if mutate_manuscript:
        mutate_manuscript(data)
    book = workspace / "book.yaml"
    book.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    manifest = _manifest()
    if mutate_manifest:
        mutate_manifest(manifest)
    _write_json(workspace / "intake" / "manifest.json", manifest)

    record = {
        "schemaVersion": "1.0",
        "bookId": "ocr-book",
        "mode": "source-faithful",
        "source": {
            "id": SOURCE_ID,
            "sha256": SOURCE_SHA,
            "pages": 2,
            "intakeManifest": "intake/manifest.json",
        },
        "enrichment": {"requested": False, "permission": None, "sources": []},
        "coverage": _coverage(),
        "derivations": [_derivation()],
        "uncertainty": [
            {
                "sourceId": SOURCE_ID,
                "page": 2,
                "note": "The degraded image is unresolved; no text is used.",
            }
        ],
        "manuscriptSha256": hashlib.sha256(book.read_bytes()).hexdigest(),
        "manuscriptRevision": 1,
    }
    if mutate_record:
        mutate_record(record)
    record_path = workspace / "authoring" / "record.json"
    _write_json(record_path, record)
    return workspace, book, record_path


def test_existing_books_still_validate_without_ocr_fields() -> None:
    assert model.load(SPECIMEN).data["schemaVersion"] == "1.0"
    assert model.load(ROOT / "content" / "catalogue.yaml").data["schemaVersion"] == "1.0"
    assert model.load(ROOT / "content" / "trial.yaml").data["schemaVersion"] == "1.0"
    # An existing durable record still validates with no `basis` or `ocr` key.
    workspace = ROOT / "content" / "agent-skill" / "source-faithful"
    manuscript = model.load(workspace / "book.yaml", root=workspace)
    loaded = author_record.load(
        workspace / "authoring" / "record.json",
        manuscript=manuscript,
    )
    assert loaded.coverage
    assert all(entry["basis"] == "text" for entry in loaded.coverage)


def test_machine_read_never_verified(tmp_path: Path) -> None:
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(_manuscript(verified=True), sort_keys=False))

    with pytest.raises(BookifyError) as error:
        model.load(path)

    assert error.value.code == "SCHEMA_INVALID"
    assert "verified" in error.value.message


def test_machine_read_table_needs_the_reconstruction_note(tmp_path: Path) -> None:
    data = _manuscript()
    data["sections"][0]["blocks"][0]["note"] = "A note without the required prefix."
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))

    with pytest.raises(BookifyError) as error:
        model.load(path)

    assert error.value.code == "SCHEMA_INVALID"
    assert "Reconstructed from an image by OCR" in error.value.message


def test_machine_read_digits_need_cross_checked_by(tmp_path: Path) -> None:
    data = _manuscript()
    data["sections"][0]["blocks"][0]["machineRead"].pop("crossCheckedBy")
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))

    with pytest.raises(BookifyError) as error:
        model.load(path)

    assert error.value.code == "SCHEMA_INVALID"
    assert "crossCheckedBy" in error.value.message


def test_region_anchor_requires_machine_read(tmp_path: Path) -> None:
    data = _manuscript(machine=False)
    data["sections"][0]["blocks"][0]["sourceAnchors"][0]["region"] = 1
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))

    with pytest.raises(BookifyError) as error:
        model.load(path)

    assert error.value.code == "SCHEMA_INVALID"
    assert "region" in error.value.message


def test_record_resolves_manifest_region_and_digit_evidence(tmp_path: Path) -> None:
    workspace, book, record = _workspace(tmp_path)
    payload = author_record.check(record, manuscript_path=book, workspace=workspace)

    assert payload["ok"] is True
    assert payload["coverage"] == {"covered": 1, "merged": 0, "excluded": 1}


def test_record_rejects_a_machine_read_region_absent_from_the_manifest(tmp_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["sections"][0]["blocks"][0]["machineRead"]["region"] = 9
        data["sections"][0]["blocks"][0]["sourceAnchors"][0]["region"] = 9

    workspace, book, record = _workspace(tmp_path, mutate_manuscript=mutate)

    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "does not contain" in error.value.message


def test_record_rejects_a_below_threshold_page_presented_as_covered(tmp_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["coverage"][1].update(
            status="covered",
            blockIds=["t-balances"],
            reason=None,
        )

    workspace, book, record = _workspace(tmp_path, mutate_record=mutate)

    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "below_threshold" in error.value.message


def test_record_rejects_digits_without_a_matching_cross_check(tmp_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["derivations"][0]["crossCheck"] = "a different claim"

    workspace, book, record = _workspace(tmp_path, mutate_record=mutate)

    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "crossCheckedBy" in error.value.message or "does not match" in error.value.message


def test_record_rejects_an_ocr_page_without_basis_ocr(tmp_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["coverage"][0]["basis"] = "text"
        data["coverage"][0].pop("ocrRegions")
        data["coverage"][0].pop("ocrStatus")

    workspace, book, record = _workspace(tmp_path, mutate_record=mutate)

    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)

    assert error.value.code == "INPUT_INVALID"
    assert "basis ocr" in error.value.message


def test_verify_machine_read_warns_on_digits_only(tmp_path: Path) -> None:
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(_manuscript(), sort_keys=False))
    manuscript = model.load(path)

    result = machine_read.check(manuscript)

    assert result.status == "warn"
    assert result.evidence["warnings"][0]["id"].startswith("MACHINE_READ_DIGITS:")


def test_verify_machine_read_fails_a_verified_block(tmp_path: Path) -> None:
    path = tmp_path / "book.yaml"
    path.write_text(yaml.safe_dump(_manuscript(verified=True), sort_keys=False))
    with pytest.raises(BookifyError):
        model.load(path)
    # Verify is independent of the model guard: it sees the block it is given.
    data = _manuscript()
    data["sections"][0]["blocks"][0]["confidence"] = "verified"
    # Bypass the model's own check to exercise the verifier's independent rule.
    from bookify.manuscript.model import Manuscript

    loaded = Manuscript(
        path=path,
        root=path.parent,
        id=data["id"],
        revision=1,
        sections=tuple(data["sections"]),
        block_ids=frozenset({"t-balances"}),
        data=data,
        engine=ROOT,
    )
    result = machine_read.check(loaded)
    assert result.status == "fail"
    assert result.code == "SCHEMA_INVALID"


def test_ocr_free_build_check_names_invocations() -> None:
    measured = {
        "ocr": {
            "invoked": False,
            "engineInvocations": 0,
            "vendorRead": False,
            "measured": True,
            "probe": "subprocess.run+io.open",
        }
    }
    assert ocr_free.check(measured).status == "pass"
    assert ocr_free.check({"ocr": {"invoked": True}}).code == "BUILD_FAILED"
    assert ocr_free.check({"ocr": {"vendorRead": True}}).code == "BUILD_FAILED"
    assert ocr_free.check(None).code == "BUILD_FAILED"
    assert ocr_free.check({"ocr": {"invoked": False, "vendorRead": False}}).status == "fail"
    assert ocr_free.check({"ocr": {**measured["ocr"], "engineInvocations": 1}}).status == "fail"


def test_build_and_verify_never_invoke_ocr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "book"
    workspace.mkdir()
    book = workspace / "book.yaml"
    source = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "no-ocr-book",
        "metadata": {"title": "No OCR", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-one",
                "title": "One",
                "blocks": [{"id": "b-one", "type": "paragraph", "text": "A short book about nothing."}],
            }
        ],
    }
    book.write_text(yaml.safe_dump(source, sort_keys=False))

    calls: list[list[str]] = []
    real_run = subprocess.run

    def guard(*args, **kwargs):
        command = args[0] if args else kwargs.get("args")
        if isinstance(command, (list, tuple)):
            calls.append([str(part) for part in command])
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guard)
    result = typst_driver.build(
        book,
        workspace / "dist" / "book.pdf",
        workspace / "build",
        offline=True,
        workspace=workspace,
    )
    assert not [call for call in calls if any("tesseract" in part for part in call)]
    boundary = result.report["ocr"]
    assert boundary["measured"] is True
    assert boundary["probe"] == "subprocess.run+io.open"
    assert boundary["engineInvocations"] == 0
    assert boundary["vendorRead"] is False

    before_verify = len(calls)
    verify_runner.run(
        result.pdf,
        book,
        None,
        previous_pdf=result.pdf,
        build_report=workspace / "build" / "build-report.json",
        workspace=workspace,
    )
    verify_calls = calls[before_verify:]
    assert verify_calls
    assert not [call for call in verify_calls if any("tesseract" in part for part in call)]


def test_measured_ocr_boundary_counts_a_real_invocation_and_a_build_report_cannot_hide_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M5/R4: the probe counts real engine calls and the report cannot fake zero."""
    from bookify.intake import manifest as intake_manifest
    from bookify.intake import ocr as intake_ocr
    from bookify.toolchain import audit

    if not DEV_ENGINE.is_file() or not DEV_TESSDATA.is_dir():
        pytest.skip("development OCR copy is unavailable; system tesseract is not required")
    monkeypatch.setenv("BOOKIFY_OCR_ALLOW_DEV", "1")

    # 1. A real OCR run through the intake path, inside the measured boundary:
    #    the probe must count the engine calls instead of writing a constant.
    options = intake_ocr.OcrOptions(enabled=True, tesseract=DEV_ENGINE, tessdata=DEV_TESSDATA)
    with audit.boundary() as measured:
        intake = intake_manifest.build(OCR_FIXTURE, tmp_path / "intake", ocr_options=options)
    assert any(page.get("ocr", {}).get("status") == "applied" for page in intake["pages"]), (
        "the public fixture did not reach an applied OCR page"
    )
    assert measured.engine_invocations > 0
    measured_evidence = measured.evidence()
    assert measured_evidence["engineInvocations"] == measured.engine_invocations
    assert measured_evidence["invoked"] is True
    assert ocr_free.check({"ocr": measured_evidence}).status == "fail"

    # 2. Inject one real engine argv inside a build's measured scope. The report
    #    must copy the measured count; a hardcoded zero fails this assertion.
    workspace = tmp_path / "book"
    workspace.mkdir()
    book = workspace / "book.yaml"
    source = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "boundary-book",
        "metadata": {"title": "Boundary", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-one",
                "title": "One",
                "blocks": [{"id": "b-one", "type": "paragraph", "text": "A short book about nothing."}],
            }
        ],
    }
    book.write_text(yaml.safe_dump(source, sort_keys=False))

    injected: list[str] = []
    real_run = subprocess.run

    def inject_tesseract(*args, **kwargs):
        argv = args[0] if args else kwargs.get("args")
        parts = [str(part) for part in argv] if isinstance(argv, (list, tuple)) else []
        if not injected and "compile" in parts:
            injected.append("done")
            # Re-enter subprocess.run inside the build boundary so the call is
            # measured exactly like a real engine invocation.
            subprocess.run([str(DEV_ENGINE), "--version"], capture_output=True, check=False)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", inject_tesseract)
    result = typst_driver.build(
        book,
        workspace / "dist" / "book.pdf",
        workspace / "build",
        offline=True,
        workspace=workspace,
    )
    boundary = result.report["ocr"]
    assert injected
    assert boundary["measured"] is True
    assert boundary["engineInvocations"] >= 1
    assert boundary["invoked"] is True
    assert ocr_free.check(result.report).status == "fail"

    report = verify_runner.run(
        result.pdf,
        book,
        None,
        previous_pdf=result.pdf,
        build_report=workspace / "build" / "build-report.json",
        workspace=workspace,
    )
    checked = next(item for item in report["checks"] if item["id"] == "ocr_free_build")
    assert checked["status"] == "fail"
    assert report["gate"] == "fail"


def test_record_rejects_a_below_threshold_line_published_in_a_table(tmp_path: Path) -> None:
    """C1: an applied page does not make an ineligible line usable."""

    def mutate_manifest(manifest: dict[str, Any]) -> None:
        manifest["pages"][0]["ocr"]["regions"][0]["lines"].append(
            {
                "index": 2,
                "text": "Owner's capital 31,205.75",
                "confidence": 77.58,
                "agreement": 1.0,
                "band": "below_threshold",
                "eligible": False,
            }
        )

    def mutate_manuscript(manuscript: dict[str, Any]) -> None:
        block = manuscript["sections"][0]["blocks"][0]
        block["rows"].append(["Owner's capital", "31,205.75"])

    workspace, book, record = _workspace(
        tmp_path,
        mutate_manuscript=mutate_manuscript,
        mutate_manifest=mutate_manifest,
    )
    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)
    assert error.value.code == "INPUT_INVALID"
    assert "ineligible OCR line" in error.value.message


def test_record_rejects_a_region_with_no_eligible_line(tmp_path: Path) -> None:
    def mutate_manifest(manifest: dict[str, Any]) -> None:
        region = manifest["pages"][0]["ocr"]["regions"][0]
        region["band"] = "below_threshold"
        region["eligibleLineCount"] = 0
        for line in region["lines"]:
            line["eligible"] = False
            line["band"] = "below_threshold"

    workspace, book, record = _workspace(tmp_path, mutate_manifest=mutate_manifest)
    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)
    assert error.value.code == "INPUT_INVALID"
    assert "below_threshold" in error.value.message


def test_record_rejects_a_confidence_that_the_manifest_did_not_measure(tmp_path: Path) -> None:
    def mutate(manuscript: dict[str, Any]) -> None:
        manuscript["sections"][0]["blocks"][0]["machineRead"]["confidence"] = 99.9

    workspace, book, record = _workspace(tmp_path, mutate_manuscript=mutate)
    with pytest.raises(BookifyError) as error:
        author_record.check(record, manuscript_path=book, workspace=workspace)
    assert error.value.code == "INPUT_INVALID"
    assert "claims confidence 99.9" in error.value.message


def test_verify_machine_read_confidence_mismatch_fails_not_warns(tmp_path: Path) -> None:
    def mutate(manuscript: dict[str, Any]) -> None:
        manuscript["sections"][0]["blocks"][0]["machineRead"]["confidence"] = 99.9

    workspace, book, _record = _workspace(tmp_path, mutate_manuscript=mutate)
    manuscript = model.load(book)
    manifest = json.loads((workspace / "intake" / "manifest.json").read_text())
    check = machine_read.check(manuscript, manifest)
    assert check.status == "fail", check.detail
    reasons = [item["reason"] for item in check.evidence["failures"]]
    assert any("does not match the measured" in reason for reason in reasons), reasons


def test_f1_evidence_exercises_d1_d4_d5_d6_and_keeps_the_degraded_page_unresolved() -> None:
    """R7: the OCR example is also an end-to-end design proof, not OCR-only."""
    import shutil

    evidence = ROOT / "content" / "agent-skill" / "ocr-example" / "evidence"
    report = json.loads((evidence / "verify.json").read_text())
    checks = {check["id"]: check for check in report["checks"]}

    assert checks["definitions"]["evidence"]["count"] >= 1
    assert checks["captions"]["evidence"]["captions"]
    assert checks["plates"]["evidence"]["plates"]
    rhythm = checks["rhythm"]["evidence"]
    assert rhythm["deckSamples"] >= 1
    assert rhythm["h2Samples"] >= 1
    assert rhythm["h3Samples"] >= 1

    # R4: the shipped public example carries a measured OCR-free boundary, not
    # a hardcoded claim.
    boundary = json.loads((evidence / "build-report.json").read_text())["ocr"]
    assert boundary["measured"] is True
    assert boundary["probe"] == "subprocess.run+io.open"
    assert boundary["engineInvocations"] == 0
    assert boundary["invoked"] is False
    assert boundary["vendorRead"] is False

    book = yaml.safe_load((evidence.parent / "book.yaml").read_text())
    table = next(
        block
        for section in book["sections"]
        for block in section["blocks"]
        if block["id"] == "t-trial"
    )
    assert all("Owner's capital" not in row for row in table["rows"])
    assert any(
        block["id"] == "u-omitted"
        for section in book["sections"]
        for block in section["blocks"]
    )
    manifest = json.loads((evidence.parent / "intake" / "manifest.json").read_text())
    page3 = next(page for page in manifest["pages"] if page["page"] == 3)
    assert page3["ocr"]["status"] == "below_threshold"
    assert page3["ocr"]["eligibleLineCount"] == 0


@pytest.mark.parametrize("name", ["ocr-example", "source-faithful", "teachable"])
def test_shipped_trial_evidence_replays_from_its_own_files(name: str, tmp_path: Path) -> None:
    """R6: review notes and the referenced second PDF ship with the evidence."""
    import shutil

    source = ROOT / "content" / "agent-skill" / name
    workspace = tmp_path / name
    shutil.copytree(source, workspace)
    recorded = json.loads((workspace / "evidence" / "verify.json").read_text())
    if recorded.get("schemaVersion") != "1.2":
        pytest.skip(
            f"evidence was recorded under verify schema {recorded.get('schemaVersion')}; "
            "it predates the docmeta check, so it is rebuilt rather than replayed"
        )
    generated = recorded["generatedFrom"]
    for key in ("pdf", "manuscript", "previousPdf"):
        assert generated[key], key
        assert (workspace / generated[key]).is_file(), (key, generated[key])
    notes = workspace / "evidence" / "review-notes.json"
    assert notes.is_file()
    decisions = json.loads(notes.read_text())["decisions"]
    missing = [warning["id"] for warning in recorded["warnings"] if warning["id"] not in decisions]
    assert not missing, missing

    replay = verify_runner.run(
        workspace / generated["pdf"],
        workspace / generated["manuscript"],
        None,
        previous_pdf=workspace / generated["previousPdf"],
        build_report=workspace / "evidence" / "build-report.json",
        contact_sheet=workspace / "evidence" / "contact-sheet.png",
        reviewed_by="evidence-replay",
        reviewed_at="2026-11-14T10:00:00Z",
        review_notes=notes,
        workspace=workspace,
    )
    assert replay["gate"] == "pass", [
        f"{check['id']}: {check['detail']}"
        for check in replay["checks"]
        if check["status"] == "fail"
    ]
