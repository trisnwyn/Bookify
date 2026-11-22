# Tracked design proofs

These files are the accepted design evidence for the integrated renderer. They
are byte-identical copies of the disposable proof sources in `build/design/`
(which `.gitignore` keeps out of the repository), tracked here so the design
truth survives a cache clean and a later reader can reproduce every measurement
without re-deriving it.

- **Owner:** the user. The AI encodes; it does not decide visual direction.
- **Status:** the user accepted the A1 four compositions, the A2 two-column flow
  and the seven cover compositions as the basis for production layout. No cover
  variant is a selected default, and the A1 open questions in
  `docs/design/textbook-layout.md` (Q1 and Q3–Q7, including Q2 column count)
  remain open. `docs/design-map.md` records the item statuses.
- **What changed when this was integrated:** the proof sources themselves are
  unchanged. The production renderer (`typst/cover.typ`,
  `typst/compositions.typ`, `typst/templates/book.typ`, `typst/theme.typ`) now
  implements them. `SPEC-design-system.md`
  ("Amendment — production layout integration") records the values.

## Groups

| Path | Source | What it shows |
| --- | --- | --- |
| `a1/` | `build/design/a1/` | Four single-column body compositions: full-width prose with a centred visual at `figure_width`, the same with a full-measure visual, prose beside a right-hand visual, and a left visual with prose plus a full-width paragraph below. Plus the measured heading-clearance record. |
| `a2/` | `build/design/a2/` | Two-column body flow with a figure inside the right column, the terminal/continuing branch numbering path and the blank-line rule, plus the measurement script and record. |
| `cover/` | `build/design/cover/` | Seven accepted cover compositions (refs 1–7): `part-a.typ` for refs 1–4, `part-b.typ` for refs 5–7, their READMEs and measurement records, and the merged index. |

## What is *not* copied here

The rendered artefacts stay in `build/design/`: `a1-proof.pdf`, `a2/proof.pdf`,
`cover/part-a.pdf`, `cover/part-b.pdf`, `cover/cover-layout-proofs.pdf`, page
rasters and contact sheets. They are large binaries and are regenerable from the
sources here. Their SHA-256 values are recorded in the source READMEs, and the
production build is what verify measures now:

- `a1-proof.pdf` — see `a1/README.md` for the page count, measured clearances and
  hashes.
- `a2/proof.pdf` — `4f64d9c249739473055bbb5007c60661d7ed49346d9ada51da52e26c6e1d7a3a`
  (two A4 pages; reproduce with the command in `a2/README.md`).
- `cover/cover-layout-proofs.pdf` — `5e5289c89e900342112cc2dc6820654f66e287fac93da4bf33120f745ab941ad`
  (seven A4 pages, refs 1–7 in order).

## Reproduction

Each group's README carries the exact offline Typst command, the pinned
toolchain version and the measured values. The copies are text only; no font,
raster asset, network access or model call is involved. The proof pages contain
neutral placeholder words only (`Cover`, `Additional information`,
`Illustration`, `Decorative illustration`) and Lorem prose — no source fact,
title, author, date or ISBN is invented anywhere in them.

## Integrity

Hashes of these tracked copies (SHA-256):

```
9ef85c0866e0ff0a0a04ecea49e2ff4ce5e755339246a8133f0ac6fdb22cf11f  a1/README.md
77a34323eb4f993add26ca0dc0b00636cae44094eef46a9c53c819de58a37aee  a1/a1-proof.measure.json
c7fdb1964051945fe5fdbb463487bf3210bdf8287c704d96cc740c309548cfac  a1/a1-proof.gaps.json
d8762e038839777be5c553cc021fadb8466621135df11bec59386cdab555f610  a1/a1-proof.typ
f66e47149d92e704a19c54188755fd1dca249637dacb49e0cb4fb9b1bc770ee1  a2/README.md
997b6f3c5f9f15dddb65fc616416d69d2ff41daec0ec19d264935a0d9c8db679  a2/measure.json
1e9e9b7a1037ea8a2bb630aec93b4cff4e8d7a62c40b9bd685c109067e6979f6  a2/measure.py
1de2a7599155324bebcfce9a2c5af22eb86adb8833916a236d8f328e76fc3602  a2/proof.typ
68e992d15e79dd3c73821f17269e520ef0d1abbbc114976dfe71c2de7ed1295d  cover/INDEX.md
b08b543713395468b1d8194b6a00a38f01a45c63f7ddca0f2bfaef0ea17a87bc  cover/README-a.md
1ee36c67b741cffdadf1b6abcf03339fbc97b532135efe4233e12bd1e0ef8694  cover/README-b.md
356c38ef64b3d4ae829ceea13389046d6f6e5fecd68add67942a71bcfe58f193  cover/part-a-measure.py
ef9b1d192ea8bd32779a63c3ee9b627ba47dc29cbc86b034024b9c64f2849afb  cover/part-a.json
0e127fc0acc7a75b4b600d68b41544b9701fc78c541a1dc4d5685a10b7f8e67c  cover/part-a.typ
4f694c98ddacff708932f56615af741a2748315c16c4579770d6624e65239686  cover/part-b-measure.py
db0d735321b1ebd9c637b8b0aad68af10486495770d3f212151bc70b81211b22  cover/part-b.json
c666e9b9b5cf06c3fcf2f53b81135b4ec4caa16cc1b1ddc492c95157cdd4ff6f  cover/part-b.typ
```

The copied `cover/INDEX.md` still says "disposable review artefact; nothing here
is an approved cover". That was true when the merge step wrote it and it is left
byte-identical on purpose: the acceptance is recorded in this README and in
`docs/design-map.md`, not by editing historical evidence.
