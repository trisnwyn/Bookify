"""Regression tests for architecture, toolchain, layout, authoring, and verify fixes."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from helpers import ROOT, SPECIMEN, compile_typ, specimen_build
from bookify import pdf_measure
from bookify.authoring import apply as author_apply
from bookify.authoring import cache, plan
from bookify.design import coverage as design_coverage
from bookify.errors import BookifyError
from bookify.intake import extract as intake_extract
from bookify.manuscript import model
from bookify.publish import normalize, typst_driver
from bookify.toolchain import audit, doctor, pins
from bookify.verify.checks import (
    captions as captions_check,
    cover as cover_check,
    illustration_limit,
    pages as pages_check,
    rhythm as rhythm_check,
    rights as rights_check,
    text as text_check,
)


def test_cetz_matrix_rows_sit_below_column_headers() -> None:
    source = (
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/cetz/diagram.typ": diagram\n'
        "#show: book_base\n"
        '#set page(paper: "a4", margin: 40pt)\n'
        '#diagram((preset: "matrix", '
        'rows: ("RowZero", "RowOne"), '
        'columns: ("ColAlpha", "ColBeta"), '
        'cells: (("Cell00", "Cell01"), ("Cell10", "Cell11")), '
        "groups: ()), 430pt)\n"
    )
    pdf = compile_typ(source, "audit-matrix-geometry")
    lines = captions_check.read_lines(pdf)
    by_text = {line.text.strip(): line for line in lines}
    assert "ColAlpha" in by_text and "RowZero" in by_text and "Cell00" in by_text and "RowOne" in by_text
    assert by_text["RowZero"].y_min > by_text["ColAlpha"].y_max - 1.0
    assert by_text["Cell00"].y_min > by_text["ColAlpha"].y_max - 1.0
    assert by_text["RowOne"].y_min > by_text["RowZero"].y_max - 1.0


def test_heading_cjk_fallback_and_table_align_render_correctly(tmp_path: Path) -> None:
    work = ROOT / ".cache" / "audit-cjk-align"
    work.mkdir(parents=True, exist_ok=True)
    manuscript_path = work / "book.yaml"
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "cjk-align-test",
        "metadata": {"title": "Alignment and Japanese", "languages": ["en", "ja"], "author": "Test Author"},
        "sections": [
            {
                "id": "sec-ja",
                "title": "日本語の見出し",
                "level": 1,
                "blocks": [
                    {"id": "b-intro", "type": "paragraph", "text": "Introductory paragraph for alignment test."},
                    {
                        "id": "b-table",
                        "type": "table",
                        "caption": "Right aligned figures.",
                        "header": ["Account", "Amount"],
                        "rows": [["Cash", "1200"], ["Debt", "450"]],
                        "align": ["left", "right"],
                    },
                ],
            }
        ],
    }
    manuscript_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    result = typst_driver.build(manuscript_path, work / "out.pdf", work / "build", offline=True)
    lines = [line for line in captions_check.read_lines(result.pdf) if line.page == 3]
    cash = next(line for line in lines if line.text.strip() == "Cash")
    amount = next(line for line in lines if line.text.strip() == "1200")
    # Right-aligned numeric cell sits near the right edge of the text block (~535 pt),
    # well past the left edge of the second half (~298 pt).
    assert amount.x_max > 500.0
    assert cash.x_min < 70.0
    assert any("日本語の見出し" in line.text for line in lines)


def test_audit_boundary_catches_subprocess_popen() -> None:
    with audit.boundary() as state:
        try:
            proc = subprocess.Popen(["tesseract", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.communicate(timeout=5)
        except FileNotFoundError:
            pass
    assert state.engine_invocations == 1
    assert state.evidence()["invoked"] is True


def test_pins_rejects_non_hex_sha256_with_bookify_error(tmp_path: Path) -> None:
    data = json.loads((ROOT / "toolchain.lock.json").read_text())
    data["typst"]["sha256"] = "z" * 64
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps(data))

    with pytest.raises(BookifyError) as error:
        pins.load(lock)
    assert error.value.code == "INPUT_INVALID"


def test_doctor_checks_poppler_and_bwrap(monkeypatch: pytest.MonkeyPatch) -> None:
    real_which = shutil.which
    monkeypatch.setattr(
        doctor.shutil,
        "which",
        lambda name: None if name == "pdftotext" else real_which(name),
    )
    report = doctor.run(ROOT, ROOT / "toolchain.lock.json")
    assert not report.ok
    failed_ids = {c.identifier for c in report.checks if not c.is_local}
    assert "tool:pdftotext" in failed_ids


def test_model_validates_cover_artwork_and_blocks_path_traversal(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "assets", tmp_path / "assets")
    base = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "cover-art-check",
        "metadata": {
            "title": "Cover Art Check",
            "languages": ["en"],
            "cover": {"composition": "cover-1", "artwork": "missing-art"},
        },
        "sections": [
            {"id": "sec-1", "title": "One", "blocks": [{"id": "b-1", "type": "paragraph", "text": "Text."}]}
        ],
    }
    target = tmp_path / "book.yaml"
    target.write_text(yaml.safe_dump(base))
    with pytest.raises(BookifyError) as error:
        model.load(target, root=tmp_path)
    assert error.value.code == "RIGHTS_INCOMPLETE"

    # Path traversal in illustration record.yaml is refused.
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("secret")
    rec_path = tmp_path / "assets" / "illustrations" / "photo-1" / "record.yaml"
    rec = yaml.safe_load(rec_path.read_text())
    rec["path"] = "../secret.txt"
    rec.pop("sha256", None)
    rec_path.write_text(yaml.safe_dump(rec))

    base["metadata"]["cover"] = {"composition": "cover-1", "artwork": "photo-1"}
    target.write_text(yaml.safe_dump(base))
    with pytest.raises(BookifyError) as err2:
        model.load(target, root=tmp_path)
    assert err2.value.code == "BUILD_FAILED"
    assert "outside the book root" in err2.value.message


def test_model_rejects_unreadable_non_matrix_chart(tmp_path: Path) -> None:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "unreadable-scatter",
        "metadata": {"title": "Scatter", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-1",
                "title": "One",
                "blocks": [
                    {
                        "id": "b-scatter",
                        "type": "chart",
                        "caption": "Unreadable scatter.",
                        "confidence": "unreadable",
                        "note": "Axis was illegible.",
                        "chart": {
                            "kind": "scatter",
                            "verification": "synthetic",
                            "notes": "Synthetic points.",
                            "series": [{"id": "s1", "label": "A"}],
                            "xAxis": {"min": 0, "max": 10},
                            "points": [[[1, 2], [3, 4], [5, 6]]],
                        },
                    }
                ],
            }
        ],
    }
    target = tmp_path / "book.yaml"
    target.write_text(yaml.safe_dump(data))
    with pytest.raises(BookifyError) as error:
        model.load(target, root=ROOT)
    assert error.value.code == "SCHEMA_INVALID"


def test_branch_letter_wraps_cleanly_past_26() -> None:
    assert normalize.branch_letter(1) == "a"
    assert normalize.branch_letter(26) == "z"
    assert normalize.branch_letter(27) == "aa"
    assert normalize.branch_letter(28) == "ab"


def test_coverage_checks_author_course_and_build_fails_on_missing_glyph() -> None:
    work = ROOT / ".cache" / "audit-glyph-build"
    work.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(SPECIMEN.read_text())
    data["metadata"]["author"] = "Author \u05d0"  # Hebrew Alef, outside Spectral/Noto CJK JP
    target = work / "book.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    manuscript = model.load(target, root=ROOT)
    result = design_coverage.check(manuscript, manuscript.engine)
    assert not result.ok
    assert any(code == "U+05D0" for _, code in result.missing)

    with pytest.raises(BookifyError) as error:
        typst_driver.build(target, work / "out.pdf", work / "build", offline=True)
    assert error.value.code == "GLYPH_MISSING"


def test_author_plan_detects_ocr_and_image_changes_on_image_only_page(tmp_path: Path) -> None:
    intake = tmp_path / "intake"
    intake.mkdir()
    empty_sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    manifest_data = {
        "schemaVersion": "1.0",
        "sourceId": "slides",
        "sourceName": "slides.pdf",
        "sourceSha256": "1" * 64,
        "pageCount": 1,
        "pages": [
            {
                "page": 1,
                "textSha256": empty_sha,
                "charCount": 0,
                "isImageOnly": True,
                "images": [{"index": 0, "file": "images/p1.png", "width": 100, "height": 100, "sha256": "a" * 64}],
            }
        ],
    }
    (intake / "manifest.json").write_text(json.dumps(manifest_data))

    manuscript_path = tmp_path / "book.yaml"
    manuscript_path.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "slides-book",
                "metadata": {"title": "Slides", "languages": ["en"]},
                "sections": [
                    {
                        "id": "sec-1",
                        "title": "One",
                        "blocks": [{"id": "b-1", "type": "paragraph", "text": "Placeholder."}],
                    }
                ],
            }
        )
    )
    manuscript = model.load(manuscript_path, root=ROOT)
    cache_dir = tmp_path / "cache"

    first_plan = plan.build(intake, manuscript, cache_dir)
    assert len(first_plan["work"]) == 1
    item = first_plan["work"][0]
    cache.save_index(
        cache_dir,
        {
            "slides#1": cache.record(
                text_sha256=item["textSha256"],
                prompt_version=item["promptVersion"],
                model="agent",
                input_hash=item["inputHash"],
                content_sha256=item["contentSha256"],
            )
        },
    )
    assert plan.build(intake, manuscript, cache_dir)["work"] == []

    # Now OCR lands on the same image-only page (textSha256 is still empty_sha).
    manifest_data["pages"][0]["ocr"] = {"status": "applied", "text": "Recognised heading"}
    (intake / "manifest.json").write_text(json.dumps(manifest_data))
    second_plan = plan.build(intake, manuscript, cache_dir)
    assert [w["page"] for w in second_plan["work"]] == [1]
    assert second_plan["work"][0]["reason"] == "changed"


def test_author_apply_preserves_multi_page_blocks_and_cleans_moved_pages(tmp_path: Path) -> None:
    manuscript_path = tmp_path / "book.yaml"
    manuscript_path.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "multi-page",
                "metadata": {"title": "Multi", "languages": ["en"]},
                "sections": [
                    {
                        "id": "sec-a",
                        "title": "Alpha",
                        "blocks": [
                            {
                                "id": "b-shared",
                                "type": "paragraph",
                                "text": "Synthesises pages 1 and 2.",
                                "sourceAnchors": [
                                    {"sourceId": "deck", "page": 1},
                                    {"sourceId": "deck", "page": 2},
                                ],
                            },
                            {
                                "id": "b-only-p1",
                                "type": "paragraph",
                                "text": "Old page 1 block in section A.",
                                "sourceAnchors": [{"sourceId": "deck", "page": 1}],
                            },
                        ],
                    },
                    {
                        "id": "sec-b",
                        "title": "Beta",
                        "blocks": [{"id": "b-beta", "type": "paragraph", "text": "Beta prose."}],
                    },
                ],
            }
        )
    )
    text_sha = "c" * 64
    input_hash = cache.key("deck", 1, text_sha, plan.PROMPT_VERSION)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "sourceId": "deck",
                "promptVersion": plan.PROMPT_VERSION,
                "work": [
                    {
                        "sourceId": "deck",
                        "page": 1,
                        "textSha256": text_sha,
                        "contentSha256": text_sha,
                        "inputHash": input_hash,
                        "promptVersion": plan.PROMPT_VERSION,
                        "schemaVersion": cache.SCHEMA_VERSION,
                    }
                ],
            }
        )
    )
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(
        json.dumps(
            {
                "sourceId": "deck",
                "pages": [
                    {
                        "page": 1,
                        "sectionId": "sec-b",
                        "textSha256": text_sha,
                        "inputHash": input_hash,
                        "blocks": [{"id": "b-moved-p1", "type": "paragraph", "text": "Moved page 1."}],
                    }
                ],
            }
        )
    )
    author_apply.apply(plan_path, draft_path, manuscript_path, tmp_path / "cache", tmp_path / "decisions.jsonl")
    updated = model.load(manuscript_path, root=ROOT)
    sec_a_ids = [b["id"] for b in updated.sections[0]["blocks"]]
    sec_b_ids = [b["id"] for b in updated.sections[1]["blocks"]]
    assert "b-shared" in sec_a_ids
    assert "b-only-p1" not in sec_a_ids
    shared = next(b for b in updated.sections[0]["blocks"] if b["id"] == "b-shared")
    assert shared["sourceAnchors"] == [{"sourceId": "deck", "page": 2}]
    assert "b-moved-p1" in sec_b_ids


def test_intake_image_sort_key_is_numeric() -> None:
    paths = [Path("img-1000.png"), Path("img-999.png"), Path("img-002.png"), Path("img-10.png")]
    ordered = sorted(paths, key=intake_extract._image_sort_key)
    assert [p.name for p in ordered] == ["img-002.png", "img-10.png", "img-999.png", "img-1000.png"]


def test_rhythm_column_bounds_cover_full_measure_on_single_column() -> None:
    assert rhythm_check._column_bounds(0, 60.0, 475.28, two_column=False) == (60.0, 535.28)
    left = rhythm_check._column_bounds(0, 60.0, 475.28, two_column=True)
    right = rhythm_check._column_bounds(1, 60.0, 475.28, two_column=True)
    assert left[1] < right[0]  # respects the 16 pt gutter


def test_colour_cover_artwork_passes_cover_check() -> None:
    work = ROOT / ".cache" / "audit-colour-cover"
    work.mkdir(parents=True, exist_ok=True)
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "colour-cover",
        "metadata": {
            "title": "Colour Cover Book",
            "languages": ["en"],
            "author": "Test Author",
            "cover": {"composition": "cover-1", "artwork": "photo-1"},
        },
        "sections": [
            {"id": "sec-1", "title": "First chapter", "level": 1, "blocks": [{"id": "b-1", "type": "paragraph", "text": "Body text."}]}
        ],
    }
    target = work / "book.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    result = typst_driver.build(target, work / "out.pdf", work / "build", offline=True)
    manuscript = model.load(target, root=ROOT)
    check = cover_check.check(result.pdf, manuscript)
    assert check.status == "pass", check.detail
    assert check.evidence["artwork"] == "present"
    assert check.evidence["chromaticPixels"] > 0


def test_inline_photograph_citations_do_not_fail_illustration_limit() -> None:
    pdf = compile_typ(
        '#set page(paper: "a4")\nCompare Photograph 1. and Photograph 2. in the body prose.\n\nPhotograph 1. Actual caption.\n',
        "audit-inline-photo-refs",
    )
    result = illustration_limit.check(pdf)
    assert result.status == "pass", result.detail
    assert result.evidence["pages"] == {1: ["Photograph 1"]}


def test_text_probes_avoid_sum_substring_and_respect_caption_override(tmp_path: Path) -> None:
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "text-probe-fixes",
        "metadata": {"title": "Probe Fixes", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-1",
                "title": "First",
                "blocks": [
                    {"id": "b-eq", "type": "equation", "typst": "summary = consumer"},
                ],
            },
            {
                "id": "sec-2",
                "title": "Second",
                "standfirst": "See {ref:sec-2}.",
                "blocks": [{"id": "b-p2", "type": "paragraph", "text": "Body."}],
            },
        ],
    }
    target = tmp_path / "book.yaml"
    target.write_text(yaml.safe_dump(data))
    manuscript = model.load(target, root=ROOT)
    probes = text_check.expected_probes(manuscript)
    assert "∑" not in probes
    assert "§1" not in probes
    assert "§2" in probes


def test_rights_check_flags_unconfirmed_cover_artwork(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "assets", tmp_path / "assets")
    rec_path = tmp_path / "assets" / "illustrations" / "photo-1" / "record.yaml"
    rec = yaml.safe_load(rec_path.read_text())
    rec["rightsStatus"] = "unconfirmed"
    rec_path.write_text(yaml.safe_dump(rec))

    target = tmp_path / "book.yaml"
    target.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "unconfirmed-cover",
                "metadata": {
                    "title": "Reading a Sample",
                    "languages": ["en"],
                    "cover": {"composition": "cover-1", "artwork": "photo-1"},
                },
                "sections": [
                    {"id": "sec-1", "title": "One", "blocks": [{"id": "b-1", "type": "paragraph", "text": "Body."}]}
                ],
            }
        )
    )
    pdf, _prev, _sheet = specimen_build()
    manuscript = model.load(target, root=tmp_path)
    check = rights_check.check(pdf, manuscript, draft=False)
    assert check.status == "fail"
    assert check.code == "RIGHTS_INCOMPLETE"


def test_pdf_measure_cache_returns_consistent_results() -> None:
    pdf, _prev, _sheet = specimen_build()
    first = pdf_measure.for_pdf(pdf)
    second = pdf_measure.for_pdf(pdf)
    assert first is second
    assert len(first.page_texts()) == first.page_count()
    assert first.numbered_labels()["Photograph 1"] == 4
