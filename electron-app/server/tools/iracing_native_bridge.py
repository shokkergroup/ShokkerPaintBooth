#!/usr/bin/env python
"""Small JSON-lines bridge for the locally installed iRacing viewer DLL.

This does not ship or unpack iRacing assets. It only talks to a user's own
installed iRacingViewer.dll and mirrors the command shape used by iRacing's
Electron UI closely enough for SHOKKER to experiment with an exact preview
bridge.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Callable


DEFAULT_ROOTS = [
    Path(os.environ.get("IRACING_ROOT", "")) if os.environ.get("IRACING_ROOT") else None,
    Path(r"C:\iRacing"),
    Path(r"D:\iRacing"),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "iRacing",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "iRacing",
]

VIEWER_FUNCS = [
    "iRacingHostRegister",
    "iRacingHostDeregister",
    "isIRacingUIRegistered",
    "isTransparencyEnabled",
    "onNotifyMsgRecv",
    "viewerSupportBegin",
    "viewerSupportEnd",
    "viewerSetPathDetails",
    "viewerSetFrameWindowBGColor",
    "viewerCreateView",
    "viewerDeleteView",
    "viewerRepositionView",
    "viewerLoadBackgroundObject",
    "viewerLoadObject",
    "viewerPaintWheelsDefault",
    "viewerPaintWheelsCustom",
    "viewerPaintItem",
    "viewerSetDriverHeadType",
    "getCarWebImage",
]


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), flush=True)


def bstr(value: Any) -> bytes:
    return str(value if value is not None else "").encode("utf-8", "replace")


def as_bool(value: Any) -> bool:
    return bool(value)


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def find_iracing_root() -> Path | None:
    for candidate in DEFAULT_ROOTS:
        if not candidate:
            continue
        try:
            ui_dir = candidate / "ui"
            dll = ui_dir / "iRacingViewer.dll"
            if dll.exists():
                return candidate
        except Exception:
            continue
    return None


def find_iracing_ui_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    try:
        out = subprocess.check_output(
            [
                "tasklist",
                "/FI",
                "IMAGENAME eq iRacingUI.exe",
                "/FO",
                "CSV",
                "/NH",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception:
        return []
    processes: list[dict[str, Any]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "No tasks are running" in line:
            continue
        try:
            parts = [p.strip().strip('"') for p in line.split('","')]
            if len(parts) >= 2 and parts[0].lower() == "iracingui.exe":
                processes.append({"name": parts[0], "pid": as_int(parts[1], 0)})
        except Exception:
            continue
    return processes


def decode_registration_char(raw: Any) -> dict[str, Any]:
    text = raw.decode("latin1", "ignore") if isinstance(raw, bytes) else str(raw)
    code = ord(text[0]) if text else 0
    return {"raw": text, "code": code, "truthy": code != 0}


class NativeBridge:
    def __init__(self) -> None:
        self.root: Path | None = None
        self.ui_dir: Path | None = None
        self.dll_path: Path | None = None
        self.dll: ctypes.WinDLL | None = None
        self.funcs: dict[str, Callable[..., Any]] = {}
        self.attached_hwnd: int | None = None
        self.view_created = False
        self.last_car_path = ""

    def load(self) -> None:
        if self.dll:
            return
        root = find_iracing_root()
        if not root:
            raise RuntimeError("iRacingViewer.dll was not found in the standard local iRacing folders.")
        ui_dir = root / "ui"
        dll_path = ui_dir / "iRacingViewer.dll"
        self.root = root
        self.ui_dir = ui_dir
        self.dll_path = dll_path
        try:
            os.add_dll_directory(str(root))
            os.add_dll_directory(str(ui_dir))
        except Exception:
            pass
        try:
            ctypes.windll.kernel32.SetDllDirectoryW(str(ui_dir))
        except Exception:
            pass
        try:
            os.chdir(str(ui_dir))
        except Exception:
            pass
        self.dll = ctypes.WinDLL(str(dll_path))
        self.bind_functions()

    def bind(self, name: str, restype: Any, argtypes: list[Any]) -> None:
        if not self.dll:
            return
        try:
            func = getattr(self.dll, name)
        except AttributeError:
            return
        func.restype = restype
        func.argtypes = argtypes
        self.funcs[name] = func

    def bind_functions(self) -> None:
        c_int = ctypes.c_int
        c_bool = ctypes.c_bool
        c_char_p = ctypes.c_char_p
        c_uint64 = ctypes.c_uint64

        self.bind("iRacingHostRegister", c_bool, [c_uint64])
        self.bind("iRacingHostDeregister", None, [])
        self.bind("isIRacingUIRegistered", ctypes.c_char, [])
        self.bind("isTransparencyEnabled", c_bool, [])
        self.bind("onNotifyMsgRecv", None, [c_int])
        self.bind("viewerSupportBegin", c_bool, [c_uint64])
        self.bind("viewerSupportEnd", None, [])
        self.bind("viewerSetPathDetails", c_bool, [c_char_p])
        self.bind("viewerSetFrameWindowBGColor", None, [c_char_p])
        self.bind("viewerCreateView", c_bool, [c_int, c_int, c_int, c_int, c_int])
        self.bind("viewerDeleteView", c_bool, [c_int])
        self.bind("viewerRepositionView", c_bool, [c_int, c_int, c_int, c_int, c_int])
        self.bind("viewerLoadBackgroundObject", c_bool, [c_int, c_char_p, c_char_p])
        self.bind("viewerLoadObject", c_bool, [c_int, c_int, c_char_p, c_char_p, c_int, c_char_p, c_char_p])
        self.bind("viewerPaintWheelsDefault", c_bool, [c_int])
        self.bind("viewerPaintWheelsCustom", c_bool, [c_int, c_char_p, c_int])
        self.bind(
            "viewerPaintItem",
            c_bool,
            [
                c_int,
                c_int,
                c_int,
                c_char_p,
                c_char_p,
                c_char_p,
                c_char_p,
                c_int,
                c_bool,
                c_bool,
                c_int,
                c_int,
                c_char_p,
                c_char_p,
                c_char_p,
                c_char_p,
                c_int,
                c_int,
                c_int,
                c_bool,
                c_char_p,
                c_bool,
            ],
        )
        self.bind("viewerSetDriverHeadType", None, [c_int, c_int])

    def require(self, name: str) -> Callable[..., Any]:
        self.load()
        func = self.funcs.get(name)
        if not func:
            raise RuntimeError(f"iRacingViewer.dll export is unavailable: {name}")
        return func

    def status(self) -> dict[str, Any]:
        root = find_iracing_root()
        payload: dict[str, Any] = {
            "root": str(root) if root else None,
            "dll": str(root / "ui" / "iRacingViewer.dll") if root else None,
            "loaded": False,
            "attached_hwnd": self.attached_hwnd,
            "view_created": self.view_created,
            "last_car_path": self.last_car_path,
            "iracing_ui_processes": find_iracing_ui_processes(),
            "functions": [],
        }
        if root:
            self.load()
            payload["loaded"] = bool(self.dll)
            payload["functions"] = sorted(self.funcs.keys())
            if "isTransparencyEnabled" in self.funcs:
                payload["transparency_enabled"] = as_bool(self.funcs["isTransparencyEnabled"]())
            if "isIRacingUIRegistered" in self.funcs:
                raw = self.funcs["isIRacingUIRegistered"]()
                registration = decode_registration_char(raw)
                payload["ui_registered_raw"] = registration["raw"]
                payload["ui_registered_code"] = registration["code"]
                payload["ui_registered"] = registration["truthy"]
        return payload

    def attach(self, data: dict[str, Any]) -> dict[str, Any]:
        hwnd = as_int(data.get("hwnd"), 0)
        if hwnd <= 0:
            raise RuntimeError("A valid Electron native window handle is required.")
        registered = as_bool(self.require("iRacingHostRegister")(hwnd))
        supported = as_bool(self.require("viewerSupportBegin")(hwnd))
        self.attached_hwnd = hwnd if registered or supported else None
        bg = str(data.get("background") or "000000").lstrip("#")[:6] or "000000"
        if "viewerSetFrameWindowBGColor" in self.funcs:
            self.funcs["viewerSetFrameWindowBGColor"](bstr(bg))
        running_ui = find_iracing_ui_processes()
        hint = ""
        if not registered and not supported and running_ui:
            hint = "iRacingUI.exe is already running and may own the only native preview host. Close iRacing UI, then retry Test Bridge."
        elif not registered and not supported:
            hint = "The DLL rejected this Electron window handle. The next fallback is an in-process Koffi bridge."
        return {
            "hwnd": hwnd,
            "registered": registered,
            "support_begin": supported,
            "background": bg,
            "iracing_ui_processes": running_ui,
            "hint": hint,
        }

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.attached_hwnd and data.get("hwnd"):
            self.attach(data)
        view = as_int(data.get("view"), 0)
        x = max(0, as_int(data.get("x"), 0))
        y = max(0, as_int(data.get("y"), 0))
        width = max(100, as_int(data.get("width"), 900))
        height = max(100, as_int(data.get("height"), 620))
        created = as_bool(self.require("viewerCreateView")(view, x, y, width, height))
        self.view_created = created or self.view_created
        background_ok = None
        if data.get("load_background", True) and "viewerLoadBackgroundObject" in self.funcs:
            background_ok = as_bool(self.funcs["viewerLoadBackgroundObject"](view, b"cars", b"ui_bg.3do"))
        return {"view": view, "created": created, "background_loaded": background_ok, "rect": [x, y, width, height]}

    def resize(self, data: dict[str, Any]) -> dict[str, Any]:
        view = as_int(data.get("view"), 0)
        x = max(0, as_int(data.get("x"), 0))
        y = max(0, as_int(data.get("y"), 0))
        width = max(100, as_int(data.get("width"), 900))
        height = max(100, as_int(data.get("height"), 620))
        ok = as_bool(self.require("viewerRepositionView")(view, x, y, width, height))
        return {"view": view, "resized": ok, "rect": [x, y, width, height]}

    def load_object(self, data: dict[str, Any]) -> dict[str, Any]:
        view = as_int(data.get("view"), 0)
        item_type = as_int(data.get("type"), 0)
        raw_path = str(data.get("objPath") or data.get("carPath") or "cars\\stockcars2\\camaro2019").replace("/", "\\").strip("\\")
        car_cfg = as_int(data.get("carCfg"), -1)
        sub_dir = data.get("carCfgSubDir") or ""
        paint_ext = data.get("carCfgCustomPaintExt") or ""
        if item_type == 0:
            candidates = [raw_path]
            lower_path = raw_path.lower()
            if lower_path.startswith("cars\\"):
                candidates.append(raw_path[5:])
            else:
                candidates.append(f"cars\\{raw_path}")
            attempts: list[dict[str, Any]] = []
            ok = False
            obj_path = raw_path
            obj_name = ""
            load_object = self.require("viewerLoadObject")
            for candidate in dict.fromkeys(candidates):
                obj_path = candidate
                obj_base = obj_path.rsplit("\\", 1)[-1]
                obj_name = f"{obj_base}_ui.3do"
                attempt_ok = as_bool(
                    load_object(
                        view,
                        item_type,
                        bstr(obj_path),
                        bstr(obj_name),
                        car_cfg,
                        bstr(sub_dir),
                        bstr(paint_ext),
                    )
                )
                attempts.append({"obj_path": obj_path, "obj_name": obj_name, "loaded": attempt_ok})
                if attempt_ok:
                    ok = True
                    break
            self.last_car_path = obj_path
            return {
                "view": view,
                "type": item_type,
                "obj_path": obj_path,
                "obj_name": obj_name,
                "loaded": ok,
                "attempts": attempts,
                "car_cfg": car_cfg,
                "car_cfg_sub_dir": sub_dir,
                "paint_ext": paint_ext,
            }
        elif item_type == 1:
            obj_path = "cars"
            obj_name = f"driver_body_0{raw_path or '1'}_ui_anim.3do"
        elif item_type == 2:
            obj_path = "cars"
            obj_name = "driver_helmet.3do"
        else:
            raise RuntimeError(f"Unsupported iRacing object type: {item_type}")
        ok = as_bool(
            self.require("viewerLoadObject")(
                view,
                item_type,
                bstr(obj_path),
                bstr(obj_name),
                car_cfg,
                bstr(sub_dir),
                bstr(paint_ext),
            )
        )
        return {
            "view": view,
            "type": item_type,
            "obj_path": obj_path,
            "obj_name": obj_name,
            "loaded": ok,
            "car_cfg": car_cfg,
            "car_cfg_sub_dir": sub_dir,
            "paint_ext": paint_ext,
        }

    def paint_item(self, data: dict[str, Any]) -> dict[str, Any]:
        item_type = as_int(data.get("itemType"), 0)
        result = as_bool(
            self.require("viewerPaintItem")(
                0,
                item_type,
                as_int(data.get("pattern"), 0),
                bstr(data.get("color1") or "000000"),
                bstr(data.get("color2") or "000000"),
                bstr(data.get("color3") or "000000"),
                bstr(data.get("licenseColor") or "FFFFFF"),
                as_int(data.get("cust_id"), 0),
                bool(data.get("allowCustomPaint", True)),
                bool(data.get("skipDecals", False)),
                as_int(data.get("number_font"), 0),
                as_int(data.get("number_slant"), 0),
                bstr(data.get("number_color1") or "000000"),
                bstr(data.get("number_color2") or "000000"),
                bstr(data.get("number_color3") or "000000"),
                bstr(data.get("car_number") or "64"),
                as_int(data.get("sponsor1"), 0),
                as_int(data.get("sponsor2"), 0),
                as_int(data.get("club_id"), 0),
                bool(data.get("skipStamps", False)),
                bstr(data.get("onCarName") or ""),
                bool(data.get("skipName", False)),
            )
        )
        wheel_ok = None
        if item_type == 0:
            wheel_color = data.get("wheelColor")
            wheel_id = data.get("wheelId")
            if wheel_color and wheel_id is not None and "viewerPaintWheelsCustom" in self.funcs:
                wheel_ok = as_bool(self.funcs["viewerPaintWheelsCustom"](0, bstr(wheel_color), as_int(wheel_id, 0)))
            elif "viewerPaintWheelsDefault" in self.funcs:
                wheel_ok = as_bool(self.funcs["viewerPaintWheelsDefault"](0))
        return {"painted": result, "wheels": wheel_ok, "item_type": item_type}

    def notify(self, data: dict[str, Any]) -> dict[str, Any]:
        message = as_int(data.get("message"), 0)
        if "onNotifyMsgRecv" in self.funcs:
            self.funcs["onNotifyMsgRecv"](message)
            return {"forwarded": True, "message": message}
        return {"forwarded": False, "message": message}

    def shutdown(self) -> dict[str, Any]:
        deleted = None
        if self.view_created and "viewerDeleteView" in self.funcs:
            deleted = as_bool(self.funcs["viewerDeleteView"](0))
        if "viewerSupportEnd" in self.funcs:
            self.funcs["viewerSupportEnd"]()
        if "iRacingHostDeregister" in self.funcs:
            self.funcs["iRacingHostDeregister"]()
        self.attached_hwnd = None
        self.view_created = False
        return {"deleted": deleted, "support_ended": True}


bridge = NativeBridge()


COMMANDS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "status": lambda data: bridge.status(),
    "attach": bridge.attach,
    "create": bridge.create,
    "resize": bridge.resize,
    "load": bridge.load_object,
    "paint": bridge.paint_item,
    "notify": bridge.notify,
    "shutdown": lambda data: bridge.shutdown(),
}


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    command = str(payload.get("command") or "")
    if command not in COMMANDS:
        raise RuntimeError(f"Unknown command: {command}")
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {k: v for k, v in payload.items() if k not in ("id", "command")}
    return COMMANDS[command](data)


def main() -> int:
    emit({"kind": "ready", "success": True, "pid": os.getpid(), "commands": sorted(COMMANDS)})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request_id = None
        try:
            payload = json.loads(line)
            request_id = payload.get("id")
            result = handle(payload)
            emit({"id": request_id, "success": True, "result": result})
        except Exception as exc:
            emit(
                {
                    "id": request_id,
                    "success": False,
                    "error": str(exc),
                    "trace": traceback.format_exc(limit=4),
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
