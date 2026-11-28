# Cross-Agent & Multi-Harness Benchmarks

All runs below execute the **exact same standardized Bookify benchmark prompt** in a clean directory (`teachable` mode, *"Gradient Descent and Regularised Regression"*, cover `cover-3`):
- 3 chapters + 1 appendix (`≥ 8` display equations including matrices, summations, and piecewise `cases`, 1 illustrative CeTZ process diagram, 1 synthetic line chart, 1 comparison table, 1 worked example, 4 distinct human error-recovery exercise workspaces including a padded fill-in table, and cross-references)
- Full offline pipeline: `manuscript check` → `design check` → double offline `build` (byte-identical determinism proof) → pure-Python Pillow `contact-sheet` + visual page inspection & defect fixes → 18-check `verify` gate (`gate: pass`).

## Measured Results (v0.2.1, November 2026)

| Harness | Model | Status | Wall Time | Build Attempts | Pages (A4) | `verify` Gate | Max Caption Δ | Warnings | Cost / Tokens | PDF SHA-256 (prefix) |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- | --- |
| **Google Antigravity** | Gemini Hydrogen | Benchmarked | **235 s** (3m 55s) | 7 | 8 | `pass` (18/18) | `0.784 pt` | 3 answered in `review-notes.json` | Not recorded | `0c9c1ce94432…` |
| **Google Antigravity** | Gemini Neon | Benchmarked | **596 s** (9m 56s) | 6 | 9 | `pass` (18/18) | `0.784 pt` | `0` (`[]`) | Not recorded | `092815937d8d…` |
| **OpenCode** | DeepSeek V4.1 Flash 1017 | Benchmarked | **1083 s** (18m 03s) | 5 | 14 | `pass` (18/18) | `0.784 pt` | `0` (`[]`) | Not recorded | `5e95e47e0545…` |
| **Claude Code** | — | Un-benchmarked | — | — | — | — | — | — | — | — |
| **OpenAI Codex** | — | Un-benchmarked | — | — | — | — | — | — | — | — |
| **Cursor** | — | Un-benchmarked | — | — | — | — | — | — | — | — |

### Run Details & Provenance

- **Antigravity / Gemini Hydrogen (`235 s`, 8 pages, 7 builds):**
  - Build breakdown: 1 Typst `diff` → `partial` syntax fix, 2 initial builds, 2 chart-label overlap fixes on `t=1..6`, 2 final deterministic builds.
  - Answered warnings in `review-notes.json`: `rhythm:unmeasured:h2`, `rhythm:unmeasured:h3`, `readability:wordsPerPage:page=7`.
  - Full PDF SHA-256: `0c9c1ce944320ac8da7200573e387079556b2cbc3839007353277daf420bddde`
- **Antigravity / Gemini Neon (`596 s`, 9 pages, 6 builds):**
  - Zero warnings across all 18 checks, byte-identical offline rebuild, all 14 figure/table/equation captions within `0.784 pt` of page centre.
  - Full PDF SHA-256: `092815937d8d6afbd198f72e766a4643c8c8539d11a5a8263b03fba59dfda2c9`
- **OpenCode / DeepSeek V4.1 Flash 1017 (`1083 s`, 14 pages, 5 builds):**
  - Included 2 environment/conflict retries; zero warnings across all 18 checks, `0.784 pt` max caption delta.
  - Full PDF SHA-256: `5e95e47e0545310369fe2e5585cc7a7bb7a5ea9154f6946fe8c589c2ab45551f`

## Key Observations

1. **100 % `gate: pass` across every benchmarked agent and harness:** Both Google Antigravity and OpenCode drove the full schema → Typst → visual inspection → 18-check verification loop to deterministic `gate: pass` without human intervention.
2. **Tight geometric consistency (`0.784 pt` max caption delta):** Every completed run hit the exact same `0.784 pt` maximum centering delta (well inside the `±2.0 pt` tolerance) across formulas, charts, diagrams, and tables.
3. **Self-correction via visual contact sheets works in practice:** Agents caught and fixed Typst math symbol mistakes (`diff` → `partial`), chart-label overlaps, and page-rhythm warnings autonomously before final verification.

## How to Reproduce or Contribute a Harness Run

Pre-install Bookify (`install.sh` / `install.ps1` + `bookify skill install`), open a **fresh conversation** in an empty directory, and run the standardized benchmark task (`book.yaml` → double offline `build` → Pillow `contact-sheet` → `verify` → `benchmark-result.json`). Pull requests adding **Claude Code**, **OpenAI Codex**, **Cursor**, or token/USD cost measurements are welcome.
