# Bookify agent-skill release — layout correction refresh (Tasks 62–68)

Status: **candidate refreshed, installed and independently reproducible — no human
sign-off, no commit, no push, no new dependency, font, mode, or engine change.**

Date: 2026-11-13. Scope: refresh the public canonical `dist/` books with the
corrected typography/pagination engine, re-check the two trial books, refresh
this report, repack the candidate under a new archive name, upgrade the global
skill and commands with the previous verified ownership proof, and re-run the
source-denied installed proof.

This document describes actual commands and measured results. It is not a human
PDF review and does not declare the overall Phase 2 review/test pipeline
complete.

## 1. Environment and pins

| Item | Value |
| --- | --- |
| Python | 3.13.16 (`.venv`) |
| Typst | 0.15.1 (`tools/typst/typst`), vendored CeTZ 0.5.3 / Oxifmt 1.0.0 |
| Offline build | `bwrap` 0.12.0, `--unshare-net`, no model calls |
| Poppler | 26.01.0 (`pdftotext`, `pdftoppm`, `pdfinfo`, `pdffonts`) |
| ImageMagick | 7.1.2-34 (`magick montage`) |
| Page | A4 595.276 × 841.89 pt |
| Fonts | Spectral, Noto Serif CJK JP, STIX Two Math (fixed, unchanged) |

No product engine file was modified by this refresh. The only source edits are
the packaging release metadata below. The concurrent
`tests/test_skill_acceptance.py` work was not edited.

## 2. Canonical rebuild (before → after)

Old canonical PDFs were copied to
`build/history/2026-11-13-layout-rebuild/` before any overwrite, with
`BEFORE.tsv` and `AFTER.tsv`. Builds used the documented legacy offline
commands and the corrected engine:

```sh
.venv/bin/bookify build --manuscript content/specimen.yaml \
  --out dist/specimen.pdf --offline --build-dir build/specimen --json
.venv/bin/bookify build --manuscript content/specimen.yaml \
  --out dist/specimen-rebuild.pdf --offline --build-dir build/specimen-rebuild --json
.venv/bin/bookify build --manuscript content/catalogue.yaml \
  --out dist/catalogue.pdf --offline --build-dir build/catalogue --json
.venv/bin/bookify build --manuscript content/catalogue.yaml \
  --out dist/catalogue-rebuild.pdf --offline --build-dir build/catalogue-rebuild --json
```

`examples/catalogue.pdf` was replaced by the same corrected catalogue bytes so
the packaged example is coherent with the engine.

| File | Before | After |
| --- | --- | --- |
| `dist/specimen.pdf` | 6 pp, 350,887 B, `9d723490511e583c73c4573fd71c53e08dd4a9a6e7b2399b4d7583f644c53e72` | **5 pp**, 348,918 B, `eb22bae2fff0b2cc408f1e98b833f7a92c918e6667eeb4705c3c96717e49d248` |
| `dist/specimen-rebuild.pdf` | 6 pp, `9d723490…` | **5 pp**, `eb22bae2…` (byte-identical to build 1) |
| `dist/catalogue.pdf` | 19 pp, 739,327 B, `b285d49f9263f85f45fbcbc20f6c61882b1ebbf125e0d6959d86a34c5e67c930` | **19 pp**, 740,828 B, `0e90e4fda3cd203b7add75f23e0054f3f103cc69a92e6c055ce7114d0e1b8567` |
| `dist/catalogue-rebuild.pdf` | 19 pp, `b285d49f…` | **19 pp**, `0e90e4fd…` (byte-identical to build 1) |
| `examples/catalogue.pdf` | 19 pp, `b285d49f…` | **19 pp**, `0e90e4fd…` |

Both double builds share SHA-256 exactly (deterministic bytes). Page counts
were not forced to an old target; the specimen lost one tail page through the
corrected leading/reflow, and the catalogue kept 19 pages with corrected
pitches.

Contact sheets and page renders:

```sh
pdftoppm -png -r 110 dist/specimen.pdf build/specimen-pages/page
magick montage build/specimen-pages/page-*.png -tile 3x -geometry +6+6 build/specimen-contact.png
pdftoppm -png -r 110 dist/catalogue.pdf build/catalogue-pages/page
magick montage build/catalogue-pages/page-*.png -tile 4x -geometry +6+6 build/catalogue-contact.png
```

Evidence hashes: specimen contact `d6d8bee90c128a81ab0080a78ed8b345b6b09558ca569dc8faf3c04a45ecd99a`;
catalogue contact `b521e2a1efbc30baf453a173c0f7b377cbf2aa25ff5ea47a43d6764ca9292beb`.
All 5 specimen pages and all 19 catalogue pages were rendered and inspected
(not merely hashed).

## 3. Verify gate

```sh
.venv/bin/bookify verify --pdf dist/specimen.pdf --manuscript content/specimen.yaml \
  --previous-pdf dist/specimen-rebuild.pdf --build-report build/specimen/build-report.json \
  --contact-sheet build/specimen-contact.png \
  --reviewed-by "integrator agent, Tasks 67-68 (not human sign-off)" \
  --reviewed-at "2026-11-13T18:15:00+00:00" --report build/specimen-verify.json --json
```

Specimen: **gate pass** — offline, determinism, glyphs (`all faces embedded;
4707 characters covered (91 Japanese)`), text (12 probes), pages (`5 A4 pages,
none blank`), captions (3 within ±2 pt), illustration-limit (1), rights (1),
xrefs (2 entries). Review `manual`.

Catalogue: **gate pass** — the same checks plus catalogue inventory
(`exact 15/10/4 inventory: 16 charts, 10 diagrams, 4 illustrations, 29 coverage
rows`) and figure geometry (`30 figure(s): visible ink within ±2 pt of the
declared centre`); glyphs `8616 characters covered (416 Japanese)`; 65 text
probes; 12 contents entries. Review `manual`.

`build/specimen-verify.json` =
`738fcd57610e96f6b2fa8efb133263c1ab7fd240b9a84dd8954178849b3c4e63`;
`build/catalogue-verify.json` =
`b0690ae65d258548830294cee71ff94df064a100a80e750e15a4e3729cb1ac5a`.

## 4. Measured typography

Measured from the rebuilt canonical PDFs with `pdftotext -bbox-layout`
successive baseline-top deltas; independent role probes from the test stage are
cited where a role does not repeat enough in the public books.

| Role | Intended total | Measured in canonical output | Note |
| --- | ---: | ---: | --- |
| body, Latin | 15.30 | 15.30 (specimen pp3–5: 6+11+9 deltas; catalogue p3: 10) | pass |
| body, Vietnamese | 15.30 | 15.30 | pass |
| body, Japanese | bounded CJK metric | 15.99 | residual +0.69, documented |
| paragraph gap | pitch + 5.40 | 20.70 | strictly wider, not double-spaced |
| h1 → standfirst | — | 26.75 | pre-review value; superseded by §13: now 32.74–32.75 with a 3.36–3.60 pt 300 dpi white band |
| lead | 16.40 | 16.40 (independent probe) | pass |
| caption | 11.20 | 11.20 (catalogue pp16–18) | pass |
| table in-cell | 11.60 | 11.60 (wrapped-cell probe); single-line row baseline 15.68 from row inset | measurement nuance |
| note | 13.60 | 13.60 (probe) | pass |
| small / role label | 12.00 | 12.00 (probe) | pass |
| quote | 15.40 | 15.40 (probe) | pass |
| h1 / h2 / h3 | 30.00 / 16.50 / 14.00 | 30.00 / 16.50 / 14.00 (probe) | pass |

The role table's probe rows are the independent test stage's rendered
measurements (`.opencode/phase2-layout-tests.md`); the body/caption figures above
were re-measured directly from the new canonical `dist/` files for this report.

## 5. Hierarchy and page-flow decisions

- Specimen: two level-1 chapters start on pages 3 and 5; no blank page.
- Catalogue: one level-1 chapter per figure family (pages 3–19), with the
  existing one-illustration-per-page rule for the four photographs/artworks.
- Source-faithful trial: level 1 `A sample arrives`, then level 2 `The record`,
  level 2 `Three levels of reading`, level 3 `Comparing counts` flow on page 3;
  level 2 `When the evidence stops` continues on page 4; level 3 `The unlabelled
  plate` is the only section with an explicit `breakBefore: page` (page 5), a
  deliberate whole-plate unit.
- Teachable trial: level 1 chapter followed by level 2 sections, all flowing;
  `Key terms` is a deliberate level-2 `breakBefore: page` that starts the
  end-matter page 5, with `Source note` and its source-index table following.
  No chapter is forced to a new page; the book has a true end-of-book page 5,
  not a page per heading.

## 6. Page inspection, occupancy and whitespace rationale

Ink fraction is the non-white pixel fraction at 110 dpi; the blank band is the
longest fully blank internal horizontal band between the first and last ink row.
Full measurements are in `build/specimen-pages-measure.json` and
`build/catalogue-pages-measure.json`.

Specimen (5 pp): cover `0.0044` ink, contents `0.0031`, body pages `0.0873`,
`0.2788`, `0.0441`; the body pages end at the normal 12.5–12.7 mm foot margin.
Page 5 is the end of the last chapter and ends around mid-page (`~108 mm` blank
band inside the text block). This is a true chapter end, not an orphaned
heading or a clipped unit; the scope explicitly allows meaningful chapter-end
space.

Catalogue (19 pp): cover `0.0039`, contents `0.0115`, body/figure pages from
`0.0061` to `0.1566`. The catalogue is a figure-family review document, not
continuous prose: full-width plates and grouped chart families deliberately
leave generous space. Page 8 (one small uncertainty chart) and page 14 (one
remaining diagram fragment) are the sparsest pages; the pre-correction
catalogue had the same occupancy pattern (page 8 old ink `0.0058` vs new
`0.0061`; page 14 old `0.0081` vs new `0.0082`), so this is an inherited design
limit, not a regression from the correction.

No blank page, split figure, orphaned caption, missing glyph or overlap was seen
in the 24 rendered canonical pages. Review status remains `manual`: this was
agent inspection, not human sign-off.

## 7. Residual limitations (recorded, not fixed)

1. **h1 → standfirst tightness — fixed in review iteration 1.** The
   pre-review gap was `26.75 pt` (pre-fix `35.64 pt`). §13 records the R1 fix:
   `32.74–32.75 pt` with a `3.36–3.60 pt` 300 dpi white band and a rendered
   gate. This item is retained as history, not as a current limitation.
2. **Low-resolution source plate.** The source-faithful fixture plate is
   `72 × 48 px` and renders at `12 ppi` on page 5. It is pixelated by design of
   the supplied fixture; no new asset or upscaling was added.
3. **Generic `Photograph 1.` label.** The illustration system prints
   `Photograph N.` for the plate record even though the plate is a synthetic,
   unreadable image. The caption/note carry the real status; the label itself is
   generic.
4. **Page 5 end-matter whitespace.** The teachable trial deliberately starts
   `Key terms` on page 5 (level-2 `breakBefore: page`) and ends after
   `Source note` and the source-index table, leaving roughly half the page
   blank. It is a true end-of-book page, not a false page break, but the
   whitespace is visible.
5. **Catalogue single-figure whitespace.** Pages 8 and 14 carry one small figure
   or diagram fragment with large surrounding whitespace, inherited from the
   catalogue's figure-family design.
6. **CJK leading residual.** Japanese body pitch is `15.99` against `15.30` for
   Latin/Vietnamese — a documented `+0.69` residual from the CJK font metric,
   within the accepted bound.
7. **No human sign-off.** Every verify gate's review check is `manual`; no human
   has reviewed these PDFs.

## 8. Trial books — evidence check (no regeneration)

The two trial books already carry authored evidence. Their recorded hashes and
manuscripts were checked against the current files before any action:

| Book | Manuscript SHA-256 | Record says | Evidence PDF | Recorded PDF hash | Match |
| --- | --- | --- | --- | --- | --- |
| source-faithful | `15ea936af749784528bf13fed135be4b9be3154c42a7c534870674e771eaf889` | same revision 2 hash | 5 pp | `d5171f775cc94de0785c8ce4d837202fd76ceebbcddc838124b68db4a4348172` | yes |
| teachable | `cfdd084660f6f24935ce1b700b7e90c451c336acf1e10444228432d8c3ef0b5a` | same revision 2 hash | 5 pp | `a678b1a4c9d1c8f59a62f6aaf18430727d11780aaa898aca70fd97c069a7608f` | yes |

Because they match, both books were rebuilt in **external workspaces** with the
installed corrected engine (step 9) and reproduced the recorded hashes exactly
on two offline builds. The files under `content/agent-skill/*/evidence/` were
**not overwritten** — another owner's evidence was verified, not silently
regenerated. `verify` passed for both rebuilt copies (offline, determinism,
glyphs, text, pages, captions, illustration-limit, rights, xrefs; review
`manual`).

## 9. Candidate archive

New archive (old candidates preserved untouched):

| Property | Value |
| --- | --- |
| Archive | `dist/bookify-skill-plan2-layout.tar.gz` |
| SHA-256 | `395e5d2284f906ba36b0bd6cb415b534add749c550725972020485736e785f50` |
| Bytes | 58,410,882 |
| Members | 251 (250 payload files + `MANIFEST.json`) |
| Release | `2026-11-13` |
| Manifest SHA-256 | `aaff7de78c7a4b4e8e9328abc5dfcf5cd6fb8655609e523de52986cc53aac398` |
| Determinism | two consecutive packs byte-identical (`--check-determinism`) |

Preserved for history only: `dist/bookify-skill.tar.gz` (`b0a74e29…6098`, v1
archive; not the current candidate). The preliminary
`dist/bookify-skill-plan2.tar.gz` (`9fa6fc2e…efa5`) was removed in review fix
iteration 1 so it cannot be installed as a pre-layout engine; see §13.

Payload checks: `commands/bookify.md`,
`commands/bookify-source-faithful.md`,
`commands/bookify-teachable-textbook.md`; all six top-level `references/*.md`
guides; the corrected `engine/` (src, schemas, typst, vendor, assets, public
content, fixtures including `fixtures/agent-skill/source.pdf` and
`invocations.json`, tests, tools, skill); `examples/catalogue.pdf` with the
corrected `0e90e4fd…` bytes. No `.opencode`, `docs`, `build`, `dist`, `.venv`,
private trial manuscript, or `content/agent-skill` workspace is packaged.

Packaging metadata updated coherently: `RELEASE = "2026-11-13"`,
`CANONICAL_CATALOGUE_SHA = 0e90e4fd…`, and the packaged README's expected
catalogue hash.

Tests:

```sh
.venv/bin/python -m pytest packaging/test_bookify_skill_bundle.py -o addopts="" -q
# 40 passed
.venv/bin/python -m pytest tests/test_publish.py tests/test_verify_geometry.py tests/test_catalogue.py -o addopts="" -q
# 39 passed
```

The first pack attempt failed determinism because the concurrent acceptance-test
author was writing `tests/test_skill_acceptance.py` mid-pack; after the file
stabilised the pack succeeded. That successful archive still predated a final
edit to the same concurrent test, so once the test file had been stable for
several minutes the archive was repacked. The hashes above are the final
repack; the earlier successful pack was discarded. This was a concurrency race,
not an archive defect.

## 10. Global installation and registration

The global upgrade used the previous candidate manifest as ownership proof and
ran twice because the archive was repacked once the concurrent test file
stabilised:

```sh
# 1) first layout candidate (discarded archive 1853085b…)
... upgrade --expect-manifest-sha256 f7dea5e62bdfa83b905f1fdb45efac5d92046c9847d7c4f2b2804e6a923c16d0 \
  --backup ~/.config/opencode/backups/bookify-layout-2026-11-13
# 2) final repack (archive 395e5d22…)
... upgrade --expect-manifest-sha256 2899d292e54f7736e90a3a93298083eaae176f3c448d2b0079d9cfb4094f61e6 \
  --backup ~/.config/opencode/backups/bookify-layout2-2026-11-13
```

Final state: 251 files, release `2026-11-13`, installed manifest
`aaff7de78c7a4b4e8e9328abc5dfcf5cd6fb8655609e523de52986cc53aac398`,
backup `~/.config/opencode/backups/bookify-layout2-2026-11-13` (the first
backup remains at `bookify-layout-2026-11-13`). `verify-install` passes.

Command install/verify against `~/.config/opencode/commands` reports all three
names `unchanged`; their bytes are the canonical
`fa7f3a8e…` / `601df692…` / `61f80eab…`. `verify-commands` passes.

Preserved unchanged: `pdf-book-design` (all files, `SKILL.md` `0d2c9cb8…`),
`AGENTS.md`, `cli.json`, `opencode.jsonc`, `service.json`, and all non-Bookify
command files — a before/after hash diff is empty. The v1 and preliminary
backups remain in place.

OpenCode API registration (running OpenCode v2.2.0), queried from an unrelated
working directory:

```text
GET /api/command -> bookify, bookify-source-faithful, bookify-teachable-textbook
GET /api/skill   -> id=bookify, path=$HOME/.config/opencode/skills/bookify/SKILL.md,
                    body "# Bookify (portable skill bundle)" (9,362 bytes)
```

## 11. Source-denied installed proof

The installed payload was exercised with the source checkout masked and a fresh
environment:

```sh
bwrap --unshare-net --bind / / --tmpfs <source-checkout> \
  --ro-bind ~/.config/opencode/skills/bookify ~/.config/opencode/skills/bookify \
  --bind /tmp/opencode /tmp/opencode --dev /dev --proc /proc \
  --chdir /tmp/opencode/source-denied-cwd -- \
  env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp/opencode/source-denied-home \
    TMPDIR=/tmp/opencode LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    ~/.config/opencode/skills/bookify/engine/.venv/bin/bookify ...
```

- `<source-checkout>` is an empty tmpfs inside the sandbox; reading the source
  `README.md` fails with `No such file or directory`.
- Fresh cwd `/tmp/opencode/source-denied-cwd`; cleared environment; the installed
  engine's own `.venv` (Python 3.13.16) is used, not the source venv.
- Engine tree is bind-mounted read-only; `PYTHONDONTWRITEBYTECODE=1` avoids
  bytecode writes. The installed engine payload hash was
  `a90e157964bed5b96e72f95b2f6a257e3cb4c4bb901cb12413a85b64262e67c7`
  before and after, unchanged.
- External workspaces: `/tmp/opencode/bookify-layout-ws2/{source-faithful,teachable}`.

Results:

```text
toolchain doctor --json                 ok true, 18 checks
author contract check (source-faithful) ok true, 6/6 pages, 1 uncertainty
author contract check (teachable)       ok true, 6/6 pages, 1 uncertainty
source-faithful build 1/2               5 pages, d5171f775cc94de0785c8ce4d837202fd76ceebbcddc838124b68db4a4348172
teachable build 1/2                     5 pages, a678b1a4c9d1c8f59a62f6aaf18430727d11780aaa898aca70fd97c069a7608f
verify both books                       gate pass (all checks; review manual)
```

The trial builds were byte-identical to each book's stored evidence hash, so the
evidence is current and reproducible under source denial. This is relocation and
runtime proof, not human visual acceptance.

## 12. What is not claimed

- No human PDF sign-off and no claim that the remaining aesthetic limitations
  above are approved.
- No commit, push, dependency, font, mode, or engine change.
- No change to the global `pdf-book-design` skill, global config, or unrelated
  commands.
- No byte-identical independent-rewrite claim; only same-manuscript/pins
  reproducibility.
- The legacy `docs/specimen-report.md` and `docs/catalogue-report.md` are dated
  historical worklogs; their old hashes are superseded by §2, not rewritten.

## 13. Review fix iteration 1 — R1–R4, rebuilt books and refreshed release (2026-11-13)

This section is append-only after the review; §2, §9 and §11 above are
historical measurements of the pre-review candidate. The independent review
`.opencode/agent-skill-review.md` returned REQUEST CHANGES with Required R1–R4.
Iteration 1 fixes them and refreshes the release; the detailed commands and
dispositions are in `.opencode/agent-skill-fixed.md`.

### R1 — level-1 deck gap

Root cause: the chapter standfirst/lead followed the h1 with only
`after_heading = 4.5 pt`; Typst’s block spacing did not add a deck gap, so the
h1 and standfirst ink formed one continuous band. Fix: a new
`tokens.space.before_standfirst = 6 pt` is added to `after_heading` for a
level-1 standfirst or first-block lead only (`preset-standfirst` in
`typst/blocks.typ`; `typst/templates/book.typ`). h2/h3 standfirsts keep their
prior spacing; body, Japanese and paragraph-gap tokens are untouched.

Measured after rebuild (all four level-1 openers, page 3):

| Book | h1→standfirst | 300 dpi white band |
| --- | ---: | ---: |
| specimen | 32.74 pt | 3.36 pt |
| catalogue | 32.75 pt | 3.36 pt |
| source-faithful | 32.75 pt | 3.60 pt |
| teachable | 32.74 pt | 3.36 pt |

h2/h3 standfirsts remain 13.61/11.18 pt. Body 15.30, Japanese 15.99 and
paragraph gap 20.70 are unchanged. The new rendered gate is
`tests/test_layout_correction.py::test_level1_deck_gap_is_clear_and_levels_2_3_keep_their_hierarchy`
plus the four-opener `test_published_level1_openers_show_the_deck_gap`.

### R2/R3 — shipped documentation

`packaging/payload/SKILL.md` no longer tells an agent to write `work/` inside
the installed engine; it directs the agent to an external user-owned workspace
or a disposable engine copy. The packaged README's catalogue reproduction now
runs in `/tmp/opencode` on a copy, and every archive reference names
`dist/bookify-skill-plan2-layout.tar.gz`. The stale preliminary archive
`dist/bookify-skill-plan2.tar.gz` was removed; v1 `dist/bookify-skill.tar.gz`
remains historical only. Packaging tests assert both properties.

### Rebuilt canonical and trial books

Page counts are unchanged (5/19/5/5); hashes changed only from the deck gap:

| File | Pages | SHA-256 |
| --- | ---: | --- |
| `dist/specimen.pdf` / `dist/specimen-rebuild.pdf` | 5 | `2d687e08f902c945e13bac0d4b7e130a145781ed8266a772a842eb6897297372` |
| `dist/catalogue.pdf` / `dist/catalogue-rebuild.pdf` | 19 | `3f5055c4902e11228843dc322ed910d120c63e9b5c799e3139c27b63c32541ed` |
| `examples/catalogue.pdf` | 19 | `3f5055c4…` |
| source-faithful evidence | 5 | `b72fac8ad40cb133001101d30cdc8c00e1d02efbce60dc912b35f71c1a666299` |
| teachable evidence | 5 | `7ae08d4bd11840922bb191798e5686d4fbf6b7f4814d0d4f50a27e7d0d75323d` |

Both canonical books and both trial books double-build byte-identically and
pass `verify` (review `manual`). Evidence metadata was refreshed; the teachable
`verify.json`/`build-report.json` now use workspace-relative paths (O4).

### Refreshed archive and installed manifest

- Archive: `dist/bookify-skill-plan2-layout.tar.gz` `4beb973a481a689b5f06010aa9505586403b29a1f84b87fb9f433eeb646f4c36`
- Bytes: 58,420,387; members 251 (250 payload + manifest); release `2026-11-13`
- Manifest SHA-256: `c2c354ebb1b7294a15a3cfdc97a896c37f29ac7837fa2094ab610bca518848f0`
- Determinism: two packs byte-identical (`--check-determinism`)
- Installed: successive verified-ownership upgrades from `aaff7de7…`
  (backup `bookify-agent-skill-fix1-2026-11-13`, then `99f409bd…`) to the
  final backup `~/.config/opencode/backups/bookify-agent-skill-fix1b-2026-11-13`;
  `verify-install` 251 files ok; `verify-commands` all three ok.

### Status

Tasks 57–68, 73–76 and Task 69 review and Task 70 iteration 1 are recorded
complete in `tasks/plan.md`/`tasks/todo.md`. Task 71 independent re-test,
Task 72 final closure, Checkpoint Q/R and final human PDF sign-off remain
unchecked. Optional O2 and O4 were fixed; O1/O3/O5 remain recorded and
unforced. No commit, push, dependency, font or mode was added.

## 14. Final verification and close-out (2026-11-13, append-only)

This section closes the technical record after the independent test stage. All
numbers below come from `.opencode/agent-skill-tests.md` (verdict **SHIPPABLE**)
and were reproduced there from rendered artifacts and executed suites, not
inherited from the review/fix stages. §13 above remains the historical
iteration-1 record and is not rewritten.

### Verified technical status

- Chapter openers: 16/16 level-1 openers measure 32.74–32.75 pt h1→next with
  3.36–8.88 pt full-width 300 dpi ink bands; the four page-3 openers are
  3.36–3.60 pt.
- Role pitches: body 15.30 Latin/Vietnamese; Japanese 15.99–16.00 (bounded
  residual); paragraph gap 20.70; lead 16.40; caption 11.20; note 13.60; small
  12.00; quote 15.40; table in-cell 11.60; h1/h2/h3 30.00/16.50/14.00; h2/h3
  standfirst 13.61/11.18.
- Suites: full 741 passed, 3 optional project-local skips; packaging 42;
  layout 19; 8/8 required mutants killed.
- Release: archive
  `dist/bookify-skill-plan2-layout.tar.gz`
  `4beb973a481a689b5f06010aa9505586403b29a1f84b87fb9f433eeb646f4c36`
  (58,420,387 B, 251 members) reproduced byte-for-byte by
  `--check-determinism`; manifest
  `c2c354ebb1b7294a15a3cfdc97a896c37f29ac7837fa2094ab610bca518848f0`
  equals the installed manifest; `verify-install` 251 files and
  `verify-commands` pass.
- Installed independence: with the source checkout denied (`SOURCE_DENIED`),
  `toolchain doctor` passes 18 checks, both contracts pass 6/6, both trial
  books rebuild byte-for-byte (`b72fac8a…` / `7ae08d4b…`) and both `verify`
  gates pass.
- Rebuilt outputs: specimen 5 pp `2d687e08…`; catalogue and
  `examples/catalogue.pdf` 19 pp `3f5055c4…`; source-faithful 5 pp
  `b72fac8a…`; teachable 5 pp `7ae08d4b…`.
- Status: Tasks 71 and 72 complete; Checkpoints Q and R technically complete;
  every append in `tasks/plan.md` and `tasks/todo.md` is additive.

### Explicit limitations and residual nuances

1. Japanese pitch carries a +0.69–0.70 pt residual (recorded bound ≤0.75).
2. `plate.png` is 72×48 px, about 12 ppi on the page-5 plate.
3. The synthetic plate uses the generic `Photograph 1.` label.
4. Teachable page 5 carries deliberate end-matter whitespace from the
   `Key terms` break.
5. Catalogue pages 8 and 14 are sparse single-figure pages (inherited design).
6. Table nuance: in-cell wrapped pitch is 11.60 pt while a single-line row's
   baseline rhythm is 15.68 pt (Typst row inset); documented, not redefined.
7. `verify_manifest.py --strict` on the installed tree fails on the runtime
   `.venv` symlink by design; default verification tolerates runtime paths and
   reports `ok true`.
8. No human PDF sign-off: every page inspection in this phase is agent
   inspection and `verify` review is `manual`.

### What is not claimed

This close-out claims technical completion only. It does not claim that the
user approved any rendered PDF, that human visual sign-off occurred, or that
the residual limitations above are accepted. No product, schema, typst,
content or test file was changed by this reconciliation, and no commit or push
was made.

## Bookify v2 design-default rebuild (2026-11-14, append-only)

The v2 design defaults (D1–D7) were implemented and the public outputs rebuilt.
This section supersedes the hash table above; the earlier records are retained
as history.

| Artefact | Before | After |
| --- | --- | --- |
| `dist/specimen.pdf` | 5 pp `2d687e08…` | **6 pp** `4e6bec0bf3ad41af9e3a197836c3493babb33494f90012d18bbd099792014042` |
| `dist/catalogue.pdf` | 19 pp `3f5055c4…` | **21 pp** `614cf15108a760e3ddf6ceedcd0098c88220949b352e6f7b9657aeae0fc73b37` |
| `examples/catalogue.pdf` | 19 pp `3f5055c4…` | **21 pp** `614cf151…` |
| source-faithful evidence | 5 pp `b72fac8a…` | **5 pp** `2fe8f78dd6950d1390540dd374d45713d34064ff889a4051a88762731c94d748` |
| teachable evidence | 5 pp `7ae08d4b…` | **6 pp** `37f567c23227fb85b3c495b0d0b0878ffe801067cad33a213a10bb18417eb901` |

Each book was built twice (byte-identical) and `verify` passes with the built
report and review notes: specimen and catalogue `gate: pass` with one answered
`readability` warning each (`plates`, `cover`, `definitions`, `xrefs`, `rhythm`
pass; captions and figure geometry pass on the catalogue). Full suite:
**769 passed, 3 skipped**. No commit, push, package rebuild, dependency or OCR
change was made; the OCR workstream's files were not touched. Detail:
`.opencode/bookify-v2-design.md`.

## Bookify v2 integration and candidate release (2026-11-14, append-only)

The v2 design defaults and OCR core intake were integrated, packaged and
installed. Full evidence, commands and limitations: `.opencode/bookify-v2-release.md`.

- Archive: `dist/bookify-skill-v2.tar.gz`, 58,709,351 bytes, 275 members,
  SHA-256 `91456883c6971232b77617942937cf5e7828df1f0e5769259aa68c106c345869`;
  deterministic double pack identical. Packaging suite 46 passed.
- OCR allowlist: OCR product code, harness, lock fragment, README/LICENSE and
  the public fixture are included; `tools/ocr/tesseract*`, `vendor/ocr/tessdata/**`,
  every `*.traineddata` and `fixtures/ocr-capability/build/**` are excluded.
- Global install: verified-ownership upgrade from
  `c2c354ebb1b7294a15a3cfdc97a896c37f29ac7837fa2094ab610bca518848f0` to
  `483daab6a9c9d4ca96f6c1d5eb300b4818fbc89bf20cae85fff7ad7dbb2213f2`;
  backup `~/.config/opencode/backups/bookify-v2-2026-11-14`; `verify-install`
  275 files and `verify-commands` pass.
- Canonical outputs (double-built, byte-identical, all pages inspected):
  specimen 6 pp `4e6bec0b…`; catalogue and `examples/catalogue.pdf` 21 pp
  `614cf151…`; source-faithful 5 pp `2fe8f78d…`; teachable 6 pp `37f567c2…`;
  OCR F1 5 pp `3671d978…` (`content/agent-skill/ocr-example/`).
- Source-denied bwrap proof: repository masked, installed engine read-only,
  doctor 18 checks, both contracts 6/6, all four books double-built and verified,
  OCR F1 re-run with an external development copy. All gates pass.
- Missing-CLI behaviour: exit 2 with `OCR_ENGINE_MISSING` and the Fedora install
  command; no manifest written. Build/verify remain OCR-free.
- Full suite: **793 passed, 3 skipped**. No test deleted, skipped or loosened.
- Limits: no system Tesseract CLI in this container, so the system-package OCR
  path is not re-measured; cross-host OCR determinism unproven; `vie` opt-in
  with tone-mark caveat; no CJK; ruled-table PSM 6; readability warnings
  answered; catalogue workspace build uses the legacy engine-root copy; no
  human sign-off. No commit or push.

## Bookify v2 final repack and reinstall (2026-11-14, append-only)

This section supersedes the archive and installed-manifest values above. It
records the repack after iteration-1 debugger fixes (C1-C5, R1-R10, O11), the
rebuild of every public output, and an independent source-denied rerun. No
human sign-off is claimed; every page inspection and `review: manual` is agent
inspection.

### Packaging and archive

- Archive: `dist/bookify-skill-v2-final.tar.gz`
  - SHA-256 `e168a72a75eba6df5194ad64b23be88599bb6804ef31d8dd9dabdee723fd5c8a`
  - 58,721,675 bytes; 279 members (278 payload files + `MANIFEST.json`)
  - payload 119,878,531 bytes; release `2026-11-14`
  - deterministic double pack: second pack byte-identical
- The older `dist/bookify-skill-v2.tar.gz` is superseded and remains only as
  history; this report and the payload README name the final archive.
- The payload adds `intake/sandbox.py`, `intake/caps.py`,
  `toolchain/audit.py` and the MIT `LICENSE` (four files more than the
  275-member candidate).
- Exclusions still verified on the built archive and installed tree:
  no `*.traineddata`, no `tools/ocr/tesseract*`, no
  `fixtures/ocr-capability/build/**`, no `.venv`, cache, `dist/`, `build/`,
  `.opencode/` or `docs/`. Retained: OCR intake code, `machine_read` and
  `ocr_free_build` checks, harness, lock fragment, OCR README/LICENSE and the
  public fixture.
- Packaging suite: **46 passed**. The OCR tests now also assert the packaged
  `tools/ocr/README.md` repeats the system-package setup command and the
  development-copy exclusion.

### Canonical outputs rebuilt

All builds are offline. Each PDF was built twice; every pair is byte-identical.
PDF hashes are unchanged from the accepted design because the iteration-1 fixes
are evidence, eligibility and check-strength changes; the reports and verify
results were regenerated.

| Artefact | Pages | SHA-256 (before = after) |
| --- | --- | --- |
| `dist/specimen.pdf` / `-rebuild` | 6 | `4e6bec0bf3ad41af9e3a197836c3493babb33494f90012d18bbd099792014042` |
| `dist/catalogue.pdf` / `-rebuild` | 21 | `614cf15108a760e3ddf6ceedcd0098c88220949b352e6f7b9657aeae0fc73b37` |
| `examples/catalogue.pdf` | 21 | `614cf151…` (copy of the catalogue) |
| source-faithful `source-faithful.pdf` / `book-2.pdf` | 5 | `2fe8f78dd6950d1390540dd374d45713d34064ff889a4051a88762731c94d748` |
| teachable `teachable-textbook.pdf` / `book-2.pdf` | 6 | `37f567c23227fb85b3c495b0d0b0878ffe801067cad33a213a10bb18417eb901` |
| OCR F1 `book.pdf` / `book-2.pdf` | 5 | `4d15590d295c55f8f4b231114ff6d27da6415ab9f8596008acce03e38cf3890e` |

Recorded manuscript hashes still match their authoring records:

- source-faithful `book.yaml` `15ea936a…` = record `manuscriptSha256`;
- teachable `book.yaml` `cfdd0846…` = record `manuscriptSha256`;
- F1 `book.yaml` `e88eefc8…` = record `manuscriptSha256`.

Verify gate results (current build report, previous build, contact sheet and
review notes): specimen **pass**, catalogue **pass**, source-faithful **pass**,
teachable **pass**, F1 **pass**. Every page was rendered and inspected; no blank
page, missing glyph, split plate or lost caption was seen.

Warnings answered (not failures):

- specimen: `rhythm:unmeasured:h2`, `rhythm:unmeasured:h3`,
  `readability:wordsPerPage:page=5`;
- catalogue: `rhythm:unmeasured:h2`, `rhythm:unmeasured:h3`,
  `readability:wordsPerPage:median`;
- source-faithful: `rhythm:unmeasured:h3`;
- teachable: `rhythm:unmeasured:h3`, `readability:wordsPerPage:page=5`;
- F1: `MACHINE_READ_DIGITS:t-trial`, `MACHINE_READ_DIGITS:t-receipts`.

The specimen and catalogue now warn on unmeasured h2/h3 rather than passing
silently (R9). Their review notes say the books have no headings at that level
and that the band remains unproven; no filler heading was added.

### OCR F1 eligibility

The tracked F1 manifest still records the page-1 `Owner's capital 31,205.75`
line as `below_threshold` / `eligible: false`. The table no longer contains that
row; an explicit `u-omitted` unresolved block on page 3 records the measured
77.58 (second pass 80.34) and says the table is not a complete balance. The
tracked manifest reproduced byte-for-byte from a fresh development-copy run
(`0d50f18d…`, pin `aeb95412…`). Build report carries the measured OCR-free
boundary (`measured: true`, probe `subprocess.run+io.open`,
`engineInvocations: 0`, `vendorRead: false`).

### Global install

Three verified-ownership upgrades, each with a fresh backup and a full payload
verification before the swap:

1. `483daab6…` → `f23edbcb…` (first v2-final archive);
2. `f23edbcb…` → `f21a5f2f…` (MIT `LICENSE` added to the payload);
3. `f21a5f2f…` → `015759cd…` (`LICENCES.md` corrected to the 21-page
   catalogue).

| Item | Value |
| --- | --- |
| Target | `~/.config/opencode/skills/bookify` |
| Backup (final) | `~/.config/opencode/backups/bookify-v2-final3-2026-11-14` (`f21a5f2f…`); earlier `bookify-v2-final2-2026-11-14` (`f23edbcb…`) and `bookify-v2-final-2026-11-14` (`483daab6…`) |
| New manifest | `015759cd550def89de6e47c06d879ae7b2d527e56237c4f319760d6c0525fe46` |
| `verify-install` | `ok: true`, 279 files, 119,878,531 bytes |
| `verify-commands` | `ok: true`, three commands unchanged and byte-identical |
| Installed doctor | `ok: true`, 18 checks |

`uv sync --python 3.13.16 --frozen` recreated the installed engine `.venv`
after the atomic swap; `verify-install` still passes with that runtime
directory. The installed tree has no dev OCR binary, no `*.traineddata` and no
fixture `build/`; no file under `engine/tools/ocr` is ELF.

With no system `tesseract`, no `BOOKIFY_*` override and a clean `PATH`, intake
exits **2** with `INPUT_INVALID` / `OCR_ENGINE_MISSING` and the Fedora install
command, and writes no manifest. Build and verify do not invoke OCR.

### Timing evidence (20 pages / 20 regions)

Synthetic public-safe A4 pages were generated under `/tmp/opencode/timing`
(a dense 20-row table raster for whole pages; two prose pages with ten
150x90 pt table images each for regions). The pinned development copy was used
explicitly; no system `tesseract` exists here.

| Set | Measured | Projected 200 | Budget |
| --- | --- | --- | --- |
| 20 whole pages | 183.12 s OCR sum, 9.156 s/page; 201.38 s wall | 30.5 min OCR; 33.6 min end-to-end | ≤45 min: within |
| 20 regions (2 pages) | 10.01 s OCR + 5.33 s render = 15.34 s; 20.08 s wall | 2.6 min OCR+render; 3.3 min end-to-end | ≤15 min: within |

The projection is a linear extrapolation from this host, these pages and this
pinned development copy. It is not a captured 200-page/200-region run; a system
Tesseract package was not available to measure.

### Source-denied rerun

`bwrap --dev-bind / / --tmpfs /home/tris/bookify` hid the source repository
(verified empty), the installed skill was bind-mounted read-only, and every
command used `env -i` with external `HOME`/`TMPDIR`, `PATH=/usr/bin:/bin`,
`PYTHONPATH=<installed engine>/src` and the installed `.venv/bin/python`.
Results:

| Check | Result |
| --- | --- |
| `toolchain doctor` | `ok: true`, 18 checks |
| specimen | 2 builds `4e6bec0b…`, 6 pp, `verify` pass |
| catalogue | 2 builds `614cf151…`, 21 pp, `verify` pass (external engine-root copy; legacy workspace limitation) |
| source-faithful contract | `ok: true`; 2 builds `2fe8f78d…`, `verify` pass |
| teachable contract | `ok: true`; 2 builds `37f567c2…`, `verify` pass |
| F1 contract | `ok: true`; 2 builds `4d15590d…`, `verify` pass |
| F1 intake | dev copy mounted at the installed engine's development path; `engineSource: development-copy`, `developmentOnly: true`, pin `aeb95412…`, manifest `f5cda8b2…` |

The source-denied F1 manifest differs from the tracked example in the engine
envelope only (`source: development-copy`, data location `explicit` rather than
`environment`/`vendored`); the pin and OCR measurements are the same. This is a
development-copy run, not a system-package measurement.

### Tests and residual limits

- Full engine suite independently re-run: **814 passed, 3 skipped** (the three
  pre-existing installed-skill absence checks).
- Packaging suite: **46 passed**. `tests/test_ocr_provenance.py`: 22 passed,
  including the added shipped-F1 measured-boundary assertions.
- No test deleted, skipped or loosened.
- No system Tesseract package: the release engine path is still not measured.
  The source-denied F1 run used the development copy, mounted explicitly and
  labelled `developmentOnly: true`.
- Cross-host OCR determinism, CJK, handwriting and rotated tables remain
  unclaimed.
- The catalogue workspace mount still does not include
  `assets/catalogue/artwork`; the source-denied catalogue used an external copy
  of the installed engine in legacy mode. This is a pre-existing engine
  limitation, not a new workaround in product code.
- No commit, no push, no new dependency beyond the documented Tesseract setup.

## Bookify v2 iteration-2 close-out (2026-11-14, append-only)

This supersedes the archive and installed-manifest values above and records the
independent verifier's three evidence-gap fixes plus the payload decision. No
product engine behaviour changed except the D6 measurement/evidence fix; no
dependency, font, content or tolerance was added or relaxed.

### Fixes and their tests

| ID | Change | Test |
| --- | --- | --- |
| M5 | `audit.boundary()` is exercised with a real engine call (public OCR fixture through intake) and with one real engine argv inside a build's measured scope; report must copy the measurement, and `ocr_free_build`/verify must fail on a non-zero count | `test_measured_ocr_boundary_counts_a_real_invocation_and_a_build_report_cannot_hide_one` |
| M4b | CLI default intake records `offline/sandboxed true`, `unsandboxedExplicit false` and a `bwrap --unshare-net` argv; `--allow-unsandboxed` records the explicit state; missing bwrap exits 3 naming the flag | `test_cli_default_intake_is_sandboxed_and_allow_unsandboxed_changes_it`, `test_cli_sandbox_default_fails_closed_without_bwrap` |
| D6 | `rhythm._ink_band` measures the real white gap (previous ink → heading ink), records `headingBands[].bandPt`, and fails an unmeasurable heading; h2/h3 gates unchanged | existing rhythm test now asserts bands; `test_rhythm_fails_when_a_heading_band_is_unmeasurable` |

Measured bands: F1 h2 28.32 / h3 21.60; source-faithful h2 28.56, 28.32,
28.32; teachable h2 28.32–29.52. The three shipped evidence files were
regenerated and now record these values:

| Evidence file | SHA-256 |
| --- | --- |
| `content/agent-skill/ocr-example/evidence/verify.json` | `4f44ea11461a8595fffe73b041944cc7ab38b3a3245f57de43c01160c6c6423a` |
| `content/agent-skill/source-faithful/evidence/verify.json` | `8b7bbb38083a7f5731ac2c291efefb3461b2bd6725c6e050a4ec0c2ed025f171` |
| `content/agent-skill/teachable/evidence/verify.json` | `df60f2a937f60087b86129be1247677e74745514ba0100d534c43124df5b5dea` |

### Payload: the suite is not shipped

The previous payload's documented full-suite recipe from the installed engine
gave **17 failed, 787 passed, 19 skipped**. The failures read source-only inputs
the allowlist excludes: `content/agent-skill` (F1/trial evidence and
skill-acceptance) and the development OCR binary/tessdata (`test_ocr_intake`:
4 failed, 7 errors). The suite therefore does not belong in the payload. The
allowlist now omits `tests`, the now-unused `engine/packaging/payload/` copies
are dropped, packaging tests assert both are absent, and the payload README
points at a source-checkout run.

### Final archive and install

| Item | Value |
| --- | --- |
| Archive | `dist/bookify-skill-v2-final.tar.gz` |
| Archive SHA-256 | `a6a9c814f12493885106f9a31402f09b647e7210d6d41a3e168b70c55661253f` |
| Bytes / members | 58,600,501 / 233 (232 payload + `MANIFEST.json`) |
| Payload bytes / engine files | 119,342,015 / 214 |
| Determinism | double pack byte-identical |
| Installed manifest | `28ad21f1fff062081634ac67b118863fd0f6e8e3fdb7d686ffb692e16bdd0a1f` |
| Previous manifests | `52b5fa919b885cd02df5f09081316dd668eafc171851c82d4675b4d1c67b37bb` (tests) → `015759cd…` (pre-iteration-2) |
| Backups | `~/.config/opencode/backups/bookify-v2-final5-2026-11-14` (`52b5fa91…`); `bookify-v2-final4-2026-11-14` (`015759cd…`) |
| verify-install | `ok: true`, 233 files, 119,342,015 bytes |
| verify-commands | `ok: true`, three commands unchanged |

### Suites and source-denied proof

- Engine: **820 passed, 3 skipped** (684.35 s) — 816 iteration-1 tests plus M5,
  two M4b and D6. Packaging: **46 passed** (179.79 s).
- Source-denied bwrap proof (`--tmpfs /home/tris/bookify`: 0 repository entries,
  `README.md` absent, module inside the installed engine, `env -i`, external
  HOME/TMPDIR, `PATH=/usr/bin:/bin`): specimen 2 builds `4e6bec0b…` and
  source-faithful 2 builds `2fe8f78d…`, both verify **pass**.
- Unchanged canonical PDFs: specimen `4e6bec0b…` 6 pp, catalogue `614cf151…`
  21 pp, source-faithful `2fe8f78d…` 5 pp, teachable `37f567c2…` 6 pp, F1
  `4d15590d…` 5 pp.

Remaining unverified: a real distro `tesseract` package (system-engine OCR) and
a captured 200-page/200-region run. The 200-page figure is a linear projection.
No commit or push; no human sign-off.

## System-engine OCR verified (2026-11-14, append-only)

This closes the last v2 evidence gap and supersedes every "no system Tesseract
package" limit above. Full record: `.opencode/bookify-v2-system-ocr.md`.

### What was measured

`tesseract 5.5.4` (`/usr/bin/tesseract`, 53,336 B, SHA-256
`2e54bf61c56a3ca1ac11758a7d9764f52333b5777a74272b4e083b016cefa74a`) with
`libtesseract.so.5.5.4` (`7cc5ff7e…`), Leptonica 1.87.0 (`27f70f64…`) and
`eng.traineddata` 4.1.0 (`7d4322bd…`, 4,113,088 B) from Fedora 44 packages.
`rpm -V tesseract tesseract-libs tesseract-langpack-eng leptonica` exits 0; the
package signature is Fedora key ID `dbfcf71c6d9f90a6`. `vie` is not installed
system-wide and stays opt-in.

`tools/ocr/ocr.lock.fragment.json` and `toolchain.lock.json` now pin 5.5.4, the
5.5.4 library hash, the system binary hash, the system tessdata prefix and the
`eng` data file, and record the system packages. The development copy
`tools/ocr/tesseract` is a **byte copy** of the installed CLI so the source test
suite keeps a single coherent pin set; it stays git-ignored and excluded from
the bundle.

### F1, old vs new

Re-run in an external workspace with `--ocr-require-system` and no `BOOKIFY_*`
override. Four runs produced the same manifest
(`92e148895d6991df1cb95c221306459f6a0e5e3b6f86c1574ddf6f73a9bb3ba0`), pin
`ff92b6ea…`; `engine.source: "path"`, `developmentOnly: false`,
`library 5.5.4`.

| Page | 5.5.3 dev copy | 5.5.4 system |
| --- | --- | --- |
| 1 (images) | applied, 95.02, agreement 1.0, 11/12 eligible | **identical** |
| 2 (page) | applied, 95.34, agreement 1.0, 9/9 eligible | **identical** |
| 3 (page) | below_threshold, 43.25, agreement 0.6667, 0 eligible | **identical** |
| 4 | not_required (text layer) | **identical** |

The page-1 `Owner's capital 31,205.75` line still measures 77.58 (second pass
80.34) and stays ineligible, so the row stays omitted and `u-omitted` stays.
Nothing was republished. The only measurement difference is one TSV line-box
row on pages 2 and 3 (top 458→462, bottom 481→477 at 300 dpi), with identical
text, word boxes, confidences and `.txt` projections.

`book.yaml` and `authoring/record.json` are unchanged (no evidence required a
change); both F1 builds are `4d15590d295c55f8f4b231114ff6d27da6415ab9f8596008acce03e38cf3890e`
and `verify` passes with the two answered digit warnings. The dev-copy manifest
is kept as `content/agent-skill/ocr-example/historical/development-copy-5.5.3/`.

### Archive, install and proof

| Item | Value |
| --- | --- |
| Archive | `dist/bookify-skill-v2-final.tar.gz`, `687b8a8ae17621b98acc1a300e4dd454c355d5ef84ae5bb0e6d1a7e39101d94f` |
| Bytes / members | 58,613,668 / 233; payload 119,349,376 |
| Determinism | double pack identical |
| Installed manifest | `b7f507c7b1b892dffcf06120f22864f09163c0163e943116a46fcb4b40dc6759` |
| Previous manifest | `28ad21f1fff062081634ac67b118863fd0f6e8e3fdb7d686ffb692e16bdd0a1f`; archive `a6a9c814…` preserved as `dist/bookify-skill-v2-final-pre-system.tar.gz` |
| Backup | `~/.config/opencode/backups/bookify-v2-system-2026-11-14` |
| verify-install / commands | `ok: true`, 233 files, 119,349,376 bytes; 3 commands unchanged |
| Installed doctor | `ok: true`, 18 checks |

Payload diff: 8 files changed, none added or removed (two locks, three docs
including the top-level reference copy, payload `README`/`SKILL`, manifest).
Exclusions hold: no `*.traineddata`, no `tools/ocr/tesseract*`, no fixture
`build/`, no `engine/tests`, no ELF under `engine/tools/ocr`. The shipped docs
now state the system requirement is verified and document
`--ocr-require-system`.

Source-denied proof with the system package available (repository masked to 0
entries, installed engine read-only, `env -i`, `PATH=/usr/bin:/bin`): doctor 18
checks; F1 intake reproduced manifest `92e14889…` byte-for-byte; contract `ok`;
F1 2 builds `4d15590d…` + verify **pass**; specimen 2 builds `4e6bec0b…` +
verify **pass**.

### Suites and limits

Engine **820 passed, 3 skipped** (706.90 s); packaging **46 tests OK**
(95.69 s); no test deleted, skipped or loosened.

Remaining: cross-host OCR determinism unproven; the 200-page/200-region figure
is still a linear projection (the system F1 pages measured 3.47 / 7.86 / 7.66 s,
consistent with the 11.65 s/page budget); `vie` opt-in and not installed; no
CJK; ruled-table PSM 6 needs calibration. **Reported, not fixed:** F1 page 4's
h1 overlaps its first body line — a pre-existing layout defect in the unchanged
`4d15590d…` PDF, outside this evidence pass. No commit, no push, no human
sign-off.

## F1 page-4 heading clearance (fixed, 2026-11-14)

The layout defect reported in the previous release row is fixed. The h1 "A page
that is only an image" was struck through by its first body line because Typst
ends the pinned face's 0.660 em layout line at the baseline and the heading's
`below` gap (4.5 pt) never reserved descender ink: at 25 pt the descenders reach
6.00 pt below the baseline while the next line's ascenders rise 0.91 pt above
their own line, so 6.91 pt were required. Only the lead-less h1 collided (h2/h3
need 3.93/3.38 pt and the h1-with-standfirst path already used 10.5 pt).

Fix, derived from the font rather than a new magic number: `theme.typ` gains
`ink_metrics` (0.660/0.750/0.240 em), `space.heading_clearance` (0.5 pt) and
`heading-below()`, which returns `max(after_heading, 6.00 + 0.954 + 0.5) =
7.454 pt` for h1 and leaves h2/h3 at exactly 4.5 pt. `verify` now measures the
rendered white row below every heading (`headingClearance`, `clearanceSamples`)
and fails a touch or a band under one 300-dpi row. h1→standfirst stays 32.75 pt.

Measured: h1→body baseline delta 26.945 → 29.899 pt; ink clearance −2.409 pt
(merged bands) → +0.545 pt (0.48 pt raster row at 300 dpi, 0.54 pt at 1200 dpi).
Only F1's PDF changed; specimen `4e6bec0b…`, catalogue `614cf151…`, trial
`e33fa816…`, source-faithful `2fe8f78d…` and teachable `37f567c2…` are
byte-identical after a fresh build, and all pass the new below-heading check
(minimum sample 0.24 pt, teachable h2; no collision).

| Artefact | Value |
| --- | --- |
| F1 `book.pdf` + `book-2.pdf` | `18517b0240c3adf55f42c91f84adc254f6c2fab0e2c7808c67bb5119f7893d29` (5 pp, double build identical) |
| F1 `build-report.json` | `3bc6e24eeb7dc47d151627b5926f746d0b20ccaef0ba3151cb8ff75ada2c1529` |
| F1 `verify.json` | `4276b627a95f2add84cecc9e74c90445302186453059ff25b06279958f104b93` |
| F1 `contact-sheet.png` | `7c5946a75e4cc3893c0a7487b30437dbf5c74deed08b0fc964c115fa9e5b0913` |
| Archive | `b095b2dec544f918621b42620f2a83b7d49a44942374f032ba7c095845dcf605` (58,598,748 B, 233 members, payload 119,355,149 B) |
| Installed manifest | `6b3b73314fc4a37f6b1c67b65107feeac93b7daaa8a6e64de1e23464cccd285b` (previous `b7f507c7…`) |
| Rollback | `dist/bookify-skill-v2-final-pre-clearance.tar.gz` `687b8a8a…`; backup `bookify-v2-clearance-2026-11-14` (interim `bookify-v2-clearance2-2026-11-14`) |
| verify-install / commands | `ok: true`, 233 files, 3 commands unchanged |
| Suites | engine **822 passed, 3 skipped** (782.97 s); packaging **46 passed** (179.45 s) |

The installed engine (no source checkout) rebuilt F1 twice as `18517b02…` and
verified `gate: pass` with the new clearance samples. Two rendered tests cover
the case and fail on the old 4.5 pt gap (mutation replayed). Visual design is
otherwise frozen pending the user's handover: no font, size, colour, cover,
numbering or established gap moved; the level-1 below gap is the only changed
value. No commit, push, human sign-off or private content.
