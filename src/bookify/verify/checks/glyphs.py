"""Font embedding and per-script coverage."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from bookify.design import coverage
from bookify.manuscript import model
from bookify.verify.checks import Check, failed, passed


def check(pdf: Path, manuscript: model.Manuscript) -> Check:
    fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=False).stdout
    unembedded = [line.split()[0] for line in fonts.splitlines()[2:] if re.search(r"\s+no\s+", line)]
    if unembedded:
        return failed("glyphs", "GLYPH_MISSING", f"unembedded font(s): {unembedded}", fonts=unembedded)
    result = coverage.check(manuscript, manuscript.root)
    if not result.ok:
        missing = [code for _, code in result.missing]
        return failed("glyphs", "GLYPH_MISSING", f"missing glyphs: {missing[:10]}", missing=missing)
    return passed(
        "glyphs",
        f"all faces embedded; {result.characters} characters covered ({result.japanese} Japanese)",
        characters=result.characters,
        japanese=result.japanese,
    )
