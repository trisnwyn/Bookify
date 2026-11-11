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
from bookify.verify.checks import determinism as determinism_check
from bookify.verify.checks import geometry as geometry_check
from bookify.verify.checks import glyphs as glyphs_check
from bookify.verify.checks import illustration_limit as limit_check
from bookify.verify.checks import offline as offline_check
from bookify.verify.checks import pages as pages_check
from bookify.verify.checks import rights as rights_check
from bookify.verify.checks import text as text_check
from bookify.verify.checks import xrefs as xrefs_check


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_report(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _review(contact_sheet: Path | None, reviewed_by: str | None, reviewed_at: str | None) -> Check:
    if contact_sheet is None or not contact_sheet.is_file():
        return failed("review", "VERIFY_FAILED", "no rendered-page inspection record")
    if not reviewed_by or not reviewed_at:
        return failed("review", "VERIFY_FAILED", "inspection needs reviewedBy and reviewedAt")
    return manual(
        "review",
        f"rendered pages inspected by {reviewed_by} at {reviewed_at}",
        contactSheet=str(contact_sheet),
        reviewedBy=reviewed_by,
        reviewedAt=reviewed_at,
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
) -> dict[str, Any]:
    if not pdf.is_file():
        raise BookifyError("INPUT_INVALID", f"pdf not found: {pdf}", str(pdf))
    manuscript = model.load(manuscript_path)
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
        determinism_check.check(pdf, previous_pdf),
        glyphs_check.check(pdf, manuscript),
        text_check.check(pdf, manuscript),
        pages_check.check_geometry(pdf),
        captions_check.check(pdf, manuscript, require_coverage=is_catalogue),
        limit_check.check(pdf),
        rights_check.check(pdf, manuscript, draft),
        xrefs_check.check(pdf, manuscript),
    ]
    if is_catalogue:
        checks.append(catalogue_check.check(pdf, manuscript))
        checks.append(geometry_check.check(pdf, manuscript))
    checks.append(_review(contact_sheet, reviewed_by, reviewed_at))
    gate = "pass" if all(check.ok for check in checks) else "fail"

    lock_path = manuscript.root / "toolchain.lock.json"
    lock = pins.load(lock_path) if lock_path.is_file() else None
    report: dict[str, Any] = {
        "schemaVersion": "1.0",
        "generatedFrom": {
            "pdf": str(pdf),
            "pdfSha256": _sha256(pdf),
            "manuscript": str(manuscript_path),
            "manuscriptRevision": manuscript.revision,
            "previousPdf": str(previous_pdf) if previous_pdf else None,
        },
        "pins": {"typst": lock.typst.version, "python": lock.python.version} if lock else None,
        "checks": [
            {"id": check.id, "status": check.status, "code": check.code, "detail": check.detail, "evidence": check.evidence}
            for check in checks
        ],
        "gate": gate,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
