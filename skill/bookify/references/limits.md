# Verified limits

State these limits plainly in the book's evidence and in your own report. A
limitation that is named is not a defect; a capability that is claimed without
evidence is.

## Source formats

- Verified intake input: PDF, read with Poppler tools (`pdfinfo`, `pdftotext`,
  `pdfimages`). A non-PDF, encrypted or unreadable file fails with
  `SOURCE_UNREADABLE`.
- OCR is intake-only and optional in setup: the release engine is the system
  `tesseract` package plus `tesseract-langpack-eng` (and `-vie` only if enabled).
  The development `tools/ocr` copy is development-only and requires
  `BOOKIFY_OCR_ALLOW_DEV=1`; `--ocr-require-system` refuses it. Build and verify
  never need OCR.
- Verified release engine: Tesseract 5.5.4, libtesseract 5.5.4, Leptonica
  1.87.0, `eng` data 4.1.0 (Fedora 44 packages, `rpm -V` clean). The public F1
  example records `engine.version: "5.5.4"` and `developmentOnly: false`. A
  different package build, CPU or Poppler is a new pin; cross-host determinism
  is not claimed.
- Default OCR language is `eng`; `vie` is opt-in because tone marks measured
  below the adequate band. No CJK OCR. An image-only CJK page cannot be
  classified before OCR; it is a recorded limitation, not guessed.
- Adequate OCR is `inferred`, never `verified`; digits need a recorded
  cross-check; reconstructed tables carry the visible reconstruction note. No
  OCR value becomes a chart value.
- Same-host, same-pin OCR is deterministic. Cross-host determinism, handwriting,
  rotated tables and low-resolution scans are not claimed.
- Other formats (DOCX, HTML, EPUB, spreadsheets, slide source files) are not
  verified intake formats. Do not promise a conversion you cannot inspect; ask
  before adding a format or dependency.
- Multi-source intake is not part of the verified contract. A book with several
  independent sources is a scope decision to raise, not something to improvise.

## Platform and toolchain

- Observed and tested platform: Linux x86_64. The pinned Typst binary is
  `x86_64-unknown-linux-musl`.
- Windows and macOS are not supported or claimed. Do not ship an instruction that
  assumes they work.
- Python 3.13.16 is the pinned interpreter; `uv` (tested 0.12.24) manages the
  environment. `uv sync` is setup and may use the network or a populated cache.
- Fonts are vendored; no system fonts are used. A missing glyph is a build error,
  not a silent fallback.
- `bwrap` with user namespaces is required to prove the offline build. Without
  it, `bookify build` refuses rather than pretending to be offline.
- Build and verify are offline, model-free and OCR-free. A repeat build does not
  consult a model, download a package, read `vendor/ocr` or execute `tesseract`.
  Authoring may use agent tools; the publishing step does not.

## Rendering and layout

- Chart labels are Latin/Vietnamese only because Matplotlib renders through
  Spectral. Japanese belongs in diagrams, body text and captions.
- Typst adds spacing after `。`; pagination is not hand-tuned around it.
- Leading is derived from the measured Latin natural height (0.660 em). Noto
  Serif CJK JP measures 0.729 em, so a Japanese body line is about 0.69 pt looser
  than a Latin line at the same role. Both are asserted; no per-script leading
  override is implemented at this leading because it would overlap CJK ink.
- A credit line is single-line in the current design and has no separate leading
  token.
- Duplicate section titles are rejected, because contents/xrefs identify a
  section by its printed title. Give same-named minor sections distinct titles or
  merge them.
- Side compositions are fixed grid columns (46 % image + 16 pt gutter). There is
  no text wrap around an image and no runtime layout choice.
- One illustration per final page. The build defers a unit that does not fit and
  reports it; it does not silently drop or split it.
- Tagged-PDF reading order is not claimed. Visual column order and manuscript
  order are the contract; screen-reader structural guarantees are out of scope.
- Approximate values, inferred labels and reconstructions stay visible in the
  rendered text. If an approximation is not printed, it is not communicated.

## Repeatability and byte identity

- Reproducibility means: the same approved manuscript, assets, templates, fonts
  and pinned toolchain rebuild the same layout and, where the current engine
  proves it, the same PDF bytes. Cache deletion changes neither.
- Two offline builds of the same manuscript are compared on page facts and bytes
  under the recorded pins. A difference is a finding, not a tolerance to edit
  away.
- Independent agent rewrites from the same source are **not** claimed to be
  byte-identical. Agent authoring is non-deterministic; only the approved stored
  manuscript is the repeatable input. Never advertise deterministic AI output.
- A successful build does not prove editorial quality. Page inspection, voice
  review and provenance checks remain separate work.

## Rights and publication

- Rights are per illustration: path, origin, creator, licence, credit, caption,
  alternative text, kind and status. Unknown rights stay `unconfirmed`; a normal
  build refuses them.
- A draft build may include unconfirmed rights only explicitly, and the output
  must not be presented as cleared for publication.
- Presence in a source deck or a search result is not a licence. Generated art is
  for conceptual or fictional subjects and must not stand in as documentary
  evidence.
- Quoted text, tables and figures carry attribution. Provenance is not the same
  as permission to republish.
- Outside enrichment requires explicit per-book permission with a citation and a
  stable locator or local hash. Permission to use one source does not authorise
  others.
- The agent's inspection is not human sign-off. Do not claim that a human
  reviewed the PDF unless one actually did.

## Packaging and installation limits

- The portable bundle is Linux x86_64. Installation is no-clobber: it refuses an
  existing skill directory or an unexpected command target and does not overwrite
  another skill or command.
- The bundle does not replace or modify the separate global `pdf-book-design`
  skill.
- The installer and its rollback are part of the packaging track. Where a command
  copy is not yet installed, load the skill directly and state the mode
  explicitly; do not invent an installed command.
