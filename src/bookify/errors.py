"""One error type for every module; the code is part of the contract."""

from __future__ import annotations


class BookifyError(RuntimeError):
    """A failure with a stable machine-readable code and optional locator."""

    def __init__(self, code: str, message: str, locator: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.locator = locator

    def as_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "message": self.message}
        if self.locator is not None:
            payload["locator"] = self.locator
        return payload
