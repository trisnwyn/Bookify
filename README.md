# Bookify

A local authoring and offline publishing pipeline for long-form books: extract supplied PDFs, author a validated manuscript with uncertainty and rights recorded, compile it with Typst, and verify the result with evidence.

Content generation (agent-assisted, separate) never runs inside publishing. A build is a pure function of manuscript + assets + pinned local tools.

## Licence and status

Original Bookify code, its tests, test fixtures and documentation are released
under the **MIT License**; see [`LICENSE`](LICENSE). Third-party components keep
their own licences and notices. Manuscripts and original artwork remain the
owner's unless a file states otherwise. See `LICENCES.md` for the full
rights record and attribution.

## Requirements

- Linux with `uv` (verified 0.12.24), Python managed by uv (3.13 environment), and the local tools already vendored here: Typst CLI under `tools/typst/`, CeTZ under `vendor/typst/`.
- Poppler utilities (`pdftotext`, `pdfimages`, `pdffonts`, `pdftoppm`, `pdfinfo`, `pdftohtml`) and `bwrap` for verification and the offline build namespace.
- OCR is intake-only: the system `tesseract` CLI plus `tesseract-langpack-eng` (add `tesseract-langpack-vie` only when Vietnamese OCR is enabled). Build and verify never need it. Fedora: `sudo dnf install tesseract tesseract-langpack-eng`.
- Ghostscript and ImageMagick are only needed for the test suite's contact sheets and PDF comparisons.

Pinned versions live in `toolchain.lock.json` (Typst 0.15.1, CeTZ 0.5.3, Matplotlib 3.11.2, Python 3.13.16 at the time of writing). Run `uv run bookify toolchain doctor` to check a machine.

## Setup

```bash
uv sync --locked
uv run bookify toolchain doctor --json
```

## Build and verify the specimen

```bash
uv run bookify build --manuscript content/specimen.yaml --out dist/specimen.pdf \
  --offline --build-dir build/specimen
uv run bookify build --manuscript content/specimen.yaml --out dist/specimen-rebuild.pdf \
  --offline --build-dir build/rebuild

pdftoppm -png -r 110 dist/specimen.pdf build/pages/page
magick montage build/pages/page-*.png -tile 3x build/specimen-contact.png

uv run bookify verify --pdf dist/specimen.pdf --manuscript content/specimen.yaml \
  --previous-pdf dist/specimen-rebuild.pdf --build-report build/specimen/build-report.json \
  --contact-sheet build/specimen-contact.png --reviewed-by "<you>" --reviewed-at "<ISO time>" \
  --report build/verify.json
```

A passing gate prints `gate: pass`. The specimen report is `docs/specimen-report.md`.

## Author from a source

```bash
uv run bookify intake --source "<deck>.pdf" --out build/intake --changed-only --json
# Intake is sandboxed (bwrap --unshare-net) by default; --allow-unsandboxed is the
# explicit escape hatch for a trusted local source. OCR is the default for a
# source that needs it; --no-ocr records a pre-OCR baseline.
# Whitelisted/pinned languages: eng (default) or eng+vie (opt-in).
uv run bookify author plan --intake build/intake --manuscript content/<book>.yaml \
  --out build/author-plan.json --cache-dir build/cache/authoring --json
# read build/intake/pages/page-NNN.txt, write a draft (see skill/bookify/SKILL.md)
uv run bookify author apply --plan build/author-plan.json --draft <draft>.json \
  --manuscript content/<book>.yaml --cache-dir build/cache/authoring \
  --decisions build/authoring/decisions.jsonl --json
```

The authoring guide is `skill/bookify/SKILL.md`; `docs/build.md` records the authoring and build behaviour.

## OCR intake

OCR is intake-only. It reads image-borne text from a supplied source and is
never used by publishing: `bookify build` and `bookify verify` are offline,
model-free and OCR-free, and a machine with no OCR engine can still build and
verify a manuscript.

The release engine is the system Tesseract package, like Poppler:

```sh
# Fedora; add tesseract-langpack-vie only when Vietnamese OCR is enabled
sudo dnf install tesseract tesseract-langpack-eng
```

- `eng` is the default; `vie` is opt-in with a measured tone-mark caveat. No CJK
  OCR. Adequate text is `inferred`, never `verified`; digits need a recorded
  cross-check.
- The extracted development CLI (`tools/ocr/tesseract`) and vendored
  `vendor/ocr/tessdata/**` are development-only and are excluded from the
  public bundle.
- The measured planning budget is 11.65 s per dual-pass page: about 39 minutes
  for 200 whole pages, about 13 minutes for 200 regions. The old 30-minute
  estimate counted OCR but not rendering; acceptance is now the measured
  budget (200 whole pages ≤ 45 minutes). The second pass is never dropped.

## Commands

| Command | Purpose |
| --- | --- |
| `uv run bookify toolchain doctor` | verify pins, fonts, packages and interpreter |
| `uv run bookify intake --source TARGET --out DIR` | stable extraction: text pages, images, hashes, OCR records |
| `uv run bookify author plan` | pages that need work since the last apply |
| `uv run bookify author apply` | merge an agent draft, validate, bump revision |
| `uv run bookify author select` / `status` | illustration provenance and rights |
| `uv run bookify manuscript check` | schema and semantic contract |
| `uv run bookify design check` | tokens, presets, glyph coverage |
| `uv run bookify figures render` | charts and diagrams outside a book build |
| `uv run bookify build --offline` | compile the PDF and write a build report |
| `uv run bookify verify` | acceptance gate over the built PDF |
| `uv run pytest -q` | full test suite |

## Package the skill bundle

```bash
python packaging/bookify_skill_bundle.py pack --out dist/bookify-skill-v2-final.tar.gz \
  --check-determinism
```

The helper is standard-library only. It uses the reviewed example at
`examples/catalogue.pdf`, so a fresh clone can build and verify a bundle without
any excluded file. Installation and verification commands are in
`packaging/payload/README.md`.

## Layout

```
content/        manuscript YAML (specimen, catalogue)
schemas/        closed JSON Schema, examples, negative fixtures
src/bookify/    toolchain, manuscript, design, figures, publish, intake, authoring, verify
typst/          theme, block presets, book template, CeTZ diagram
assets/          fonts, illustration records and images
fixtures/       adversarial, negative and synthetic-trial test inputs
examples/       reviewed catalogue PDF used by the packaging helper
probe/          stack probe scripts from Checkpoint A
skill/bookify/  this project's local skill (does not replace pdf-book-design)
build/, dist/   generated output (ignored)
```

## Limits (v1)

- One chart kind (`grouped_bar`) and two diagram presets; no other output formats.
- OCR is Latin-first: `eng` by default, `vie` opt-in (tone-mark errors measured below the adequate band), no CJK. Adequate OCR is inferred, never verified; digits need a recorded cross-check. Image-only pages stay unresolved when OCR is below threshold.
- Publishing requires `--offline` and a build directory inside the repository; the build uses `bwrap --unshare-net`.
- `bwrap` is a verification dependency, not a pinned runtime package.
- Typst still adds spacing after `。`; pagination is not hand-tuned.
- The private lecture-deck trial used during development is not published. The public test suite uses the source-independent, clearly synthetic `fixtures/synthetic-trial.yaml`, documented in `docs/synthetic-trial.md`.

## Licence note

Original code, tests, test fixtures and documentation are MIT-licensed; see
`LICENSE`. The specimen and catalogue manuscripts and original artwork are not
MIT-licensed and remain the owner's; see `LICENCES.md`. Spectral, Noto Serif CJK
and STIX Two Math are redistributed under the SIL Open Font License 1.1; see
`assets/fonts/fonts.yaml` and `packaging/payload/licences/`. The specimen
photograph is a public-domain US State Department work, credited in
`assets/illustrations/photo-1/record.yaml`; the catalogue's historical
photograph is credited in `assets/illustrations/hist-1/record.yaml`.
