# Python dependency and setup record

The bundle does not embed a virtual environment or wheels. `engine/uv.lock`
pins the resolved distributions; `uv sync --python 3.13.16 --frozen` installs
them into `engine/.venv` at setup. A first sync may use the network or a
populated uv cache. Build and verify do not download anything.

Versions observed in the tested environment (the same versions resolved from
`uv.lock`):

| Distribution | Version | Licence metadata observed |
| --- | --- | --- |
| Python | 3.13.16 | PSF-2.0 (provided by `uv`) |
| matplotlib | 3.11.2 | matplotlib licence (PSF-based) with bundled third-party notices |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| PyYAML | 6.0.3 | MIT |
| jsonschema | 4.26.0 | MIT |
| fonttools | 4.68.0 | MIT |
| pytest | 9.2.0 | MIT |
| contourpy | 1.4.0 | BSD-3-Clause |
| cycler | 0.12.1 | matplotlib project copyright |
| kiwisolver | 1.5.1 | BSD-3-Clause |
| pillow | 13.0.0 | MIT-CMU |
| pyparsing | 3.3.3 | MIT |
| python-dateutil | 4.0.0 | BSD-3-Clause |
| referencing | 0.37.0 | MIT |
| rpds-py | 2026.9.1 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.7.0 | MIT |
| iniconfig | 2.3.1 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| tzdata | 2026.6 | Apache-2.0 |
| hatchling (build backend) | resolved by uv | MIT |

The authoritative licence text for each distribution is in the installed
distribution metadata and its upstream source. The `uv.lock` file records the
exact versions and artifact hashes used for this release.

## Build and system tools (not distributed)

| Tool | Observed version | Licence |
| --- | --- | --- |
| uv | 0.12.24 | MIT OR Apache-2.0 |
| Bubblewrap | 0.12.0 | LGPL-2.1-or-later |
| Poppler | 26.01.0 | GPL-2.0-or-later |
| ImageMagick | 7.1.2-34 | ImageMagick License |
| fontconfig (not used for the build) | 2.17.0 | MIT-like |

These tools are prerequisites on the target machine and are not included in the
archive.
