# Bookify portable skill bundle

This archive packages the accepted Bookify v0.1.0 authoring and offline
publishing implementation as an OpenCode skill, with the three slash command
assets and the authoring guides. It is a packaging release, not a new renderer
or a new capability.

```text
bookify/
├── SKILL.md                 discoverable OpenCode skill (ID: bookify)
├── README.md                this file
├── LICENSE                  MIT licence for Bookify original code
├── LICENCES.md              third-party licences and attribution
├── MANIFEST.json            SHA-256, size and mode of every payload file
├── verify_manifest.py       bundle-local stdlib payload verifier
├── commands/
│   ├── bookify.md                       default alias -> source-faithful
│   ├── bookify-source-faithful.md       explicit strict entry
│   └── bookify-teachable-textbook.md    explicit teachable entry
├── references/
│   ├── checklist.md         self-critique pass
│   ├── modes-and-playbooks.md
│   ├── source-and-provenance.md
│   ├── editorial.md
│   ├── visual-design.md
│   └── limits.md
├── licences/
│   ├── OFL-1.1.txt          SIL Open Font License 1.1 text
│   ├── fonts-metadata.md    copyright/licence data read from the font files
│   └── python-dependencies.md
├── examples/
│   └── catalogue.pdf        reviewed 21-page catalogue (reference output)
└── engine/                  relocatable Bookify engine
    ├── pyproject.toml
    ├── uv.lock
    ├── toolchain.lock.json
    ├── src/bookify/         includes intake/ocr.py and machine-read checks
    ├── schemas/
    ├── typst/
    ├── vendor/typst/        CeTZ 0.5.3 and Oxifmt 1.0.0, with licences
    ├── assets/              fonts, illustrations, catalogue artwork
    ├── content/             public catalogue and specimen manuscripts
    ├── fixtures/            adversarial, negative, synthetic-trial,
    │                        agent-skill and OCR capability test inputs
    ├── tools/typst/         pinned Typst 0.15.1 binary, LICENSE, NOTICE
    ├── tools/ocr/           OCR harness, lock fragment, README, LICENSE
    │                        (development CLI and tessdata are NOT shipped)
    └── skill/bookify/       preserved original project-local skill
```

The private trial manuscript is not part of this payload. The payload declares
the three commands and the six guides in `MANIFEST.json`; pack-time checks
compare every packaged command and guide with the tracked canonical source.

The OCR product code is included: `engine/src/bookify/intake/ocr.py`, the
`machine_read` and `ocr_free_build` checks, and `engine/tools/ocr/` with its
harness, lock fragment, README and licence. Development-only OCR artefacts —
`tools/ocr/tesseract*`, `vendor/ocr/tessdata/**`, any `*.traineddata`, and
`fixtures/ocr-capability/build/**` — are **excluded and must never be
published**. The release engine is the system Tesseract package.

## Prerequisites

Observed and tested on Linux x86_64:

- `uv` 0.12.24 (or a compatible version) and network or a populated uv cache for
  the first `uv sync`.
- Python 3.13.16, the pin in `engine/toolchain.lock.json`; `uv` can provide it.
- `bwrap` with user namespaces (required by the offline build).
- Poppler: `pdftotext`, `pdfinfo`, `pdftoppm`, `pdffonts`.
- ImageMagick: `magick montage` (or `montage`) for contact sheets.
- OCR intake only: system `tesseract` plus `tesseract-langpack-eng`. Add
  `tesseract-langpack-vie` only when Vietnamese OCR is enabled. Fedora:
  `sudo dnf install tesseract tesseract-langpack-eng`. `bookify build` and
  `bookify verify` never need OCR, so a publishing-only machine may omit it.
  Publishing is offline, model-free and OCR-free.

The bundle vendors Typst, CeTZ, Oxifmt and every font. It does not use system
fonts. Python dependencies are resolved from `uv.lock` at setup; they are not
embedded. Setup may use the network; build and verify do not.

Windows and macOS are not supported or claimed.

## Install

The release helper (`packaging/bookify_skill_bundle.py`) lives in the Bookify
source project and is not part of this payload. It requires Python 3.12 or
newer.

A **fresh skill install** is no-clobber: the helper validates every archive path
and manifest hash, extracts into an atomic staging directory, and only then
renames it into place. It refuses an existing target, a symlink, a broken link
and an unexpected file.

```sh
python packaging/bookify_skill_bundle.py install \
  --archive dist/bookify-skill-v2-final.tar.gz \
  --target "$HOME/.config/opencode/skills/bookify"
```

An **upgrade** is allowed only for a verified Bookify installation. Supply the
SHA-256 of the installed `MANIFEST.json` as the ownership proof; the helper also
re-verifies every installed file, so a user-edited payload is refused. The old
payload is moved to a new backup path, the new payload is renamed into place, and
any failure restores the backup. There is no `--force`. Keep the backup on the
same filesystem as the skill directory; the swap is an atomic rename, and a
cross-filesystem backup path is refused before anything moves.

```sh
sha256sum "$HOME/.config/opencode/skills/bookify/MANIFEST.json"
python packaging/bookify_skill_bundle.py upgrade \
  --archive dist/bookify-skill-v2-final.tar.gz \
  --target "$HOME/.config/opencode/skills/bookify" \
  --expect-manifest-sha256 <installed-manifest-sha256> \
  --backup "$HOME/.config/opencode/backups/bookify-previous"
```

If you only have the archive, extract it manually **only when the target does
not already exist**. Manual extraction does not provide the helper's no-clobber,
path-validation or atomicity guarantees, so inspect `MANIFEST.json` afterwards:

```sh
test ! -e "$HOME/.config/opencode/skills/bookify"
test ! -L "$HOME/.config/opencode/skills/bookify"
mkdir -p /tmp/opencode/bookify-extract
tar -xzf bookify-skill-v2-final.tar.gz -C /tmp/opencode/bookify-extract
# inspect first; then move the single bookify/ directory into place
mv /tmp/opencode/bookify-extract/bookify "$HOME/.config/opencode/skills/bookify"
```

### Install the slash commands

The skill is usable by naming the mode directly, but the three entries are the
primary interface. The global install is the default; a project install is
optional and writes only inside that project.

```sh
# Global default
python packaging/bookify_skill_bundle.py install-commands \
  --archive dist/bookify-skill-v2-final.tar.gz \
  --target "$HOME/.config/opencode/commands"

# Optional project-local install (parent directory must exist)
python packaging/bookify_skill_bundle.py install-commands \
  --archive dist/bookify-skill-v2-final.tar.gz \
  --target "<project>/.opencode/commands" --create
```

`install-commands` preflights all three files before writing. It refuses an
existing non-Bookify command, a user-edited command, a symlink and a
non-regular file; two commands that are already identical are reported as
`unchanged`. There is no `--force` and no partial replace. A project-local
command with the same name replaces a global command while that project is
active; that is OpenCode behaviour, not something this installer can override.

```sh
python packaging/bookify_skill_bundle.py verify-commands \
  --archive dist/bookify-skill-v2-final.tar.gz \
  --target "$HOME/.config/opencode/commands"
```

The installed command filenames register the slash names. The command bodies are
prompt templates that load this skill; they contain a single standalone
`$ARGUMENTS` line, preserve composer attachments and requested preferences, and
contain no `!` shell block, no `@path` dependence and no hardcoded
`agent`/`model`.

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
project root from its own `pyproject.toml`. Do not point the installed engine at
the source checkout, and do not reuse a virtual environment from another copy:
each installation sets up its own `engine/.venv`.

## Use

Read `SKILL.md` for the full workflow. The catalogue reproduction is a legacy
engine-root regression fixture. Run it in a disposable copy under `/tmp/opencode`
so the installed engine stays read-only:

```sh
export BOOKIFY_SKILL="${BOOKIFY_SKILL:-$HOME/.config/opencode/skills/bookify}"
WS="${BOOKIFY_WORKSPACE:-/tmp/opencode/bookify-catalogue}"
rm -rf "$WS" && mkdir -p "$WS"
cp -a "$BOOKIFY_SKILL/engine/." "$WS/engine/"
rm -rf "$WS/engine/.venv"
cd "$WS/engine"
uv sync --python 3.13.16 --frozen
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

Every write above lands in `$WS/engine`, never in `$BOOKIFY_SKILL/engine`.
Expected: 21 pages, identical double build, SHA-256
`614cf15108a760e3ddf6ceedcd0098c88220949b352e6f7b9657aeae0fc73b37`,
and `gate: pass`.

For an agent-authored book, prefer one external workspace per book and write
`book.yaml`, `assets/`, `intake/`, `authoring/record.json`, `build/` and `dist/`
there. The engine remains read-only:

```sh
uv run bookify build --workspace <workspace> --manuscript <workspace>/book.yaml \
  --out <workspace>/dist/book.pdf --offline --build-dir <workspace>/build/book --json
uv run bookify author contract check --workspace <workspace> --json
```

This catalogue reproduction is a legacy regression fixture, not the default
book shape. It is not evidence for either new mode's content quality.

## OCR intake

OCR is **intake-only**. It reads image-borne text from a supplied source; it
never runs during `bookify build` or `bookify verify`. The release engine is
the **system Tesseract package**, like Poppler. The development copy
at `tools/ocr/tesseract` and vendored `vendor/ocr/tessdata/**` are **not in this
bundle and are never shipped**.

Verified release engine (measured through `bookify intake --ocr-require-system`
on the public F1 example): Tesseract **5.5.4**, libtesseract **5.5.4**,
Leptonica **1.87.0**, `eng` traineddata **4.1.0**, from Fedora 44 packages with
`rpm -V` clean. The intake manifest records `engine.version: "5.5.4"`,
`engine.source: "path"`, `developmentOnly: false` and the measured binary and
library hashes; a different package build is a new pin.

```sh
# Fedora, release engine
sudo dnf install tesseract tesseract-langpack-eng
# only when Vietnamese OCR is enabled
sudo dnf install tesseract-langpack-vie

# intake (OCR is on by default; --no-ocr records a pre-OCR baseline)
cd "$BOOKIFY_SKILL/engine"
uv run bookify intake --source "<source.pdf>" --out "<workspace>/intake" \
  --ocr-require-system --json   # refuses the development copy; sandboxed by default
```

`--ocr-require-system` makes a release run assert the system package: if only
the development copy is available, intake fails with `OCR_ENGINE_MISSING`
instead of measuring with it.

- Default language is `eng`. `vie` is **opt-in** (`--ocr-lang eng+vie`) because
  tone-mark errors measured below the adequate band; never present Vietnamese
  OCR as verified.
- No CJK OCR. An image-only CJK page cannot be classified before OCR; record it
  as a limitation instead of guessing.
- Adequate OCR text is `inferred`, never `verified`; digits need a recorded
  cross-check; a reconstructed table is marked `ocr-table-v1` and carries the
  note `Reconstructed from an image by OCR`.
- Cross-scale agreement is corroboration, not correctness; ruled tables at PSM 6
  can agree on the same misread.
- If the system CLI is missing, intake stops before writing a manifest with
  `OCR_ENGINE_MISSING` and the install command. Build and verify continue to
  work on a machine without OCR.
- **Revised budget:** 11.65 s per dual-pass page measured, so 200 whole pages is
  about 39 minutes (200 regions about 13 minutes); acceptance is the measured
  budget (200 whole pages ≤ 45 minutes). The second pass is part of
  the contract, not optional for speed.

The bundled `engine/tools/ocr/ocr_harness.py` is a capability probe, not part of
the product. It resolves the system CLI first; the development copy exists only
in a source checkout and requires `BOOKIFY_OCR_ALLOW_DEV=1`.

The engine suite is not shipped. It reads source-checkout-only workspaces under
`content/agent-skill/` and the development Tesseract copy, both deliberately
outside this payload, so a shipped copy could not pass. Run the suite from the
source checkout:

```sh
cd /path/to/bookify
uv run python -m pytest -q
```

The release packaging tests (`packaging/test_bookify_skill_bundle.py`) also run
from that checkout. This archive's own release checks are recorded with the
release, not inside the payload.

## Verify the installation

The manifest covers `SKILL.md`, `README.md`, `LICENCES.md`,
`verify_manifest.py`, every file under `commands/` and `references/`,
`licences/OFL-1.1.txt`, `licences/fonts-metadata.md`,
`licences/python-dependencies.md`, `examples/catalogue.pdf`,
`engine/pyproject.toml`, `engine/uv.lock`,
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
reported `manifestSha256` with the release record for an external anchor. It
works from an unrelated working directory and does not read the source
repository; no path in the payload points back at the checkout.

If you are working in the Bookify source project and have the release helper,
`python packaging/bookify_skill_bundle.py verify-install --target <dir>` performs
the same check, and `verify-commands` checks installed command copies against the
archive. The helper is not part of this payload.

## Rollback

Skill install (fresh or upgraded):

```sh
rm -rf "$HOME/.config/opencode/skills/bookify"
# For an upgrade, or restore the backup created by the helper:
# mv "$HOME/.config/opencode/backups/bookify-previous" \
#    "$HOME/.config/opencode/skills/bookify"
```

Commands:

```sh
rm -f "$HOME/.config/opencode/commands/bookify.md" \
      "$HOME/.config/opencode/commands/bookify-source-faithful.md" \
      "$HOME/.config/opencode/commands/bookify-teachable-textbook.md"
```

Only those paths. `pdf-book-design` and every other global skill/config stay
untouched. The archive and the upgrade backup are the restore sources.

## Limits

Portable here means relocatable on the documented compatible Linux x86_64 stack
with the listed system tools and a working `uv` setup. It does not mean
zero-prerequisite, fully offline installation, or support for untested
platforms. See `SKILL.md` and `LICENCES.md` for the complete limits and rights
record.

- Installation is collision-safe for the three command names and the skill
  directory only. It does not manage other commands, other skills or global
  configuration.
- Installation and upgrades are tested with a single top-level `bookify/`
  payload. It is not a general-purpose tar installer.
- The bundled engine is a copy: fixes made in a source checkout do not reach an
  installed bundle until a new archive is packed and installed.
- Verification of a build is not human sign-off. Same-manuscript repeatability
  is not a claim that independent rewrites are byte-identical.
- This candidate does not include the future same-source example books or their
  trial evidence; those are authored and reviewed separately.
