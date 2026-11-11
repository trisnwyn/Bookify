# Bookify portable skill bundle

This archive packages the accepted Bookify v0.1.0 authoring and offline
publishing implementation as an OpenCode skill. It is a packaging release, not
a new renderer or a new capability.

```text
bookify/
├── SKILL.md                 discoverable OpenCode skill (ID: bookify)
├── README.md                this file
├── LICENCES.md              third-party licences and attribution
├── MANIFEST.json            SHA-256, size and mode of every payload file
├── verify_manifest.py       bundle-local stdlib payload verifier
├── references/
│   └── checklist.md         authoring checklist
├── licences/
│   ├── OFL-1.1.txt          SIL Open Font License 1.1 text
│   ├── fonts-metadata.md    copyright/licence data read from the font files
│   └── python-dependencies.md
├── examples/
│   └── catalogue.pdf        reviewed 19-page catalogue (reference output)
└── engine/                  relocatable Bookify engine
    ├── pyproject.toml
    ├── uv.lock
    ├── toolchain.lock.json
    ├── src/bookify/
    ├── schemas/
    ├── typst/
    ├── vendor/typst/        CeTZ 0.5.3 and Oxifmt 1.0.0, with licences
    ├── assets/              fonts, illustrations, catalogue artwork
    ├── content/             catalogue and specimen manuscripts
    ├── fixtures/            adversarial, negative and synthetic-trial test inputs
    ├── tests/               full existing test suite
    ├── tools/typst/         pinned Typst 0.15.1 binary, LICENSE, NOTICE
    └── skill/bookify/       preserved original project-local skill
```

## Prerequisites

Observed and tested on Linux x86_64:

- `uv` 0.12.24 (or a compatible version) and network or a populated uv cache for
  the first `uv sync`.
- Python 3.13.16, the pin in `engine/toolchain.lock.json`; `uv` can provide it.
- `bwrap` with user namespaces (required by the offline build).
- Poppler: `pdftotext`, `pdfinfo`, `pdftoppm`, `pdffonts`.
- ImageMagick: `magick montage` (or `montage`) for contact sheets.

The bundle vendors Typst, CeTZ, Oxifmt and every font. It does not use system
fonts. Python dependencies are resolved from `uv.lock` at setup; they are not
embedded. Setup may use the network; build and verify do not.

Windows and macOS are not supported or claimed.

## Install

The release helper (`packaging/bookify_skill_bundle.py`) lives in the Bookify
source project and is not part of this payload. It is the supported installer
for a fresh archive: it refuses an existing target, validates every archive path
and manifest hash, extracts into an atomic staging directory, and only then
renames it into place. It requires Python 3.12 or newer.

If you only have the archive, extract it manually **only when the target does
not already exist**. Manual extraction does not provide the helper's no-clobber,
path-validation or atomicity guarantees, so inspect `MANIFEST.json` afterwards:

```sh
test ! -e "$HOME/.config/opencode/skills/bookify"
test ! -L "$HOME/.config/opencode/skills/bookify"
mkdir -p /tmp/opencode/bookify-extract
tar -xzf bookify-skill.tar.gz -C /tmp/opencode/bookify-extract
# inspect first; then move the single bookify/ directory into place
mv /tmp/opencode/bookify-extract/bookify "$HOME/.config/opencode/skills/bookify"
```

## Setup

```sh
export BOOKIFY_SKILL="${BOOKIFY_SKILL:-$HOME/.config/opencode/skills/bookify}"
cd "$BOOKIFY_SKILL/engine"
uv sync --python 3.13.16 --frozen
uv run bookify toolchain doctor --json
```

`uv sync` may use the network or the uv cache. Build and verify are offline and
model-free.

If the bundle is extracted somewhere other than the global skill path, set
`BOOKIFY_SKILL` to the directory containing `SKILL.md`. Always change to the
bundled `engine/` before running engine commands; the engine locates its
project root from its own `pyproject.toml`.

## Use

Read `SKILL.md` for the full workflow. A short catalogue reproduction:

```sh
cd "$BOOKIFY_SKILL/engine"
uv run bookify manuscript check --manuscript content/catalogue.yaml --json
uv run bookify design check --manuscript content/catalogue.yaml --json
uv run bookify build --manuscript content/catalogue.yaml --out dist/catalogue.pdf \
  --offline --build-dir work/catalogue --json
uv run bookify build --manuscript content/catalogue.yaml \
  --out dist/catalogue-rebuild.pdf --offline --build-dir work/catalogue-rebuild
mkdir -p work/pages
pdftoppm -png -r 110 dist/catalogue.pdf work/pages/page
magick montage work/pages/page-*.png -tile 4x work/catalogue-contact.png
uv run bookify verify --pdf dist/catalogue.pdf --manuscript content/catalogue.yaml \
  --previous-pdf dist/catalogue-rebuild.pdf \
  --build-report work/catalogue/build-report.json \
  --contact-sheet work/catalogue-contact.png \
  --reviewed-by "<name>" --reviewed-at "<ISO time>" \
  --report work/verify.json
```

Expected: 19 pages, identical double build, SHA-256
`b285d49f9263f85f45fbcbc20f6c61882b1ebbf125e0d6959d86a34c5e67c930`,
and `gate: pass`.

Full tests:

```sh
cd "$BOOKIFY_SKILL/engine"
uv run python -m pytest -q
```

## Verify the installation

The manifest covers `SKILL.md`, `README.md`, `LICENCES.md`,
`verify_manifest.py`, `references/checklist.md`, `licences/OFL-1.1.txt`,
`licences/fonts-metadata.md`, `licences/python-dependencies.md`,
`examples/catalogue.pdf`, `engine/pyproject.toml`, `engine/uv.lock`,
`engine/toolchain.lock.json`, and every file under `engine/`.

The payload includes `verify_manifest.py`, a standard-library checker that runs
from the installed bundle without the release helper. It re-checks every
manifest hash, size, mode and the file set without running the engine, and it
tolerates runtime-only paths created by setup (`.venv`, `work`, `dist`,
`build`, caches):

```sh
export BOOKIFY_SKILL="${BOOKIFY_SKILL:-$HOME/.config/opencode/skills/bookify}"
python "$BOOKIFY_SKILL/verify_manifest.py" --target "$BOOKIFY_SKILL"
```

Run it with `--strict` to require a pristine payload with no runtime paths. The
check is integrity-relative to `MANIFEST.json`: it detects a changed, missing or
extra file, but it does not authenticate the manifest itself. Compare the
reported `manifestSha256` with the release record for an external anchor.

If you are working in the Bookify source project and have the release helper,
`python packaging/bookify_skill_bundle.py verify-install --target <dir>` performs
the same check. The helper is not part of this payload.

## Rollback

```sh
rm -rf "$HOME/.config/opencode/skills/bookify"
```

Only that directory. `pdf-book-design` and every other global skill/config stay
untouched. The archive is the restore source.

## Limits

Portable here means relocatable on the documented compatible Linux x86_64 stack
with the listed system tools and a working `uv` setup. It does not mean
zero-prerequisite, fully offline installation, or support for untested
platforms. See `SKILL.md` and `LICENCES.md` for the complete limits and rights
record.
