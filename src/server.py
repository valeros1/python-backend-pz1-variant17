"""Многопоточный RPC-сервер по TCP."""

import json
import os
import socketserver
import threading
from datetime import datetime, timezone
from pathlib import Path

from src import model, protocol


def _json_value(value):
    if isinstance(value, tuple) and hasattr(value, "_asdict"):
        return value._asdict()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


class RpcServer(socketserver.ThreadingTCPServer):
    """Сервер с общей моделью и журналом запросов."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, journal_path="journal.log"):
        self.journal_path = Path(journal_path)
        self.model_lock = threading.Lock()
        self.journal_lock = threading.Lock()
        super().__init__(address, RpcHandler)

    def journal(self, **event):
        """Добавить одну JSON-строку о запросе в journal.log."""
        event["time"] = datetime.now(timezone.utc).isoformat()
        with self.journal_lock:
            with self.journal_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=True) + "\n")


class RpcHandler(socketserver.BaseRequestHandler):
    """Обслуживать последовательность RPC-запросов в одном соединении."""

    def handle(self):
        """Читать пакеты до закрытия соединения клиентом."""
        while True:
            try:
                request = protocol.read_request(self.request)
            except protocol.ProtocolError as error:
                self.server.journal(error=str(error))
                return
            if request is None:
                return
            version, opcode, params = request
            self.server.journal(version=version, opcode=opcode,
                                params=params)
            payload = self._dispatch(version, opcode, params)
            self.request.sendall(protocol.pack_response(opcode, payload))

    def _dispatch(self, version, opcode, params):
        if version != protocol.VERSION:
            return self._error("ProtocolError", "Неизвестная версия")
        name = protocol.NAMES.get(opcode)
        if name is None:
            return self._error("ProtocolError", "Неизвестная операция")
        try:
            with self.server.model_lock:
                result = getattr(model, name)(**params)
        except (model.ModelError, TypeError) as error:
            return self._error(type(error).__name__, str(error))
        return {"result": _json_value(result)}

    @staticmethod
    def _error(name, message):
        return {"error": {"type": name, "message": message}}


def main():
    """Запустить сервер с настройками из окружения."""
    host = os.getenv("RPC_HOST", "127.0.0.1")
    port = int(os.getenv("RPC_PORT", "5017"))
    with RpcServer((host, port)) as server:
        print("RPC сервер: {}:{}".format(host, port))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nСервер остановлен")


if __name__ == "__main__":
    main()
