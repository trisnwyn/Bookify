# Synthetic trial fixture

`fixtures/synthetic-trial.yaml` is the public test fixture that replaces the
private development trial in the public test suite.

- **Synthetic.** It was authored for this repository as test data. It is not
  extracted from, paraphrased from, or modelled on a lecture, book, dataset or
  other external source.
- **No provenance claims.** It contains no `sourceAnchors`, no measurements and
  no statements about an external document. The metadata says so explicitly.
- **Purpose.** It exercises manuscript validation and deterministic
  normalization without making the public suite depend on private material.
- **Not the private trial.** `content/trial.yaml` and `docs/trial.md` remain
  local to the owner, unchanged and unpublished. The public repository does not
  include the private deck or any derived manuscript.
- **Canonical output unchanged.** The specimen and catalogue manuscripts and
  their reviewed outputs are not affected by this fixture.

Integrity: 1,854 bytes, SHA-256
`9f0c5ad7befbc7b327f771941898af67bc0ac70e16e4b0065f64ebd9fb92123b`.

Checks:

```bash
uv run bookify manuscript check --manuscript fixtures/synthetic-trial.yaml --json
uv run pytest -q tests/test_manuscript.py tests/test_layout_normalize.py
```

The test `test_specimen_and_synthetic_trial_normalized_documents_are_unchanged`
pins the fixture's normalized document hash, so an accidental content or
normalization change is visible. The fixture is test data under the repository's
MIT licence.
