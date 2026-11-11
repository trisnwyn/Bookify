"""Task 12: glyph coverage, extraction probes and page geometry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from helpers import ADVERSARIAL, ROOT, SPECIMEN, compile_typ, specimen_build
from bookify.manuscript import model
from bookify.verify.checks import glyphs, pages, text


def test_glyphs_text_and_pages_pass_on_the_specimen() -> None:
    pdf, _previous, _sheet = specimen_build()
    manuscript = model.load(SPECIMEN)

    assert glyphs.check(pdf, manuscript).status == "pass"
    assert text.check(pdf, manuscript).status == "pass"
    assert pages.check_geometry(pdf).status == "pass"


def test_blank_page_fails_geometry() -> None:
    pdf = compile_typ('#set page(paper: "a4")\n#pagebreak()\n', "blank")

    result = pages.check_geometry(pdf)
    assert result.status == "fail"
    assert result.code == "BUILD_FAILED"
    assert result.evidence["blanks"]


def test_blank_page_on_a_ten_page_book_is_named() -> None:
    parts = ["Page one."]
    for number in range(2, 11):
        parts.append("" if number == 5 else f"Page {number}.")
    source = '#set page(paper: "a4")\n' + "\n#pagebreak()\n".join(parts)
    pdf = compile_typ(source, "ten-pages-blank")

    assert pages.blank_pages(pdf) == [5]
    result = pages.check_geometry(pdf)
    assert result.status == "fail"
    assert result.code == "BUILD_FAILED"
    assert result.evidence["blanks"] == [5]


def test_blank_page_ten_of_twelve_is_named() -> None:
    parts = ["Page one."]
    for number in range(2, 13):
        parts.append("" if number == 10 else f"Page {number}.")
    source = '#set page(paper: "a4")\n' + "\n#pagebreak()\n".join(parts)
    pdf = compile_typ(source, "twelve-pages-blank-ten")

    assert pages.blank_pages(pdf) == [10]
    result = pages.check_geometry(pdf)
    assert result.status == "fail"
    assert result.code == "BUILD_FAILED"
    assert result.evidence["blanks"] == [10]


def test_missing_glyph_fails_with_named_code(tmp_path: Path) -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    data["sections"][0]["blocks"][0]["text"] += " " + chr(0x1F9EA)
    target = tmp_path / "emoji.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    manuscript = model.load(target, root=ROOT)
    pdf, _previous, _sheet = specimen_build()

    result = glyphs.check(pdf, manuscript)
    assert result.status == "fail"
    assert result.code == "GLYPH_MISSING"


def test_text_probes_fail_for_a_different_manuscript() -> None:
    pdf, _previous, _sheet = specimen_build()
    other = model.load(ADVERSARIAL)

    result = text.check(pdf, other)
    assert result.status == "fail"
    assert "Adversarial placement" in result.detail
