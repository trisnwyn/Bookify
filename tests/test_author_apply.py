"""Task 18: apply drafts, preserve uncertainty, never invent values."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from helpers import compile_typ, manuscript_with
from bookify.authoring import apply as author_apply
from bookify.authoring import plan
from bookify.intake import manifest
from bookify.manuscript import model

SOURCE = '''
#set page(paper: "a4", margin: 40pt)
Page one text.
#pagebreak()
Page two text.
#pagebreak()
Page three is an image-only slide.
#image("/assets/illustrations/photo-1/original.jpg", width: 40%)
'''

CHANGED = SOURCE.replace("Page one text.", "Page one text, revised.")


def _setup(tmp_path: Path):
    source = compile_typ(SOURCE, "apply-src")
    intake = tmp_path / "intake"
    manifest.build(source, intake)
    manuscript_path = manuscript_with("apply-src", tmp_path / "manuscript.yaml")
    cache_dir = tmp_path / "cache"
    plan_data = plan.build(intake, model.load(manuscript_path), cache_dir)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan_data))
    return manuscript_path, cache_dir, plan_path, tmp_path / "draft.json"


def _work(plan_path: Path, page: int) -> dict:
    data = json.loads(plan_path.read_text())
    return next(item for item in data["work"] if item["page"] == page)


def _page(plan_path: Path, page: int, section_id: str = "sec-src", **fields) -> dict:
    item = _work(plan_path, page)
    return {
        "page": page,
        "sectionId": section_id,
        "textSha256": item["textSha256"],
        "inputHash": item["inputHash"],
        **fields,
    }


def _apply(manuscript_path: Path, cache_dir: Path, plan_path: Path, draft_path: Path, draft: dict):
    draft_path.write_text(json.dumps(draft))
    return author_apply.apply(
        plan_path, draft_path, manuscript_path, cache_dir, manuscript_path.parent / "decisions.jsonl"
    )


def test_apply_replaces_anchored_blocks_and_reports_calls(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    result = _apply(
        manuscript_path, cache_dir, plan_path, draft_path,
        {
            "sourceId": "apply-src",
            "pages": [
                _page(
                    plan_path, 1,
                    blocks=[{"id": "b-one", "type": "paragraph", "text": "Rewritten page one."}],
                    decisions=["Rewrote page one from the extracted text."],
                )
            ],
            "modelCalls": [{"model": "agent", "purpose": "rewrite page 1"}],
        },
    )

    assert result["revision"] == 2
    assert result["modelCalls"] == [{"model": "agent", "purpose": "rewrite page 1"}]
    manuscript = model.load(manuscript_path)
    block = next(block for block in manuscript.sections[0]["blocks"] if block["id"] == "b-one")
    assert block["text"] == "Rewritten page one."
    assert {"sourceId": "apply-src", "page": 1} in block["sourceAnchors"]
    assert (manuscript_path.parent / "decisions.jsonl").is_file()

    remaining = plan.build(tmp_path / "intake", manuscript, cache_dir)["work"]
    assert [item["page"] for item in remaining] == [2, 3]


def test_changed_source_page_is_applied_again(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    _apply(
        manuscript_path, cache_dir, plan_path, draft_path,
        {
            "sourceId": "apply-src",
            "pages": [_page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "First pass."}])],
        },
    )

    # Same source id (same file stem) with page one changed: the plan must list
    # page one as changed, and a matching draft must actually replace the text.
    changed_source = compile_typ(CHANGED, "apply-src")
    manifest.build(changed_source, tmp_path / "intake")
    replanned = plan.build(tmp_path / "intake", model.load(manuscript_path), cache_dir)
    plan_path.write_text(json.dumps(replanned))
    assert [(item["page"], item["reason"]) for item in replanned["work"]] == [
        (1, "changed"), (2, "new"), (3, "new")
    ]

    result = _apply(
        manuscript_path, cache_dir, plan_path, draft_path,
        {
            "sourceId": "apply-src",
            "pages": [_page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "Second pass."}])],
        },
    )

    assert result["revision"] == 3
    assert result["applied"][0]["page"] == 1
    manuscript = model.load(manuscript_path)
    block = next(block for block in manuscript.sections[0]["blocks"] if block["id"] == "b-one")
    assert block["text"] == "Second pass."


def test_changed_page_apply_converges_and_records_the_new_hash(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    _apply(
        manuscript_path, cache_dir, plan_path, draft_path,
        {
            "sourceId": "apply-src",
            "pages": [_page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "First pass."}])],
        },
    )
    changed_source = compile_typ(CHANGED, "apply-src")
    manifest.build(changed_source, tmp_path / "intake")
    replanned = plan.build(tmp_path / "intake", model.load(manuscript_path), cache_dir)
    plan_path.write_text(json.dumps(replanned))
    _apply(
        manuscript_path, cache_dir, plan_path, draft_path,
        {
            "sourceId": "apply-src",
            "pages": [_page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "Second pass."}])],
        },
    )

    converged = plan.build(tmp_path / "intake", model.load(manuscript_path), cache_dir)["work"]
    assert 1 not in [item["page"] for item in converged], "the applied page must stop being work"
    current = json.loads((tmp_path / "intake" / "manifest.json").read_text())["pages"][0]["textSha256"]
    index = json.loads((cache_dir / "index.json").read_text())
    assert index["apply-src#1"]["textSha256"] == current


def test_stale_draft_for_changed_content_is_rejected(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    old_draft = {
        "sourceId": "apply-src",
        "pages": [_page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "Old content."}])],
    }
    _apply(manuscript_path, cache_dir, plan_path, draft_path, old_draft)
    before = manuscript_path.read_bytes()

    changed_source = compile_typ(CHANGED, "apply-src")
    manifest.build(changed_source, tmp_path / "intake")
    replanned = plan.build(tmp_path / "intake", model.load(manuscript_path), cache_dir)
    plan_path.write_text(json.dumps(replanned))

    # Simulate a deleted cache and an old draft applied to the new plan.
    with pytest.raises(Exception) as error:
        _apply(manuscript_path, tmp_path / "fresh-cache", plan_path, draft_path, old_draft)

    assert getattr(error.value, "code", "") == "INPUT_INVALID"
    assert manuscript_path.read_bytes() == before


def test_unreadable_page_becomes_an_explicit_unresolved_block(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    _apply(
        manuscript_path, cache_dir, plan_path, draft_path,
        {
            "sourceId": "apply-src",
            "pages": [
                _page(
                    plan_path, 3,
                    unreadable=True,
                    note="The label is not readable in the extraction.",
                    decisions=["Recorded uncertainty instead of guessing."],
                )
            ],
        },
    )

    manuscript = model.load(manuscript_path)
    block = next(
        block
        for block in manuscript.sections[0]["blocks"]
        if any(anchor["page"] == 3 for anchor in block.get("sourceAnchors", []))
    )
    assert block["type"] == "unresolved"
    assert block["confidence"] == "unreadable"
    assert block["note"].startswith("The label is not readable")
    assert "text" not in block


def test_unreadable_page_cannot_carry_blocks(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    before = manuscript_path.read_text()

    with pytest.raises(Exception) as error:
        _apply(
            manuscript_path, cache_dir, plan_path, draft_path,
            {
                "sourceId": "apply-src",
                "pages": [
                    _page(
                        plan_path, 3,
                        unreadable=True,
                        note="Unreadable.",
                        blocks=[{"type": "paragraph", "text": "Guessed 95%."}],
                    )
                ],
            },
        )

    assert getattr(error.value, "code", "") == "SCHEMA_INVALID"
    assert manuscript_path.read_text() == before


def test_invalid_manuscript_is_not_written(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    before = manuscript_path.read_text()

    with pytest.raises(Exception) as error:
        _apply(
            manuscript_path, cache_dir, plan_path, draft_path,
            {
                "sourceId": "apply-src",
                "pages": [
                    _page(
                        plan_path, 1,
                        blocks=[{"id": "b-fig", "type": "paragraph", "text": "Duplicate id."}],
                    )
                ],
            },
        )

    assert getattr(error.value, "code", "") == "SCHEMA_INVALID"
    assert manuscript_path.read_text() == before
    assert model.load(manuscript_path).revision == 1


def test_failed_atomic_replace_keeps_the_old_manuscript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    before = manuscript_path.read_bytes()

    def fail(_source, _target):
        raise OSError("simulated disk full")

    monotonic = author_apply.os.replace
    monkeypatch.setattr(author_apply.os, "replace", fail)
    try:
        with pytest.raises(OSError):
            _apply(
                manuscript_path, cache_dir, plan_path, draft_path,
                {
                    "sourceId": "apply-src",
                    "pages": [_page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "Lost."}])],
                },
            )
    finally:
        monkeypatch.setattr(author_apply.os, "replace", monotonic)

    assert manuscript_path.read_bytes() == before
    assert model.load(manuscript_path).revision == 1
    assert not list(manuscript_path.parent.glob(f".{manuscript_path.name}.*.tmp"))
    assert not (cache_dir / "index.json").exists() or not json.loads((cache_dir / "index.json").read_text())


def test_draft_without_the_plan_echo_is_rejected(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    before = manuscript_path.read_bytes()

    with pytest.raises(Exception) as error:
        _apply(
            manuscript_path, cache_dir, plan_path, draft_path,
            {
                "sourceId": "apply-src",
                "pages": [{"page": 1, "sectionId": "sec-src", "blocks": [
                    {"id": "b-one", "type": "paragraph", "text": "Unverifiable content."}
                ]}],
            },
        )

    assert getattr(error.value, "code", "") == "INPUT_INVALID"
    assert manuscript_path.read_bytes() == before


def test_write_failure_before_replace_keeps_the_old_manuscript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    before = manuscript_path.read_bytes()

    def fail(_descriptor):
        raise OSError("simulated disk full while flushing")

    monkeypatch.setattr(author_apply.os, "fsync", fail)

    with pytest.raises(OSError):
        _apply(
            manuscript_path, cache_dir, plan_path, draft_path,
            {"sourceId": "apply-src", "pages": [
                _page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "Lost."}])
            ]},
        )

    assert manuscript_path.read_bytes() == before
    assert model.load(manuscript_path).revision == 1
    assert not list(manuscript_path.parent.glob(f".{manuscript_path.name}.*.tmp"))
    assert not (cache_dir / "index.json").exists()


def test_page_outside_the_plan_is_refused(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)

    with pytest.raises(Exception) as error:
        _apply(
            manuscript_path, cache_dir, plan_path, draft_path,
            {"sourceId": "apply-src", "pages": [{"page": 9, "sectionId": "sec-src", "blocks": []}]},
        )

    assert getattr(error.value, "code", "") == "INPUT_INVALID"
    assert model.load(manuscript_path).revision == 1


def test_reapplying_an_unchanged_draft_is_a_no_op(tmp_path: Path) -> None:
    manuscript_path, cache_dir, plan_path, draft_path = _setup(tmp_path)
    draft = {
        "sourceId": "apply-src",
        "pages": [
            _page(plan_path, 1, blocks=[{"id": "b-one", "type": "paragraph", "text": "Once."}])
        ],
        "modelCalls": [{"model": "agent", "purpose": "first pass"}],
    }
    first = _apply(manuscript_path, cache_dir, plan_path, draft_path, draft)
    before = manuscript_path.read_text()

    second = _apply(manuscript_path, cache_dir, plan_path, draft_path, draft)

    assert first["revision"] == 2
    assert second["revision"] == 2
    assert second["applied"] == []
    assert second["skipped"] == [{"sourceId": "apply-src", "page": 1, "reason": "already applied"}]
    assert second["modelCalls"] == []
    assert manuscript_path.read_text() == before
