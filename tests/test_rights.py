"""Task 10: rights are enforced, captions distinguish kinds, credit is rendered."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from bookify.errors import BookifyError
from bookify.publish import rights, typst_driver

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"
NEGATIVE = ROOT / "fixtures" / "negative" / "rights.yaml"


def _work(name: str) -> Path:
    path = ROOT / ".cache" / f"rights-{name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_normal_build_rejects_unconfirmed_rights() -> None:
    work = _work("refuse")
    with pytest.raises(BookifyError) as error:
        typst_driver.build(NEGATIVE, work / "rights.pdf", work / "build", offline=True)

    assert error.value.code == "RIGHTS_INCOMPLETE"
    assert "unconfirmed" in error.value.message


def test_explicit_draft_allows_unconfirmed_rights() -> None:
    work = _work("draft")
    result = typst_driver.build(NEGATIVE, work / "rights.pdf", work / "build", offline=True, draft=True)

    assert result.report["draft"] is True
    text = subprocess.run(
        ["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    assert "Credit unknown" in text
    assert "Photograph 1." in text


def test_caption_wording_distinguishes_kinds() -> None:
    base = dict(
        id="x", path="p", origin_url="u", creator="c", licence="l",
        credit="cr", caption="A scene from the ceremony.", alt="a", rights_status="verified",
    )

    reconstruction = rights.Illustration(kind="reconstruction", **base)
    later = rights.Illustration(kind="later_depiction", **base)
    contemporary = rights.Illustration(kind="contemporary_photograph", **base)

    assert "Reconstruction." in rights.caption(reconstruction, None)
    assert "Later depiction." in rights.caption(later, None)
    assert "Reconstruction" not in rights.caption(contemporary, None)
    assert rights.caption(contemporary, "An override.") == "An override."


def test_lowercase_prose_keeps_the_printed_class_wording() -> None:
    base = dict(
        id="x", path="p", origin_url="u", creator="c", licence="l",
        credit="cr", alt="a", rights_status="verified",
    )
    reconstruction = rights.Illustration(
        kind="reconstruction",
        caption="Conceptual reconstruction of a bow, measured from a description.",
        **base,
    )

    caption = rights.caption(reconstruction, None)

    assert caption == reconstruction.caption, "an honest prose class name is not duplicated"
    assert rights.printed_class_wording(reconstruction, None) == "reconstruction"


def test_a_caption_without_the_class_gets_the_canonical_sentence_and_probe() -> None:
    base = dict(
        id="x", path="p", origin_url="u", creator="c", licence="l",
        credit="cr", caption="A measured scene.", alt="a",
        rights_status="verified",
    )
    reconstruction = rights.Illustration(kind="reconstruction", **base)

    assert rights.caption(reconstruction, None) == "A measured scene. Reconstruction."
    assert rights.printed_class_wording(reconstruction, None) == "Reconstruction"


def test_record_missing_credit_fails(tmp_path: Path) -> None:
    record = yaml.safe_load((ROOT / "assets" / "illustrations" / "photo-1" / "record.yaml").read_text())
    del record["credit"]
    directory = tmp_path / "assets" / "illustrations" / "photo-1"
    directory.mkdir(parents=True)
    (directory / "record.yaml").write_text(yaml.safe_dump(record))

    with pytest.raises(BookifyError) as error:
        rights.load(tmp_path, "photo-1")

    assert error.value.code == "RIGHTS_INCOMPLETE"
    assert "credit" in error.value.message


def test_specimen_renders_caption_and_credit() -> None:
    work = _work("specimen")
    result = typst_driver.build(SPECIMEN, work / "specimen.pdf", work / "build", offline=True)
    text = subprocess.run(
        ["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout

    assert "Photograph 1." in text
    assert "Photo: William Ng / US Department of State (public domain)" in text
    assert "formal public greeting" in text


def test_soft_hyphen_line_break_rejoins_a_wrapped_credit() -> None:
    from bookify.verify.checks import rights as rights_check

    wrapped = "Artwork: original vector drawing made for this catalogue; concep\u00ad\n\ntual reconstruction, no external source."
    credit = "Artwork: original vector drawing made for this catalogue; conceptual reconstruction, no external source."

    assert rights_check._normalise(credit) in rights_check._normalise(wrapped)
