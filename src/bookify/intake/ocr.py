"""Offline OCR intake for image-borne source text.

OCR runs only from ``bookify intake``. Publishing never imports this module;
``bookify build`` and ``bookify verify`` stay OCR-free (SPEC-bookify-v2 §3.1,
§6.8, §7.5).

The release engine is the system Tesseract CLI (Fedora package), exactly like
Poppler. The extracted development copy under ``tools/ocr`` is never used unless
``BOOKIFY_OCR_ALLOW_DEV=1`` is set. Every measurement is produced with list
argv, a fixed environment, one thread and a per-subprocess timeout; nothing is
interpolated through a shell.

The output is evidence, not truth. A page or line is only ``adequate`` when the
300 dpi and 450 dpi reads agree on the normalised token multiset, the mean word
confidence is high and very few words fall below the low-confidence floor.
Agreement corroborates a read; it does not prove correctness (two passes can
agree on the same misread).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from bookify.errors import BookifyError
from bookify.intake import sandbox
from bookify.intake.caps import (
    CAP_LINES,
    CAP_PAGE_PIXELS,
    CAP_PDF_BYTES,
    CAP_REGIONS_PER_PAGE,
    CAP_REGION_PIXELS,
    CAP_TSV_BYTES,
    CAP_WORDS,
)

BAND_ADEQUATE_MEAN = 90.0
BAND_ADEQUATE_LOW_SHARE = 0.05
BAND_ADEQUATE_AGREEMENT = 0.98
BAND_UNCERTAIN_MEAN = 80.0
BAND_UNCERTAIN_AGREEMENT = 0.90
TOKEN_CONFIDENCE_FLOOR = 70.0
LOW_CONFIDENCE = 60.0

DEFAULT_MIN_TEXT_CHARS = 40
DEFAULT_MIN_REGION_AREA_PT2 = 12_000.0
DEFAULT_TIMEOUT = 60.0
DEFAULT_PAGE_TIMEOUT = 120.0
DEFAULT_SOURCE_TIMEOUT = 30 * 60.0

OCR_STATUSES = ("applied", "uncertain", "below_threshold", "not_required", "skipped", "failed")
SUPPORTED_LANGUAGES = ("eng", "vie")
CANONICAL_NOTE = "Reconstructed from an image by OCR; values are machine-read and unverified."

_EDGE_PUNCTUATION = ".,;:!?()[]{}<>\"'`*_|/\\"
_SETUP_PACKAGE = (
    "Fedora: sudo dnf install tesseract tesseract-langpack-eng "
    "[tesseract-langpack-vie]"
)


@dataclass(frozen=True)
class OcrOptions:
    """Everything intake may vary; the rest is pinned in the lock."""

    enabled: bool = True
    lang: str = "eng"
    offline: bool = True
    allow_unsandboxed: bool = False
    keep_raster: bool = False
    require_system: bool = False
    tesseract: Path | None = None
    tessdata: Path | None = None
    lock_path: Path | None = None
    timeout: float = DEFAULT_TIMEOUT
    page_timeout: float = DEFAULT_PAGE_TIMEOUT
    source_timeout: float = DEFAULT_SOURCE_TIMEOUT
    min_text_chars: int = DEFAULT_MIN_TEXT_CHARS
    min_region_area_pt2: float = DEFAULT_MIN_REGION_AREA_PT2


@dataclass(frozen=True)
class EngineIdentity:
    name: str
    version: str
    source: str
    development_only: bool
    binary: str
    binary_sha256: str
    oem: int
    page_psm: int
    region_psm: int
    threads: int
    library: dict[str, Any]
    leptonica: dict[str, Any]
    data: tuple[dict[str, Any], ...]
    raster: dict[str, Any]
    trigger: dict[str, Any]
    pin_sha256: str

    def manifest(self) -> dict[str, Any]:
        """The engine block of a page OCR record (no paths, no timings)."""
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "developmentOnly": self.development_only,
            "binary": self.binary,
            "binarySha256": self.binary_sha256,
            "oem": self.oem,
            "pagePsm": self.page_psm,
            "regionPsm": self.region_psm,
            "threads": self.threads,
            "library": self.library,
            "leptonica": self.leptonica,
            "models": [
                {"lang": entry["lang"], "sha256": entry["sha256"]}
                for entry in self.data
            ],
            "data": list(self.data),
        }


@dataclass(frozen=True)
class ResolvedEngine:
    path: Path
    tessdata: Path
    identity: EngineIdentity
    env: dict[str, str]


@dataclass
class RegionMeasure:
    """One measured region, before it becomes a manifest object."""

    index: int
    bbox: tuple[float, float, float, float]
    width: int
    height: int
    second_width: int
    second_height: int
    crop_sha256: str
    crop_sha256_second: str
    tsv: bytes
    tsv_second: bytes
    lines: list[dict[str, Any]]
    confidence: dict[str, Any]
    agreement: float | None
    band: str
    line_count: int
    word_count: int
    eligible_line_count: int
    reason: str | None = None
    second_failed: bool = False
    duplicate_of: int | None = None
    raster_path: Path | None = None
    dpi: int = 300
    second_dpi: int = 450
    colorspace: str = "gray"
    timing: dict[str, float] = field(default_factory=dict)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _tail(data: bytes, limit: int = 400) -> str:
    text = data.decode("utf-8", "replace").strip().replace("\n", " ")
    return text[-limit:]


def _round(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)


# ---------------------------------------------------------------------------
# Engine resolution and pin verification
# ---------------------------------------------------------------------------


def _engine_root() -> Path:
    from bookify import runtime

    return runtime.engine_root()


def _dev_engine() -> Path:
    return _engine_root() / "tools" / "ocr" / "tesseract"


def _dev_tessdata() -> Path:
    return _engine_root() / "vendor" / "ocr" / "tessdata"


def _system_tessdata_candidates() -> tuple[Path, ...]:
    return (
        Path("/usr/share/tesseract/tessdata"),
        Path("/usr/share/tessdata"),
        Path("/usr/local/share/tessdata"),
    )


def _setup_message(detail: str) -> str:
    dev = ""
    dev_path = _dev_engine()
    if dev_path.is_file():
        dev = (
            " A development copy exists at tools/ocr/tesseract but is disabled;"
            " set BOOKIFY_OCR_ALLOW_DEV=1 in development only."
        )
    return (
        f"OCR_ENGINE_MISSING: {detail} Release uses the system Tesseract package. "
        f"{_SETUP_PACKAGE}. Install tesseract-langpack-eng; add "
        "tesseract-langpack-vie only when Vietnamese OCR is enabled. "
        "OCR runs at intake only: bookify build and bookify verify never need OCR."
        + dev
    )


def _allow_dev() -> bool:
    return os.environ.get("BOOKIFY_OCR_ALLOW_DEV") == "1"


def _resolve_engine(options: OcrOptions) -> tuple[Path, str]:
    """Resolve the CLI in release order, with the dev copy behind an opt-in gate."""
    candidates: list[tuple[Path, str]] = []
    if options.tesseract is not None:
        candidates.append((Path(options.tesseract).expanduser(), "explicit"))
    from_env = os.environ.get("BOOKIFY_TESSERACT")
    if from_env:
        candidates.append((Path(from_env).expanduser(), "environment"))
    on_path = shutil.which("tesseract")
    if on_path:
        candidates.append((Path(on_path), "path"))
    dev = _dev_engine()
    if dev.is_file():
        candidates.append((dev, "development-copy"))

    for candidate, source in candidates:
        if not candidate.is_file():
            if source in {"explicit", "environment"}:
                raise BookifyError(
                    "INPUT_INVALID",
                    _setup_message(f"{source} Tesseract path is not a file: {candidate}"),
                    "ocr",
                )
            continue
        resolved = candidate.resolve()
        development = resolved == dev.resolve()
        if development and (not _allow_dev() or options.require_system):
            raise BookifyError(
                "INPUT_INVALID",
                _setup_message(
                    "--require-system refuses the development copy."
                    if options.require_system
                    else "the development copy is disabled."
                ),
                "ocr",
            )
        return resolved, source
    raise BookifyError("INPUT_INVALID", _setup_message("no Tesseract CLI found."), "ocr")


def _resolve_tessdata(options: OcrOptions, engine: Path) -> tuple[Path, str]:
    if options.tessdata is not None:
        candidate = Path(options.tessdata).expanduser().resolve()
        if not candidate.is_dir():
            raise BookifyError(
                "INPUT_INVALID",
                f"OCR_DATA_MISSING: tessdata directory not found: {candidate}. {_SETUP_PACKAGE}",
                "ocr",
            )
        return candidate, _tessdata_location(candidate)
    from_env = os.environ.get("BOOKIFY_TESSDATA")
    if from_env:
        candidate = Path(from_env).expanduser().resolve()
        if not candidate.is_dir():
            raise BookifyError(
                "INPUT_INVALID",
                f"OCR_DATA_MISSING: $BOOKIFY_TESSDATA is not a directory: {candidate}",
                "ocr",
            )
        return candidate, _tessdata_location(candidate)

    if engine == _dev_engine().resolve() and _dev_tessdata().is_dir():
        return _dev_tessdata().resolve(), "vendored"
    for candidate in _system_tessdata_candidates():
        if (candidate / "eng.traineddata").is_file():
            return candidate.resolve(), "system"
    raise BookifyError(
        "INPUT_INVALID",
        "OCR_DATA_MISSING: no eng.traineddata found. " + _SETUP_PACKAGE,
        "ocr",
    )


def _tessdata_location(path: Path) -> str:
    if path == _dev_tessdata().resolve():
        return "vendored"
    if any(path == candidate.resolve() for candidate in _system_tessdata_candidates()):
        return "system"
    return "explicit"


def _find_soname(soname: str) -> Path | None:
    directories = ["/usr/lib64", "/lib64", "/usr/lib", "/lib"]
    extra = os.environ.get("LD_LIBRARY_PATH", "")
    directories.extend(part for part in extra.split(":") if part)
    for directory in directories:
        candidate = Path(directory) / soname
        if candidate.exists():
            return candidate.resolve()
    return None


def _lock_ocr(options: OcrOptions) -> dict[str, Any]:
    """Read the OCR lock entry, preferring the merged toolchain lock."""
    candidates: list[Path] = []
    if options.lock_path is not None:
        candidates.append(Path(options.lock_path))
    else:
        root = _engine_root()
        candidates.extend(
            [
                root / "toolchain.lock.json",
                root / "tools" / "ocr" / "ocr.lock.fragment.json",
            ]
        )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BookifyError("INPUT_INVALID", f"OCR lock unreadable: {error}", str(path)) from error
        entry = data.get("ocr")
        if isinstance(entry, dict):
            return entry
    raise BookifyError(
        "INPUT_INVALID",
        "OCR_PIN_MISSING: no ocr entry in toolchain.lock.json or tools/ocr/ocr.lock.fragment.json",
        "ocr",
    )


def _tool_env(workdir: Path, tessdata: Path, threads: int) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "HOME": str(workdir),
        "TMPDIR": str(workdir),
        "OMP_THREAD_LIMIT": str(threads),
        "TESSDATA_PREFIX": str(tessdata),
    }


def resolve(options: OcrOptions | None = None) -> ResolvedEngine:
    """Resolve engine, data and pins; fail before any page is read or written."""
    options = options or OcrOptions()
    lock = _lock_ocr(options)
    engine_path, source = _resolve_engine(options)
    tessdata, _location = _resolve_tessdata(options, engine_path)
    development = engine_path == _dev_engine().resolve()

    actual_binary = _sha_file(engine_path)
    pinned_binary = lock.get("binarySha256")
    if development and isinstance(pinned_binary, str) and actual_binary != pinned_binary:
        raise BookifyError(
            "INPUT_INVALID",
            "OCR_PIN_MISMATCH: development engine binary sha256 does not match the lock",
            "ocr.binarySha256",
        )

    options_lock = lock.get("engineOptions", {})
    oem = int(options_lock.get("oem", 1))
    page_psm = int(options_lock.get("pagePsm", 3))
    region_psm = int(options_lock.get("regionPsm", 6))
    threads = int(options_lock.get("threads", 1))
    raster = dict(lock.get("raster", {"dpi": 300, "secondPassDpi": 450, "colorspace": "gray"}))
    trigger = dict(lock.get("trigger", {}))
    if options.min_text_chars != DEFAULT_MIN_TEXT_CHARS:
        trigger["minTextChars"] = options.min_text_chars
    if options.min_region_area_pt2 != DEFAULT_MIN_REGION_AREA_PT2:
        trigger["minRegionAreaPt2"] = options.min_region_area_pt2

    workdir = Path(os.environ.get("TMPDIR", "/tmp")) / "bookify-ocr-probe"
    workdir.mkdir(parents=True, exist_ok=True)
    env = _tool_env(workdir, tessdata, threads)
    version = _run([str(engine_path), "--version"], env, options.timeout, options.offline, allow_unsandboxed=options.allow_unsandboxed)
    if version.returncode != 0:
        raise BookifyError("INPUT_INVALID", f"engine --version failed: {_tail(version.stderr)}", "ocr")
    version_text = version.stdout.decode("utf-8", "replace")
    first = version_text.splitlines()[0] if version_text else ""
    match = re.search(r"tesseract\s+(\S+)", first)
    found_version = match.group(1) if match else "unknown"
    if found_version != lock.get("version"):
        raise BookifyError(
            "INPUT_INVALID",
            f"OCR_PIN_MISMATCH: engine version {found_version} != pinned {lock.get('version')}; "
            "re-pin engine, library and data together",
            "ocr.version",
        )
    leptonica = re.search(r"leptonica-([\d.]+)", version_text)
    leptonica_version = leptonica.group(1) if leptonica else "unknown"
    if leptonica_version != lock.get("leptonica", {}).get("version"):
        raise BookifyError(
            "INPUT_INVALID",
            f"OCR_PIN_MISMATCH: leptonica {leptonica_version} != pinned "
            f"{lock.get('leptonica', {}).get('version')}",
            "ocr.leptonica.version",
        )

    library = dict(lock.get("library", {}))
    leptonica_lib = dict(lock.get("leptonica", {}))
    for entry, label in ((library, "libtesseract"), (leptonica_lib, "libleptonica")):
        soname = entry.get("soname")
        if not soname:
            continue
        path = _find_soname(soname)
        if path is None:
            raise BookifyError("INPUT_INVALID", f"OCR_PIN_MISMATCH: library not found: {soname}", f"ocr.{label}")
        if _sha_file(path) != entry.get("sha256"):
            raise BookifyError(
                "INPUT_INVALID",
                f"OCR_PIN_MISMATCH: {label} sha256 does not match the lock",
                f"ocr.{label}.sha256",
            )

    requested = _parse_lang(options.lang)
    pinned = {entry["lang"]: entry for entry in lock.get("languages", [])}
    data: list[dict[str, Any]] = []
    for lang in requested:
        entry = pinned.get(lang)
        if entry is None:
            raise BookifyError("INPUT_INVALID", f"OCR language not pinned: {lang}", "ocr.languages")
        path = tessdata / f"{lang}.traineddata"
        if not path.is_file():
            raise BookifyError(
                "INPUT_INVALID",
                f"OCR_DATA_MISSING: {lang}.traineddata not found in {tessdata}",
                f"ocr.languages.{lang}",
            )
        digest = _sha_file(path)
        if digest != entry.get("sha256"):
            raise BookifyError(
                "INPUT_INVALID",
                f"OCR_PIN_MISMATCH: traineddata sha256 mismatch: {lang}",
                f"ocr.languages.{lang}.sha256",
            )
        data.append(
            {
                "lang": lang,
                "file": f"{lang}.traineddata",
                "location": _location_for(tessdata),
                "sha256": digest,
            }
        )

    identity = EngineIdentity(
        name=str(lock.get("engine", "tesseract")),
        version=str(lock.get("version")),
        source=source,
        development_only=development,
        binary="tesseract",
        binary_sha256=actual_binary,
        oem=oem,
        page_psm=page_psm,
        region_psm=region_psm,
        threads=threads,
        library={"name": library.get("name", "libtesseract"), "version": library.get("version"), "sha256": library.get("sha256")},
        leptonica={"version": leptonica_lib.get("version"), "sha256": leptonica_lib.get("sha256")},
        data=tuple(data),
        raster=raster,
        trigger=trigger,
        pin_sha256=_pin_sha256(
            lock,
            requested,
            raster,
            trigger,
            oem,
            page_psm,
            region_psm,
            threads,
            data,
            actual_binary,
            development,
        ),
    )
    return ResolvedEngine(path=engine_path, tessdata=tessdata, identity=identity, env=env)


def _location_for(tessdata: Path) -> str:
    return _tessdata_location(tessdata)


def _pin_sha256(
    lock: dict[str, Any],
    languages: list[str],
    raster: dict[str, Any],
    trigger: dict[str, Any],
    oem: int,
    page_psm: int,
    region_psm: int,
    threads: int,
    data: list[dict[str, Any]],
    binary_sha256: str,
    development_only: bool,
) -> str:
    """The whole OCR identity.

    The binary hash and its resolution source are part of the pin: two engines
    that report the same version but differ in bytes (a distro package versus a
    development copy, or two distro builds) are different pins, so
    ``--changed-only`` cannot reuse OCR text measured with another binary.
    """
    payload = {
        "engine": lock.get("engine"),
        "version": lock.get("version"),
        "binarySha256": binary_sha256,
        "developmentOnly": development_only,
        "library": lock.get("library", {}).get("sha256"),
        "leptonica": lock.get("leptonica", {}).get("sha256"),
        "languages": languages,
        "data": sorted((entry["lang"], entry["sha256"]) for entry in data),
        "raster": raster,
        "trigger": trigger,
        "oem": oem,
        "pagePsm": page_psm,
        "regionPsm": region_psm,
        "threads": threads,
    }
    return _sha_bytes(_canonical_json(payload).encode("utf-8"))


def pin_for(options: OcrOptions | None = None) -> str:
    """The pin hash without measuring pages; used by ``--changed-only``."""
    return resolve(options).identity.pin_sha256


def _parse_lang(value: str) -> list[str]:
    langs = [part.strip() for part in value.split("+") if part.strip()]
    if not langs:
        raise BookifyError("INPUT_INVALID", "OCR language list is empty", "ocr.lang")
    for lang in langs:
        if lang not in SUPPORTED_LANGUAGES:
            raise BookifyError(
                "INPUT_INVALID",
                f"OCR language not supported: {lang}. Latin-script eng and opt-in vie only; CJK is out of scope.",
                "ocr.lang",
            )
    return langs


# ---------------------------------------------------------------------------
# Process execution: list argv only, optional bwrap, fixed timeout
# ---------------------------------------------------------------------------


def _policy(env: dict[str, str], timeout: float, offline: bool, cwd: Path | None,
            allow_unsandboxed: bool = False) -> sandbox.SandboxPolicy:
    workdir = Path(env.get("TMPDIR") or (cwd or Path.cwd()))
    writable = tuple(path for path in (workdir, cwd) if path is not None)
    return sandbox.SandboxPolicy(
        offline=offline,
        timeout=timeout,
        env=env,
        workdir=workdir,
        writable_dirs=writable,
        allow_unsandboxed=allow_unsandboxed,
    )


def _run(
    argv: list[str],
    env: dict[str, str],
    timeout: float,
    offline: bool,
    cwd: Path | None = None,
    allow_unsandboxed: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    return sandbox.run(
        argv,
        _policy(env, timeout, offline, cwd, allow_unsandboxed),
        cwd=cwd,
        timeout=timeout,
        locator="ocr",
    )



# ---------------------------------------------------------------------------
# PDF geometry and rasterisation
# ---------------------------------------------------------------------------


def page_size(pdf: Path, page: int, env: dict[str, str], timeout: float, offline: bool, allow_unsandboxed: bool = False) -> tuple[float, float]:
    result = _run(["pdfinfo", "-f", str(page), "-l", str(page), str(pdf)], env, timeout, offline, allow_unsandboxed=allow_unsandboxed)
    if result.returncode != 0:
        raise BookifyError("SOURCE_UNREADABLE", f"pdfinfo failed: {_tail(result.stderr)}", f"ocr.page.{page}")
    text = result.stdout.decode("utf-8", "replace")
    size = re.search(
        rf"^Page\s+{page}\s+size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts",
        text,
        re.MULTILINE,
    )
    if size is None:
        size = re.search(r"^Page size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", text, re.MULTILINE)
    if size is None:
        raise BookifyError("SOURCE_UNREADABLE", f"pdfinfo did not report page {page} size", f"ocr.page.{page}")
    return float(size.group(1)), float(size.group(2))


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise BookifyError("SOURCE_UNREADABLE", f"not a PNG: {path.name}", str(path))
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _render_page(
    pdf: Path,
    page: int,
    dpi: int,
    outdir: Path,
    env: dict[str, str],
    timeout: float,
    offline: bool,
    max_pixels: int,
    allow_unsandboxed: bool = False,
) -> tuple[Path, int, int]:
    prefix = outdir / f"page-{page:03d}-{dpi}"
    argv = [
        "pdftoppm",
        "-f", str(page),
        "-l", str(page),
        "-r", str(dpi),
        "-gray",
        "-png",
        "-singlefile",
        str(pdf),
        str(prefix),
    ]
    result = _run(argv, env, timeout, offline, cwd=outdir, allow_unsandboxed=allow_unsandboxed)
    png = Path(f"{prefix}.png")
    if result.returncode != 0 or not png.is_file():
        raise BookifyError("SOURCE_UNREADABLE", f"pdftoppm failed: {_tail(result.stderr)}", f"ocr.page.{page}")
    width, height = png_size(png)
    if width * height > max_pixels:
        raise BookifyError(
            "INPUT_INVALID",
            f"page raster {width}x{height} exceeds cap {max_pixels} px",
            f"ocr.page.{page}",
        )
    return png, width, height


def _render_crop(
    pdf: Path,
    page: int,
    dpi: int,
    box: tuple[float, float, float, float],
    outdir: Path,
    env: dict[str, str],
    timeout: float,
    offline: bool,
    max_pixels: int,
    allow_unsandboxed: bool = False,
) -> tuple[Path, int, int]:
    left, top, right, bottom = box
    scale = dpi / 72.0
    x = max(0, round(left * scale))
    y = max(0, round(top * scale))
    width = max(1, round((right - left) * scale))
    height = max(1, round((bottom - top) * scale))
    if width * height > max_pixels:
        raise BookifyError(
            "INPUT_INVALID",
            f"region raster {width}x{height} exceeds cap {max_pixels} px",
            f"ocr.page.{page}",
        )
    prefix = outdir / f"crop-{page:03d}-{dpi}-{x}-{y}-{width}-{height}"
    argv = [
        "pdftoppm",
        "-f", str(page),
        "-l", str(page),
        "-r", str(dpi),
        "-x", str(x),
        "-y", str(y),
        "-W", str(width),
        "-H", str(height),
        "-gray",
        "-png",
        "-singlefile",
        str(pdf),
        str(prefix),
    ]
    result = _run(argv, env, timeout, offline, cwd=outdir, allow_unsandboxed=allow_unsandboxed)
    png = Path(f"{prefix}.png")
    if result.returncode != 0 or not png.is_file():
        raise BookifyError("SOURCE_UNREADABLE", f"pdftoppm crop failed: {_tail(result.stderr)}", f"ocr.page.{page}")
    real_width, real_height = png_size(png)
    return png, real_width, real_height


# ---------------------------------------------------------------------------
# Engine output: TSV parsing, lines, confidence and agreement
# ---------------------------------------------------------------------------


def _ocr_tsv(
    engine: Path,
    tessdata: Path,
    lang: str,
    image: Path,
    psm: int,
    oem: int,
    threads: int,
    env: dict[str, str],
    timeout: float,
    offline: bool,
    allow_unsandboxed: bool = False,
) -> bytes:
    argv = [
        str(engine),
        str(image),
        "stdout",
        "--tessdata-dir", str(tessdata),
        "-l", lang,
        "--oem", str(oem),
        "--psm", str(psm),
        "-c", "tessedit_create_tsv=1",
    ]
    local_env = dict(env)
    local_env["OMP_THREAD_LIMIT"] = str(threads)
    local_env["TESSDATA_PREFIX"] = str(tessdata)
    result = _run(argv, local_env, timeout, offline, allow_unsandboxed=allow_unsandboxed)
    if result.returncode != 0:
        raise BookifyError("INPUT_INVALID", f"tesseract failed: {_tail(result.stderr)}", "ocr.engine")
    if len(result.stdout) > CAP_TSV_BYTES:
        raise BookifyError("INPUT_INVALID", f"TSV exceeds cap {CAP_TSV_BYTES} bytes", "ocr.tsv")
    try:
        result.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BookifyError("INPUT_INVALID", f"TSV is not UTF-8: {error}", "ocr.tsv") from error
    return result.stdout


def parse_tsv(data: bytes) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BookifyError("INPUT_INVALID", f"TSV is not UTF-8: {error}", "ocr.tsv") from error
    rows = text.splitlines()
    if not rows or not rows[0].startswith("level\tpage_num\t"):
        raise BookifyError("INPUT_INVALID", "TSV header missing", "ocr.tsv")
    words: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not row:
            continue
        fields = row.split("\t", 11)
        if len(fields) != 12:
            raise BookifyError("INPUT_INVALID", "TSV row does not have 12 fields", "ocr.tsv")
        level, _page, block, par, line, word_num, left, top, width, height, conf, word = fields
        if level != "5":
            continue
        try:
            confidence = float(conf)
            box = (int(left), int(top), int(width), int(height))
        except ValueError as error:
            raise BookifyError("INPUT_INVALID", f"TSV numeric field invalid: {error}", "ocr.tsv") from error
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
        raise BookifyError("INPUT_INVALID", f"word count {len(words)} exceeds cap {CAP_WORDS}", "ocr.words")
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
        members = sorted(grouped[key], key=lambda word: word["word_num"])
        lefts = [word["box"][0] for word in members]
        tops = [word["box"][1] for word in members]
        rights = [word["box"][0] + word["box"][2] for word in members]
        bottoms = [word["box"][1] + word["box"][3] for word in members]
        lines.append(
            {
                "words": members,
                "bbox_px": (min(lefts), min(tops), max(rights), max(bottoms)),
                "text": " ".join(word["text"] for word in members),
                "confidence": round(sum(word["conf"] for word in members) / len(members), 2),
            }
        )
    if len(lines) > CAP_LINES:
        raise BookifyError("INPUT_INVALID", f"line count {len(lines)} exceeds cap {CAP_LINES}", "ocr.lines")
    return lines


def normalized_tokens(line: dict[str, Any], floor: float = TOKEN_CONFIDENCE_FLOOR) -> Counter[str]:
    tokens: Counter[str] = Counter()
    for word in line["words"]:
        if word["conf"] < floor:
            continue
        for raw in word["text"].split():
            token = raw.casefold().strip(_EDGE_PUNCTUATION)
            token = "".join(character for character in token if character.isprintable())
            if token and (token[0].isalnum() or token[0] in "$€£¥"):
                tokens[token] += 1
    return tokens


def agreement_for(
    primary: list[dict[str, Any]], secondary: list[dict[str, Any]]
) -> tuple[float | None, list[float | None], list[float | None]]:
    primary_tokens = [normalized_tokens(line) for line in primary]
    secondary_tokens = [normalized_tokens(line) for line in secondary]
    total_primary = sum(sum(counts.values()) for counts in primary_tokens)
    total_secondary = sum(sum(counts.values()) for counts in secondary_tokens)
    if total_primary == 0 and total_secondary == 0:
        return None, [None] * len(primary), [None] * len(primary)

    used: set[int] = set()
    line_agreement: list[float | None] = []
    secondary_confidence: list[float | None] = []
    matched_tokens = 0
    for counts in primary_tokens:
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
    confidences = [word["conf"] for line in lines for word in line["words"]]
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


# ---------------------------------------------------------------------------
# Image placement discovery
# ---------------------------------------------------------------------------


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
        raise BookifyError("SOURCE_UNREADABLE", "pdftohtml page box is malformed", f"ocr.page.{page}") from error
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


def image_boxes(
    pdf: Path,
    page: int,
    page_width_pt: float,
    env: dict[str, str],
    timeout: float,
    offline: bool,
    workdir: Path,
    allow_unsandboxed: bool = False,
) -> list[tuple[float, float, float, float]]:
    """Image placements in PDF points, derived from pdftohtml's own unit."""
    link = workdir / "pdftohtml-source.pdf"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(pdf.resolve())
    result = _run(
        ["pdftohtml", "-xml", "-stdout", "-q", "-f", str(page), "-l", str(page), str(link)],
        env,
        timeout,
        offline,
        cwd=workdir,
        allow_unsandboxed=allow_unsandboxed,
    )
    if result.returncode != 0:
        raise BookifyError("SOURCE_UNREADABLE", f"pdftohtml failed: {_tail(result.stderr)}", f"ocr.page.{page}")
    text = result.stdout.decode("utf-8", "replace")
    parsed = _parse_xml_images(text, page)
    if not parsed:
        return []
    images, xml_width, _xml_height = parsed
    if xml_width <= 0:
        raise BookifyError("SOURCE_UNREADABLE", "pdftohtml reported a zero page width", f"ocr.page.{page}")
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


# ---------------------------------------------------------------------------
# Per-region measurement
# ---------------------------------------------------------------------------


def _line_band(mean: float, low_share: float, agreement: float | None) -> str:
    return band_for(mean, low_share, agreement)


def _measure_region(
    pdf: Path,
    page: int,
    index: int,
    box: tuple[float, float, float, float],
    scope_page: bool,
    options: OcrOptions,
    resolved: ResolvedEngine,
    outdir: Path,
    timeout: float,
) -> RegionMeasure:
    identity = resolved.identity
    dpi = int(identity.raster.get("dpi", 300))
    second_dpi = int(identity.raster.get("secondPassDpi", 450))
    psm = identity.page_psm if scope_page else identity.region_psm
    oem = identity.oem
    threads = identity.threads

    start = time.perf_counter()
    if scope_page:
        primary_png, width, height = _render_page(
            pdf, page, dpi, outdir, resolved.env, timeout, options.offline, CAP_PAGE_PIXELS,
            options.allow_unsandboxed,
        )
        secondary_png, second_width, second_height = _render_page(
            pdf, page, second_dpi, outdir, resolved.env, timeout, options.offline, CAP_PAGE_PIXELS,
            options.allow_unsandboxed,
        )
    else:
        primary_png, width, height = _render_crop(
            pdf, page, dpi, box, outdir, resolved.env, timeout, options.offline, CAP_REGION_PIXELS,
            options.allow_unsandboxed,
        )
        secondary_png, second_width, second_height = _render_crop(
            pdf, page, second_dpi, box, outdir, resolved.env, timeout, options.offline, CAP_REGION_PIXELS,
            options.allow_unsandboxed,
        )
    render_seconds = time.perf_counter() - start

    ocr_start = time.perf_counter()
    primary_tsv = _ocr_tsv(
        resolved.path,
        resolved.tessdata,
        options.lang,
        primary_png,
        psm,
        oem,
        threads,
        resolved.env,
        timeout,
        options.offline,
        options.allow_unsandboxed,
    )
    second_failed = False
    try:
        secondary_tsv = _ocr_tsv(
            resolved.path,
            resolved.tessdata,
            options.lang,
            secondary_png,
            psm,
            oem,
            threads,
            resolved.env,
            timeout,
            options.offline,
            options.allow_unsandboxed,
        )
    except BookifyError:
        # The second pass is corroboration. Its failure is recorded honestly as
        # `agreement: null`; it never becomes a silent pass.
        secondary_tsv = b""
        second_failed = True
    ocr_seconds = time.perf_counter() - ocr_start

    primary_lines = build_lines(parse_tsv(primary_tsv))
    secondary_lines = build_lines(parse_tsv(secondary_tsv)) if not second_failed else []
    if second_failed:
        agreement = None
        line_agreements = [None] * len(primary_lines)
        second_confidence = [None] * len(primary_lines)
    else:
        agreement, line_agreements, second_confidence = agreement_for(primary_lines, secondary_lines)
    stats = confidence_stats(primary_lines)

    scale = 72.0 / dpi
    origin_x, origin_y = (0.0, 0.0) if scope_page else (box[0], box[1])
    lines: list[dict[str, Any]] = []
    for line_index, line in enumerate(primary_lines, start=1):
        left, top, right, bottom = line["bbox_px"]
        member_confidences = [word["conf"] for word in line["words"]]
        low_share = (
            sum(1 for value in member_confidences if value < LOW_CONFIDENCE) / len(member_confidences)
            if member_confidences
            else 1.0
        )
        line_agreement = line_agreements[line_index - 1]
        line_band = _line_band(line["confidence"], round(low_share, 4), line_agreement)
        lines.append(
            {
                "index": line_index,
                "bbox": [
                    round(origin_x + left * scale, 2),
                    round(origin_y + top * scale, 2),
                    round(origin_x + right * scale, 2),
                    round(origin_y + bottom * scale, 2),
                ],
                "confidence": line["confidence"],
                "agreement": line_agreement,
                "secondPassConfidence": second_confidence[line_index - 1],
                "band": line_band,
                "eligible": line_band in {"adequate", "uncertain"},
                "text": line["text"],
                "wordCount": len(line["words"]),
            }
        )
    eligible_line_count = sum(1 for line in lines if line["eligible"])

    band = band_for(stats["mean"], stats["lowConfidenceShare"], agreement)
    return RegionMeasure(
        index=index,
        bbox=box,
        width=width,
        height=height,
        second_width=second_width,
        second_height=second_height,
        crop_sha256=_sha_file(primary_png),
        crop_sha256_second=_sha_file(secondary_png),
        tsv=primary_tsv,
        tsv_second=secondary_tsv,
        lines=lines,
        confidence=stats,
        agreement=agreement,
        band=band,
        line_count=stats["lineCount"],
        word_count=stats["wordCount"],
        eligible_line_count=eligible_line_count,
        reason=None
        if band == "adequate"
        else _band_reason(stats["mean"], stats["lowConfidenceShare"], agreement),
        second_failed=second_failed,
        raster_path=primary_png if options.keep_raster else None,
        dpi=dpi,
        second_dpi=second_dpi,
        colorspace=str(identity.raster.get("colorspace", "gray")),
        timing={"renderSeconds": round(render_seconds, 3), "ocrSeconds": round(ocr_seconds, 3)},
    )


def _band_reason(mean: float | None, low_share: float | None, agreement: float | None) -> str | None:
    """A deterministic, measured explanation; never a guess about the cause."""
    reasons: list[str] = []
    if agreement is None:
        reasons.append("second-pass agreement unavailable")
    elif agreement < BAND_ADEQUATE_AGREEMENT:
        reasons.append(f"agreement {agreement:.4f} below {BAND_ADEQUATE_AGREEMENT:.2f}")
    if mean is None:
        reasons.append("no confident word")
    elif mean < BAND_ADEQUATE_MEAN:
        reasons.append(f"mean confidence {mean:.2f} below {BAND_ADEQUATE_MEAN:.2f}")
    if low_share is None or low_share > BAND_ADEQUATE_LOW_SHARE:
        reasons.append(
            f"low-confidence share {low_share if low_share is not None else 'n/a'} above "
            f"{BAND_ADEQUATE_LOW_SHARE:.2f}"
        )
    return "; ".join(reasons) if reasons else None


def _best_band(region: RegionMeasure) -> str:
    if region.band == "adequate" or any(line["band"] == "adequate" for line in region.lines):
        return "adequate"
    if region.band == "uncertain" or any(line["band"] == "uncertain" for line in region.lines):
        return "uncertain"
    return "below_threshold"


def _page_status(regions: list[RegionMeasure]) -> str:
    bands = {_best_band(region) for region in regions}
    if "adequate" in bands:
        return "applied"
    if "uncertain" in bands:
        return "uncertain"
    return "below_threshold"


# ---------------------------------------------------------------------------
# Script detection
# ---------------------------------------------------------------------------

_SCRIPT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("cjk", 0x3040, 0x30FF),
    ("cjk", 0x3400, 0x4DBF),
    ("cjk", 0x4E00, 0x9FFF),
    ("cjk", 0xF900, 0xFAFF),
    ("cjk", 0xFF66, 0xFF9D),
    ("cyrillic", 0x0400, 0x04FF),
    ("greek", 0x0370, 0x03FF),
    ("arabic", 0x0600, 0x06FF),
    ("hebrew", 0x0590, 0x05FF),
    ("thai", 0x0E00, 0x0E7F),
    ("devanagari", 0x0900, 0x097F),
    ("hangul", 0xAC00, 0xD7AF),
)
_VIETNAMESE = re.compile(
    r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)


def unsupported_script(text: str, lang: str) -> bool:
    """A page in a script outside the declared OCR data is not guessed at.

    This is a text-layer signal. An image-only CJK page cannot be classified
    without OCR, so it stays unclaimed; the guide states that limit.
    """
    languages = set(_parse_lang(lang))
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    foreign = 0
    for character in letters:
        codepoint = ord(character)
        if any(low <= codepoint <= high for _name, low, high in _SCRIPT_RANGES):
            foreign += 1
            continue
        if character.lower() in "abcdefghijklmnopqrstuvwxyz" or character.isdigit():
            continue
        if _VIETNAMESE.match(character) and "vie" not in languages:
            foreign += 1
    return foreign / len(letters) > 0.10


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _nonspace(text: str) -> int:
    return sum(1 for character in text if not character.isspace())


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _projection(lines: list[dict[str, Any]]) -> bytes:
    return ("\n".join(line["text"] for line in lines) + ("\n" if lines else "")).encode("utf-8")


def _region_paths(page: int, index: int) -> tuple[str, str, str]:
    return (
        f"ocr/page-{page:03d}-region-{index:02d}.txt",
        f"ocr/page-{page:03d}-region-{index:02d}.tsv",
        f"ocr/page-{page:03d}-region-{index:02d}.png",
    )


def _record_from_region(
    page: int,
    region: RegionMeasure,
    out: Path,
    scope: str,
    keep_raster: bool,
) -> dict[str, Any]:
    text_rel, tsv_rel, png_rel = _region_paths(page, region.index)
    _write_bytes(out / tsv_rel, region.tsv)
    _write_bytes(out / text_rel, _projection(region.lines))
    if keep_raster and region.raster_path is not None:
        _write_bytes(out / png_rel, region.raster_path.read_bytes())
    record: dict[str, Any] = {
        "index": region.index,
        "bbox": [round(value, 2) for value in region.bbox],
        "bboxUnits": "pt",
        "raster": {
            "width": region.width,
            "height": region.height,
            "dpi": region.dpi,
            "secondPassWidth": region.second_width,
            "secondPassHeight": region.second_height,
            "secondPassDpi": region.second_dpi,
            "colorspace": region.colorspace,
        },
        "cropSha256": region.crop_sha256,
        "cropSha256SecondPass": region.crop_sha256_second,
        "tsvSha256": _sha_bytes(region.tsv),
        "tsvSha256SecondPass": _sha_bytes(region.tsv_second),
        "confidence": {
            "mean": region.confidence["mean"],
            "minLine": region.confidence["minLine"],
            "lowConfidenceShare": region.confidence["lowConfidenceShare"],
        },
        "agreement": region.agreement,
        "band": region.band,
        "reason": None
        if region.band == "adequate"
        else _band_reason(
            region.confidence["mean"], region.confidence["lowConfidenceShare"], region.agreement
        ),
        "lineCount": region.line_count,
        "wordCount": region.word_count,
        "eligibleLineCount": region.eligible_line_count,
        "textPath": text_rel,
        "tsvPath": tsv_rel,
        "machineRead": region.word_count > 0,
        "lines": region.lines,
    }
    if keep_raster:
        record["rasterPath"] = png_rel
    if region.second_failed:
        record["secondPassFailed"] = True
    if region.duplicate_of is not None:
        record["duplicateOf"] = region.duplicate_of
    if scope == "page":
        record["scope"] = "page"
    return record


def _too_small_entries(
    boxes: list[tuple[float, float, float, float]], index_from: int = 1
) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "bbox": [round(value, 2) for value in box],
            "bboxUnits": "pt",
            "reason": "too_small",
        }
        for index, box in enumerate(boxes, start=index_from)
    ]


def _page_summary(
    page: int,
    scope: str,
    regions: list[RegionMeasure],
    out: Path,
    keep_raster: bool,
    too_small: list[tuple[float, float, float, float]] | None = None,
) -> dict[str, Any]:
    eligible = [region for region in regions if _best_band(region) in {"adequate", "uncertain"}]
    pool = eligible or regions
    means = [region.confidence["mean"] for region in pool if region.confidence["mean"] is not None]
    lows = [
        region.confidence["lowConfidenceShare"]
        for region in pool
        if region.confidence["lowConfidenceShare"] is not None
    ]
    agreements = [region.agreement for region in pool if region.agreement is not None]
    mins = [region.confidence["minLine"] for region in pool if region.confidence["minLine"] is not None]
    summary = {
        "status": _page_status(regions),
        "scope": scope,
        "meanConfidence": round(sum(means) / len(means), 2) if means else None,
        "minLine": min(mins) if mins else None,
        "lowConfidenceShare": round(sum(lows) / len(lows), 4) if lows else None,
        "agreement": round(sum(agreements) / len(agreements), 4) if agreements else None,
        "lineCount": sum(region.line_count for region in pool),
        "wordCount": sum(region.word_count for region in pool),
        "eligibleLineCount": sum(region.eligible_line_count for region in pool),
        "regions": [_record_from_region(page, region, out, scope, keep_raster) for region in regions],
        "unsupportedScript": False,
        "skipReason": None,
    }
    if scope == "page" and regions:
        region = regions[0]
        text_rel, tsv_rel, _png_rel = _region_paths(page, region.index)
        summary["textPath"] = text_rel
        summary["tsvPath"] = tsv_rel
        summary["tsvSha256"] = _sha_bytes(region.tsv)
        summary["textSha256"] = _sha_bytes(_projection(region.lines))
    else:
        text = b"\n".join(_projection(region.lines) for region in regions)
        summary["textSha256"] = _sha_bytes(text)
    summary["machineRead"] = bool(summary["wordCount"])
    summary["aggregate"] = "unweighted-mean-over-regions" if scope == "images" else "region"
    region_reasons = [
        region.reason
        for region in pool
        if region.reason
    ]
    if summary["status"] in {"below_threshold", "uncertain"}:
        summary["reason"] = "; ".join(dict.fromkeys(region_reasons)) or (
            "no region or line reached the adequate band"
        )
    else:
        summary["reason"] = None
    if too_small:
        summary["tooSmallRegions"] = _too_small_entries(too_small)
    return summary



def _disabled_analysis(
    source: Path, page_list: list[tuple[int, str]], options: OcrOptions
) -> dict[str, Any]:
    """`--no-ocr`: record what would need OCR, never silently ignore it."""
    records: dict[int, dict[str, Any]] = {}
    with _workdir(Path(os.environ.get("TMPDIR", "/tmp")) / "bookify-ocr-disabled") as workdir:
        env = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "HOME": str(workdir),
            "TMPDIR": str(workdir),
        }
        for page, text in page_list:
            if _nonspace(text) < options.min_text_chars:
                records[page] = _minimal_record("skipped", skip_reason="disabled_by_flag")
                continue
            width, _height = page_size(source, page, env, options.timeout, options.offline, options.allow_unsandboxed)
            boxes = image_boxes(source, page, width, env, options.timeout, options.offline, workdir, options.allow_unsandboxed)
            too_small = [
                box
                for box in boxes
                if (box[2] - box[0]) * (box[3] - box[1]) < options.min_region_area_pt2
            ]
            boxes = [
                box
                for box in boxes
                if (box[2] - box[0]) * (box[3] - box[1]) >= options.min_region_area_pt2
            ]
            if boxes:
                records[page] = _minimal_record("skipped", skip_reason="disabled_by_flag")
            elif too_small:
                records[page] = _minimal_record(
                    "skipped", skip_reason="too_small", too_small=too_small
                )
            else:
                records[page] = _minimal_record("not_required", skip_reason="text_layer")
    return {"pages": records, "identity": None, "pinSha256": None, "engineSource": None, "developmentOnly": None}


def analyse_source(
    source: Path,
    out: Path,
    pages: Iterable[tuple[int, str]],
    options: OcrOptions | None = None,
) -> dict[str, Any]:
    """Measure every page that needs OCR and return manifest-ready records.

    ``pages`` is ``(page_number, text_layer_text)`` in ascending order. Pages
    that carry a text layer and no qualifying image region get a
    ``not_required`` record and no engine work.
    """
    options = options or OcrOptions()
    source = source.resolve()
    out = out.resolve()
    if not source.is_file():
        raise BookifyError("SOURCE_UNREADABLE", f"source not found: {source}", str(source))
    if not options.enabled:
        return _disabled_analysis(source, list(pages), options)
    if source.stat().st_size > CAP_PDF_BYTES:
        raise BookifyError("INPUT_INVALID", f"source exceeds cap {CAP_PDF_BYTES} bytes", "ocr.source")

    out.mkdir(parents=True, exist_ok=True)
    ocr_dir = out / "ocr"
    ocr_dir.mkdir(exist_ok=True)

    page_list = list(pages)
    resolved: ResolvedEngine | None = None
    records: dict[int, dict[str, Any]] = {}
    runlog: list[dict[str, Any]] = []
    source_start = time.perf_counter()
    seen_crops: dict[str, tuple[int, int]] = {}

    with _workdir(ocr_dir) as workdir:
        # Resolve lazily: a text-only source must not require OCR setup.
        probe_env = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "HOME": str(workdir),
            "TMPDIR": str(workdir),
        }
        needs: dict[
            int,
            tuple[
                str,
                list[tuple[float, float, float, float]],
                float,
                float,
                list[tuple[float, float, float, float]],
            ],
        ] = {}
        for page, text in page_list:
            low_text = _nonspace(text) < options.min_text_chars
            if not low_text and _nonspace(text) >= options.min_text_chars:
                width, height = page_size(source, page, probe_env, options.timeout, options.offline, options.allow_unsandboxed)
                placements = image_boxes(source, page, width, probe_env, options.timeout, options.offline, workdir, options.allow_unsandboxed)
                boxes = [
                    box
                    for box in placements
                    if (box[2] - box[0]) * (box[3] - box[1]) >= options.min_region_area_pt2
                ]
                too_small = [
                    box
                    for box in placements
                    if (box[2] - box[0]) * (box[3] - box[1]) < options.min_region_area_pt2
                ]
                boxes.sort(key=lambda box: (round(box[1], 3), round(box[0], 3)))
                if boxes:
                    if unsupported_script(text, options.lang):
                        records[page] = _minimal_record(
                            "skipped", skip_reason="unsupported_script", unsupported=True
                        )
                    else:
                        needs[page] = ("images", boxes, width, height, too_small)
                elif too_small:
                    # The extractor saw image placements; they are logos or rules
                    # below the region floor. Record the skip, never upscale them.
                    records[page] = _minimal_record(
                        "skipped", skip_reason="too_small", too_small=too_small
                    )
                else:
                    records[page] = _minimal_record("not_required", skip_reason="text_layer")
                continue
            if unsupported_script(text, options.lang):
                records[page] = _minimal_record(
                    "skipped", skip_reason="unsupported_script", unsupported=True
                )
            else:
                needs[page] = ("page", [(0.0, 0.0, 0.0, 0.0)], 0.0, 0.0, [])

        if needs and resolved is None:
            resolved = resolve(options)
        identity = resolved.identity if resolved is not None else None
        if resolved is not None:
            env = dict(resolved.env)
            env["HOME"] = str(workdir)
            env["TMPDIR"] = str(workdir)
            resolved = replace(resolved, env=env)
        else:
            env = {"TMPDIR": str(workdir)}

        for page in sorted(needs):
            scope, boxes, width, height, too_small = needs[page]
            page_start = time.perf_counter()
            deadline = page_start + options.page_timeout
            if source_start + options.source_timeout < time.perf_counter():
                raise BookifyError("SOURCE_UNREADABLE", "whole-source OCR timeout", str(source))
            if resolved is None:
                raise BookifyError("INPUT_INVALID", "OCR engine was not resolved", "ocr")

            if scope == "page":
                page_width, page_height = page_size(source, page, env, options.timeout, options.offline, options.allow_unsandboxed)
                box = (0.0, 0.0, page_width, page_height)
                remaining = min(options.timeout, deadline - time.perf_counter())
                region = _measure_region(
                    source, page, 1, box, True, options, resolved, workdir, remaining
                )
                regions = [region]
                regions[0].bbox = box
            else:
                if len(boxes) > CAP_REGIONS_PER_PAGE:
                    raise BookifyError(
                        "INPUT_INVALID",
                        f"region count {len(boxes)} exceeds cap {CAP_REGIONS_PER_PAGE}",
                        f"ocr.page.{page}",
                    )
                regions = []
                for index, box in enumerate(boxes, start=1):
                    if time.perf_counter() > deadline:
                        raise BookifyError(
                            "SOURCE_UNREADABLE",
                            f"page OCR timeout after {options.page_timeout:g}s",
                            f"ocr.page.{page}",
                        )
                    remaining = min(options.timeout, deadline - time.perf_counter())
                    region = _measure_region(
                        source, page, index, box, False, options, resolved, workdir, remaining
                    )
                    key = region.crop_sha256
                    if key in seen_crops:
                        first_page, first_index = seen_crops[key]
                        region.duplicate_of = first_index if first_page == page else None
                    else:
                        seen_crops[key] = (page, index)
                    regions.append(region)

            record = _page_summary(
                page, scope, regions, out, options.keep_raster, too_small
            )
            if identity is not None:
                record["engine"] = identity.manifest()
                record["raster"] = dict(identity.raster)
                record["pinSha256"] = identity.pin_sha256
            records[page] = record
            runlog.append(
                {
                    "event": "page",
                    "page": page,
                    "scope": scope,
                    "status": record["status"],
                    "band": _page_status(regions),
                    "regions": len(regions),
                    "seconds": round(time.perf_counter() - page_start, 3),
                    "sandbox": options.offline,
                }
            )
            for region in regions:
                runlog.append(
                    {
                        "event": "region",
                        "page": page,
                        "region": region.index,
                        "renderSeconds": region.timing.get("renderSeconds"),
                        "ocrSeconds": region.timing.get("ocrSeconds"),
                    }
                )

    _write_runlog(ocr_dir, runlog, options, identity, source)

    for page, _text in page_list:
        records.setdefault(page, _minimal_record("not_required", skip_reason="text_layer"))

    return {
        "pages": records,
        "identity": identity.manifest() if identity is not None else None,
        "pinSha256": identity.pin_sha256 if identity is not None else None,
        "engineSource": identity.source if identity is not None else None,
        "developmentOnly": identity.development_only if identity is not None else None,
    }


def _minimal_record(
    status: str,
    *,
    skip_reason: str,
    unsupported: bool = False,
    too_small: list[tuple[float, float, float, float]] | None = None,
) -> dict[str, Any]:
    record = {
        "status": status,
        "scope": None,
        "meanConfidence": None,
        "minLine": None,
        "lowConfidenceShare": None,
        "agreement": None,
        "lineCount": 0,
        "wordCount": 0,
        "eligibleLineCount": 0,
        "textSha256": _sha_bytes(b""),
        "regions": [],
        "machineRead": False,
        "unsupportedScript": unsupported,
        "skipReason": skip_reason,
    }
    if too_small:
        record["tooSmallRegions"] = _too_small_entries(too_small)
    return record


class _workdir:
    """A scratch directory for Poppler side files and Poisson rasters."""

    def __init__(self, parent: Path) -> None:
        self.path = parent / ".ocr-tmp"

    def __enter__(self) -> Path:
        shutil.rmtree(self.path, ignore_errors=True)
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path

    def __exit__(self, *_exc: object) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def append_runlog(ocr_dir: Path, payload: dict[str, Any]) -> None:
    """Append one run-log record; the manifest never carries timings."""
    ocr_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, sort_keys=True) + "\n"
    with (ocr_dir / "runlog.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(line)


def _write_runlog(
    ocr_dir: Path,
    events: list[dict[str, Any]],
    options: OcrOptions,
    identity: EngineIdentity | None,
    source: Path,
) -> None:
    """Timings, sandbox state and engine source; never part of the manifest."""
    workdir = Path(os.environ.get("TMPDIR", "/tmp")) / "bookify-ocr-probe"
    policy = sandbox.SandboxPolicy(
        offline=options.offline,
        timeout=options.timeout,
        workdir=workdir,
        allow_unsandboxed=options.allow_unsandboxed,
    )
    payload = {
        "schemaVersion": "1.0",
        "phase": "ocr",
        "sourceSha256": _sha_file(source),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "offline": sandbox.record(policy)["offline"],
        "sandbox": sandbox.record(policy),
        "keepRaster": options.keep_raster,
        "lang": options.lang,
        "engineSource": identity.source if identity is not None else None,
        "developmentOnly": identity.development_only if identity is not None else None,
        "pinSha256": identity.pin_sha256 if identity is not None else None,
        "events": events,
    }
    append_runlog(ocr_dir, payload)


# ---------------------------------------------------------------------------
# Table reconstruction (authoring helper, method id ocr-table-v1)
# ---------------------------------------------------------------------------


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def reconstruct_table(tsv: bytes) -> list[list[str]]:
    """Group TSV words into rows and cells deterministically (``ocr-table-v1``).

    Rows follow TSV block/paragraph/line order. Cells split where the horizontal
    gap between adjacent words exceeds three times the region's median word gap
    (with a 40 px floor, so a single wide gutter still splits). No text is
    rewritten and no missing cell is invented.
    """
    words = parse_tsv(tsv)
    lines = build_lines(words)
    all_gaps: list[float] = []
    for line in lines:
        members = sorted(line["words"], key=lambda word: word["box"][0])
        for previous, current in zip(members, members[1:]):
            gap = current["box"][0] - (previous["box"][0] + previous["box"][2])
            if 0 < gap <= 300:
                all_gaps.append(gap)
    # A word space is small; a column gutter is large. The floor keeps a
    # two-column row (one huge gap) splitting correctly.
    word_gap = _median(all_gaps) if all_gaps else 16.0
    threshold = max(40.0, 3.0 * word_gap)

    rows: list[list[str]] = []
    for line in lines:
        members = sorted(line["words"], key=lambda word: word["box"][0])
        if not members:
            continue
        cells: list[list[str]] = [[members[0]["text"]]]
        for previous, current in zip(members, members[1:]):
            gap = current["box"][0] - (previous["box"][0] + previous["box"][2])
            if gap > threshold:
                cells.append([current["text"]])
            else:
                cells[-1].append(current["text"])
        rows.append([" ".join(cell) for cell in cells])
    return rows


def canonical_note() -> str:
    return CANONICAL_NOTE


def page_ocr_hash(record: dict[str, Any] | None) -> str | None:
    """Stable hash of one page OCR record, used by change detection."""
    if not isinstance(record, dict):
        return None
    return _sha_bytes(_canonical_json(record).encode("utf-8"))


# Keep flake-free unused imports explicit for type checkers that read __all__.
__all__ = [
    "BAND_ADEQUATE_AGREEMENT",
    "BAND_ADEQUATE_LOW_SHARE",
    "BAND_ADEQUATE_MEAN",
    "BAND_UNCERTAIN_AGREEMENT",
    "BAND_UNCERTAIN_MEAN",
    "CANONICAL_NOTE",
    "CAP_PAGE_PIXELS",
    "CAP_PDF_BYTES",
    "CAP_REGIONS_PER_PAGE",
    "CAP_REGION_PIXELS",
    "CAP_TSV_BYTES",
    "DEFAULT_MIN_REGION_AREA_PT2",
    "DEFAULT_MIN_TEXT_CHARS",
    "OcrOptions",
    "OCR_STATUSES",
    "SUPPORTED_LANGUAGES",
    "analyse_source",
    "band_for",
    "build_lines",
    "canonical_note",
    "confidence_stats",
    "image_boxes",
    "page_ocr_hash",
    "page_size",
    "parse_tsv",
    "pin_for",
    "reconstruct_table",
    "resolve",
    "unsupported_script",
]
