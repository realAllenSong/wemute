from __future__ import annotations

import ctypes
import platform
import plistlib
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, Slot


class SparkleUpdater(QObject):
    """Small Objective-C bridge to Sparkle without a PyObjC runtime dependency."""

    def __init__(self) -> None:
        super().__init__()
        self._controller: int | None = None
        self._framework: ctypes.CDLL | None = None
        self._objc: ctypes.CDLL | None = None
        self._available = self._start()

    @staticmethod
    def _contents_root() -> Path | None:
        if not getattr(sys, "frozen", False):
            return None
        executable = Path(sys.executable).resolve()
        if executable.parent.name != "MacOS":
            return None
        return executable.parent.parent

    def _start(self) -> bool:
        if platform.system() != "Darwin":
            return False
        contents = self._contents_root()
        if contents is None:
            return False
        info_path = contents / "Info.plist"
        framework_binary = contents / "Frameworks" / "Sparkle.framework" / "Versions" / "B" / "Sparkle"
        try:
            with info_path.open("rb") as stream:
                info = plistlib.load(stream)
            if not info.get("SUFeedURL") or not info.get("SUPublicEDKey"):
                return False
            self._framework = ctypes.CDLL(str(framework_binary), mode=ctypes.RTLD_GLOBAL)
            self._objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
            self._objc.objc_getClass.argtypes = [ctypes.c_char_p]
            self._objc.objc_getClass.restype = ctypes.c_void_p
            self._objc.sel_registerName.argtypes = [ctypes.c_char_p]
            self._objc.sel_registerName.restype = ctypes.c_void_p
            controller_class = self._objc.objc_getClass(b"SPUStandardUpdaterController")
            if not controller_class:
                return False
            allocated = self._send_id(controller_class, b"alloc")
            self._controller = self._send_id_bool_objects(
                allocated,
                b"initWithStartingUpdater:updaterDelegate:userDriverDelegate:",
                True,
                None,
                None,
            )
            return bool(self._controller)
        except (OSError, ValueError, plistlib.InvalidFileException):
            self._controller = None
            return False

    def _selector(self, name: bytes) -> int:
        assert self._objc is not None
        return int(self._objc.sel_registerName(name))

    def _send_id(self, receiver: int, selector: bytes) -> int:
        assert self._objc is not None
        function = self._objc.objc_msgSend
        function.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        function.restype = ctypes.c_void_p
        return int(function(receiver, self._selector(selector)) or 0)

    def _send_id_bool_objects(
        self,
        receiver: int,
        selector: bytes,
        flag: bool,
        first: int | None,
        second: int | None,
    ) -> int:
        assert self._objc is not None
        function = self._objc.objc_msgSend
        function.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        function.restype = ctypes.c_void_p
        return int(function(receiver, self._selector(selector), flag, first, second) or 0)

    @Property(bool, constant=True)
    def available(self) -> bool:
        return self._available

    @Slot()
    def checkForUpdates(self) -> None:
        if not self._controller or not self._objc:
            return
        function = self._objc.objc_msgSend
        function.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        function.restype = None
        function(self._controller, self._selector(b"checkForUpdates:"), None)

    def shutdown(self) -> None:
        if not self._controller or not self._objc:
            return
        function = self._objc.objc_msgSend
        function.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        function.restype = None
        function(self._controller, self._selector(b"release"))
        self._controller = None
