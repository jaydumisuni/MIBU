from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGate(QObject):
    """Own one local MIBU process and activate it on duplicate launch."""

    activate_requested = Signal()

    def __init__(self, name: str = "THETECHGUY.MIBU.PCHelper") -> None:
        super().__init__()
        self.name = name
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._handle_connection)
        self._owns_server = False
        self._mutex_handle: int | None = None

    def _acquire_platform_lock(self) -> bool:
        if sys.platform != "win32":
            return True

        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_bool,
            ctypes.c_wchar_p,
        ]
        create_mutex.restype = ctypes.c_void_p

        handle = create_mutex(
            None,
            False,
            "Local\\" + self.name,
        )
        if not handle:
            raise OSError(
                ctypes.get_last_error(),
                "CreateMutexW failed for MIBU single-instance lock",
            )

        ERROR_ALREADY_EXISTS = 183
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return False

        self._mutex_handle = int(handle)
        return True

    def _release_platform_lock(self) -> None:
        if self._mutex_handle is None or sys.platform != "win32":
            return

        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(ctypes.c_void_p(self._mutex_handle))
        self._mutex_handle = None

    def _request_activation(self) -> None:
        probe = QLocalSocket()
        probe.connectToServer(self.name)
        if probe.waitForConnected(350):
            probe.write(b"activate\n")
            probe.flush()
            probe.waitForBytesWritten(350)
            probe.disconnectFromServer()

    def acquire(self) -> bool:
        if not self._acquire_platform_lock():
            self._request_activation()
            return False

        if self.server.listen(self.name):
            self._owns_server = True
            return True

        # Unix-domain sockets can survive an unclean exit. The Win32 mutex
        # above already proves exclusive ownership before this cleanup.
        QLocalServer.removeServer(self.name)
        self._owns_server = self.server.listen(self.name)
        if not self._owns_server:
            self._release_platform_lock()
        return self._owns_server

    def _handle_connection(self) -> None:
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                break
            self.activate_requested.emit()
            socket.disconnectFromServer()
            socket.deleteLater()

    def close(self) -> None:
        if self._owns_server:
            if self.server.isListening():
                self.server.close()
            QLocalServer.removeServer(self.name)
            self._owns_server = False
        self._release_platform_lock()
