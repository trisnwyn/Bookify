"""Build boundary: publishing may not invoke OCR or read vendored OCR data."""

from __future__ import annotations

from bookify.verify.checks import Check, failed, passed


def check(build_report: dict | None) -> Check:
    if build_report is None:
        return failed(
            "ocr_free_build",
            "BUILD_FAILED",
            "no build report; the OCR-free build boundary is unproven",
        )
    evidence = build_report.get("ocr")
    if not isinstance(evidence, dict):
        return failed(
            "ocr_free_build",
            "BUILD_FAILED",
            "build report has no OCR boundary record",
        )
    if evidence.get("measured") is not True or not isinstance(evidence.get("engineInvocations"), int):
        return failed(
            "ocr_free_build",
            "BUILD_FAILED",
            "build report OCR boundary is not a measured probe",
            ocr=evidence,
        )
    if evidence.get("probe") != "subprocess.run+io.open":
        return failed(
            "ocr_free_build",
            "BUILD_FAILED",
            "build report OCR boundary has an unknown probe",
            ocr=evidence,
        )
    if evidence.get("invoked") or evidence.get("engineInvocations"):
        return failed(
            "ocr_free_build",
            "BUILD_FAILED",
            "build invoked an OCR engine",
            ocr=evidence,
        )
    if evidence.get("vendorRead"):
        return failed(
            "ocr_free_build",
            "BUILD_FAILED",
            "build read vendor/ocr data",
            ocr=evidence,
        )
    return passed(
        "ocr_free_build",
        "build ran without an OCR engine or vendored OCR data (measured probe)",
        ocr=evidence,
    )
