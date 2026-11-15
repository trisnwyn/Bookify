#!/usr/bin/env python3
"""Standalone OCR capability probe for Bookify v2.

This file is deliberately outside the product package: it proves the pinned
engine and the measurement method, and it is not imported by ``bookify``.
It uses only the Python standard library, invokes pinned binaries with list
argv (never a shell), and writes byte-stable JSON with no timestamps.

Modes
-----
page    Rasterise one PDF page at two resolutions, OCR both, and compare the
        normalized token multiset per line.
regions Image placements reported by ``pdftohtml -xml`` are cropped with
        ``pdftoppm -x -y -W -H`` and measured the same way.

Exit codes follow the Bookify error classes: INPUT_INVALID=2,
SOURCE_UNREADABLE=2, BUILD_FAILED=3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXIT_CODES = {"INPUT_INVALID": 2, "SOURCE_UNREADABLE": 2, "BUILD_FAILED": 3}
SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"

# Caps from SPEC-bookify-v2.md §3.9, applied before work and named in errors.
CAP_PDF_BYTES = 512 * 1024 * 1024
CAP_PAGES = 1000
CAP_PAGE_PIXELS = 50_000_000
CAP_REGION_PIXELS = 40_000_000
CAP_REGIONS_PER_PAGE = 12
CAP_TSV_BYTES = 8 * 1024 * 1024
CAP_WORDS = 20_000
CAP_LINES = 5_000

# Confidence bands from SPEC-bookify-v2.md §3.5 (provisional until frozen).
BAND_ADEQUATE_MEAN = 90.0
BAND_ADEQUATE_LOW_SHARE = 0.05
BAND_ADEQUATE_AGREEMENT = 0.98
BAND_UNCERTAIN_MEAN = 80.0
BAND_UNCERTAIN_AGREEMENT = 0.90
TOKEN_CONFIDENCE_FLOOR = 70.0
LOW_CONFIDENCE = 60.0


class HarnessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(
    argv: list[str],
    env: dict[str, str],
    timeout: float,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run one tool with list argv. No shell, no interpolation, hard timeout.

    ``cwd`` is set for tools that can drop side files (pdftohtml extracts page
    images even with -stdout), so any such file lands in the scratch directory.
    """
    try:
        return subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
            cwd=cwd,
            check=False,
        )
    except FileNotFoundError as error:
        raise HarnessError("INPUT_INVALID", f"tool not found: {argv[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise HarnessError(
            "SOURCE_UNREADABLE", f"timeout after {timeout:g}s: {Path(argv[0]).name}"
        ) from error


def _tail(data: bytes, limit: int = 400) -> str:
    text = data.decode("utf-8", "replace").strip().replace("\n", " ")
    return text[-limit:]


def png_size(path: Path) -> tuple[int, int]:
    """Read PNG dimensions from the IHDR chunk without an image library."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise HarnessError("SOURCE_UNREADABLE", f"not a PNG: {path.name}")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def pdf_info(pdf: Path, page: int, env: dict[str, str], timeout: float) -> tuple[int, float, float]:
    # Page count and range are checked before the per-page query so an
    # out-of-range page is INPUT_INVALID, not a Poppler stderr message.
    base = _run(["/usr/bin/pdfinfo", str(pdf)], env, timeout)
    if base.returncode != 0:
        raise HarnessError("SOURCE_UNREADABLE", f"pdfinfo failed: {_tail(base.stderr)}")
    base_text = base.stdout.decode("utf-8", "replace")
    pages_match = re.search(r"^Pages:\s+(\d+)", base_text, re.MULTILINE)
    if not pages_match:
        raise HarnessError("SOURCE_UNREADABLE", "pdfinfo did not report a page count")
    pages = int(pages_match.group(1))
    if pages > CAP_PAGES:
        raise HarnessError("INPUT_INVALID", f"page count {pages} exceeds cap {CAP_PAGES}")
    if re.search(r"^Encrypted:\s+yes", base_text, re.MULTILINE):
        raise HarnessError("SOURCE_UNREADABLE", f"pdf is encrypted (page {page})")
    if page < 1 or page > pages:
        raise HarnessError("INPUT_INVALID", f"page {page} outside 1..{pages}")

    proc = _run(["/usr/bin/pdfinfo", "-f", str(page), "-l", str(page), str(pdf)], env, timeout)
    if proc.returncode != 0:
        raise HarnessError("SOURCE_UNREADABLE", f"pdfinfo failed: {_tail(proc.stderr)}")
    text = proc.stdout.decode("utf-8", "replace")
    size = re.search(rf"^Page\s+{page}\s+size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", text, re.MULTILINE)
    if size is None:
        size = re.search(r"^Page size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", text, re.MULTILINE)
    if size is None:
        raise HarnessError("SOURCE_UNREADABLE", f"pdfinfo did not report page {page} size")
    return pages, float(size.group(1)), float(size.group(2))


def render_page(
    pdf: Path,
    page: int,
    dpi: int,
    outdir: Path,
    env: dict[str, str],
    timeout: float,
    max_pixels: int,
) -> tuple[Path, int, int]:
    prefix = outdir / f"page-{page:03d}-{dpi}"
    argv = [
        "/usr/bin/pdftoppm",
        "-f",
        str(page),
        "-l",
        str(page),
        "-r",
        str(dpi),
        "-gray",
        "-png",
        "-singlefile",
        str(pdf),
        str(prefix),
    ]
    proc = _run(argv, env, timeout)
    png = Path(f"{prefix}.png")
    if proc.returncode != 0 or not png.is_file():
        raise HarnessError("SOURCE_UNREADABLE", f"pdftoppm failed: {_tail(proc.stderr)}")
    width, height = png_size(png)
    if width * height > max_pixels:
        raise HarnessError(
            "INPUT_INVALID", f"raster {width}x{height} exceeds cap {max_pixels} px"
        )
    return png, width, height


def render_crop(
    pdf: Path,
    page: int,
    dpi: int,
    box_pt: tuple[float, float, float, float],
    outdir: Path,
    env: dict[str, str],
    timeout: float,
    max_pixels: int,
) -> tuple[Path, int, int]:
    left, top, right, bottom = box_pt
    scale = dpi / 72.0
    x = max(0, round(left * scale))
    y = max(0, round(top * scale))
    width = max(1, round((right - left) * scale))
    height = max(1, round((bottom - top) * scale))
    if width * height > max_pixels:
        raise HarnessError(
            "INPUT_INVALID", f"region raster {width}x{height} exceeds cap {max_pixels} px"
        )
    prefix = outdir / f"crop-{page:03d}-{dpi}-{x}-{y}-{width}-{height}"
    argv = [
        "/usr/bin/pdftoppm",
        "-f",
        str(page),
        "-l",
        str(page),
        "-r",
        str(dpi),
        "-x",
        str(x),
        "-y",
        str(y),
        "-W",
        str(width),
        "-H",
        str(height),
        "-gray",
        "-png",
        "-singlefile",
        str(pdf),
        str(prefix),
    ]
    proc = _run(argv, env, timeout)
    png = Path(f"{prefix}.png")
    if proc.returncode != 0 or not png.is_file():
        raise HarnessError("SOURCE_UNREADABLE", f"pdftoppm crop failed: {_tail(proc.stderr)}")
    real_width, real_height = png_size(png)
    return png, real_width, real_height


def ocr_tsv(
    engine: Path,
    tessdata: Path,
    lang: str,
    image: Path,
    psm: int,
    oem: int,
    threads: int,
    env: dict[str, str],
    timeout: float,
) -> str:
    argv = [
        str(engine),
        str(image),
        "stdout",
        "--tessdata-dir",
        str(tessdata),
        "-l",
        lang,
        "--oem",
        str(oem),
        "--psm",
        str(psm),
        "-c",
        "tessedit_create_tsv=1",
    ]
    local_env = dict(env)
    local_env["OMP_THREAD_LIMIT"] = str(threads)
    local_env["TESSDATA_PREFIX"] = str(tessdata)
    proc = _run(argv, local_env, timeout)
    if proc.returncode != 0:
        raise HarnessError("INPUT_INVALID", f"tesseract failed: {_tail(proc.stderr)}")
    if len(proc.stdout) > CAP_TSV_BYTES:
        raise HarnessError("INPUT_INVALID", f"TSV exceeds cap {CAP_TSV_BYTES} bytes")
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HarnessError("INPUT_INVALID", f"TSV is not UTF-8: {error}") from error


def parse_tsv(text: str) -> list[dict[str, Any]]:
    rows = text.splitlines()
    if not rows or not rows[0].startswith("level\tpage_num\t"):
        raise HarnessError("INPUT_INVALID", "TSV header missing")
    words: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not row:
            continue
        fields = row.split("\t", 11)
        if len(fields) != 12:
            raise HarnessError("INPUT_INVALID", "TSV row does not have 12 fields")
        level, _page, block, par, line, word_num, left, top, width, height, conf, word = fields
        if level != "5":
            continue
        try:
            confidence = float(conf)
            box = (int(left), int(top), int(width), int(height))
        except ValueError as error:
            raise HarnessError("INPUT_INVALID", f"TSV numeric field invalid: {error}") from error
        if confidence < 0 or not word.strip():
            continue
        words.append(
            {
                "block": int(block),
                "par": int(par),
                "line": int(line),
                "word_num": int(word_num),
                "box": box,
                "conf": confidence,
                "text": word,
            }
        )
    if len(words) > CAP_WORDS:
        raise HarnessError("INPUT_INVALID", f"word count {len(words)} exceeds cap {CAP_WORDS}")
    return words


def build_lines(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    order: list[tuple[int, int, int]] = []
    for word in words:
        key = (word["block"], word["par"], word["line"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(word)
    lines: list[dict[str, Any]] = []
    for key in order:
        members = sorted(grouped[key], key=lambda w: w["word_num"])
        lefts = [w["box"][0] for w in members]
        tops = [w["box"][1] for w in members]
        rights = [w["box"][0] + w["box"][2] for w in members]
        bottoms = [w["box"][1] + w["box"][3] for w in members]
        lines.append(
            {
                "words": members,
                "bbox_px": (min(lefts), min(tops), max(rights), max(bottoms)),
                "text": " ".join(w["text"] for w in members),
                "confidence": round(sum(w["conf"] for w in members) / len(members), 2),
            }
        )
    if len(lines) > CAP_LINES:
        raise HarnessError("INPUT_INVALID", f"line count {len(lines)} exceeds cap {CAP_LINES}")
    return lines


_EDGE_PUNCTUATION = ".,;:!?()[]{}<>\"'`*_|/\\"


def normalized_tokens(line: dict[str, Any], floor: float = TOKEN_CONFIDENCE_FLOOR) -> Counter[str]:
    """Casefolded word multiset, edges stripped, internal punctuation kept."""
    tokens: Counter[str] = Counter()
    for word in line["words"]:
        if word["conf"] < floor:
            continue
        for raw in word["text"].split():
            token = raw.casefold().strip(_EDGE_PUNCTUATION)
            token = "".join(ch for ch in token if ch.isprintable())
            if token and (token[0].isalnum() or token[0] in "$€£¥"):
                tokens[token] += 1
    return tokens


def agreement_for(
    primary: list[dict[str, Any]], secondary: list[dict[str, Any]]
) -> tuple[float | None, list[float | None], list[float | None]]:
    """Match lines by token overlap; return page agreement and per-line values.

    Agreement for a pair is |A ∩ B| / max(|A|, |B|) over the normalized
    multiset of tokens with confidence >= 70 in the pass each came from.
    A matched pair is therefore made only of tokens confident in both passes.
    """
    primary_tokens = [normalized_tokens(line) for line in primary]
    secondary_tokens = [normalized_tokens(line) for line in secondary]
    total_primary = sum(sum(c.values()) for c in primary_tokens)
    total_secondary = sum(sum(c.values()) for c in secondary_tokens)
    if total_primary == 0 and total_secondary == 0:
        return None, [None] * len(primary), [None] * len(primary)

    used: set[int] = set()
    line_agreement: list[float | None] = []
    secondary_confidence: list[float | None] = []
    matched_tokens = 0
    for index, counts in enumerate(primary_tokens):
        best_index: int | None = None
        best_score = 0.0
        best_shared = 0
        for candidate, other in enumerate(secondary_tokens):
            if candidate in used:
                continue
            denominator = max(sum(counts.values()), sum(other.values()))
            shared = sum((counts & other).values())
            score = shared / denominator if denominator else 0.0
            if score > best_score:
                best_score = score
                best_index = candidate
                best_shared = shared
        if best_index is None or best_score <= 0.0:
            line_agreement.append(0.0)
            secondary_confidence.append(None)
            continue
        used.add(best_index)
        matched_tokens += best_shared
        line_agreement.append(round(best_score, 4))
        secondary_confidence.append(secondary[best_index]["confidence"])

    denominator = max(total_primary, total_secondary)
    page_agreement = round(matched_tokens / denominator, 4) if denominator else None
    return page_agreement, line_agreement, secondary_confidence


def band_for(mean: float | None, low_share: float | None, agreement: float | None) -> str:
    if mean is None or low_share is None or agreement is None:
        return "below_threshold"
    if (
        mean >= BAND_ADEQUATE_MEAN
        and low_share <= BAND_ADEQUATE_LOW_SHARE
        and agreement >= BAND_ADEQUATE_AGREEMENT
    ):
        return "adequate"
    if mean >= BAND_UNCERTAIN_MEAN and agreement >= BAND_UNCERTAIN_AGREEMENT:
        return "uncertain"
    return "below_threshold"


def confidence_stats(lines: list[dict[str, Any]]) -> dict[str, Any]:
    confidences = [w["conf"] for line in lines for w in line["words"]]
    if not confidences:
        return {
            "mean": None,
            "minLine": None,
            "lowConfidenceShare": None,
            "lineCount": len(lines),
            "wordCount": 0,
        }
    low = sum(1 for value in confidences if value < LOW_CONFIDENCE) / len(confidences)
    return {
        "mean": round(sum(confidences) / len(confidences), 2),
        "minLine": min(line["confidence"] for line in lines),
        "lowConfidenceShare": round(low, 4),
        "lineCount": len(lines),
        "wordCount": len(confidences),
    }


def measure(
    pdf: Path,
    page: int,
    box_pt: tuple[float, float, float, float],
    args: argparse.Namespace,
    engine: Path,
    tessdata: Path,
    env: dict[str, str],
    outdir: Path,
    psm: int,
    oem: int,
    threads: int,
    scope_is_page: bool,
) -> dict[str, Any]:
    start = time.perf_counter()
    primary_png, width, height = (
        render_page(pdf, page, args.dpi, outdir, env, args.timeout, args.max_pixels)
        if scope_is_page
        else render_crop(pdf, page, args.dpi, box_pt, outdir, env, args.timeout, args.max_region_pixels)
    )
    secondary_png, second_width, second_height = (
        render_page(pdf, page, args.second_dpi, outdir, env, args.timeout, args.max_pixels)
        if scope_is_page
        else render_crop(
            pdf, page, args.second_dpi, box_pt, outdir, env, args.timeout, args.max_region_pixels
        )
    )
    render_ms = (time.perf_counter() - start) * 1000.0

    ocr_start = time.perf_counter()
    primary_tsv = ocr_tsv(
        engine, tessdata, args.lang, primary_png, psm, oem, threads, env, args.timeout
    )
    secondary_tsv = ocr_tsv(
        engine, tessdata, args.lang, secondary_png, psm, oem, threads, env, args.timeout
    )
    ocr_ms = (time.perf_counter() - ocr_start) * 1000.0

    primary_lines = build_lines(parse_tsv(primary_tsv))
    secondary_lines = build_lines(parse_tsv(secondary_tsv))
    agreement, per_line, second_confidence = agreement_for(primary_lines, secondary_lines)
    stats = confidence_stats(primary_lines)

    scale = 72.0 / args.dpi
    origin_x, origin_y = (0.0, 0.0) if scope_is_page else (box_pt[0], box_pt[1])
    lines: list[dict[str, Any]] = []
    for index, line in enumerate(primary_lines, start=1):
        left, top, right, bottom = line["bbox_px"]
        lines.append(
            {
                "index": index,
                "bboxPt": [
                    round(origin_x + left * scale, 2),
                    round(origin_y + top * scale, 2),
                    round(origin_x + right * scale, 2),
                    round(origin_y + bottom * scale, 2),
                ],
                "bboxPx": [left, top, right, bottom],
                "confidence": line["confidence"],
                "agreement": per_line[index - 1],
                "secondPassConfidence": second_confidence[index - 1],
                "text": line["text"],
                "wordCount": len(line["words"]),
            }
        )

    return {
        "bboxPt": [round(value, 2) for value in box_pt],
        "bboxUnits": "pt",
        "raster": {
            "width": width,
            "height": height,
            "dpi": args.dpi,
            "secondPassWidth": second_width,
            "secondPassHeight": second_height,
            "secondPassDpi": args.second_dpi,
            "colorspace": "gray",
        },
        "cropSha256": sha256_file(primary_png),
        "cropSha256SecondPass": sha256_file(secondary_png),
        "tsvSha256": sha256_bytes(primary_tsv.encode("utf-8")),
        "tsvSha256SecondPass": sha256_bytes(secondary_tsv.encode("utf-8")),
        "confidence": {
            "mean": stats["mean"],
            "minLine": stats["minLine"],
            "lowConfidenceShare": stats["lowConfidenceShare"],
        },
        "agreement": agreement,
        "band": band_for(stats["mean"], stats["lowConfidenceShare"], agreement),
        "lineCount": stats["lineCount"],
        "wordCount": stats["wordCount"],
        "lines": lines,
        "_timing": {"renderMs": round(render_ms, 1), "ocrMs": round(ocr_ms, 1)},
    }


def _parse_xml_images(
    text: str, page: int
) -> tuple[list[tuple[float, float, float, float]], float, float] | None:
    page_match = re.search(rf'<page number="{page}"([^>]*)>', text)
    if page_match is None:
        return None
    attributes = dict(re.findall(r'(\w+)="([^"]*)"', page_match.group(1)))
    try:
        xml_width = float(attributes["width"])
        xml_height = float(attributes["height"])
    except (KeyError, ValueError) as error:
        raise HarnessError("SOURCE_UNREADABLE", "pdftohtml page box is malformed") from error
    images: list[tuple[float, float, float, float]] = []
    for element in re.findall(r"<image\b([^>]*)/?>", text):
        values = dict(re.findall(r'(\w+)="([^"]*)"', element))
        try:
            left = float(values["left"])
            top = float(values["top"])
            width = float(values["width"])
            height = float(values["height"])
        except (KeyError, ValueError):
            continue
        images.append((left, top, width, height))
    return images, xml_width, xml_height


def xml_regions(
    pdf: Path,
    page: int,
    page_width_pt: float,
    env: dict[str, str],
    timeout: float,
    workdir: Path,
) -> list[tuple[float, float, float, float]]:
    # pdftohtml writes extracted page images next to the path it is given, even
    # with -stdout; that path must therefore live in the scratch directory.
    # A symlink keeps the copy cheap and confines the side file.
    link = workdir / "pdftohtml-source.pdf"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(pdf)
    proc = _run(
        ["/usr/bin/pdftohtml", "-xml", "-stdout", "-q", "-f", str(page), "-l", str(page), str(link)],
        env,
        timeout,
        cwd=workdir,
    )
    if proc.returncode != 0:
        raise HarnessError("SOURCE_UNREADABLE", f"pdftohtml failed: {_tail(proc.stderr)}")
    text = proc.stdout.decode("utf-8", "replace")
    parsed = _parse_xml_images(text, page)
    if not parsed:
        return []
    images, xml_width, _xml_height = parsed
    if xml_width <= 0:
        raise HarnessError("SOURCE_UNREADABLE", "pdftohtml reported a zero page width")
    # pdftohtml emits its own unit; derive the conversion from the page width so
    # no fixed 1.5 factor is assumed.
    units_per_pt = xml_width / page_width_pt
    boxes: list[tuple[float, float, float, float]] = []
    for left, top, width, height in images:
        boxes.append(
            (
                left / units_per_pt,
                top / units_per_pt,
                (left + width) / units_per_pt,
                (top + height) / units_per_pt,
            )
        )
    return boxes


DEV_ENGINE = ROOT / "tools/ocr/tesseract"
DEV_TESSDATA = ROOT / "vendor/ocr/tessdata"
SYSTEM_TESSDATA_CANDIDATES = (
    Path("/usr/share/tesseract/tessdata"),
    Path("/usr/share/tessdata"),
    Path("/usr/local/share/tessdata"),
)
SYSTEM_PACKAGE = (
    "Fedora: sudo dnf install tesseract tesseract-langpack-eng "
    "[tesseract-langpack-vie]"
)


def _setup_message(detail: str) -> str:
    dev = ""
    if DEV_ENGINE.is_file():
        dev = (
            " A development copy exists at tools/ocr/tesseract but is disabled;"
            " set BOOKIFY_OCR_ALLOW_DEV=1 in development only."
        )
    return (
        f"OCR_ENGINE_MISSING: {detail} Release uses the system Tesseract package. "
        f"{SYSTEM_PACKAGE}. Install tesseract-langpack-eng; add "
        "tesseract-langpack-vie only when Vietnamese OCR is enabled. "
        "The OCR harness is intake-only: bookify build and bookify verify never "
        "need OCR." + dev
    )


def resolve_engine(args: argparse.Namespace) -> tuple[Path, str]:
    """Resolve the CLI in release order, with the dev copy behind an opt-in gate.

    1. --tesseract
    2. $BOOKIFY_TESSERACT
    3. tesseract on PATH
    4. tools/ocr/tesseract, only with BOOKIFY_OCR_ALLOW_DEV=1
    """
    if args.tesseract:
        candidate = Path(args.tesseract).expanduser()
        if not candidate.is_file():
            raise HarnessError("INPUT_INVALID", _setup_message(f"--tesseract is not a file: {candidate}"))
        return candidate.resolve(), "explicit"

    from_env = os.environ.get("BOOKIFY_TESSERACT")
    if from_env:
        candidate = Path(from_env).expanduser()
        if not candidate.is_file():
            raise HarnessError(
                "INPUT_INVALID",
                _setup_message(f"$BOOKIFY_TESSERACT is not a file: {candidate}"),
            )
        return candidate.resolve(), "environment"

    on_path = shutil.which("tesseract")
    if on_path:
        return Path(on_path).resolve(), "path"

    allow_dev = os.environ.get("BOOKIFY_OCR_ALLOW_DEV") == "1"
    if DEV_ENGINE.is_file() and allow_dev:
        return DEV_ENGINE.resolve(), "development-copy"

    raise HarnessError("INPUT_INVALID", _setup_message("no Tesseract CLI found."))


def resolve_tessdata(args: argparse.Namespace, engine: Path) -> tuple[Path, str]:
    if args.tessdata:
        candidate = Path(args.tessdata).expanduser().resolve()
        if not candidate.is_dir():
            raise HarnessError(
                "INPUT_INVALID",
                f"OCR_DATA_MISSING: tessdata directory not found: {candidate}. "
                "Fedora: sudo dnf install tesseract-langpack-eng [tesseract-langpack-vie]",
            )
        if candidate == DEV_TESSDATA.resolve():
            location = "vendored"
        elif any(candidate == path.resolve() for path in SYSTEM_TESSDATA_CANDIDATES):
            location = "system"
        else:
            location = "explicit"
        return candidate, location

    if engine == DEV_ENGINE.resolve() and DEV_TESSDATA.is_dir():
        return DEV_TESSDATA.resolve(), "vendored"

    for candidate in SYSTEM_TESSDATA_CANDIDATES:
        if (candidate / "eng.traineddata").is_file():
            return candidate.resolve(), "system"

    raise HarnessError(
        "INPUT_INVALID",
        "OCR_DATA_MISSING: no system eng.traineddata found. "
        "Fedora: sudo dnf install tesseract-langpack-eng "
        "[tesseract-langpack-vie]. The OCR harness is intake-only; "
        "bookify build and bookify verify never need OCR.",
    )


def verify_engine(
    args: argparse.Namespace,
) -> tuple[Path, Path, dict[str, Any], dict[str, str], dict[str, Any]]:
    engine, source = resolve_engine(args)
    tessdata, tessdata_location = resolve_tessdata(args, engine)

    lock_path = Path(args.lock).resolve()
    if not lock_path.is_file():
        raise HarnessError("INPUT_INVALID", f"lock fragment not found: {lock_path}")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError("INPUT_INVALID", f"lock fragment unreadable: {error}") from error
    ocr = lock.get("ocr")
    if not isinstance(ocr, dict):
        raise HarnessError("INPUT_INVALID", "lock fragment has no ocr entry")

    development_only = engine == DEV_ENGINE.resolve()
    if development_only:
        print(
            "WARNING development-only engine: "
            f"{engine} (never ship; release uses the system package)",
            file=sys.stderr,
        )
    if args.require_system and development_only:
        raise HarnessError(
            "INPUT_INVALID",
            "OCR_ENGINE_MISSING: --require-system refuses the development copy. "
            f"{SYSTEM_PACKAGE}",
        )

    actual_binary = sha256_file(engine)
    if development_only and actual_binary != ocr.get("binarySha256"):
        raise HarnessError(
            "INPUT_INVALID",
            "OCR_PIN_MISMATCH: development engine binary sha256 does not match "
            "the lock fragment",
        )

    options = ocr["engineOptions"]
    resolved = {
        "oem": options["oem"] if args.oem is None else args.oem,
        "pagePsm": options["pagePsm"] if args.psm is None else args.psm,
        "regionPsm": options["regionPsm"] if args.region_psm is None else args.region_psm,
        "threads": options["threads"],
    }
    env = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "OMP_THREAD_LIMIT": str(resolved["threads"]),
    }
    with tempfile.TemporaryDirectory(prefix="ocr-verify-") as holder:
        probe_env = dict(env)
        probe_env["HOME"] = holder
        probe_env["TMPDIR"] = holder
        version = _run([str(engine), "--version"], probe_env, args.timeout)
    if version.returncode != 0:
        raise HarnessError("INPUT_INVALID", f"engine --version failed: {_tail(version.stderr)}")
    version_text = version.stdout.decode("utf-8", "replace")
    first = version_text.splitlines()[0] if version_text else ""
    match = re.search(r"tesseract\s+(\S+)", first)
    if match is None or match.group(1) != ocr.get("version"):
        found = match.group(1) if match else "unknown"
        raise HarnessError(
            "INPUT_INVALID",
            f"OCR_PIN_MISMATCH: engine version {found} != pinned {ocr.get('version')}; "
            "re-pin engine, library and data together",
        )
    leptonica = re.search(r"leptonica-([\d.]+)", version_text)
    if leptonica is None or leptonica.group(1) != ocr["leptonica"]["version"]:
        found = leptonica.group(1) if leptonica else "unknown"
        raise HarnessError(
            "INPUT_INVALID",
            f"OCR_PIN_MISMATCH: leptonica {found} != pinned "
            f"{ocr['leptonica']['version']}",
        )

    library = ocr["library"]
    library_path = _find_soname(library["soname"])
    if library_path is None:
        raise HarnessError("INPUT_INVALID", f"OCR_PIN_MISMATCH: library not found: {library['soname']}")
    if sha256_file(library_path) != library["sha256"]:
        raise HarnessError("INPUT_INVALID", "OCR_PIN_MISMATCH: libtesseract sha256 does not match the lock")
    leptonica_lib = ocr["leptonica"]
    leptonica_path = _find_soname(leptonica_lib["soname"])
    if leptonica_path is None:
        raise HarnessError("INPUT_INVALID", f"OCR_PIN_MISMATCH: library not found: {leptonica_lib['soname']}")
    if sha256_file(leptonica_path) != leptonica_lib["sha256"]:
        raise HarnessError("INPUT_INVALID", "OCR_PIN_MISMATCH: libleptonica sha256 does not match the lock")

    requested = args.lang.split("+")
    pinned = {entry["lang"]: entry for entry in ocr["languages"]}
    data: list[dict[str, str]] = []
    for lang in requested:
        entry = pinned.get(lang)
        if entry is None:
            raise HarnessError("INPUT_INVALID", f"language not pinned: {lang}")
        path = tessdata / f"{lang}.traineddata"
        if not path.is_file():
            raise HarnessError(
                "INPUT_INVALID",
                f"OCR_DATA_MISSING: {lang}.traineddata not found in {tessdata}",
            )
        if sha256_file(path) != entry["sha256"]:
            raise HarnessError("INPUT_INVALID", f"OCR_PIN_MISMATCH: traineddata sha256 mismatch: {lang}")
        data.append(
            {
                "lang": lang,
                "file": f"{lang}.traineddata",
                "location": tessdata_location,
                "sha256": entry["sha256"],
            }
        )

    engine_info = {
        "name": ocr["engine"],
        "version": ocr["version"],
        "source": source,
        "developmentOnly": development_only,
        "binary": "tesseract",
        "binarySha256": actual_binary,
        "oem": resolved["oem"],
        "psm": resolved["pagePsm"],
        "threads": resolved["threads"],
        "library": {
            "name": library["name"],
            "version": library["version"],
            "sha256": library["sha256"],
        },
        "leptonica": {
            "version": leptonica_lib["version"],
            "sha256": leptonica_lib["sha256"],
        },
        "data": data,
    }
    return engine, tessdata, engine_info, env, resolved


def _find_soname(soname: str) -> Path | None:
    directories = ["/usr/lib64", "/lib64", "/usr/lib", "/lib"]
    extra = os.environ.get("LD_LIBRARY_PATH", "")
    directories.extend(part for part in extra.split(":") if part)
    for directory in directories:
        candidate = Path(directory) / soname
        if candidate.exists():
            return candidate.resolve()
    return None


def sandbox_reexec(args: argparse.Namespace) -> None:
    """Re-run this harness inside a network-less bwrap namespace.

    The root is read-only; only /tmp and the directory holding --out are
    writable. This is the proof harness, not the product guard: it exists so
    the offline claim is enforced by the kernel, not by inspection.
    """
    bwrap = Path("/usr/bin/bwrap")
    if not bwrap.is_file():
        raise HarnessError("BUILD_FAILED", "bwrap is required for --sandbox but is missing")
    rest = [token for token in sys.argv[1:] if token != "--sandbox"]
    argv = [
        str(bwrap),
        "--unshare-net",
        "--die-with-parent",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/run",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
    ]
    if args.out:
        outdir = Path(args.out).resolve().parent
        if outdir == Path("/tmp") or Path("/tmp") in outdir.parents:
            raise HarnessError(
                "INPUT_INVALID",
                "--sandbox needs --out outside /tmp; the namespace mounts a fresh /tmp",
            )
        outdir.mkdir(parents=True, exist_ok=True)
        argv.extend(["--bind", str(outdir), str(outdir)])
    argv.extend(["--chdir", str(Path.cwd()), "--", sys.executable, str(Path(__file__).resolve())])
    argv.extend(rest)
    os.execv(str(bwrap), argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bookify v2 OCR capability probe")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--page", required=True, type=int)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--second-dpi", type=int, default=450)
    parser.add_argument("--lang", default="eng")
    parser.add_argument(
        "--tesseract",
        "--engine",
        dest="tesseract",
        type=Path,
        help="explicit Tesseract CLI; --engine is a compatibility alias",
    )
    parser.add_argument(
        "--tessdata",
        type=Path,
        help="explicit tessdata directory; default is the system directory "
        "(or the vendored development data when the development copy is used)",
    )
    parser.add_argument("--lock", default=str(ROOT / "tools/ocr/ocr.lock.fragment.json"))
    parser.add_argument("--oem", type=int)
    parser.add_argument("--psm", type=int)
    parser.add_argument("--region-psm", type=int)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-pixels", type=int, default=CAP_PAGE_PIXELS)
    parser.add_argument("--max-region-pixels", type=int, default=CAP_REGION_PIXELS)
    parser.add_argument("--min-region-area", type=float, default=12000.0)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--regions", action="store_true")
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument(
        "--require-system",
        action="store_true",
        help="refuse the development copy; use in release checks",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.sandbox:
            sandbox_reexec(args)
        pdf = args.pdf.resolve()
        if not pdf.is_file():
            raise HarnessError("SOURCE_UNREADABLE", f"pdf not found: {args.pdf}")
        if pdf.stat().st_size > CAP_PDF_BYTES:
            raise HarnessError("INPUT_INVALID", f"pdf exceeds cap {CAP_PDF_BYTES} bytes")
        engine, tessdata, engine_info, env, resolved = verify_engine(args)
        page_count, page_width, page_height = pdf_info(pdf, args.page, env, args.timeout)
        pdf_hash = sha256_file(pdf)

        with tempfile.TemporaryDirectory(prefix="bookify-ocr-") as holder:
            outdir = Path(holder)
            env["HOME"] = holder
            env["TMPDIR"] = holder

            if not args.regions:
                region = measure(
                    pdf,
                    args.page,
                    (0.0, 0.0, page_width, page_height),
                    args,
                    engine,
                    tessdata,
                    env,
                    outdir,
                    resolved["pagePsm"],
                    resolved["oem"],
                    resolved["threads"],
                    scope_is_page=True,
                )
                engine_info["psm"] = resolved["pagePsm"]
                scope = "page"
                regions = [region]
            else:
                boxes = xml_regions(pdf, args.page, page_width, env, args.timeout, outdir)
                boxes = [
                    box
                    for box in boxes
                    if (box[2] - box[0]) * (box[3] - box[1]) >= args.min_region_area
                ]
                boxes.sort(key=lambda box: (round(box[1], 3), round(box[0], 3)))
                if len(boxes) > CAP_REGIONS_PER_PAGE:
                    raise HarnessError(
                        "INPUT_INVALID",
                        f"region count {len(boxes)} exceeds cap {CAP_REGIONS_PER_PAGE}",
                    )
                engine_info["psm"] = resolved["regionPsm"]
                scope = "images"
                regions = []
                for index, box in enumerate(boxes, start=1):
                    region = measure(
                        pdf,
                        args.page,
                        box,
                        args,
                        engine,
                        tessdata,
                        env,
                        outdir,
                        resolved["regionPsm"],
                        resolved["oem"],
                        resolved["threads"],
                        scope_is_page=False,
                    )
                    region["index"] = index
                    regions.append(region)

        for region in regions:
            timing = region.pop("_timing", {"renderMs": 0.0, "ocrMs": 0.0})
            region["index"] = region.get("index", 1)
            if scope == "page":
                region["index"] = 1
            timing_text = f"render={timing['renderMs']}ms ocr={timing['ocrMs']}ms"
            print(
                f"timing page={args.page} region={region['index']} {timing_text}",
                file=sys.stderr,
            )

        confidences = [region["confidence"]["mean"] for region in regions if region["confidence"]["mean"] is not None]
        agreements = [region["agreement"] for region in regions if region["agreement"] is not None]
        words = sum(region["wordCount"] for region in regions)
        lines = sum(region["lineCount"] for region in regions)
        page_mean = round(sum(confidences) / len(confidences), 2) if confidences else None
        page_agreement = round(sum(agreements) / len(agreements), 4) if agreements else None
        low_values = [
            region["confidence"]["lowConfidenceShare"]
            for region in regions
            if region["confidence"]["lowConfidenceShare"] is not None
        ]
        page_low = round(sum(low_values) / len(low_values), 4) if low_values else None
        page_min = min(
            (region["confidence"]["minLine"] for region in regions if region["confidence"]["minLine"] is not None),
            default=None,
        )

        document = {
            "schemaVersion": SCHEMA_VERSION,
            "kind": "bookify-ocr-probe",
            "toolVersion": TOOL_VERSION,
            "scope": scope,
            "pdf": {
                "page": args.page,
                "pageCount": page_count,
                "sha256": pdf_hash,
                "pageSizePt": [round(page_width, 2), round(page_height, 2)],
            },
            "engine": engine_info,
            "raster": {
                "dpi": args.dpi,
                "secondPassDpi": args.second_dpi,
                "colorspace": "gray",
            },
            "confidence": {
                "mean": page_mean,
                "minLine": page_min,
                "lowConfidenceShare": page_low,
                "lineCount": lines,
                "wordCount": words,
            },
            "agreement": page_agreement,
            "band": band_for(page_mean, page_low, page_agreement),
            "regions": regions,
        }
        payload = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(payload.encode("utf-8"))
        else:
            sys.stdout.buffer.write(payload.encode("utf-8"))
        return 0
    except HarnessError as error:
        print(f"ERROR {error.code} {error.message}", file=sys.stderr)
        return EXIT_CODES[error.code]


if __name__ == "__main__":
    raise SystemExit(main())
