"""Measured build boundary: prove publishing never reaches OCR.

The build report used to say ``engineInvocations: 0`` because the writer wrote
that constant. This module measures it instead: while a build runs, every
``subprocess.run`` argv and every file open is inspected. Any Tesseract command
or any read under ``vendor/ocr`` is counted. The report carries the measured
result and verify rejects a report that does not claim a measured probe.
"""

from __future__ import annotations

import io
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _is_ocr_path(value: str) -> bool:
    text = value.replace("\\", "/")
    name = Path(text).name
    return (
        "vendor/ocr" in text
        or name == "tesseract"
        or name.startswith("tesseract-")
        or name.endswith(".traineddata")
    )


def _ocr_command(argv: Any) -> bool:
    if isinstance(argv, (str, os.PathLike)):
        parts = [os.fspath(argv)]
    elif isinstance(argv, (list, tuple)):
        parts = [os.fspath(item) for item in argv if isinstance(item, (str, os.PathLike))]
    else:
        return False
    for part in parts:
        name = Path(part.replace("\\", "/")).name
        if name == "tesseract" or name.startswith("tesseract-"):
            return True
        if "vendor/ocr" in part.replace("\\", "/") or part.endswith(".traineddata"):
            return True
    return False


@dataclass
class Boundary:
    engine_invocations: int = 0
    vendor_read: bool = False
    subprocess_calls: int = 0
    commands: list[str] = field(default_factory=list)

    def evidence(self) -> dict[str, Any]:
        return {
            "invoked": bool(self.engine_invocations),
            "engineInvocations": self.engine_invocations,
            "vendorRead": bool(self.vendor_read),
            "measured": True,
            "probe": "subprocess.run+io.open",
            "subprocessCalls": self.subprocess_calls,
        }


class _BoundaryContext:
    def __init__(self) -> None:
        self.state = Boundary()
        self._run = subprocess.run
        self._io_open = io.open
        self._os_open = os.open

    def __enter__(self) -> Boundary:
        state = self.state
        original_run = self._run

        def measured_run(*args: Any, **kwargs: Any):
            argv = args[0] if args else kwargs.get("args")
            state.subprocess_calls += 1
            if _ocr_command(argv):
                state.engine_invocations += 1
                if len(state.commands) < 8:
                    state.commands.append(str(argv))
            return original_run(*args, **kwargs)

        def measured_io_open(file: Any, *args: Any, **kwargs: Any):
            path = os.fspath(file) if isinstance(file, (str, os.PathLike)) else ""
            if path and _is_ocr_path(path):
                state.vendor_read = True
            return self._io_open(file, *args, **kwargs)

        def measured_os_open(path: Any, *args: Any, **kwargs: Any):
            if isinstance(path, (str, os.PathLike)) and _is_ocr_path(os.fspath(path)):
                state.vendor_read = True
            return self._os_open(path, *args, **kwargs)

        subprocess.run = measured_run
        io.open = measured_io_open
        os.open = measured_os_open
        return state

    def __exit__(self, *_exc: object) -> None:
        subprocess.run = self._run
        io.open = self._io_open
        os.open = self._os_open


def boundary() -> _BoundaryContext:
    return _BoundaryContext()


__all__ = ["Boundary", "boundary"]
