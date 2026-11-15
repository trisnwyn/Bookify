"""Run every acceptance check and write one machine-readable report."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.toolchain import pins
from bookify.verify.checks import Check, failed, manual
from bookify.verify.checks import captions as captions_check
from bookify.verify.checks import catalogue as catalogue_check
from bookify.verify.checks import cover as cover_check
from bookify.verify.checks import definitions as definitions_check
from bookify.verify.checks import determinism as determinism_check
from bookify.verify.checks import geometry as geometry_check
from bookify.verify.checks import glyphs as glyphs_check
from bookify.verify.checks import illustration_limit as limit_check
from bookify.verify.checks import machine_read as machine_read_check
from bookify.verify.checks import ocr_free as ocr_free_check
from bookify.verify.checks import offline as offline_check
from bookify.verify.checks import pages as pages_check
from bookify.verify.checks import plates as plates_check
from bookify.verify.checks import readability as readability_check
from bookify.verify.checks import rhythm as rhythm_check
from bookify.verify.checks import rights as rights_check
from bookify.verify.checks import text as text_check
from bookify.verify.checks import xrefs as xrefs_check


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portable(path: Path | None, workspace: Path | None) -> str | None:
    """Name a file the way a replay can find it, not by this host's absolute path."""
    if path is None:
        return None
    if workspace is not None:
        try:
            return path.resolve().relative_to(workspace.resolve()).as_posix()
        except ValueError:
            pass
    return str(path)


def _load_report(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _intake_manifest(workspace: Path | None) -> dict[str, Any] | None:
    """The source evidence beside a book, when one is present.

    Verify never reads vendor/ocr or invokes an engine; it only compares the
    manuscript's machine-read claims with the manifest intake already wrote.
    """
    if workspace is None:
        return None
    path = workspace / "intake" / "manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _warn_decisions(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    decisions = data.get("decisions", data)
    if not isinstance(decisions, dict):
        return {}
    return {key: value for key, value in decisions.items() if isinstance(value, str) and value.strip()}


def _review(
    contact_sheet: Path | None,
    reviewed_by: str | None,
    reviewed_at: str | None,
    warning_ids: list[str] | None = None,
    review_notes: Path | None = None,
    workspace: Path | None = None,
) -> Check:
    if contact_sheet is None or not contact_sheet.is_file():
        return failed("review", "VERIFY_FAILED", "no rendered-page inspection record")
    if not reviewed_by or not reviewed_at:
        return failed("review", "VERIFY_FAILED", "inspection needs reviewedBy and reviewedAt")
    warning_ids = warning_ids or []
    warnings_answered = 0
    if warning_ids:
        decisions = _warn_decisions(review_notes)
        missing = [identifier for identifier in warning_ids if identifier not in decisions]
        if missing:
            return failed(
                "review",
                "VERIFY_FAILED",
                f"{len(missing)} warning(s) not answered in review notes: {missing[:4]}",
                missingWarnings=missing,
                warningsAnswered=len(warning_ids) - len(missing),
            )
        warnings_answered = len(warning_ids)
    return manual(
        "review",
        f"rendered pages inspected by {reviewed_by} at {reviewed_at}",
        contactSheet=_portable(contact_sheet, workspace),
        reviewedBy=reviewed_by,
        reviewedAt=reviewed_at,
        warningsAnswered=warnings_answered,
    )


def run(
    pdf: Path,
    manuscript_path: Path,
    report_path: Path | None = None,
    *,
    previous_pdf: Path | None = None,
    build_report: Path | None = None,
    contact_sheet: Path | None = None,
    reviewed_by: str | None = None,
    reviewed_at: str | None = None,
    review_notes: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    if not pdf.is_file():
        raise BookifyError("INPUT_INVALID", f"pdf not found: {pdf}", str(pdf))
    manuscript = (
        model.load(manuscript_path, workspace=workspace)
        if workspace is not None
        else model.load(manuscript_path)
    )
    build = _load_report(build_report)
    draft = bool(build.get("draft")) if build else False
    pdf_sha256 = _sha256(pdf)
    manuscript_sha256 = _sha256(manuscript_path)
    is_catalogue = manuscript.id == catalogue_check.CATALOGUE_ID

    checks: list[Check] = [
        offline_check.check(
            build,
            pdf_sha256=pdf_sha256,
            manuscript_sha256=manuscript_sha256,
            manuscript_revision=manuscript.revision,
        ),
        ocr_free_check.check(build),
        determinism_check.check(pdf, previous_pdf),
        glyphs_check.check(pdf, manuscript),
        cover_check.check(pdf, manuscript),
        definitions_check.check(pdf, manuscript),
        text_check.check(pdf, manuscript),
        pages_check.check_geometry(pdf),
        captions_check.check(pdf, manuscript, require_coverage=is_catalogue),
        limit_check.check(pdf),
        rights_check.check(pdf, manuscript, draft),
        xrefs_check.check(pdf, manuscript),
        rhythm_check.check(pdf, manuscript),
        plates_check.check(pdf, manuscript),
        readability_check.check(pdf, manuscript),
        machine_read_check.check(manuscript, _intake_manifest(workspace)),
    ]
    if is_catalogue:
        checks.append(catalogue_check.check(pdf, manuscript))
        checks.append(geometry_check.check(pdf, manuscript))
    warning_ids = [
        warning["id"]
        for check in checks
        if check.status == "warn"
        for warning in check.evidence.get("warnings", [])
        if isinstance(warning, dict) and warning.get("id")
    ]
    checks.append(_review(contact_sheet, reviewed_by, reviewed_at, warning_ids, review_notes, workspace))
    gate = "pass" if all(check.ok for check in checks) else "fail"

    lock_path = getattr(manuscript, "engine", manuscript.root) / "toolchain.lock.json"
    lock = pins.load(lock_path) if lock_path.is_file() else None
    report: dict[str, Any] = {
        "schemaVersion": "1.1",
        "generatedFrom": {
            "pdf": _portable(pdf, workspace),
            "pdfSha256": _sha256(pdf),
            "manuscript": _portable(manuscript_path, workspace),
            "manuscriptRevision": manuscript.revision,
            "previousPdf": _portable(previous_pdf, workspace),
        },
        "pins": {"typst": lock.typst.version, "python": lock.python.version} if lock else None,
        "checks": [
            {"id": check.id, "status": check.status, "code": check.code, "detail": check.detail, "evidence": check.evidence}
            for check in checks
        ],
        "warnings": [
            {"id": warning["id"], "check": check.id, "detail": warning}
            for check in checks
            if check.status == "warn"
            for warning in check.evidence.get("warnings", [])
            if isinstance(warning, dict)
        ],
        "gate": gate,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
