"""Stable manifests for extracted sources: sorted keys, no timestamps."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from bookify.errors import BookifyError
from bookify.intake import extract, images, ocr, sandbox

SCHEMA_VERSION = "1.0"
PAGE_FILE = "pages/page-{page:03d}.txt"
MANIFEST = "manifest.json"
CHANGES = "changes.json"


def source_id(path: Path) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    return slug[:64] or "source"


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_json(path: Path, data: Any) -> None:
    _write_atomic(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def load(path: Path) -> dict[str, Any] | None:
    manifest = path / MANIFEST
    if not manifest.is_file():
        return None
    return json.loads(manifest.read_text())


def _text_sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pair(files: list[Path], listed: list[extract.ImageInfo]) -> list[tuple[Path, extract.ImageInfo]]:
    """Pair extracted files with pdfimages rows positionally; keep image rows only."""
    return [(file, info) for file, info in zip(files, listed) if info.kind == "image"]


def _policy(ocr_options: ocr.OcrOptions | None, out: Path) -> sandbox.SandboxPolicy:
    """Extraction uses the same offline boundary as OCR, sandboxed by default."""
    options = ocr_options or ocr.OcrOptions()
    return extract.policy_for(
        out,
        offline=options.offline,
        allow_unsandboxed=options.allow_unsandboxed,
    )


def _extract_events(
    source: Path, policy: sandbox.SandboxPolicy, page_count: int
) -> list[dict[str, Any]]:
    return [
        {
            "event": "extract",
            "source": source.name,
            "pages": page_count,
            "sandbox": sandbox.record(policy),
        }
    ]


def _build_pages(
    source: Path,
    out: Path,
    temp: Path,
    ocr_options: ocr.OcrOptions | None = None,
) -> dict[str, Any]:
    pages_dir = out / "pages"
    images_dir = out / "images"
    policy = _policy(ocr_options, out)
    count = extract.page_count(source, policy)
    seen_images: dict[str, str] = {}
    pages: list[dict[str, Any]] = []
    texts: list[tuple[int, str]] = []

    for page in range(1, count + 1):
        text = extract.page_text(source, page, policy)
        texts.append((page, text))
        text_path = out / PAGE_FILE.format(page=page)
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text)

        listed = extract.list_images(source, page, policy)
        page_temp = temp / f"page-{page:03d}"
        files = extract.extract_images(source, page, page_temp, policy)
        if len(files) != len(listed):
            raise BookifyError(
                "SOURCE_UNREADABLE",
                f"page {page}: {len(files)} images extracted, {len(listed)} listed",
                str(source),
            )
        stored = [
            images.store(file, info.page, info.index, info.width, info.height, images_dir, seen_images)
            for file, info in _pair(files, listed)
        ]
        pages.append(
            {
                "page": page,
                "textSha256": _text_sha(text),
                "charCount": len(text),
                "isImageOnly": text.strip() == "",
                "images": [
                    {"index": item.index, "file": item.file, "width": item.width, "height": item.height, "sha256": item.sha256}
                    for item in stored
                ],
            }
        )

    referenced = {page["page"] for page in pages}
    for stale in (out / "pages").glob("page-*.txt") if (out / "pages").is_dir() else []:
        number = int(stale.stem.split("-")[1])
        if number not in referenced:
            stale.unlink()
    kept_images = {entry["file"] for page in pages for entry in page["images"]}
    if images_dir.is_dir():
        for stale in images_dir.glob("page-*-img-*.png"):
            if f"images/{stale.name}" not in kept_images:
                stale.unlink()

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceId": source_id(source),
        "sourceName": source.name,
        "sourceSha256": extract.source_sha256(source),
        "pageCount": count,
        "pages": pages,
    }
    append_runlog = ocr.append_runlog
    append_runlog(
        out / "ocr",
        {
            "schemaVersion": "1.0",
            "phase": "extract",
            "sourceSha256": extract.source_sha256(source),
            "sandbox": sandbox.record(policy),
            "events": _extract_events(source, policy, count),
        },
    )

    if ocr_options is not None:
        analysis = ocr.analyse_source(source, out, texts, ocr_options)
        for page in pages:
            record = analysis["pages"].get(page["page"])
            if record is not None:
                page["ocr"] = record
        if analysis.get("pinSha256") is not None:
            manifest["ocr"] = {
                "pinSha256": analysis["pinSha256"],
                "engine": analysis.get("identity"),
                "engineSource": analysis.get("engineSource"),
                "developmentOnly": analysis.get("developmentOnly"),
            }
        _clean_ocr_files(out, pages)
    return manifest


def _clean_ocr_files(out: Path, pages: list[dict[str, Any]]) -> None:
    """Remove OCR files this manifest does not reference."""
    ocr_dir = out / "ocr"
    if not ocr_dir.is_dir():
        return
    kept: set[str] = set()
    for page in pages:
        record = page.get("ocr") or {}
        for key in ("textPath", "tsvPath", "rasterPath"):
            value = record.get(key)
            if isinstance(value, str):
                kept.add(value)
        for region in record.get("regions", []):
            for key in ("textPath", "tsvPath", "rasterPath"):
                value = region.get(key)
                if isinstance(value, str):
                    kept.add(value)
    for stale in ocr_dir.glob("*"):
        if stale.is_file() and stale.name != "runlog.jsonl":
            rel = f"ocr/{stale.name}"
            if rel not in kept:
                stale.unlink()


def build(
    source: Path,
    out: Path,
    *,
    ocr_options: ocr.OcrOptions | None = None,
) -> dict[str, Any]:
    if not source.is_file():
        raise BookifyError("SOURCE_UNREADABLE", f"source not found: {source}", str(source))
    # Resolve once: the sandbox runs with the output directory as its cwd.
    source = source.resolve()
    out.mkdir(parents=True, exist_ok=True)
    temp = out / ".tmp"
    shutil.rmtree(temp, ignore_errors=True)
    temp.mkdir(exist_ok=True)
    # Fail on the source cap before spending time on extraction. A previous
    # runlog is removed so a failed preflight cannot look like a fresh run.
    (out / "ocr" / "runlog.jsonl").unlink(missing_ok=True)
    policy = _policy(ocr_options, out)
    try:
        extract.preflight(source, policy)
        manifest = _build_pages(source, out, temp, ocr_options)
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    write_json(out / MANIFEST, manifest)
    return manifest
