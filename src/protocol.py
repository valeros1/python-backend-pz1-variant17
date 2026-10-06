"""Кодирование сообщений RPC из таблицы 17 задания."""

import json

VERSION = 1
MIN_OPCODE = 0
MAX_OPCODE = 255
REQUEST_HEADER_SIZE = 7
RESPONSE_HEADER_SIZE = 5
MAX_BODY_SIZE = 1024 * 1024

OPERATIONS = (
    "create_member", "get_members", "update_member", "delete_member",
    "create_query", "get_queries", "update_query", "delete_query",
    "create_response", "get_responses", "update_response",
    "delete_response", "select_recent_responses",
)
OPCODES = {name: code for code, name in enumerate(OPERATIONS, 1)}
NAMES = {code: name for name, code in OPCODES.items()}


class ProtocolError(ValueError):
    """Ошибка структуры сообщения или JSON-тела."""


def _body(payload: dict) -> bytes:
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    if len(data) > MAX_BODY_SIZE:
        raise ProtocolError("Тело сообщения слишком велико")
    return data


def read_exact(sock, count: int, allow_eof: bool = False) -> bytes | None:
    """Прочитать ровно count байтов; EOF допустим только до заголовка."""
    data = bytearray()
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            if allow_eof and not data:
                return None
            raise ProtocolError("Соединение закрыто посреди сообщения")
        data.extend(chunk)
    return bytes(data)


def _read_body(sock, count: int) -> dict:
    if count > MAX_BODY_SIZE:
        raise ProtocolError("Тело сообщения слишком велико")
    try:
        result = json.loads(read_exact(sock, count).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ProtocolError("Некорректное JSON-тело") from error
    if not isinstance(result, dict):
        raise ProtocolError("JSON-тело должно быть объектом")
    return result


def pack_request(opcode: int, params: dict) -> bytes:
    """Собрать запрос: version(1), opcode(1), length(5), JSON."""
    if not MIN_OPCODE <= opcode <= MAX_OPCODE:
        raise ProtocolError("Недопустимый код операции")
    body = _body(params)
    return bytes((VERSION, opcode)) + len(body).to_bytes(5, "big") + body


def read_request(sock) -> tuple[int, int, dict] | None:
    """Прочитать запрос или None при закрытом соединении."""
    first = read_exact(sock, 1, allow_eof=True)
    if first is None:
        return None
    rest = read_exact(sock, REQUEST_HEADER_SIZE - 1)
    header = first + rest
    size = int.from_bytes(header[2:7], "big")
    return header[0], header[1], _read_body(sock, size)


def pack_response(opcode: int, payload: dict) -> bytes:
    """Собрать ответ: length(4), opcode(1), JSON."""
    if not MIN_OPCODE <= opcode <= MAX_OPCODE:
        raise ProtocolError("Недопустимый код операции")
    body = _body(payload)
    return len(body).to_bytes(4, "big") + bytes((opcode,)) + body


def read_response(sock) -> tuple[int, dict]:
    """Прочитать ответ сервера из TCP-потока."""
    header = read_exact(sock, RESPONSE_HEADER_SIZE)
    size = int.from_bytes(header[:4], "big")
    return header[4], _read_body(sock, size)
