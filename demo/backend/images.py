"""Small image I/O helpers used by the isolated demo runtime."""

from __future__ import annotations

import base64
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import threading
from typing import Any

import numpy as np
from PIL import Image


MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_PIXELS = 4096 * 4096


class SourceImageError(ValueError):
    pass


@dataclass(frozen=True)
class SourceRecord:
    token: str
    payload: bytes
    width: int
    height: int


class SourceCache:
    """Process-local bounded cache for repeated live-canvas preview calls."""

    def __init__(self, limit: int = 4):
        self.limit = max(1, int(limit))
        self._records: "OrderedDict[str, SourceRecord]" = OrderedDict()
        self._lock = threading.Lock()

    def remember_data_url(self, value: str) -> SourceRecord:
        payload = decode_png_data_url(value)
        digest = hashlib.sha256(payload).hexdigest()
        token = f"demo-src-{digest[:24]}"
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
        record = SourceRecord(token=token, payload=payload, width=width, height=height)
        with self._lock:
            self._records[token] = record
            self._records.move_to_end(token)
            while len(self._records) > self.limit:
                self._records.popitem(last=False)
        return record

    def resolve(self, token: str | None) -> SourceRecord | None:
        if not token:
            return None
        with self._lock:
            record = self._records.get(str(token))
            if record is not None:
                self._records.move_to_end(str(token))
            return record


def decode_png_data_url(value: Any) -> bytes:
    if not isinstance(value, str) or not value.startswith("data:image/png;base64,"):
        raise SourceImageError("source_data_url must be a base64 PNG data URL")
    encoded = value.split(",", 1)[1]
    if len(encoded) > (MAX_SOURCE_BYTES * 4 // 3) + 8:
        raise SourceImageError("source_data_url exceeds the 64 MiB decoded limit")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SourceImageError("source_data_url contains invalid base64") from exc
    if not payload or len(payload) > MAX_SOURCE_BYTES:
        raise SourceImageError("source_data_url exceeds the 64 MiB decoded limit")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.format != "PNG":
                raise SourceImageError("source_data_url must contain a PNG")
            if image.width * image.height > MAX_SOURCE_PIXELS:
                raise SourceImageError("Source image exceeds the 4096 x 4096 demo limit")
            image.verify()
    except SourceImageError:
        raise
    except Exception as exc:
        raise SourceImageError("source_data_url is not a valid PNG") from exc
    return payload


def load_source_image(path: str | Path | None = None, payload: bytes | None = None) -> Image.Image:
    if payload is not None:
        stream: Any = io.BytesIO(payload)
    elif path is not None:
        source_path = Path(path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Source paint file not found: {source_path}")
        if source_path.stat().st_size > 512 * 1024 * 1024:
            raise SourceImageError("Source paint file exceeds the 512 MiB demo limit")
        if source_path.suffix.lower() in {".psd", ".psb"}:
            try:
                from psd_tools import PSDImage
            except ImportError as exc:
                raise SourceImageError("psd-tools is required to open PSD source files") from exc
            image = PSDImage.open(source_path).composite()
            if image is None:
                raise SourceImageError("PSD has no flattened composite")
            result = image.convert("RGBA")
            if result.width * result.height > MAX_SOURCE_PIXELS:
                raise SourceImageError("Source image exceeds the 4096 x 4096 demo limit")
            return result
        stream = source_path
    else:
        raise SourceImageError("paint_file or source_data_url is required")

    try:
        with Image.open(stream) as image:
            if image.width * image.height > MAX_SOURCE_PIXELS:
                raise SourceImageError("Source image exceeds the 4096 x 4096 demo limit")
            image.load()
            return image.convert("RGBA")
    except SourceImageError:
        raise
    except Exception as exc:
        raise SourceImageError(f"Unable to read source paint image: {exc}") from exc


def png_bytes(image: Image.Image, *, compress_level: int = 3) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG", compress_level=max(0, min(9, int(compress_level))))
    return buffer.getvalue()


def png_data_url(image: Image.Image, *, compress_level: int = 3) -> str:
    encoded = base64.b64encode(png_bytes(image, compress_level=compress_level)).decode("ascii")
    return "data:image/png;base64," + encoded


def image_from_rgb(array: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="RGB")


def image_from_rgba(array: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="RGBA")

