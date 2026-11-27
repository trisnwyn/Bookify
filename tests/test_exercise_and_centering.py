"""Regression tests for Phase 1 centering and exercise workspace primitives."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bookify.design import coverage, lint
from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.publish import typst_driver
from bookify.verify.checks import captions
from helpers import ROOT


def _write_manuscript(path: Path, blocks: list[dict]) -> Path:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "phase1-test",
        "metadata": {
            "title": "Centering and Exercise Workspace Showcase",
            "languages": ["en"],
            "author": "Bookify Test Suite",
            "cover": {"composition": "cover-3"},
        },
        "sections": [
            {
                "id": "sec-practice",
                "title": "Practice Problems and Proofs",
                "level": 1,
                "blocks": blocks,
            }
        ],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path


def test_design_lint_passes_after_workspace_and_centering_updates() -> None:
    issues = lint.lint(ROOT)
    assert issues == [], [(i.path.name, i.line, i.message) for i in issues]
    assert lint.missing_presets(ROOT) == set()


def test_all_exercise_response_spaces_and_centered_equations_build_and_verify(tmp_path: Path) -> None:
    manuscript_path = _write_manuscript(
        tmp_path / "book.yaml",
        [
            {
                "id": "b-intro",
                "type": "paragraph",
                "text": "This section tests centred equations, centred captions, and human-friendly exercise workspaces.",
            },
            {
                "id": "b-eq-1",
                "type": "equation",
                "typst": "sum_(k=1)^infinity (1) / (k^2) = (pi^2) / (6)",
                "caption": "Basel identity rendered as a centred display formula with a centred description.",
            },
            {
                "id": "b-ex-lines",
                "type": "assessment",
                "title": "Exercise 1 (Short Explanation)",
                "text": "Explain why compact operators cannot have bounded inverses on infinite-dimensional Hilbert spaces.",
                "responseSpace": {
                    "kind": "lines",
                    "lines": 5,
                    "lineStyle": "dotted",
                    "label": "Write your explanation (extra lines included for revisions):",
                },
            },
            {
                "id": "b-ex-grid",
                "type": "assessment",
                "title": "Exercise 2 (Derivation)",
                "text": "Derive the Euler–Lagrange equation for the Tikhonov functional.",
                "responseSpace": {
                    "kind": "grid",
                    "heightPt": 130,
                    "label": "Dot-grid scratchpad for derivation and false starts:",
                },
            },
            {
                "id": "b-ex-blank",
                "type": "assessment",
                "title": "Exercise 3 (Proof Sketch)",
                "text": "Prove the primal–dual gap is non-negative.",
                "responseSpace": {"kind": "blank", "heightPt": 100, "label": "Proof box:"},
            },
            {
                "id": "b-ex-coord",
                "type": "assessment",
                "title": "Exercise 4 (Curve Sketch)",
                "text": "Sketch the bias-squared and variance curves across regularisation scale.",
                "responseSpace": {"kind": "coordinate", "heightPt": 130, "label": "Axes with margin:"},
            },
            {
                "id": "b-ex-choices",
                "type": "assessment",
                "title": "Exercise 5 (Multiple Choice with Justification)",
                "text": "Which regulariser produces exact coordinate sparsity?",
                "responseSpace": {
                    "kind": "choices",
                    "choices": ["A. Quadratic L²", "B. Lasso ℓ₁", "C. Identity"],
                    "lines": 3,
                },
            },
            {
                "id": "b-ex-trace",
                "type": "assessment",
                "title": "Exercise 6 (Algorithm Trace)",
                "text": "Trace three iterations of proximal gradient descent starting at x = 2.",
                "responseSpace": {
                    "kind": "trace",
                    "traceColumns": ["Step t", "Iterate x", "Gradient", "Scratch"],
                    "rows": 5,
                },
            },
            {
                "id": "b-fill-table",
                "type": "table",
                "caption": "Fill-in-the-blank comparison table with tall writable cells and extra overflow rows.",
                "header": ["Method", "Rate", "Notes"],
                "rows": [["ISTA", "", ""], ["FISTA", "", ""]],
                "fillSpace": True,
                "extraRows": 2,
            },
        ],
    )
    manuscript = model.load(manuscript_path, root=ROOT)
    cov = coverage.require_coverage(manuscript, ROOT)
    assert cov.ok

    out_pdf = tmp_path / "exercise.pdf"
    result = typst_driver.build(
        manuscript_path,
        out_pdf,
        tmp_path / "build",
        offline=True,
        workspace=tmp_path,
        engine=ROOT,
    )
    assert result.report["pdf"]["pages"] >= 2
    assert out_pdf.is_file()

    cap_check = captions.check(out_pdf, manuscript)
    assert cap_check.status == "pass", cap_check.detail
    assert cap_check.evidence["maxDeltaPt"] <= captions.TOLERANCE_PT


def test_response_space_rejected_on_non_assessment_block(tmp_path: Path) -> None:
    path = _write_manuscript(
        tmp_path / "bad.yaml",
        [
            {
                "id": "b-p1",
                "type": "paragraph",
                "text": "Not an exercise.",
                "responseSpace": {"kind": "lines", "lines": 4},
            }
        ],
    )
    with pytest.raises(BookifyError) as exc:
        model.load(path, root=ROOT)
    assert exc.value.code == "SCHEMA_INVALID"


def test_fill_space_rejected_on_non_table_block(tmp_path: Path) -> None:
    path = _write_manuscript(
        tmp_path / "bad-table.yaml",
        [
            {
                "id": "b-p1",
                "type": "paragraph",
                "text": "Not a table.",
                "fillSpace": True,
            }
        ],
    )
    with pytest.raises(BookifyError) as exc:
        model.load(path, root=ROOT)
    assert exc.value.code == "SCHEMA_INVALID"
