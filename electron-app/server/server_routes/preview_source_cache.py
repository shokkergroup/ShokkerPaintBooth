"""Bounded in-memory cache for unchanged live-preview paint sources.

The browser's native-2048 canvas can encode to several megabytes.  Finish and
intensity edits do not change those pixels, so repeatedly putting the same PNG
inside JSON wastes main-thread, parser, base64, and loopback bandwidth.  This
cache lets a client upload the PNG once and reuse an opaque token.  Tokens are
process-local, expire quickly, and fail closed after restart or eviction.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG_IHDR = b"IHDR"
MAX_PREVIEW_DIMENSION = 4096


class PreviewSourceError(ValueError):
    """Raised when an inline preview source is malformed or too large."""


@dataclass(frozen=True)
class PreviewSource:
    token: str
    digest: str
    payload: bytes
    created_at: float

    @property
    def byte_count(self) -> int:
        return len(self.payload)


class PreviewSourceCache:
    """Thread-safe byte/item/TTL-bounded LRU of decoded PNG payloads."""

    def __init__(
        self,
        *,
        max_bytes: int = 64 * 1024 * 1024,
        max_items: int = 8,
        max_item_bytes: int = 32 * 1024 * 1024,
        ttl_seconds: float = 15 * 60,
    ) -> None:
        self.max_bytes = int(max_bytes)
        self.max_items = int(max_items)
        self.max_item_bytes = int(max_item_bytes)
        self.ttl_seconds = float(ttl_seconds)
        self._items: OrderedDict[str, PreviewSource] = OrderedDict()
        self._digest_to_token: dict[str, str] = {}
        self._bytes = 0
        self._lock = threading.Lock()

    @staticmethod
    def decode_data_url(value: object, *, max_item_bytes: int) -> bytes:
        if not isinstance(value, str) or not value:
            raise PreviewSourceError("paint_image_base64 must be a non-empty PNG data URL")
        encoded = value.split(",", 1)[-1] if value.startswith("data:") else value
        # A decoded payload can be at most three quarters of base64 length.
        if len(encoded) > ((max_item_bytes + 2) // 3) * 4 + 8:
            raise PreviewSourceError("paint_image_base64 exceeds the preview source limit")
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PreviewSourceError("paint_image_base64 is not valid base64") from exc
        if len(payload) > max_item_bytes:
            raise PreviewSourceError("decoded preview source exceeds the preview source limit")
        if not payload.startswith(PNG_MAGIC):
            raise PreviewSourceError("paint_image_base64 must contain a PNG image")
        # Validate the fixed PNG signature + IHDR before Pillow/OpenCV touches
        # the bytes. A highly compressed payload can be small while claiming a
        # gigantic decoded canvas; the preview contract already caps either
        # dimension at 4096, so reject that memory-amplification path here.
        if len(payload) < 24 or payload[12:16] != PNG_IHDR:
            raise PreviewSourceError("paint_image_base64 has an invalid PNG header")
        width = int.from_bytes(payload[16:20], "big")
        height = int.from_bytes(payload[20:24], "big")
        if not (1 <= width <= MAX_PREVIEW_DIMENSION and 1 <= height <= MAX_PREVIEW_DIMENSION):
            raise PreviewSourceError(
                f"preview source dimensions must be 1-{MAX_PREVIEW_DIMENSION} pixels"
            )
        return payload

    def remember_data_url(self, value: object) -> PreviewSource:
        payload = self.decode_data_url(value, max_item_bytes=self.max_item_bytes)
        digest = hashlib.sha256(payload).hexdigest()
        now = time.monotonic()
        with self._lock:
            self._expire_locked(now)
            old_token = self._digest_to_token.get(digest)
            old = self._items.get(old_token) if old_token else None
            if old is not None:
                self._items.move_to_end(old.token)
                return old
            item = PreviewSource(
                token=secrets.token_urlsafe(32),
                digest=digest,
                payload=payload,
                created_at=now,
            )
            self._items[item.token] = item
            self._digest_to_token[digest] = item.token
            self._bytes += item.byte_count
            self._trim_locked()
            return item

    def resolve(self, token: object) -> PreviewSource | None:
        if not isinstance(token, str) or not (24 <= len(token) <= 128):
            return None
        now = time.monotonic()
        with self._lock:
            self._expire_locked(now)
            item = self._items.get(token)
            if item is None:
                return None
            self._items.move_to_end(token)
            return item

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._digest_to_token.clear()
            self._bytes = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            self._expire_locked(time.monotonic())
            return {"items": len(self._items), "bytes": self._bytes}

    def _remove_locked(self, token: str) -> None:
        item = self._items.pop(token, None)
        if item is None:
            return
        self._bytes -= item.byte_count
        if self._digest_to_token.get(item.digest) == token:
            self._digest_to_token.pop(item.digest, None)

    def _expire_locked(self, now: float) -> None:
        expired = [
            token
            for token, item in self._items.items()
            if now - item.created_at > self.ttl_seconds
        ]
        for token in expired:
            self._remove_locked(token)

    def _trim_locked(self) -> None:
        while self._items and (
            len(self._items) > self.max_items or self._bytes > self.max_bytes
        ):
            self._remove_locked(next(iter(self._items)))


preview_source_cache = PreviewSourceCache()
