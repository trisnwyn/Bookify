# Cross-Agent & Multi-Harness Benchmarks

All runs below execute the **exact same standardized Bookify benchmark prompt** in a clean directory (`teachable` mode, *"Gradient Descent and Regularised Regression"*, cover `cover-3`):
- 3 chapters + 1 appendix (`≥ 8` display equations including matrices, summations, and piecewise `cases`, 1 illustrative CeTZ process diagram, 1 synthetic line chart, 1 comparison table, 1 worked example, 4 distinct human error-recovery exercise workspaces including a padded fill-in table, and cross-references)
- Full offline pipeline: `manuscript check` → `design check` → double offline `build` (byte-identical determinism proof) → pure-Python Pillow `contact-sheet` + visual page inspection & defect fixes → 18-check `verify` gate (`gate: pass`).

## Measured Results (v0.2.1, November 2026)

| Harness | Model | Status | Wall Time | Build Attempts | Pages (A4) | `verify` Gate | Max Caption Δ | Warnings | Cost / Tokens | PDF SHA-256 (prefix) |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- | --- |
| **Google Antigravity** | Gemini Hydrogen | Benchmarked | **235 s** (3m 55s) | 7 | 8 | `pass` (18/18) | `0.784 pt` | 3 answered in `review-notes.json` | Not recorded | `0c9c1ce94432…` |
| **OpenAI Codex** | GPT 6 Luna | Benchmarked | **421 s** (7m 01s) | 2 | 9 | `pass` (18/18) | `0.784 pt` | 2 (`rhythm:unmeasured:h2`, `h3`) | Not recorded | `7b2cfc7790f6…` |
| **Google Antigravity** | Gemini Neon | Benchmarked | **596 s** (9m 56s) | 6 | 9 | `pass` (18/18) | `0.784 pt` | `0` (`[]`) | Not recorded | `092815937d8d…` |
| **OpenAI Codex** | GPT 6.2 Sol | Benchmarked | **651 s** (10m 51s) | 6 | 8 | `pass` (18/18) | `0.784 pt` | `0` (`[]`) | Not recorded | `418cdabc93d6…` |
| **Cursor** | Grok 4.7 | Benchmarked | **697 s** (11m 37s) | 3 | 10 | `pass` (18/18) | `0.784 pt` | `0` (`[]`) | Not recorded | `5403a8fe9c64…` |
| **OpenCode** | DeepSeek V4.1 Flash 1017 | Benchmarked | **1083 s** (18m 03s) | 5 | 14 | `pass` (18/18) | `0.784 pt` | `0` (`[]`) | Not recorded | `5e95e47e0545…` |
| **Claude Code** | — | Un-benchmarked | — | — | — | — | — | — | — | — |

### Run Details & Provenance

- **Antigravity / Gemini Hydrogen (`235 s`, 8 pages, 7 builds):**
  - Build breakdown: 1 Typst `diff` → `partial` syntax fix, 2 initial builds, 2 chart-label overlap fixes on `t=1..6`, 2 final deterministic builds.
  - Answered warnings in `review-notes.json`: `rhythm:unmeasured:h2`, `rhythm:unmeasured:h3`, `readability:wordsPerPage:page=7`.
  - Full PDF SHA-256: `0c9c1ce944320ac8da7200573e387079556b2cbc3839007353277daf420bddde`
- **OpenAI Codex / GPT 6 Luna (`421 s`, 9 pages, 2 builds):**
  - Completed in just 2 offline builds (initial + byte-identical comparison rebuild), `0.784 pt` max caption delta.
  - Warnings: `rhythm:unmeasured:h2`, `rhythm:unmeasured:h3`.
  - Full PDF SHA-256: `7b2cfc7790f6edf559c863191278e3bd13c6e821e9baae1baff22e1e0e306162`
- **Antigravity / Gemini Neon (`596 s`, 9 pages, 6 builds):**
  - Zero warnings across all 18 checks, byte-identical offline rebuild, all 14 figure/table/equation captions within `0.784 pt` of page centre.
  - Full PDF SHA-256: `092815937d8d6afbd198f72e766a4643c8c8539d11a5a8263b03fba59dfda2c9`
- **OpenAI Codex / GPT 6.2 Sol (`651 s`, 8 pages, 6 builds):**
  - 6 offline builds in a clean staging directory, zero warnings across all 18 checks, byte-identical rebuild, `0.784 pt` max caption delta.
  - Full PDF SHA-256: `418cdabc93d654715931210d5d87659fdc85156b033655ed2c30657f32fcfc0d`
- **Cursor / Grok 4.7 (`697 s`, 10 pages, 3 builds):**
  - 10-page A4 monograph completed in 3 builds, zero warnings across all 18 checks, byte-identical rebuild, `0.784 pt` max caption delta.
  - Full PDF SHA-256: `5403a8fe9c64c4b73eb1f251ee07aafe37a88b2f014874e5761f1608bfac10ca`
- **OpenCode / DeepSeek V4.1 Flash 1017 (`1083 s`, 14 pages, 5 builds):**
  - Included 2 environment/conflict retries; zero warnings across all 18 checks, `0.784 pt` max caption delta.
  - Full PDF SHA-256: `5e95e47e0545310369fe2e5585cc7a7bb7a5ea9154f6946fe8c589c2ab45551f`

## Key Observations

1. **100 % `gate: pass` across 6 models and 4 harnesses:** Google Antigravity, OpenAI Codex, Cursor, and OpenCode all drove the full schema → Typst → visual inspection → 18-check verification loop to deterministic `gate: pass` without human intervention (4 of 6 runs achieved zero warnings).
2. **Tight geometric consistency (`0.784 pt` max caption delta):** Every completed run hit the exact same `0.784 pt` maximum centering delta (well inside the `±2.0 pt` tolerance) across formulas, charts, diagrams, and tables.
3. **Fast convergence and self-correction:** Codex (`GPT 6 Luna`, 2 builds) and Cursor (`Grok 4.7`, 3 builds, 0 warnings) passed in minimal build cycles, while agents catching chart-label overlaps or Typst symbol mistakes (`diff` → `partial`) self-corrected autonomously via visual contact sheets before final verification.

## How to Reproduce or Contribute a Harness Run

Pre-install Bookify (`install.sh` / `install.ps1` + `bookify skill install`), open a **fresh conversation** in an empty directory, and run the standardized benchmark task (`book.yaml` → double offline `build` → Pillow `contact-sheet` → `verify` → `benchmark-result.json`). Pull requests adding **Claude Code** or token/USD cost measurements are welcome.
