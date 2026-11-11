"""Task 17: work lists only for changed pages, plus the interpretation cache."""

from __future__ import annotations

import json
from pathlib import Path

from helpers import compile_typ, manuscript_with
from bookify.authoring import cache, plan
from bookify.intake import manifest
from bookify.manuscript import model

SOURCE = '''
#set page(paper: "a4", margin: 40pt)
Page one text.
#pagebreak()
Page two text.
#pagebreak()
Page three text.
'''


def _setup(tmp_path: Path):
    source = compile_typ(SOURCE, "author-src")
    intake = tmp_path / "intake"
    manifest.build(source, intake)
    manuscript_path = manuscript_with("author-src", tmp_path / "manuscript.yaml")
    return intake, model.load(manuscript_path), tmp_path / "cache"


def _applied_record(intake: Path, page: dict, prompt_version: str = plan.PROMPT_VERSION) -> dict:
    data = json.loads((intake / "manifest.json").read_text())
    source_id = data["sourceId"]
    return cache.record(
        text_sha256=page["textSha256"],
        prompt_version=prompt_version,
        model="agent",
        input_hash=cache.key(source_id, page["page"], page["textSha256"], prompt_version),
    )


def _index(intake: Path, prompt_version: str = plan.PROMPT_VERSION) -> dict:
    data = json.loads((intake / "manifest.json").read_text())
    return {
        f"{data['sourceId']}#{page['page']}": _applied_record(intake, page, prompt_version)
        for page in data["pages"]
    }


def test_new_pages_are_the_work_and_figures_are_named(tmp_path: Path) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)

    result = plan.build(intake, manuscript, cache_dir)

    assert [item["page"] for item in result["work"]] == [1, 2, 3]
    assert all(item["reason"] == "new" for item in result["work"])
    page_one = result["work"][0]
    assert list(page_one["blockIds"]) == ["b-one"]
    assert list(page_one["figureIds"]) == []
    assert page_one["promptVersion"] == plan.PROMPT_VERSION
    assert page_one["schemaVersion"] == cache.SCHEMA_VERSION
    assert page_one["inputHash"]
    page_two = result["work"][1]
    assert list(page_two["figureIds"]) == ["b-fig"]


def test_index_makes_unchanged_pages_zero_work(tmp_path: Path) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    cache.save_index(cache_dir, _index(intake))

    assert plan.build(intake, manuscript, cache_dir)["work"] == []


def test_changed_page_is_the_only_work(tmp_path: Path) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    data = json.loads((intake / "manifest.json").read_text())
    index = _index(intake)
    index[f"{data['sourceId']}#2"]["textSha256"] = "0" * 64
    cache.save_index(cache_dir, index)

    work = plan.build(intake, manuscript, cache_dir)["work"]
    assert [item["page"] for item in work] == [2]
    assert work[0]["reason"] == "changed"
    assert list(work[0]["blockIds"]) == ["b-fig"]


def test_prompt_version_change_reappears_as_work(tmp_path: Path) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    cache.save_index(cache_dir, _index(intake, prompt_version="v0"))

    work = plan.build(intake, manuscript, cache_dir)["work"]

    assert [item["page"] for item in work] == [1, 2, 3]
    assert all(item["reason"] == "changed" for item in work)


def test_changing_the_prompt_constant_invalidates_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    cache.save_index(cache_dir, _index(intake))
    assert plan.build(intake, manuscript, cache_dir)["work"] == []

    monkeypatch.setattr(plan, "PROMPT_VERSION", "v2")
    work = plan.build(intake, manuscript, cache_dir)["work"]

    assert [item["page"] for item in work] == [1, 2, 3]


def test_changing_the_schema_constant_invalidates_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    cache.save_index(cache_dir, _index(intake))
    assert plan.build(intake, manuscript, cache_dir)["work"] == []

    monkeypatch.setattr(cache, "SCHEMA_VERSION", "2.0")
    work = plan.build(intake, manuscript, cache_dir)["work"]

    assert [item["page"] for item in work] == [1, 2, 3]


def test_legacy_hash_only_index_is_stale(tmp_path: Path) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    data = json.loads((intake / "manifest.json").read_text())
    cache.save_index(
        cache_dir,
        {f"{data['sourceId']}#{page['page']}": page["textSha256"] for page in data["pages"]},
    )

    assert len(plan.build(intake, manuscript, cache_dir)["work"]) == 3


def test_cache_key_covers_prompt_version_and_content(tmp_path: Path) -> None:
    first = cache.key("deck", 2, "a" * 64, "v1")
    same = cache.key("deck", 2, "a" * 64, "v1")
    other_prompt = cache.key("deck", 2, "a" * 64, "v2")
    other_text = cache.key("deck", 2, "b" * 64, "v1")

    assert first == same
    assert len({first, other_prompt, other_text}) == 3

    cache.put(tmp_path, first, {"text": "drafted"}, "agent", "v1", "a" * 64)
    record = cache.get(tmp_path, first)
    assert record["output"] == {"text": "drafted"}
    assert record["model"] == "agent" and record["promptVersion"] == "v1" and record["inputHash"] == "a" * 64
    assert cache.get(tmp_path, other_prompt) is None


def test_deleting_the_cache_does_not_change_validation(tmp_path: Path) -> None:
    intake, manuscript, cache_dir = _setup(tmp_path)
    cache.put(cache_dir, cache.key("author-src", 1, "a" * 64, "v1"), {"x": 1}, "agent", "v1", "a" * 64)

    import shutil

    shutil.rmtree(cache_dir)
    assert model.load(manuscript.path, root=manuscript.root).revision == 1
