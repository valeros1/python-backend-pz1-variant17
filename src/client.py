"""Клиент RPC с теми же 13 именами операций, что и у модели."""

import socket

from src import protocol


class RpcError(Exception):
    """Ошибка модели или протокола, возвращённая сервером."""


class RpcClient:
    """Одно TCP-соединение для последовательных вызовов."""

    def __init__(self, host="127.0.0.1", port=5017, timeout=5):
        self.socket = socket.create_connection((host, port), timeout)

    def close(self):
        """Закрыть соединение."""
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _call(self, name, **params):
        opcode = protocol.OPCODES[name]
        self.socket.sendall(protocol.pack_request(opcode, params))
        received, payload = protocol.read_response(self.socket)
        if received != opcode:
            raise RpcError("Сервер вернул другой код операции")
        if "error" in payload:
            error = payload["error"]
            raise RpcError(f"{error['type']}: {error['message']}")
        return payload["result"]

    def create_member(self, ip, locale, platform, datetime=None):
        return self._call("create_member", ip=ip, locale=locale,
                          platform=platform, datetime=datetime)

    def get_members(self):
        return self._call("get_members")

    def update_member(self, identifier, changes):
        return self._call("update_member", identifier=identifier,
                          changes=changes)

    def delete_member(self, identifier):
        return self._call("delete_member", identifier=identifier)

    def create_query(self, argument, member, description, executing,
                     datetime=None):
        return self._call("create_query", argument=argument, member=member,
                          description=description, executing=executing,
                          datetime=datetime)

    def get_queries(self):
        return self._call("get_queries")

    def update_query(self, identifier, changes):
        return self._call("update_query", identifier=identifier,
                          changes=changes)

    def delete_query(self, identifier):
        return self._call("delete_query", identifier=identifier)

    def create_response(self, output, status, exception, query, cache_hit,
                        duration, datetime=None):
        return self._call(
            "create_response", output=output, status=status,
            exception=exception, query=query, cache_hit=cache_hit,
            duration=duration, datetime=datetime,
        )

    def get_responses(self):
        return self._call("get_responses")

    def update_response(self, identifier, changes):
        return self._call("update_response", identifier=identifier,
                          changes=changes)

    def delete_response(self, identifier):
        return self._call("delete_response", identifier=identifier)

    def select_recent_responses(self, now=None):
        return self._call("select_recent_responses", now=now)
