---
name: Bookify
description: Author a Bookify manuscript from extracted sources and publish it offline with Typst. Use when turning supplied PDFs or slides into a validated manuscript, recording uncertainty and rights, reviewing the visual catalogue, or rebuilding the specimen. The bundle ID is bookify; the separate global pdf-book-design skill is a reference only and is not modified.
---

# Bookify (portable skill bundle)

Bookify is a local authoring and offline publishing pipeline: extract sources →
author a validated manuscript → build a Typst PDF offline → verify the PDF.
Content generation is separate from rendering; publishing never calls a model
or the network.

This bundle is self-contained for the engine, vendored tools, fonts and assets.
System tools, the uv-managed interpreter and the uv cache are external
prerequisites, as listed below. The engine is in `engine/` below the directory
that contains this `SKILL.md` (the skill base directory). The original
project-local skill is preserved unchanged at `engine/skill/bookify/` for
reference; this file is the packaged entry point with relocated commands.

The global `pdf-book-design` skill is a separate design reference. This bundle
does not replace, install over, or modify it.

## Setup once per installation

Prerequisites, all observed on the packaging host (Linux x86_64):

- `uv` (tested 0.12.24) and network or a populated uv cache for the first sync.
- Python 3.13.16 (the engine's `toolchain.lock.json` pin; `uv` can provide it).
- Bubblewrap `bwrap` with user namespaces enabled (offline build proof).
- Poppler tools: `pdftotext`, `pdfinfo`, `pdftoppm`, `pdffonts`.
- ImageMagick: `magick montage` (or `montage`) for contact sheets.
- No system fonts are used: the bundle vendors every font.

```sh
export BOOKIFY_SKILL="${BOOKIFY_SKILL:-$HOME/.config/opencode/skills/bookify}"
export BOOKIFY_ENGINE="$BOOKIFY_SKILL/engine"
cd "$BOOKIFY_ENGINE"

uv sync --python 3.13.16 --frozen
uv run bookify toolchain doctor --json
```

`uv sync` may use the network or the local uv cache. That is setup only.
`bookify build` and `bookify verify` are offline and model-free; they do not
download packages or fonts.

If the bundle lives somewhere other than the standard global path, set
`BOOKIFY_SKILL` to the directory containing this `SKILL.md` before running any
command. Do not run engine commands from a user's project directory: the
engine finds its project root from its own `pyproject.toml`, and build output
must stay inside that root.

## Working rule: change to the bundled engine first

```sh
cd "$BOOKIFY_ENGINE"
```

All commands below assume that current directory. Write disposable output under
`work/` and final PDFs under `dist/` inside the engine. Never write into the
user's current repository, and never modify a source original.

## Workflow

### 1. Extract a source

```sh
uv run bookify intake --source "<path to a PDF>" --out work/intake --changed-only --json
```

- `manifest.json` is byte-stable across reruns; pages are `<sourceId>#<page>`.
- Image-only pages are flagged `isImageOnly: true` with no text. Never invent
  their labels.
- Rerunning with an unchanged source reports `skipped: true`.

### 2. Plan the work

```sh
uv run bookify author plan --intake work/intake --manuscript content/<book>.yaml \
  --out work/author-plan.json --cache-dir work/cache/authoring --json
```

Only pages whose text hash changed since the last apply appear. Unchanged
inputs produce `"work": []`.

### 3. Draft and apply (agent-assisted)

Read the extracted page text (`work/intake/pages/page-NNN.txt`). Draft blocks
strictly from it:

- every factual block keeps its page anchor (apply adds it if missing);
- no new names, numbers, dates or categories;
- a page whose content cannot be read becomes one `unresolved` block with a
  note — never a guessed value;
- chart values you cannot read stay `null` with a note; never fill them in;
- record one decision per rewrite, drop or uncertainty.

Write a draft JSON. Copy `textSha256` and `inputHash` from each plan work item;
apply rejects a page whose echo does not match the current plan:

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

```sh
uv run bookify author apply --plan work/author-plan.json --draft <draft>.json \
  --manuscript content/<book>.yaml --cache-dir work/cache/authoring \
  --decisions work/authoring/decisions.jsonl --json
```

- A failing validation leaves the manuscript untouched and does not bump
  `revision`.
- Reapplying an unchanged draft is a no-op: `applied: []`, `modelCalls: []`.
- The cache is disposable; deleting `work/cache/` never changes validity or the
  built PDF.

### 4. Record illustrations

```sh
uv run bookify author select --section sec-x --illustration photo-1 \
  --reason "Recognition: shows the ceremony in context." --json
uv run bookify author status --manuscript content/<book>.yaml --json
```

- Selection happens before pagination and is recorded once; repeating it reuses
  the record without a new search.
- There is no quota. Select only for recognition, evidence, context or a
  concrete example.
- Rights live in `assets/illustrations/<id>/record.yaml`: path, origin URL,
  creator, licence, credit, caption, alt, kind, `rightsStatus`. Unknown rights
  stay `unconfirmed`; a normal build refuses them, `--draft` allows them
  explicitly.
- Never claim a licence from a lecture deck's presence. Generated art is only
  for conceptual or fictional subjects.
- **Composition is authored data, not a runtime choice.** An illustration may
  declare:
  ```yaml
  composition:
    preset: side-left          # full | side-left | side-right
    companion: b-photo-note    # required for side-*; forbidden for full
  ```
  The companion must be the **immediately following** prose block in the same
  section, at most 520 collapsed characters including any title/term/note, and
  is rendered once. `side-left` puts the image column left; `side-right` puts it
  right; `full` is the existing full-measure layout. There is no auto-pairing,
  alternation, model or build-time layout choice.
- A side composition is one unbreakable unit. If it does not fit, the whole
  unit defers to the next page; if it cannot fit an empty text block the build
  fails with `BUILD_FAILED`. The report records `compositions` and
  `deferredIllustrations`; never split or drop only the companion.
- Side captions are centred line by line in the image column; the credit stays
  separate and left in that column. Charts, diagrams and full-width
  illustrations remain main-measure/page-centred.
- One illustration per final page; the build defers and reports rather than
  silently dropping.

### 5. Check, build twice offline, inspect, verify

```sh
uv run bookify manuscript check --manuscript content/<book>.yaml --json
uv run bookify design check --manuscript content/<book>.yaml --json
uv run bookify build --manuscript content/<book>.yaml --out dist/<book>.pdf \
  --offline --build-dir work/<book> --json
uv run bookify build --manuscript content/<book>.yaml --out dist/<book>-rebuild.pdf \
  --offline --build-dir work/<book>-rebuild
mkdir -p work/pages
pdftoppm -png -r 110 dist/<book>.pdf work/pages/page
magick montage work/pages/page-*.png -tile 4x work/<book>-contact.png
uv run bookify verify --pdf dist/<book>.pdf --manuscript content/<book>.yaml \
  --previous-pdf dist/<book>-rebuild.pdf \
  --build-report work/<book>/build-report.json \
  --contact-sheet work/<book>-contact.png \
  --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report work/verify.json
```

Render and look at every page. Record what you actually see. The verifier treats
inspection as a manual check with evidence; it does not replace human sign-off.

### 6. Review the visual catalogue

`content/catalogue.yaml` is a data-only review document: 12 sections, 16 chart
figures across 15 families (pie and donut are one family, two figures), 10
diagram figures across 10 presets, four illustration figures across four
curation families, and a 29-row coverage table. No per-figure Python or Typst
snippet belongs in it.

The catalogue demonstrates the approved composition mapping: Photograph 1
(`photo-1`) is `side-left`, Photograph 2 (`hist-1`) is `side-right` with a
bilingual caption, Photograph 3 (`art-1`) is `full`, and Photograph 4 (`rec-1`)
is `side-left`. Each side block is followed immediately by its explicit
companion block. Changing a mapping is a manuscript edit, not a build option.

```sh
uv run bookify manuscript check --manuscript content/catalogue.yaml --json
uv run bookify design check --manuscript content/catalogue.yaml --json
uv run bookify figures render --manuscript content/catalogue.yaml \
  --out work/figures/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue.pdf \
  --offline --build-dir work/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml \
  --out dist/catalogue-rebuild.pdf --offline --build-dir work/catalogue-rebuild
mkdir -p work/catalogue-pages
pdftoppm -png -r 110 dist/catalogue.pdf work/catalogue-pages/page
magick montage work/catalogue-pages/page-*.png -tile 4x work/catalogue-contact.png
uv run bookify verify --pdf dist/catalogue.pdf --manuscript content/catalogue.yaml \
  --previous-pdf dist/catalogue-rebuild.pdf \
  --build-report work/catalogue/build-report.json \
  --contact-sheet work/catalogue-contact.png \
  --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report work/verify.json
```

Expected on the documented compatible stack:

- 19 A4 pages; two builds byte-identical;
- `dist/catalogue.pdf` SHA-256
  `b285d49f9263f85f45fbcbc20f6c61882b1ebbf125e0d6959d86a34c5e67c930`;
- `verify` gate `pass`, 30 figures within ±2 pt, 16 charts / 15 families,
  10 diagrams / 10 presets, 4 illustrations / 4 families, 29 coverage rows,
  12 contents entries, 65 text probes, 6 embedded faces;
- the 110 dpi / 4-column contact sheet SHA-256
  `3497d40cb78a1f00cb373d44cb9c9a49d5bd41bd99dfdb38ed5d41fd57f67630`.

Any difference is a finding to report, not a value to edit.

The catalogue keeps the same rules as any book:

- **Descriptions are centred to their declared measure.** Charts, diagrams and
  full-width illustrations are page-centred line by line, including wrapped
  lines. Side illustrations are centred line by line in their image column;
  their credits stay separate and left in that column. Table and equation
  captions keep their existing alignment.
- **Composition is explicit data.** `full`, `side-left` and `side-right` are the
  only presets. Side presets require the immediately following prose companion;
  `full` forbids one; 520 collapsed characters is the cap; the companion is
  consumed once. No auto-pairing, alternation or model choice.
- **The composition is unbreakable.** Image, caption, credit and companion stay
  on one page; the whole unit defers if needed and never splits. Four
  illustrations occupy four distinct pages, one per page.
- **Charts are synthetic and say so.** `verification: synthetic` forbids a
  source, requires notes, and prints `Synthetic data.`; chart labels stay
  Latin/Vietnamese because Matplotlib renders through Spectral.
- **Diagrams are illustrative and say so.** `synthetic: true` requires a block
  note and prints `Illustrative diagram.`; Japanese belongs in diagrams, body
  text and captions.
- **The inventory is exact.** Both pie (`hole: 0`) and donut (`hole > 0`) must
  be present; a missing or extra kind, preset or family fails the catalogue
  gate.
- **The 29-row coverage table** lists each family once and references its
  figure or figures.

### 7. Tests

The full existing suite is included in the bundle (`engine/tests/`).

```sh
cd "$BOOKIFY_ENGINE"
uv run python -m pytest -q
```

`uv run pytest` fails to spawn the console script in the observed environment;
the module form is the working command. The suite takes about five minutes and
builds with the bundled pins, fonts and templates.

## Rules that are not optional

- **Never invent** an unreadable label, value or name. Use `unresolved`,
  `null` + note, or an uncertainty note.
- **Do not upgrade uncertainty.** `inferred` stays inferred; approximate chart
  values keep their wording.
- **Publishing is offline and model-free.** `build` refuses without `--offline`.
- **One illustration per final page**, enforced from the PDF; the build defers
  and reports rather than silently dropping.
- **Rights before publication.** Every illustration carries complete rights;
  unknown stays explicit.
- **Original material is read-only.** Copy into the engine only when a test
  needs a stable fixture.
- **No per-figure scripts in a manuscript.** Charts, diagrams and compositions
  are authored data.

## Outputs

| Path (inside the engine) | What |
| --- | --- |
| `content/<book>.yaml` | manuscript |
| `dist/<book>.pdf` | built book |
| `work/<book>/build-report.json` | pages, sections, numbering, placements, warnings, pins |
| `work/verify.json` | gate report |
| `work/authoring/decisions.jsonl` | why each edit or uncertainty exists |
| `work/intake/manifest.json` | stable source evidence |

## Visual vocabulary

- **Charts — 15 families, 16 figures:** `bar`, `grouped_bar`, `stacked_bar`,
  `line`, `area`, `scatter`, `bubble`, `histogram`, `box`, `violin`, `heatmap`,
  `radar`, `pie`/donut, `waterfall`, `error_bar`. Pie and donut share one family
  but are two figures (`hole: 0` and `hole > 0`).
- **Diagrams — 10 presets, 10 figures:** `process`, `model`, `cycle`,
  `hierarchy`, `decision_tree`, `network`, `timeline`, `matrix`, `venn`,
  `swimlane`.
- **Illustrations — 4 families:** contemporary photograph, public-domain
  historical image, original editorial artwork, conceptual reconstruction. The
  catalogue shows side-left, side-right and full compositions with explicit
  companions.
- Charts, diagrams and full illustrations are page-centred; side illustrations
  are image-column-centred with left credits in that column. Charts are
  synthetic and diagrams illustrative; both state it in the printed caption.

## Known limits of this bundle

- Observed and tested platform: Linux x86_64. The vendored Typst binary is
  `x86_64-unknown-linux-musl`; Windows and macOS are not supported or claimed.
- `uv sync` is a setup step and may require the network or a populated uv cache.
  Build and verify are offline, but a first-time setup is not claimed to be
  offline or hermetic.
- `bwrap` and user namespaces are required to prove the offline build; without
  them `bookify build` refuses.
- Chart labels are Latin/Vietnamese only; Japanese is used in diagrams, body
  text and captions.
- No OCR: image-only pages must be authored from what is actually readable.
- Typst adds spacing after `。`; pagination is not hand-tuned.
- Side compositions are fixed grid columns (46 % image + 16 pt gutter); there
  is no text wrap around an image and no runtime layout choice.
- Tagged-PDF reading order is not claimed; visual column order and manuscript
  order are the contract.
- The specimen uses a neutral fixture; the public test fixture
  `fixtures/synthetic-trial.yaml` is synthetic and source-independent.
- The public source history starts with a single initial commit. The engine
  source, tests, fixtures and documentation are MIT-licensed; see `LICENCES.md`. Third-party
  components keep their own licences and notices.

## Rollback

The bundle installs only one directory. To remove the global skill:

```sh
rm -rf "$HOME/.config/opencode/skills/bookify"
```

Do not remove or edit `~/.config/opencode/skills/pdf-book-design` or any other
skill. To restore, re-extract `bookify-skill.tar.gz` with the packaging helper
or `tar`. The archive is self-contained; deleting the installed directory loses
no source data beyond the disposable `work/` output and the `.venv` created by
setup.
