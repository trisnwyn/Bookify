"""The PDF must describe the book it contains, and invent nothing."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from helpers import SPECIMEN, compile_typ
from bookify.manuscript import model
from bookify.verify.checks import docmeta

TITLE = "Reading a Sample"
AUTHOR = "Bookify specimen"


@pytest.fixture(scope="module")
def manuscript() -> model.Manuscript:
    return model.load(SPECIMEN)


def pdf(name: str, title: str | None = None, author: str | None = None) -> Path:
    fields = []
    if title is not None:
        fields.append(f'title: "{title}"')
    if author is not None:
        fields.append(f'author: "{author}"')
    lines = [f"#set document({', '.join(fields)})"] if fields else []
    lines += ['#set page(paper: "a4")', "= A chapter", "Body text."]
    return compile_typ("\n".join(lines) + "\n", name)


def test_matching_identity_passes(manuscript) -> None:
    check = docmeta.check(pdf("docmeta-match", TITLE, AUTHOR), manuscript)

    assert check.id == "docmeta"
    assert check.status == "pass", check.detail
    assert check.evidence["title"] == TITLE
    assert check.evidence["author"] == AUTHOR
    assert check.evidence["xmp"] is True
    # The declared language is evidence, never a silent pass or fail.
    assert "languages" in check.evidence
    assert check.evidence["expectedLanguages"] == ["en", "vi", "ja"]


def test_wrong_title_fails(manuscript) -> None:
    check = docmeta.check(pdf("docmeta-wrong", "Another Book", AUTHOR), manuscript)

    assert check.status == "fail"
    assert check.code == "BUILD_FAILED"
    assert "title is" in check.detail


def test_missing_title_fails(manuscript) -> None:
    check = docmeta.check(pdf("docmeta-untitled"), manuscript)

    assert check.status == "fail"
    assert check.code == "BUILD_FAILED"
    assert "no title" in check.detail


def test_missing_author_fails_when_the_manuscript_names_one(manuscript) -> None:
    check = docmeta.check(pdf("docmeta-anonymous", TITLE), manuscript)

    assert check.status == "fail"
    assert "no author" in check.detail


def test_invented_author_fails(manuscript) -> None:
    anonymous = replace(manuscript, data={
        **manuscript.data,
        "metadata": {"title": TITLE, "languages": ["en"]},
    })

    check = docmeta.check(pdf("docmeta-invented", TITLE, "Someone Else"), anonymous)

    assert check.status == "fail"
    assert "invents an author" in check.detail


def test_untitled_manuscript_still_needs_the_title(manuscript) -> None:
    check = docmeta.check(pdf("docmeta-untitled-again", author=AUTHOR), manuscript)

    assert check.status == "fail"
    assert "no title" in check.detail
