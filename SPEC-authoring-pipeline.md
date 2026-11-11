# SPEC-authoring-pipeline

Module id: `authoring-pipeline` · depends on: `source-intake`, `manuscript-model` · build step 7 · status: approved 2026-11-10.

## Objective

Turn extracted evidence into a valid manuscript through an agent-guided flow that never invents values, records why it chose what it chose, and reprocesses only what changed. This is the only module allowed to call a model, and it produces data — never a PDF.

The revised local skill (`skill/bookify/SKILL.md`) lives here: it tells an agent how to author a manuscript and how to invoke publishing. It does not replace or overwrite the global `pdf-book-design` skill.

## Tech stack

Python for planning, cache, validation and asset bookkeeping; the model calls are made by the agent running the skill (no new provider service, no hosted component). Manuscript writes go through `manuscript-model`; source reads go through `source-intake` manifests.

## Commands (proposed, not implemented)

```bash
uv run bookify author plan  --intake build/intake --manuscript content/specimen.yaml --out build/author-plan.json
uv run bookify author apply --plan build/author-plan.json --manuscript content/specimen.yaml
uv run bookify author status --manuscript content/specimen.yaml --json
```

`plan` is deterministic and offline. `apply` is the agent-driven step: it may call a model, must record each call, and writes only through the manuscript validator.

## Project structure

```
src/bookify/authoring/
  plan.py                    # intake vs manuscript diff -> work items
  cache.py                  # content-addressed responses, prompt version, provenance
  decisions.py              # decisions log: why redrawn / dropped / marked uncertain
  illustrations.py          # relevance selection + rights capture
  apply.py                  # applies planned work, validates, writes revision
build/cache/authoring/      # disposable; deleting it changes nothing in publishing
skill/bookify/
  SKILL.md                  # local authoring + publishing guide
  references/               # source-grounding and rights checklists
```

## Workflow (the skill's contract)

1. **Plan** — list sections and blocks whose source anchors changed, are new, or have no manuscript block. Unchanged work is not listed.
2. **Ground** — draft each block from the cited page; every factual claim keeps its `sourceAnchors`. Quoting is short and attributed.
3. **Never invent** — an unreadable label, value or name becomes `null` plus an uncertainty note and a decision entry. Paraphrase is allowed; new numbers, names, dates and categories are not.
4. **Interpret figures** — read a source chart/diagram once, store the numbers or geometry plus `verification` and confidence, and let `figure-engine` redraw it. The interpretation is data; the picture is never copied.
5. **Select illustrations** — rank candidates per section by relevance before pagination, for recognition, evidence, context or a concrete example only. No quota, no filler, no automatic new search once an illustration is selected.
6. **Capture rights** — every selected illustration gets path, origin URL, creator, licence, credit, caption, alt, kind and `rightsStatus`. Permission to use a lecture deck is not a licence for its stock artwork; unknown stays `unconfirmed`.
7. **Record decisions** — every drop, redraw, merge or uncertainty gets one line with the reason.
8. **Validate and write** — `manuscript check` must pass; a failed validation does not increment `revision`.

## Cache and incremental rules

Cache key: `sha256(schemaVersion | promptVersion | sourceId#page | contentSha256)`. A hit makes no model call. A miss stores the raw response with model id, prompt version, timestamp and input hash for audit. `build/cache/` is disposable: publishing works after deletion, and cache contents never become manuscript truth.

Reprocessing: a changed page maps to blocks through `sourceAnchors`; only those blocks and their derived figures are replanned. `author plan` on unchanged inputs returns `{ "work": [] }` and `apply` performs zero model calls.

## Code style

```python
def plan_work(intake: IntakeIndex, manuscript: Manuscript) -> list[WorkItem]:
    """Return only sections/blocks whose cited content changed or is missing."""
    stale = [b for b in manuscript.blocks if intake.hash_for(b.anchors) != b.sourceHash]
    missing = [s for s in intake.sections if not manuscript.has_section(s.id)]
    return [*map(WorkItem.from_block, stale), *map(WorkItem.from_section, missing)]
```

## Testing strategy

`pytest` under `tests/authoring/`:

- No-invention fixture: an image-only page with no readable value yields `null` + uncertainty, never a number or name; a test fails if any new numeric literal appears without an anchor.
- Incremental: changing one page replans only its blocks and derived figures; unchanged pages produce zero work items.
- Cache: second apply with unchanged inputs performs zero model calls; deleting the cache does not change the manuscript's validity or the built PDF.
- Rights: a selected illustration without licence/credit/alt fails validation; `unconfirmed` is preserved, never upgraded.
- Selection: given identical candidate rankings, the chosen set is identical; no quota rule exists in code.
- Skill: the local skill file references only commands that exist in this index and never instructs overwriting the global skill.

## Boundaries

- Always: cite an anchor per factual block; keep interpretation separate from rendering; record decisions; keep the cache disposable; keep the skill local.
- Ask first: adding a new source type, changing the prompt/cache contract, allowing a model call outside `author apply`.
- Never: publish a PDF; overwrite the global skill; infer a licence; invent an unreadable value; copy a source chart as an image; re-search for an already selected illustration; write a manuscript that fails validation.

## Success criteria

1. From one fixture deck section, `author apply` produces a manuscript that passes `manuscript check`.
2. An image-only page produces an uncertainty record and no fabricated value.
3. Second apply on unchanged inputs reports zero model calls and no manuscript change.
4. Every selected illustration has complete rights metadata; unknown rights remain explicit.
5. `skill/bookify/SKILL.md` guides authoring and publishing using only commands listed in `SPEC-INDEX.md`.
6. Deleting `build/cache/` and rebuilding still passes the specimen gate.
