"""Task 16: changed-only processing and per-page diffs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from helpers import compile_typ
from bookify.intake import manifest


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


BASE = '''
#set page(paper: "a4", margin: 40pt)
Page one is stable.
#pagebreak()
Page two says alpha.
#pagebreak()
Page three says gamma.
'''

CHANGED = BASE.replace("Page two says alpha.", "Page two says beta.")


def test_unchanged_source_skips_extraction(tmp_path: Path, capsys) -> None:
    from bookify.toolchain.cli import main

    source = compile_typ(BASE, "changes-base")
    out = tmp_path / "intake"
    assert main(["intake", "--source", str(source), "--out", str(out), "--json"]) == 0
    capsys.readouterr()
    before = _sha(out / "manifest.json")
    page_mtime = (out / "pages" / "page-001.txt").stat().st_mtime_ns

    assert main(["intake", "--source", str(source), "--out", str(out), "--changed-only", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["skipped"] is True
    assert payload["changedPages"] == []
    assert _sha(out / "manifest.json") == before
    assert (out / "pages" / "page-001.txt").stat().st_mtime_ns == page_mtime
    assert json.loads((out / "changes.json").read_text())["changedPages"] == []


def test_one_changed_page_is_the_only_change(tmp_path: Path) -> None:
    out = tmp_path / "intake"
    first = manifest.build(compile_typ(BASE, "changes-one"), out)
    second = manifest.build(compile_typ(CHANGED, "changes-two"), out)

    from bookify.intake import changes

    diff = changes.diff(first, second)
    assert diff["changedPages"] == [2]
    assert diff["addedPages"] == [] and diff["removedPages"] == []
    assert first["pages"][0]["textSha256"] == second["pages"][0]["textSha256"]
    assert first["pages"][2]["textSha256"] == second["pages"][2]["textSha256"]


def test_manifest_replacement_is_atomic(tmp_path: Path) -> None:
    out = tmp_path / "intake"
    manifest.build(compile_typ(BASE, "atomic"), out)

    assert not (out / "manifest.json.tmp").exists()
    assert not (out / ".tmp").exists()
