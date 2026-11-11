"""Illustration placement: at most one per final page, deterministically."""

from __future__ import annotations

from typing import Any

from bookify.errors import BookifyError

MAX_ATTEMPTS = 3


def conflicts(placements: list[dict[str, Any]]) -> dict[int, list[str]]:
    by_page: dict[int, list[str]] = {}
    for placement in placements:
        page = placement.get("page")
        if page is None:
            continue
        by_page.setdefault(page, []).append(placement["illustrationId"])
    return {page: ids for page, ids in by_page.items() if len(ids) > 1}


def defer_later(document: dict[str, Any], conflicting: dict[int, list[str]]) -> list[str]:
    """Push the later illustration in each conflict to the next page."""
    order = [illustration["id"] for illustration in document["illustrations"]]
    deferred: list[str] = []
    for ids in conflicting.values():
        later = max(ids, key=order.index)
        for illustration in document["illustrations"]:
            if illustration["id"] == later:
                illustration["pagebreak"] = True
                deferred.append(later)
    for section in document["sections"]:
        for block in section["blocks"]:
            if block["type"] == "illustration" and block.get("illustrationId") in deferred:
                block["pagebreak"] = True
    return deferred


def require_limit(conflicting: dict[int, list[str]]) -> None:
    if conflicting:
        pages = ", ".join(str(page) for page in sorted(conflicting))
        raise BookifyError("ILLUSTRATION_LIMIT", f"more than one illustration on page(s): {pages}")
