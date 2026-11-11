# Licences and attribution

This file records what is in the bundle and the rights evidence found in the
source project. It does not relicense anything and does not invent a licence
where the source had none.

## Bookify code, tests, documentation and original artwork

Original Bookify Python code, tests, test fixtures and documentation are
licensed under the **MIT License**; the source project's `LICENSE` applies.
This bundle includes that engine source, so the MIT grant travels with it.

The manuscripts in `engine/content/` and the original vector artwork
(`engine/assets/catalogue/artwork/art-1.svg`,
`engine/assets/catalogue/artwork/rec-1.svg`) are published by the owner and are
not separately MIT-licensed unless a file says so. Third-party components keep the
terms recorded below.

The preserved project-local skill at `engine/skill/bookify/` is part of the same
source project.

### MIT License text

```text
MIT License

Copyright (c) 2026 Tris Nguyen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Third-party components included in the payload

| Component | Version | Licence | Evidence in this bundle |
| --- | --- | --- | --- |
| Typst | 0.15.1 | Apache-2.0 | `engine/tools/typst/LICENSE`, `engine/tools/typst/NOTICE` |
| CeTZ | 0.5.3 | LGPL-3.0 | `engine/vendor/typst/preview/cetz/0.5.3/LICENSE` |
| Oxifmt | 1.0.0 | MIT OR Apache-2.0 | `engine/vendor/typst/preview/oxifmt/1.0.0/LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE` |
| Spectral | 7 faces | SIL Open Font License 1.1 | `licences/OFL-1.1.txt`, `licences/fonts-metadata.md` |
| Noto Serif CJK JP | variable TTC | SIL Open Font License 1.1 | `licences/OFL-1.1.txt`, `licences/fonts-metadata.md` |
| STIX Two Math | Regular OTF | SIL Open Font License 1.1 | `licences/OFL-1.1.txt`, `licences/fonts-metadata.md` |

The Typst binary is the upstream static `x86_64-unknown-linux-musl` build. It is
unmodified. Its `LICENSE` and `NOTICE` are included at the path above. CeTZ and
Oxifmt are unmodified vendored Typst packages.

### Fonts

The font files are unmodified. Their embedded name tables identify the
copyright holder, the licence description and the licence URL; those values are
transcribed in `licences/fonts-metadata.md`. The full SIL Open Font License 1.1
text is included at `licences/OFL-1.1.txt`.

OFL 1.1 condition 3 restricts modified versions from using a Reserved Font
Name. These are unmodified upstream files. Trademark acknowledgements from the
name tables are retained in the metadata file. The OFL does not apply to
documents created with the fonts.

## Illustrations in `engine/assets/illustrations/`

| ID | Kind | Rights record |
| --- | --- | --- |
| `photo-1` | contemporary photograph | William Ng / US Department of State; public domain (US Government work); Wikimedia Commons `File:Barack_Obama_and_Emperor_Akihito_20140424.jpg`. Evidence in `record.yaml`. |
| `hist-1` | contemporary photograph | Gaetano Faillace / US Army; public domain (`PD-USGov-Military-Army`); Wikimedia Commons `File:Macarthur_hirohito.jpg`. Evidence in `record.yaml` and `LICENCE.md`. |
| `art-1` | conceptual artwork | Original vector drawing made for this catalogue; no external source. Record says `rightsStatus: verified`. No separate licence file. |
| `rec-1` | reconstruction | Original vector drawing made for this catalogue from a written description; no original traced. Record says `rightsStatus: verified`. No separate licence file. |
| `photo-a`, `photo-b` | test fixtures | Small crops derived from `photo-1`; public-domain source. Used only by tests. |
| `photo-c` | test fixture | Deliberately `rightsStatus: unconfirmed` negative fixture derived from `photo-1`; used only to test refusal. Not used in the catalogue. |

The two photographs are public-domain works of the US federal government. The
Wikimedia Commons file pages and licence tags are recorded in each
`record.yaml`; `hist-1` also has a detailed `LICENCE.md`. The original vector
artwork is the project owner's work; it is not traced from an external source.

## Reference PDF

`examples/catalogue.pdf` is the reviewed 19-page catalogue output. It contains
the fonts and illustrations above. It is included as a reference example, not
as an additional licensed asset. Its SHA-256 is recorded in the release
documentation and checked during packaging.

## Python dependencies (not vendored)

The bundle ships `engine/pyproject.toml` and `engine/uv.lock`; `uv sync` resolves
these distributions at setup. They are not included as wheels. Primary
distributions:

| Distribution | Version | Licence |
| --- | --- | --- |
| matplotlib | 3.11.2 | matplotlib licence (PSF-based) with bundled third-party notices |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| PyYAML | 6.0.3 | MIT |
| jsonschema | 4.26.0 | MIT |
| fonttools | 4.68.0 | MIT |
| pytest | 9.2.0 | MIT |
| hatchling (build) | resolved by uv | MIT |

`uv.lock` carries the exact resolved versions and hashes. `licences/python-dependencies.md`
records the metadata observed in the tested environment.

## System tools (not distributed)

`uv`, Python, Bubblewrap, Poppler and ImageMagick are prerequisites, not payload.
They keep their own licences: `uv` MIT OR Apache-2.0; CPython PSF-2.0;
Bubblewrap LGPL-2.1-or-later; Poppler GPL-2.0-or-later; ImageMagick
ImageMagick License. Consult the installed packages for the authoritative text.
