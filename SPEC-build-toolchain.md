# SPEC-build-toolchain

Module id: `build-toolchain` · depends on: nothing · build step 0 · status: approved 2026-11-10.

## Objective

Make one machine able to rebuild the same book twice, offline, from pinned local tools, fonts and packages. This module exists so that "the publishing run made no network or model calls" is an enforced property, not a promise. It also owns the record of every substitution made against the intended Typst + Matplotlib + CeTZ stack.

## Tech stack

| Item | State |
| --- | --- |
| Python | 3.14.8 present; 3.13.16 also available. Which interpreter runs Matplotlib is **pending validation** (the cached Matplotlib wheel is cp313-only). |
| uv | 0.12.24 (verified) |
| Typst CLI | **absent** at inspection. Version to be pinned after validation; not invented here. |
| CeTZ | **absent**; version and vendoring path to be pinned after validation. |
| Matplotlib / numpy | not installed; cache holds candidates 3.11.2 / 2.5.4, not yet accepted as pins. |
| Fonts | Spectral 7 cuts verified (sha256 in `.opencode/inspection.md`); CJK and maths faces verified present, selection pending. |
| Poppler 26.01.0, Ghostscript 10.06.0 | verification-time only, not runtime dependencies. |

## Commands (proposed, not implemented)

```bash
uv sync --locked
uv run bookify toolchain doctor --json
uv run bookify toolchain vendor --verify
uv run bookify build --manuscript content/specimen.yaml --out dist/specimen.pdf --offline
```

## Project structure

```
pyproject.toml              # one project, one lockfile
uv.lock
toolchain.lock.json         # typst + packages + fonts, versions and sha256, written by vendor
vendor/typst/               # vendored CeTZ and any other Typst packages
assets/fonts/               # Spectral + CJK + maths faces, with LICENCES.md
src/bookify/toolchain/
  cli.py                    # thin dispatcher: intake | author | build | verify | toolchain
  pins.py                   # load and validate toolchain.lock.json
  guard.py                  # offline / no-model enforcement
  doctor.py                 # local readiness report
```

## Code style

```python
class BookifyError(RuntimeError):
    def __init__(self, code: str, message: str, locator: str | None = None) -> None:
        super().__init__(message)
        self.code, self.message, self.locator = code, message, locator


def require_local_toolchain(lock: ToolchainLock, report: DoctorReport) -> None:
    """Fail before any build work if a pin, font or package is missing."""
    for pin in lock.required_pins():
        if not pin.is_present():
            report.add(Issue("FONT_MISSING" if pin.kind == "font" else "BUILD_FAILED", pin.name))
    if report.has_errors:
        raise BookifyError(report.first_code, report.summary)
```

Rules: typed public functions, frozen dataclasses for records, one error type, no hidden I/O in helpers, every pin carries a hash.

## Testing strategy

`pytest` under `tests/toolchain/`:

- Unit: guard denies `socket.socket.connect` and any subprocess flagged as model access; report contains `NETWORK_DENIED` / `MODEL_CALL_DENIED`.
- Unit: `doctor` fails on a missing font, a hash mismatch, or a lock entry without a version.
- Integration: a build invoked with `--offline` completes with no outbound socket; a deliberately enabled network call fails the build.
- Contract: `toolchain.lock.json` round-trips; no pin is accepted without a source URL and sha256.

No network is required to run these tests once setup is complete.

## Boundaries

- Always: record versions and hashes that were actually observed; vendor packages under `vendor/`; keep setup (`uv sync`) separate from the offline build; document substitutions and why.
- Ask first: adding a runtime dependency, choosing the Typst/CeTZ/Matplotlib pins, upgrading a pinned version.
- Never: let `build` or `verify` fetch anything; commit a lock entry without a hash; invent a version from memory; modify the global `pdf-book-design` skill or the original repo.

## Success criteria

1. `uv run bookify toolchain doctor --json` resolves every pin locally and exits 0 on a prepared machine, non-zero with exact missing items otherwise.
2. `toolchain.lock.json` lists Typst, CeTZ, Matplotlib, numpy, Python and every font file with a version (where applicable) and sha256; no entry is a guess.
3. `uv run bookify build --offline` attempts no network connection; a test proves the guard fails a forced call.
4. A clean checkout plus `uv sync --locked` reproduces the specimen build without manual downloads beyond the documented setup step.
5. Substitutions against the target stack are recorded, with impact, in one place.

## Open questions

- Final Typst and CeTZ versions, and the Python/Matplotlib combination, are **pending toolchain validation** (must be measured, not chosen from memory).
- Whether CeTZ is vendored as a Typst package directory or pinned through Typst's package manifest is an implementation detail for the plan, not a scope question.
