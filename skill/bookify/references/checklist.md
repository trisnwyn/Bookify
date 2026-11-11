# Authoring checklist

Use with `skill/bookify/SKILL.md`. Tick only what you verified.

## Before authoring

- [ ] Source path is read-only and outside the repository (or copied deliberately as a fixture).
- [ ] `bookify intake` ran; `manifest.json` exists and every page has a `textSha256`.
- [ ] Image-only pages are listed and none has fabricated text.
- [ ] `bookify author plan` shows only genuinely new or changed pages.

## Per page

- [ ] Every block has a `sourceAnchors` entry for that page.
- [ ] Every number, name and date appears in the extracted page text.
- [ ] No definition or explanation was added that the source does not contain.
- [ ] An unreadable label is an `unresolved` block with a note, not a guess.
- [ ] A chart value that cannot be read is `null` with a note; approximate readings are marked.
- [ ] A diagram is labelled a reconstruction when it is redrawn from a description.
- [ ] A decision line records every rewrite, drop or uncertainty.

## Illustrations

- [ ] Selection has a relevance reason (recognition, evidence, context, concrete example).
- [ ] No quota or filler selection.
- [ ] Reused selections were not searched for again.
- [ ] Record has path, origin URL, creator, licence, credit, caption, alt, kind, `rightsStatus`.
- [ ] Unknown rights remain `unconfirmed`; only an explicit `--draft` build may contain them.
- [ ] Contemporary photographs, later depictions and reconstructions are named as such.
- [ ] Alt text describes the image without interpreting it.
- [ ] Composition is explicit: `full`, `side-left` or `side-right`; absent means full; charts/diagrams do not carry a composition.
- [ ] A side illustration's companion is the immediately following prose block in the same section, is used once, and is at most 520 collapsed characters including title/term/note.
- [ ] The composition is unbreakable: image, caption, credit and companion share one page; the whole unit defers if needed; no split or silent drop.
- [ ] Side captions are column-centred on every line; credits stay left in the same image column; full/chart/diagram descriptions remain page-centred.

## Catalogue

- [ ] The manuscript is `content/catalogue.yaml`, `id: visual-catalogue`, languages `[en, vi, ja]`, data only, with no per-figure scripts.
- [ ] Exact inventory: 16 chart figures / 15 families, 10 diagram presets, 4 illustration families.
- [ ] Pie (`hole: 0`) and donut (`hole > 0`) are both present and counted as one family.
- [ ] The 29-row coverage table matches the PDF; pie/donut is one row with two figure references.
- [ ] Every chart is `verification: synthetic` with notes and no source/source anchors; every diagram is `synthetic: true` with a note.
- [ ] Chart labels are Latin/Vietnamese only; Japanese appears in diagrams, body text and captions.
- [ ] At least one short and one wrapped caption exists for charts, diagrams and photographs; every description line is centred to its declared measure (page or side column).
- [ ] Credits and source notes are separate; credits are left at the page margin or inside the side image column; table and equation captions are unchanged.
- [ ] Four illustrations appear once each, on four distinct pages; no page holds two; the catalogue demonstrates at least one `side-left`, one `side-right` and one `full`.
- [ ] Side companion prose is honest and explicit; the bilingual side caption wraps without clipping; all text is extractable.
- [ ] The double offline build is identical and `verify` returns `gate: pass`, including the 30-figure geometry check.

## Build and verify

- [ ] `manuscript check` and `design check` pass.
- [ ] Build ran with `--offline`; build directory is inside the project.
- [ ] A second build exists for the layout comparison.
- [ ] Every page was rendered and inspected; contact sheet saved.
- [ ] Verify report has `gate: pass`, no failing check, and a review record.
- [ ] Approximate values and reconstructions are visible in the PDF text.
- [ ] `uv run python -m pytest -q` passes (`uv run pytest` cannot spawn in this environment).
