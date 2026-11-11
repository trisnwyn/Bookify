"""Independent acceptance: the side composition unit stays unbreakable.

Task 55 gap found by mutation: the adversarial fixture's compositions both fit,
so setting the side block's `breakable` flag to `true` changed nothing and
survived the suite. This test supplies the missing input — a side composition
taller than the text block — and requires the documented loud failure instead of
a silently split composition (SPEC Area 2.4).
"""

from __future__ import annotations

import pytest

from helpers import ROOT
from bookify.errors import BookifyError
from bookify.publish import typst_driver

OVER_TALL_CAPTION = "Photograph 1. " + (
    "A deliberately over-tall caption for the fit probe. " * 90
).strip()


def test_an_over_tall_side_composition_fails_loudly_instead_of_splitting() -> None:
    work = ROOT / ".cache" / "visual-layout-acceptance"
    work.mkdir(parents=True, exist_ok=True)
    manuscript = work / "over-tall.yaml"
    manuscript.write_text(
        "schemaVersion: \"1.0\"\n"
        "revision: 1\n"
        "id: over-tall-side\n"
        "metadata:\n"
        "  title: \"Over-tall side composition\"\n"
        "  languages: [en]\n"
        "sections:\n"
        "  - id: sec-over-tall\n"
        "    title: \"Over-tall\"\n"
        "    blocks:\n"
        "      - id: b-photo\n"
        "        type: illustration\n"
        "        illustrationId: hist-1\n"
        f"        caption: \"{OVER_TALL_CAPTION}\"\n"
        "        composition:\n"
        "          preset: side-left\n"
        "          companion: b-note\n"
        "      - id: b-note\n"
        "        type: paragraph\n"
        "        text: \"Short companion.\"\n"
    )

    with pytest.raises(BookifyError) as error:
        typst_driver.build(
            manuscript,
            work / "over-tall.pdf",
            work / "build",
            offline=True,
        )

    assert error.value.code == "BUILD_FAILED"
    assert error.value.locator == "b-photo"
    assert "does not fit the text block" in error.value.message
