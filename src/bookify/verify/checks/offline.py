"""Offline and model-free evidence, bound to the artifacts being verified."""

from __future__ import annotations

from bookify.verify.checks import Check, failed, passed


def check(
    build_report: dict | None,
    *,
    pdf_sha256: str | None = None,
    manuscript_sha256: str | None = None,
    manuscript_revision: int | None = None,
) -> Check:
    if build_report is None:
        return failed("offline", "NETWORK_DENIED", "no build report; offline build is unproven")
    if build_report.get("offline") is not True:
        return failed("offline", "NETWORK_DENIED", "build did not run under the offline guard")
    if "networkAttempts" not in build_report:
        return failed("offline", "NETWORK_DENIED", "build report has no network-attempt record")
    if build_report.get("networkAttempts"):
        return failed("offline", "NETWORK_DENIED", "build recorded network attempts")
    report_pdf = build_report.get("pdf") or {}
    if pdf_sha256 is not None and report_pdf.get("sha256") != pdf_sha256:
        return failed(
            "offline", "NETWORK_DENIED",
            "build report is not bound to this PDF; rebuild it or verify the report that produced this file",
        )
    report_manuscript = build_report.get("manuscript") or {}
    if manuscript_sha256 is not None and report_manuscript.get("sha256") != manuscript_sha256:
        return failed(
            "offline", "NETWORK_DENIED",
            "build report is not bound to this manuscript; rebuild it or verify the report that produced it",
        )
    if manuscript_revision is not None and report_manuscript.get("revision") != manuscript_revision:
        return failed(
            "offline", "NETWORK_DENIED",
            "build report revision does not match the manuscript",
        )
    return passed(
        "offline",
        "build ran with networking disabled and no model calls",
        draft=build_report.get("draft"),
    )
