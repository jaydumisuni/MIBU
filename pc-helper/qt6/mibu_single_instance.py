from __future__ import annotations

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

    def acquire(self) -> bool:
        if self.server.listen(self.name):
            self._owns_server = True
            return True

        probe = QLocalSocket()
        probe.connectToServer(self.name)
        if probe.waitForConnected(250):
            probe.write(b"activate\n")
            probe.flush()
            probe.waitForBytesWritten(250)
            probe.disconnectFromServer()
            return False

        QLocalServer.removeServer(self.name)
        self._owns_server = self.server.listen(self.name)
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
        if not self._owns_server:
            return
        if self.server.isListening():
            self.server.close()
        QLocalServer.removeServer(self.name)
        self._owns_server = False
