"""Task 13: limits read from the PDF, rights status and contents folios."""

from __future__ import annotations

from pathlib import Path

import yaml

from helpers import ROOT, SPECIMEN, compile_typ, specimen_build
from bookify.manuscript import model
from bookify.verify.checks import illustration_limit, rights, xrefs


def test_specimen_is_within_the_illustration_limit() -> None:
    pdf, _previous, _sheet = specimen_build()

    result = illustration_limit.check(pdf)
    assert result.status == "pass"
    assert result.evidence["pages"] == {4: ["Photograph 1"]}


def test_two_captions_on_one_page_fail_only_the_limit() -> None:
    pdf = compile_typ(
        '#set page(paper: "a4")\nPhotograph 1. First.\nPhotograph 2. Second.\n',
        "two-on-one",
    )

    result = illustration_limit.check(pdf)
    assert result.status == "fail"
    assert result.code == "ILLUSTRATION_LIMIT"
    assert result.evidence["offending"] == {1: ["Photograph 1", "Photograph 2"]}


def test_contents_folio_mismatch_fails_xrefs(tmp_path: Path) -> None:
    pdf = compile_typ(
        '#set page(paper: "a4")\nContents\n\nSection A . . . 9\n#pagebreak()\nSection A\n',
        "bad-contents",
    )
    manuscript = tmp_path / "one.yaml"
    manuscript.write_text(
        yaml.safe_dump(
            {
                "schemaVersion": "1.0",
                "revision": 1,
                "id": "one-section",
                "metadata": {"title": "One", "languages": ["en"]},
                "sections": [
                    {
                        "id": "sec-a",
                        "title": "Section A",
                        "blocks": [{"id": "b-one", "type": "paragraph", "text": "Body."}],
                    }
                ],
            }
        )
    )

    result = xrefs.check(pdf, model.load(manuscript, root=ROOT))
    assert result.status == "fail"
    assert result.code == "XREF_MISSING"
    assert "contents says 9" in result.detail


def test_specimen_xrefs_pass() -> None:
    pdf, _previous, _sheet = specimen_build()

    result = xrefs.check(pdf, model.load(SPECIMEN))
    assert result.status == "pass"


def test_unconfirmed_rights_are_flagged() -> None:
    pdf, _previous, _sheet = specimen_build()
    manuscript = model.load(ROOT / "fixtures" / "negative" / "rights.yaml")

    result = rights.check(pdf, manuscript, draft=False)
    assert result.status == "fail"
    assert result.code == "RIGHTS_INCOMPLETE"
    assert "unconfirmed" in result.detail
