---
name: bookify-authoring
description: Author a Bookify manuscript from extracted sources and publish it offline with Typst. Use when turning supplied PDFs/slides into a validated manuscript, recording uncertainty and rights, reviewing the visual catalogue, or rebuilding the specimen. This is a local project skill; it does not replace the global pdf-book-design skill.
---

# Bookify authoring (local skill)

One local pipeline: extract sources → author a validated manuscript → build a Typst PDF offline → verify it. Content generation is separate from rendering; publishing never calls a model or the network.

This skill governs *this repository*. The global `pdf-book-design` skill remains the design reference and is not modified.

## Before you start

- Work from the repository root; the `bookify` CLI is run with `uv run bookify …`.
- Read `SPEC-INDEX.md` for contracts. The manuscript schema is `schemas/manuscript.schema.json`.
- Sources are read-only. Put extracted output under `build/`; it is disposable.
- The build directory must live inside the repository (Typst resolves assets from the project root).
- Publishing requires `bwrap` for the offline namespace; it is a verification dependency, not a pinned package.

## Workflow

### 1. Extract a source

```bash
uv run bookify intake --source "<path to a PDF>" --out build/intake --changed-only --json
```

- `manifest.json` is byte-stable across reruns; pages are addressed as `<sourceId>#<page>`.
- Image-only pages are flagged `isImageOnly: true` with **no** text. Never invent their labels.
- Rerunning with an unchanged source reports `skipped: true` and extracts nothing.

### 2. Plan the work

```bash
uv run bookify author plan --intake build/intake --manuscript content/<book>.yaml \
  --out build/author-plan.json --cache-dir build/cache/authoring --json
```

Only pages whose text hash changed since the last apply appear. Unchanged inputs produce `"work": []`.

### 3. Draft and apply (agent-assisted)

Read the extracted page text (`build/intake/pages/page-NNN.txt`). Draft blocks strictly from it:

- every factual block keeps its page anchor (apply adds it if missing);
- no new names, numbers, dates or categories;
- a page whose content cannot be read becomes one `unresolved` block with a note — never a guessed value;
- chart values you cannot read stay `null` with a note; never fill them in;
- record one decision per rewrite, drop or uncertainty.

Write a draft JSON. Copy `textSha256` and `inputHash` from each plan work item; apply rejects a page whose echo does not match the current plan:

```json
{
  "sourceId": "<sourceId>",
  "promptVersion": "v1",
  "model": "<agent or model id>",
  "modelCalls": [{"model": "…", "purpose": "…"}],
  "pages": [
    {"page": 7, "sectionId": "sec-x",
     "textSha256": "<from plan work item>",
     "inputHash": "<from plan work item>",
     "blocks": [{"type": "paragraph", "text": "…", "confidence": "verified"}],
     "decisions": ["Paraphrased page 7 only; no definitions added."]}
  ]
}
```

```bash
uv run bookify author apply --plan build/author-plan.json --draft <draft>.json \
  --manuscript content/<book>.yaml --cache-dir build/cache/authoring \
  --decisions build/authoring/decisions.jsonl --json
```

- A failing validation leaves the manuscript untouched and does not bump `revision`.
- Reapplying an unchanged draft is a no-op: `applied: []`, `modelCalls: []`.
- The cache is disposable; deleting `build/cache/` never changes validity or the built PDF.

### 4. Record illustrations

```bash
uv run bookify author select --section sec-x --illustration photo-1 \
  --reason "Recognition: shows the ceremony in context." --json
uv run bookify author status --manuscript content/<book>.yaml --json
```

- Selection happens before pagination and is recorded once; repeating it reuses the record without a new search.
- There is no quota. Select only for recognition, evidence, context or a concrete example.
- Rights live in `assets/illustrations/<id>/record.yaml`: path, origin URL, creator, licence, credit, caption, alt, kind, `rightsStatus`. Unknown rights stay `unconfirmed`; a normal build refuses them, `--draft` allows them explicitly.
- Never claim a licence from a lecture deck's presence. Generated art is only for conceptual or fictional subjects.
- **Composition is authored data, not a runtime choice.** An illustration may declare:
  ```yaml
  composition:
    preset: side-left          # full | side-left | side-right
    companion: b-photo-note    # required for side-*; forbidden for full
  ```
  The companion must be the **immediately following** prose block in the same section, at most 520 collapsed characters including any title/term/note, and is rendered once. `side-left` puts the image column left; `side-right` puts it right; `full` is the existing full-measure layout. There is no auto-pairing, alternation, model or build-time layout choice.
- A side composition is one unbreakable unit. If it does not fit, the whole unit defers to the next page; if it cannot fit an empty text block the build fails with `BUILD_FAILED`. The report records `compositions` and `deferredIllustrations`; never split or drop only the companion.
- Side captions are centred line by line in the image column; the credit stays separate and left in that column. Charts, diagrams and full-width illustrations remain main-measure/page-centred.

### 5. Build and verify

```bash
uv run bookify manuscript check --manuscript content/<book>.yaml --json
uv run bookify design check --manuscript content/<book>.yaml --json
uv run bookify build --manuscript content/<book>.yaml --out dist/<book>.pdf \
  --offline --build-dir build/<book> --json
uv run bookify build --manuscript content/<book>.yaml --out dist/<book>-rebuild.pdf \
  --offline --build-dir build/<book>-rebuild
uv run bookify verify --pdf dist/<book>.pdf --manuscript content/<book>.yaml \
  --previous-pdf dist/<book>-rebuild.pdf --build-report build/<book>/build-report.json \
  --contact-sheet build/<book>-contact.png --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report build/verify.json
```

Render and look at every page (`pdftoppm`, contact sheet). Record what you see; the verifier treats inspection as a manual check with evidence.

### 6. Review the visual catalogue

`content/catalogue.yaml` is a data-only review document: 12 sections, 16 chart figures across 15 families (pie and donut are one family, two figures), 10 diagram figures across 10 presets, four illustration figures across four curation families, and a 29-row coverage table. No per-figure Python or Typst snippet belongs in it.

The catalogue demonstrates the approved composition mapping: Photograph 1 (`photo-1`) is `side-left`, Photograph 2 (`hist-1`) is `side-right` with a bilingual caption, Photograph 3 (`art-1`) is `full`, and Photograph 4 (`rec-1`) is `side-left`. Each side block is followed immediately by its explicit companion block. Changing a mapping is a manuscript edit, not a build option.

```bash
uv run bookify manuscript check --manuscript content/catalogue.yaml --json
uv run bookify design check --manuscript content/catalogue.yaml --json
uv run bookify figures render --manuscript content/catalogue.yaml --out build/figures/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue.pdf \
  --offline --build-dir build/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue-rebuild.pdf \
  --offline --build-dir build/catalogue-rebuild
uv run bookify verify --pdf dist/catalogue.pdf --manuscript content/catalogue.yaml \
  --previous-pdf dist/catalogue-rebuild.pdf --build-report build/catalogue/build-report.json \
  --contact-sheet build/catalogue-contact.png --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report build/verify.json
```

The catalogue keeps the same rules as any book:

- **Descriptions are centred to their declared measure.** Charts, diagrams and full-width illustrations are page-centred line by line, including wrapped lines. Side illustrations are centred line by line in their image column; their credits stay separate and left in that column. Table and equation captions keep their existing alignment.
- **Composition is explicit data.** `full`, `side-left` and `side-right` are the only presets. Side presets require the immediately following prose companion; `full` forbids one; 520 collapsed characters is the cap; the companion is consumed once. No auto-pairing, alternation or model choice.
- **The composition is unbreakable.** Image, caption, credit and companion stay on one page; the whole unit defers if needed and never splits. Four illustrations occupy four distinct pages, one per page.
- **Charts are synthetic and say so.** `verification: synthetic` forbids a source, requires notes, and prints `Synthetic data.`; chart labels stay Latin/Vietnamese because Matplotlib renders through Spectral.
- **Diagrams are illustrative and say so.** `synthetic: true` requires a block note and prints `Illustrative diagram.`; Japanese belongs in diagrams, body text and captions.
- **The inventory is exact.** Both pie (`hole: 0`) and donut (`hole > 0`) must be present; a missing or extra kind, preset or family fails the catalogue gate.
- **The 29-row coverage table** lists each family once and references its figure or figures.

### 7. Tests

```bash
uv run python -m pytest -q
```

`uv run pytest` fails to spawn the console script in this environment; the
module form is the working command.

## Rules that are not optional

- **Never invent** an unreadable label, value or name. Use `unresolved`, `null` + note, or an uncertainty note.
- **Do not upgrade uncertainty.** `inferred` stays inferred; approximate chart values keep their wording.
- **Publishing is offline and model-free.** `build` refuses without `--offline`.
- **One illustration per final page**, enforced from the PDF; the build defers and reports rather than silently dropping.
- **Rights before publication.** Every illustration carries complete rights; unknown stays explicit.
- **Original material is read-only.** Copy into the repository only when a test needs a stable fixture.

## Outputs

| Path | What |
| --- | --- |
| `content/<book>.yaml` | manuscript |
| `dist/<book>.pdf` | built book |
| `build/<book>/build-report.json` | pages, sections, numbering, placements, warnings, pins |
| `build/verify.json` | gate report |
| `build/authoring/decisions.jsonl` | why each edit or uncertainty exists |
| `build/intake/manifest.json` | stable source evidence |

## Visual vocabulary

- **Charts — 15 families, 16 figures:** `bar`, `grouped_bar`, `stacked_bar`, `line`, `area`, `scatter`, `bubble`, `histogram`, `box`, `violin`, `heatmap`, `radar`, `pie`/donut, `waterfall`, `error_bar`. Pie and donut share one family but are two figures (`hole: 0` and `hole > 0`).
- **Diagrams — 10 presets, 10 figures:** `process`, `model`, `cycle`, `hierarchy`, `decision_tree`, `network`, `timeline`, `matrix`, `venn`, `swimlane`.
- **Illustrations — 4 families:** contemporary photograph, public-domain historical image, original editorial artwork, conceptual reconstruction. The catalogue shows side-left, side-right and full compositions with explicit companions.
- Charts, diagrams and full illustrations are page-centred; side illustrations are image-column-centred with left credits in that column. Charts are synthetic and diagrams illustrative; both state it in the printed caption.

## Known limits of this v1

- Chart labels are Latin/Vietnamese only; Japanese is used in diagrams, body text and captions.
- No OCR: image-only pages must be authored from what is actually readable.
- Typst adds spacing after `。`; pagination is not hand-tuned.
- Side compositions are fixed grid columns (46 % image + 16 pt gutter); there is no text wrap around an image and no runtime layout choice.
- Tagged-PDF reading order is not claimed; visual column order and manuscript order are the contract.
- The specimen uses a neutral fixture; the public test fixture `fixtures/synthetic-trial.yaml` is synthetic and source-independent.
- The public repository history starts with a single initial commit; there is no earlier project history.
