"""Offline and model-free enforcement.

Publishing must be provably offline. This guard replaces the socket entry
points for the duration of a build and refuses model calls unless authoring
explicitly opts in.
"""

from __future__ import annotations

import socket
from contextlib import contextmanager
from typing import Iterator

from bookify.errors import BookifyError

_MODEL_ALLOWED = False
_ACTIVE = False
_ATTEMPTS = 0


def _deny_network(*_args: object, **_kwargs: object) -> None:
    global _ATTEMPTS
    _ATTEMPTS += 1
    raise BookifyError("NETWORK_DENIED", "network access is not allowed during publishing")


def attempts() -> int:
    """How many network attempts the guard denied in the current build."""
    return _ATTEMPTS


def active() -> bool:
    return _ACTIVE


@contextmanager
def offline(allow_model: bool = False) -> Iterator[None]:
    """Block sockets for the block; model calls stay denied by default."""
    global _MODEL_ALLOWED, _ACTIVE, _ATTEMPTS

    saved = (socket.socket, socket.create_connection, socket.getaddrinfo)
    previous_model = _MODEL_ALLOWED
    socket.socket = _deny_network  # type: ignore[assignment]
    socket.create_connection = _deny_network  # type: ignore[assignment]
    socket.getaddrinfo = _deny_network  # type: ignore[assignment]
    _MODEL_ALLOWED = allow_model
    _ACTIVE = True
    _ATTEMPTS = 0
    try:
        yield
    finally:
        socket.socket, socket.create_connection, socket.getaddrinfo = saved  # type: ignore[assignment]
        _MODEL_ALLOWED = previous_model
        _ACTIVE = False


def model_call(purpose: str) -> None:
    """Refuse a model call outside an authoring context."""
    if not _MODEL_ALLOWED:
        raise BookifyError("MODEL_CALL_DENIED", f"model call refused during publishing: {purpose}")
