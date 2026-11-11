"""Illustration records: complete rights, kind-specific caption wording, credit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from bookify.errors import BookifyError

REQUIRED = ("path", "originUrl", "creator", "licence", "credit", "caption", "alt", "kind", "rightsStatus")
KINDS = {"contemporary_photograph", "later_depiction", "reconstruction", "conceptual_artwork"}
STATUS = {"verified", "unconfirmed"}
KIND_WORDING = {
    "reconstruction": "Reconstruction.",
    "later_depiction": "Later depiction.",
}


@dataclass(frozen=True)
class Illustration:
    id: str
    path: str
    origin_url: str
    creator: str
    licence: str
    credit: str
    caption: str
    alt: str
    kind: str
    rights_status: str


def load(root: Path, illustration_id: str) -> Illustration:
    record_path = root / "assets" / "illustrations" / illustration_id / "record.yaml"
    if not record_path.is_file():
        raise BookifyError("RIGHTS_INCOMPLETE", f"missing record: {illustration_id}", str(record_path))
    data = yaml.safe_load(record_path.read_text())
    if not isinstance(data, dict):
        raise BookifyError("RIGHTS_INCOMPLETE", "record must be a mapping", str(record_path))
    for field in REQUIRED:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BookifyError("RIGHTS_INCOMPLETE", f"record missing {field}", f"{record_path}:{field}")
    if data["kind"] not in KINDS:
        raise BookifyError("RIGHTS_INCOMPLETE", f"unsupported kind: {data['kind']}", str(record_path))
    if data["rightsStatus"] not in STATUS:
        raise BookifyError("RIGHTS_INCOMPLETE", f"unsupported rights status: {data['rightsStatus']}", str(record_path))
    image = root / data["path"]
    if not image.is_file():
        raise BookifyError("RIGHTS_INCOMPLETE", f"missing image: {data['path']}", str(image))
    return Illustration(
        id=illustration_id,
        path=data["path"],
        origin_url=data["originUrl"],
        creator=data["creator"],
        licence=data["licence"],
        credit=data["credit"],
        caption=data["caption"],
        alt=data["alt"],
        kind=data["kind"],
        rights_status=data["rightsStatus"],
    )


def kind_wording(kind: str) -> str | None:
    """The canonical class sentence for a record kind, if it has one."""
    return KIND_WORDING.get(kind)


def caption(record: Illustration, override: str | None) -> str:
    text = override.strip() if override else record.caption
    marker = kind_wording(record.kind)
    # Do not add a second class sentence when the prose already names the
    # class ("Conceptual reconstruction ..."). The canonical sentence is only
    # the fallback for a caption that does not name it at all.
    if marker and marker.lower().rstrip(".") not in text.lower():
        text = f"{text.rstrip()} {marker}"
    return text


def printed_class_wording(record: Illustration, override: str | None) -> str | None:
    """The class wording as the printed caption actually spells it.

    Extraction probes must compare against the printed case, not a hard-coded
    capitalised token. When the caption already names the class in prose this
    returns that printed phrase; when the canonical sentence was appended it
    returns the canonical sentence.
    """
    text = caption(record, override)
    marker = kind_wording(record.kind)
    if not marker:
        return None
    stem = marker.rstrip(".")
    match = re.search(re.escape(stem), text, re.IGNORECASE)
    return match.group(0) if match else marker


def require_publishable(record: Illustration, draft: bool) -> None:
    if record.rights_status == "unconfirmed" and not draft:
        raise BookifyError(
            "RIGHTS_INCOMPLETE",
            f"rights unconfirmed for {record.id}; publish a draft explicitly or verify the licence",
            record.id,
        )
