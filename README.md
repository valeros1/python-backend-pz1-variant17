# Практическая работа №1 — вариант 17

Модель данных в памяти для `Member`, `Query`, `Response`; далее — RPC
поверх TCP и тестирование на основе модели. Данные не сохраняются на диск.

## Этап 1: модель

Записи представлены `NamedTuple`, то есть кортежами с именованными полями.
`Query.member` ссылается на `Member.identifier`, а `Response.query` — на
`Query.identifier`. Несуществующие ссылки и удаление записи, на которую
ссылаются, вызывают `ModelError`. Идентификаторы не переиспользуются.

| Сущность | Функции |
| --- | --- |
| Member | `create_member`, `get_members`, `update_member`, `delete_member` |
| Query | `create_query`, `get_queries`, `update_query`, `delete_query` |
| Response | `create_response`, `get_responses`, `update_response`, `delete_response` |

`select_recent_responses` реализует полное внешнее соединение Query и
Response по `Query.identifier = Response.query`, отбирает строки с
`Response.datetime >= now - 420` и возвращает `argument`, `cache_hit`,
`status`. Время — целое число секунд Unix. Если оно не передано при
создании записи, используется текущее. `now` в выборке можно указать
явно для воспроизводимой проверки граничного случая.

## Интерактивный режим

Команда: `make install`, затем `make repl`. Каждая строка состоит из
имени функции и необязательного JSON-объекта аргументов. `help` выводит
функции; `exit` завершает работу.

```text
> create_member {"ip":"127.0.0.1","locale":"ru","platform":"Linux","datetime":1000}
{"identifier": 1, "datetime": 1000, "ip": "127.0.0.1", "locale": "ru", "platform": "Linux"}
> create_query {"argument":"x","member":1,"description":"demo","executing":0}
> create_response {"output":"ok","status":"done","exception":"","query":1,"cache_hit":0,"duration":2}
> select_recent_responses
> delete_member {"identifier":1}
Ошибка: Нельзя удалить Member со связанными Query
```

Если `datetime` не указан, значение зависит от времени запуска.

## Этапы 2 и 3

Сервер, клиент, демонстрация RPC и тесты будут добавлены следующими
коммитами.
