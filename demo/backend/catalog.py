"""Manifest-backed demo catalogue.

This module deliberately reads only ``demo/product-manifest.json``.  The paid
application's registry and server modules are build-time inputs, never runtime
dependencies of SHOKK DEMO.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA = "spb-demo-product/1"
EXPECTED_VISIBLE_COUNT = 29
EXPECTED_RENDERABLE_COUNT = 30


class ManifestError(ValueError):
    """Raised when the immutable product manifest is internally inconsistent."""


@dataclass(frozen=True)
class DemoFinish:
    id: str
    name: str
    category: str
    kind: str
    swatch: str
    visible: bool
    access: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DemoFinish":
        finish_id = str(value.get("id") or "").strip()
        name = str(value.get("name") or "").strip()
        category = str(value.get("category") or "").strip()
        kind = str(value.get("kind") or "").strip().lower()
        swatch = str(value.get("swatch") or "").strip()
        if not finish_id or not name or not category:
            raise ManifestError("Every demo finish needs id, name, and category")
        if kind not in {"base", "monolithic"}:
            raise ManifestError(f"Unsupported finish kind for {finish_id}: {kind!r}")
        if not swatch.startswith("#") or len(swatch) not in {4, 7}:
            raise ManifestError(f"Finish {finish_id} must use a static hex swatch")
        return cls(
            id=finish_id,
            name=name,
            category=category,
            kind=kind,
            swatch=swatch.lower(),
            visible=bool(value.get("visible", True)),
            access=(str(value["access"]) if value.get("access") else None),
        )

    def picker_entry(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "swatch": self.swatch,
            "thumbnail": f"/demo-assets/thumbnails/{self.id}.png",
            "type": self.kind,
        }


class DemoCatalog:
    """Validated read-only catalogue and capability view."""

    def __init__(self, manifest_path: str | Path):
        self.path = Path(manifest_path).resolve()
        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict) or raw.get("schema") != MANIFEST_SCHEMA:
            raise ManifestError(f"Expected manifest schema {MANIFEST_SCHEMA!r}")

        finishes: "OrderedDict[str, DemoFinish]" = OrderedDict()
        for item in raw.get("finishes", []):
            if not isinstance(item, dict):
                raise ManifestError("Manifest finishes must be JSON objects")
            finish = DemoFinish.from_dict(item)
            if finish.id in finishes:
                raise ManifestError(f"Duplicate demo finish id: {finish.id}")
            finishes[finish.id] = finish

        visible = [finish for finish in finishes.values() if finish.visible]
        if len(visible) != EXPECTED_VISIBLE_COUNT:
            raise ManifestError(
                f"SHOKK DEMO must expose exactly {EXPECTED_VISIBLE_COUNT} finishes; "
                f"found {len(visible)}"
            )
        if len(finishes) != EXPECTED_RENDERABLE_COUNT:
            raise ManifestError(
                f"SHOKK DEMO must render exactly {EXPECTED_RENDERABLE_COUNT} finishes; "
                f"found {len(finishes)}"
            )
        hidden = [finish for finish in finishes.values() if not finish.visible]
        if [finish.id for finish in hidden] != ["fs_core_emerald"]:
            raise ManifestError("fs_core_emerald must be the only hidden renderable finish")

        capabilities = raw.get("capabilities")
        if not isinstance(capabilities, dict):
            raise ManifestError("Manifest capabilities are missing")
        if capabilities.get("patterns") is not False:
            raise ManifestError("Demo manifest must disable regular patterns")
        if capabilities.get("spec_patterns") is not False:
            raise ManifestError("Demo manifest must disable spec patterns")
        if int(capabilities.get("extra_base_overlays", -1)) != 0:
            raise ManifestError("Demo manifest must disable extra base overlays")

        self.raw = raw
        self.finishes = finishes

    @property
    def visible(self) -> list[DemoFinish]:
        return [finish for finish in self.finishes.values() if finish.visible]

    @property
    def renderable_ids(self) -> frozenset[str]:
        return frozenset(self.finishes)

    @property
    def visible_ids(self) -> tuple[str, ...]:
        return tuple(finish.id for finish in self.visible)

    def get(self, finish_id: str) -> DemoFinish | None:
        return self.finishes.get(str(finish_id or "").strip())

    def picker_payload(self) -> dict[str, Any]:
        bases = [finish.picker_entry() for finish in self.visible if finish.kind == "base"]
        specials = [
            finish.picker_entry() for finish in self.visible if finish.kind == "monolithic"
        ]
        base_groups = self._groups(finish for finish in self.visible if finish.kind == "base")
        special_groups = self._groups(
            finish for finish in self.visible if finish.kind == "monolithic"
        )
        return {
            "bases": bases,
            "patterns": [],
            "specials": specials,
            "groups": {
                "bases": base_groups,
                "patterns": {},
                "specials": special_groups,
            },
            "counts": {
                "bases": len(bases),
                "patterns": 0,
                "specials": len(specials),
                "total": len(bases) + len(specials),
            },
        }

    @staticmethod
    def _groups(finishes: Iterable[DemoFinish]) -> dict[str, list[str]]:
        groups: "OrderedDict[str, list[str]]" = OrderedDict()
        for finish in finishes:
            groups.setdefault(finish.category, []).append(finish.id)
        return dict(groups)
