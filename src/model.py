"""Три связанные таблицы в памяти и выборка по варианту 17."""

import time
from typing import NamedTuple

RECENT_SECONDS = 7 * 60


class ModelError(ValueError):
    """Некорректная операция над данными."""


class Member(NamedTuple):
    """Строка Member."""

    identifier: int
    datetime: int
    ip: str
    locale: str
    platform: str


class Query(NamedTuple):
    """Строка Query; member ссылается на Member.identifier."""

    identifier: int
    datetime: int
    argument: str
    member: int
    description: str
    executing: int


class Response(NamedTuple):
    """Строка Response; query ссылается на Query.identifier."""

    identifier: int
    datetime: int
    output: str
    status: str
    exception: str
    query: int
    cache_hit: int
    duration: int


class RecentResponse(NamedTuple):
    """Результат проекции из формулы варианта."""

    argument: str | None
    cache_hit: int
    status: str


_members: dict[int, Member] = {}
_queries: dict[int, Query] = {}
_responses: dict[int, Response] = {}
_next_ids = {"member": 1, "query": 1, "response": 1}


def reset() -> None:
    """Очистить состояние между независимыми запусками тестовой модели."""
    _members.clear()
    _queries.clear()
    _responses.clear()
    _next_ids.update(member=1, query=1, response=1)


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise ModelError(f"{field} должен быть целым числом")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ModelError(f"{field} должен быть строкой")
    return value


def _stamp(value: int | None) -> int:
    return int(time.time()) if value is None else _integer(value, "datetime")


def _new_id(name: str) -> int:
    identifier = _next_ids[name]
    _next_ids[name] += 1
    return identifier


def _find(table: dict, identifier: int, name: str):
    _integer(identifier, "identifier")
    try:
        return table[identifier]
    except KeyError as error:
        raise ModelError(f"{name} #{identifier} не найден") from error


def _changes(changes: dict, fields: dict[str, type]) -> dict:
    if not isinstance(changes, dict) or not changes:
        raise ModelError("Нужно указать изменяемые поля")
    unknown = changes.keys() - fields.keys()
    if unknown:
        raise ModelError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
    result = {}
    for field, value in changes.items():
        result[field] = (
            _integer(value, field) if fields[field] is int
            else _text(value, field)
        )
    return result


def create_member(ip: str, locale: str, platform: str,
                  datetime: int | None = None) -> Member:
    """Создать Member с новым идентификатором."""
    values = (_stamp(datetime), _text(ip, "ip"),
              _text(locale, "locale"), _text(platform, "platform"))
    record = Member(_new_id("member"), *values)
    _members[record.identifier] = record
    return record


def get_members() -> list[Member]:
    """Вернуть все Member в порядке создания."""
    return list(_members.values())


def update_member(identifier: int, changes: dict) -> Member:
    """Изменить поля существующего Member, кроме идентификатора."""
    record = _find(_members, identifier, "Member")
    fields = {"datetime": int, "ip": str, "locale": str,
              "platform": str}
    updated = record._replace(**_changes(changes, fields))
    _members[identifier] = updated
    return updated


def delete_member(identifier: int) -> Member:
    """Удалить Member, если на него не ссылается Query."""
    record = _find(_members, identifier, "Member")
    if any(query.member == identifier for query in _queries.values()):
        raise ModelError("Нельзя удалить Member со связанными Query")
    return _members.pop(record.identifier)


def create_query(argument: str, member: int, description: str,
                 executing: int, datetime: int | None = None) -> Query:
    """Создать Query, связанную с существующим Member."""
    _find(_members, member, "Member")
    values = (_stamp(datetime), _text(argument, "argument"), member,
              _text(description, "description"),
              _integer(executing, "executing"))
    record = Query(_new_id("query"), *values)
    _queries[record.identifier] = record
    return record


def get_queries() -> list[Query]:
    """Вернуть все Query в порядке создания."""
    return list(_queries.values())


def update_query(identifier: int, changes: dict) -> Query:
    """Изменить поля Query с проверкой новой ссылки на Member."""
    record = _find(_queries, identifier, "Query")
    fields = {"datetime": int, "argument": str, "member": int,
              "description": str, "executing": int}
    values = _changes(changes, fields)
    if "member" in values:
        _find(_members, values["member"], "Member")
    updated = record._replace(**values)
    _queries[identifier] = updated
    return updated


def delete_query(identifier: int) -> Query:
    """Удалить Query, если на неё не ссылается Response."""
    record = _find(_queries, identifier, "Query")
    if any(response.query == identifier for response in _responses.values()):
        raise ModelError("Нельзя удалить Query со связанными Response")
    return _queries.pop(record.identifier)


def create_response(output: str, status: str, exception: str,
                    query: int, cache_hit: int, duration: int,
                    datetime: int | None = None) -> Response:
    """Создать Response, связанную с существующей Query."""
    _find(_queries, query, "Query")
    values = (_stamp(datetime), _text(output, "output"),
              _text(status, "status"), _text(exception, "exception"),
              query, _integer(cache_hit, "cache_hit"),
              _integer(duration, "duration"))
    record = Response(_new_id("response"), *values)
    _responses[record.identifier] = record
    return record


def get_responses() -> list[Response]:
    """Вернуть все Response в порядке создания."""
    return list(_responses.values())


def update_response(identifier: int, changes: dict) -> Response:
    """Изменить поля Response с проверкой новой ссылки на Query."""
    record = _find(_responses, identifier, "Response")
    fields = {"datetime": int, "output": str, "status": str,
              "exception": str, "query": int, "cache_hit": int,
              "duration": int}
    values = _changes(changes, fields)
    if "query" in values:
        _find(_queries, values["query"], "Query")
    updated = record._replace(**values)
    _responses[identifier] = updated
    return updated


def delete_response(identifier: int) -> Response:
    """Удалить Response."""
    record = _find(_responses, identifier, "Response")
    return _responses.pop(record.identifier)


def select_recent_responses(now: int | None = None
                            ) -> list[RecentResponse]:
    """Выполнить полное соединение, фильтр >= 7 минут и проекцию."""
    border = _stamp(now) - RECENT_SECONDS
    rows: list[tuple[Query | None, Response | None]] = []
    matched: set[int] = set()
    for query in _queries.values():
        related = [item for item in _responses.values()
                   if item.query == query.identifier]
        rows.extend((query, item) for item in related)
        matched.update(item.identifier for item in related)
        if not related:
            rows.append((query, None))
    rows.extend((None, item) for item in _responses.values()
                if item.identifier not in matched)
    projected = [RecentResponse(query.argument if query else None,
                                response.cache_hit, response.status)
                 for query, response in rows
                 if response is not None and response.datetime >= border]
    return list(dict.fromkeys(projected))
