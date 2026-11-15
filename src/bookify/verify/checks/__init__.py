"""One check result shape for every verifier."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Check:
    id: str
    status: str  # pass | fail | warn | manual
    code: str | None
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        # A warning is evidence for review, not a gate failure (D7).
        return self.status in {"pass", "warn", "manual"}


def passed(identifier: str, detail: str, **evidence: Any) -> Check:
    return Check(identifier, "pass", None, detail, evidence)


def failed(identifier: str, code: str, detail: str, **evidence: Any) -> Check:
    return Check(identifier, "fail", code, detail, evidence)


def manual(identifier: str, detail: str, **evidence: Any) -> Check:
    return Check(identifier, "manual", None, detail, evidence)


def warned(identifier: str, detail: str, **evidence: Any) -> Check:
    return Check(identifier, "warn", None, detail, evidence)
