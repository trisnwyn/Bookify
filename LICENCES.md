# Rights, licences and attribution

This file records what this repository contains and the rights evidence found in
the source project. It does **not** relicense third-party components and does
not invent terms for material the owner has not licensed. It is not legal
advice.

## Bookify original code, tests and documentation

Original Bookify source code, tests, test fixtures and the documentation that
describes them are licensed under the **MIT License**; the full text is in
[`LICENSE`](LICENSE).

Copyright (c) 2026 Tris Nguyen.

The project-local skill at `skill/bookify/` is source documentation for the same
project and is covered by the same MIT grant.

## Manuscripts and original artwork

The specimen and catalogue manuscripts in `content/` and the original vector artwork
(`assets/catalogue/artwork/art-1.svg`, `assets/catalogue/artwork/rec-1.svg`)
are published by the owner. They are **not** licensed under MIT unless a file
states otherwise; the owner retains all rights in them.

`examples/catalogue.pdf` is the reviewed catalogue output, included so the
packaging helper can build a bundle from a fresh public clone. It is a
reference document, not an additional licensed asset; its fonts and
illustrations keep the terms recorded below.

## Third-party components

| Component | Version | Licence | Evidence in this repository |
| --- | --- | --- | --- |
| Typst | 0.15.1 | Apache-2.0 | `tools/typst/LICENSE`, `tools/typst/NOTICE` |
| CeTZ | 0.5.3 | LGPL-3.0 | `vendor/typst/preview/cetz/0.5.3/LICENSE` |
| Oxifmt | 1.0.0 | MIT OR Apache-2.0 | `vendor/typst/preview/oxifmt/1.0.0/LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE` |
| Spectral | 7 faces | SIL Open Font License 1.1 | `assets/fonts/fonts.yaml`, `packaging/payload/licences/OFL-1.1.txt`, `packaging/payload/licences/fonts-metadata.md` |
| Noto Serif CJK JP | variable TTC | SIL Open Font License 1.1 | same as above |
| STIX Two Math | Regular OTF | SIL Open Font License 1.1 | same as above |

The Typst binary is the upstream static `x86_64-unknown-linux-musl` build. It is
unmodified. CeTZ and Oxifmt are unmodified vendored Typst packages. The font
files are unmodified; their embedded name tables identify the copyright holder,
the licence description and the licence URL, transcribed in
`packaging/payload/licences/fonts-metadata.md`. The full SIL Open Font License
1.1 text is at `packaging/payload/licences/OFL-1.1.txt`. The OFL does not apply
to documents created with the fonts.

## Illustrations in `assets/illustrations/`

| ID | Kind | Rights record |
| --- | --- | --- |
| `photo-1` | contemporary photograph | William Ng / US Department of State; public domain (US Government work); Wikimedia Commons `File:Barack_Obama_and_Emperor_Akihito_20140424.jpg`. Evidence in `record.yaml`. |
| `hist-1` | contemporary photograph | Gaetano Faillace / US Army; public domain (`PD-USGov-Military-Army`); Wikimedia Commons `File:Macarthur_hirohito.jpg`. Evidence in `record.yaml` and `LICENCE.md`. |
| `art-1` | conceptual artwork | Original vector drawing made for this catalogue; no external source. Record says `rightsStatus: verified`. |
| `rec-1` | reconstruction | Original vector drawing made for this catalogue from a written description; no original traced. Record says `rightsStatus: verified`. |
| `photo-a`, `photo-b` | test fixtures | Small crops derived from `photo-1`; public-domain source. Used only by tests. |
| `photo-c` | test fixture | Deliberately `rightsStatus: unconfirmed` negative fixture derived from `photo-1`; used only to test refusal. Not used in the catalogue. |

The two photographs are public-domain works of the US federal government. The
Wikimedia Commons file pages and licence tags are recorded in each `record.yaml`;
`hist-1` also has a detailed `LICENCE.md`. The original vector artwork is the
project owner's work; it is not traced from an external source.

## Material deliberately not published

This repository does not include the private lecture deck used for the
development trial, the private trial manuscript derived from that deck, the
local portable bundle archive, generated build output, or internal worklogs and
reports. Those files remain local and unchanged.

The public test suite uses `fixtures/synthetic-trial.yaml` instead: a
source-independent fixture authored for testing, with no source anchors and no
claims about an external document. The private trial build is therefore not
reproducible from a fresh clone; the specimen and catalogue builds are.

## Python dependencies (not vendored)

`pyproject.toml` and `uv.lock` resolve these distributions at setup. They are
not included as wheels.

| Distribution | Version | Licence |
| --- | --- | --- |
| matplotlib | 3.11.2 | matplotlib licence (PSF-based) with bundled third-party notices |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| PyYAML | 6.0.3 | MIT |
| jsonschema | 4.26.0 | MIT |
| fonttools | 4.68.0 | MIT |
| pytest | 9.2.0 | MIT |
| hatchling (build) | resolved by uv | MIT |

`uv.lock` carries the exact resolved versions and hashes.
`packaging/payload/licences/python-dependencies.md` records the metadata
observed in the tested environment.

## System tools (not distributed)

`uv`, Python, Bubblewrap, Poppler and ImageMagick are prerequisites, not
payload. They keep their own licences: `uv` MIT OR Apache-2.0; CPython PSF-2.0;
Bubblewrap LGPL-2.1-or-later; Poppler GPL-2.0-or-later; ImageMagick
ImageMagick License. Consult the installed packages for the authoritative text.
