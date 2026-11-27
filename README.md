# Bookify

**Offline Typst book authoring, mathematical typesetting, and 18-check PDF verification for AI coding agents.**

Bookify turns PDFs, slide decks, or structured notes into publication-grade A4 **PDF/A-2b** monographs, scholarly math articles, textbooks, and practice workbooks — authored by your AI agent (Claude Code, OpenAI Codex, OpenCode, Cursor, or Google Antigravity) and compiled deterministically offline with Typst.

## Highlights

- **Publication typography out of the box:** Vendored `Spectral` (all 7 weights) + `STIX Two Math` (display equations with stacked limits, matrices, integrals, and piecewise cases) + optional on-demand `Noto Serif CJK JP`.
- **Geometric centering:** Display formulas, formula descriptions, tables, graphs, diagrams, and illustrations are mathematically centered to their measure and verified within `±2 pt`.
- **Human-friendly exercise workspaces:** Native Typst primitives (`responseSpace` + `fillSpace`/`extraRows`) and a 10-case editorial rule ensure practice problems leave realistic error-recovery space (handwriting-pitch dotted lines, dot-grid proof boxes, tall padded fill-in tables with overflow rows, coordinate grids, choice checkboxes with revision lines, and algorithm trace tables).
- **18-check verification gate:** Checks offline determinism (byte-identical double builds), embedded glyphs, PDF/A-2b metadata, cover geometry, caption centering, heading rhythm, readability bands, cross-references, rights/provenance, and visual contact-sheet inspection.
- **Multi-platform skill + lightweight CLI:** The portable agent skill (`skills/bookify/`) is **< 100 KB** of pure markdown and pairs with a **~4 MB** installable Python CLI working across **Linux, macOS, and Windows**.

---

## Quickstart (30 Seconds)

### 1. Install the Bookify CLI Engine

```bash
uv tool install bookify-typst  # or: pipx install bookify-typst
bookify toolchain install      # installs pinned Typst 0.15.1 for Linux / macOS / Windows
bookify toolchain doctor       # checks Typst, fonts, and Poppler
```

*(Optional — only needed when authoring Japanese/CJK books:)*

```bash
bookify fonts install cjk
```

### 2. Install the AI-Agent Skill

Install directly to one or all supported platforms with the built-in installer:

```bash
bookify skill install --platform all
# Or target a single platform:
bookify skill install --platform claude       # ~/.claude/skills/bookify + commands
bookify skill install --platform codex        # ~/.agents/skills/bookify
bookify skill install --platform opencode     # ~/.config/opencode/skills/bookify + commands
bookify skill install --platform cursor       # ~/.cursor/skills/bookify
bookify skill install --platform antigravity  # ~/.gemini/config/skills/bookify
```

Or install via the universal Agent Skills ecosystem / Claude Code Plugin Marketplace:

```bash
# Universal Agent Skills CLI (Claude Code, Codex, Cursor, OpenCode, Antigravity, Copilot)
npx skills add trisnwyn/Bookify

# Claude Code Plugin Marketplace
# /plugin marketplace add trisnwyn/Bookify
```

---

## Supported Agent Platforms & OS Matrix

| Platform | Skill Format | Slash Commands Included |
| --- | --- | --- |
| **Claude Code** | `skills/bookify/SKILL.md` + `.claude-plugin/plugin.json` | `/bookify`, `/bookify-source-faithful`, `/bookify-teachable-textbook` |
| **OpenAI Codex** | `~/.agents/skills/bookify/SKILL.md` | Prompt modes via skill |
| **OpenCode** | `~/.config/opencode/skills/bookify/SKILL.md` | `/bookify`, `/bookify-source-faithful`, `/bookify-teachable-textbook` |
| **Cursor** | `~/.cursor/skills/bookify/SKILL.md` | Prompt modes via skill |
| **Google Antigravity** | `~/.gemini/config/skills/bookify/SKILL.md` | Prompt modes via skill |

| OS | Typst Compile | Offline Isolation | Contact Sheets | Poppler (`verify`) |
| --- | --- | --- | --- | --- |
| **Linux (x86_64 / arm64)** | Auto-installed `0.15.1` | `bwrap --unshare-net` (or `env-isolated`) | Built-in Pillow | `apt/dnf install poppler-utils` |
| **macOS (arm64 / x86_64)** | Auto-installed `0.15.1` | `env-isolated` (local-only Typst) | Built-in Pillow | `brew install poppler` |
| **Windows (x86_64)** | Auto-installed `0.15.1` | `env-isolated` (local-only Typst) | Built-in Pillow | `winget install oschwartz10612.Poppler` |

---

## Core CLI Commands

| Command | Purpose |
| --- | --- |
| `bookify --version` | Print installed engine version |
| `bookify toolchain install` | Download and verify pinned Typst `0.15.1` for the host OS/arch |
| `bookify toolchain doctor [--json]` | Verify Typst, vendored packages, fonts, and system tools |
| `bookify fonts status \| install cjk` | Check or install the optional Noto Serif CJK JP font pack |
| `bookify skill list \| install` | List or install the portable skill across agent platforms |
| `bookify intake --source FILE --out DIR` | Extract source PDF text/images with optional Tesseract OCR |
| `bookify manuscript check --manuscript FILE` | Validate schema, cross-references, and exercise/figure rules |
| `bookify design check --manuscript FILE` | Validate design tokens, presets, and exact glyph coverage |
| `bookify build --manuscript FILE --out PDF --offline` | Compile deterministic PDF/A-2b offline (`--sandbox auto\|bwrap\|none`) |
| `bookify figures contact-sheet --pdf PDF --out PNG` | Generate a PNG contact sheet with pure Pillow (no ImageMagick) |
| `bookify verify --pdf PDF --manuscript FILE` | Run the 18-check acceptance gate |

---

## Build & Verify From Any Directory

```bash
bookify manuscript check --manuscript book.yaml --json
bookify design check --manuscript book.yaml --json

bookify build --manuscript book.yaml --out dist/book.pdf --offline --json
bookify build --manuscript book.yaml --out build/rebuild.pdf --offline --json

bookify figures contact-sheet --pdf dist/book.pdf --out build/contact-sheet.png --cols 4 --json

bookify verify \
  --pdf dist/book.pdf \
  --manuscript book.yaml \
  --previous-pdf build/rebuild.pdf \
  --contact-sheet build/contact-sheet.png \
  --reviewed-by "agent-visual-review" \
  --reviewed-at "2026-11-28" \
  --report build/verify.json --json
```

---

## Development Setup (From Source Checkout)

```bash
uv sync --locked
uv run bookify toolchain doctor --json
uv run python -m pytest -q
```

### Repository Layout

```text
skills/bookify/     portable multi-platform AI-agent skill (<100 KB, agentskills.io standard)
.claude-plugin/     Claude Code plugin and marketplace manifests
src/bookify/        CLI engine: runtime, toolchain, manuscript, design, figures, publish, intake, verify
typst/              design tokens, block presets, 7 covers, compositions, CeTZ diagram engine
schemas/            closed JSON Schema (v1.0) for manuscripts and exercise workspaces
vendor/typst/       vendored CeTZ 0.5.3 and Oxifmt 1.0.0 packages
assets/fonts/       Spectral (7 weights), STIX Two Math, and Noto Serif CJK JP
tests/              comprehensive pytest verification suite
.github/workflows/  Linux/macOS/Windows CI and PyPI/GitHub Release automation
```

---

## Licensing & Attribution

- **Bookify original code, tests, and documentation:** MIT License — see [`LICENSE`](LICENSE).
- **Third-party components:** Typst, CeTZ, and Oxifmt (Apache-2.0); Spectral, STIX Two Math, and Noto Serif CJK JP (SIL Open Font License 1.1). Full attribution and rights records live in [`LICENCES.md`](LICENCES.md).
- **Private development trials:** Never tracked or shipped; public tests use synthetic fixtures only.
