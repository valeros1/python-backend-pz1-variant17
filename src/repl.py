"""Интерактивная оболочка модели: имя функции и JSON-аргументы."""

import json

from src import model

FUNCTIONS = (
    "create_member", "get_members", "update_member", "delete_member",
    "create_query", "get_queries", "update_query", "delete_query",
    "create_response", "get_responses", "update_response",
    "delete_response", "select_recent_responses",
)


def _json_value(value):
    if isinstance(value, tuple) and hasattr(value, "_asdict"):
        return value._asdict()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def execute(line: str):
    """Выполнить одну команду; вернуть результат функции модели."""
    name, _, body = line.strip().partition(" ")
    if name not in FUNCTIONS:
        raise ValueError(f"Неизвестная команда: {name}")
    params = json.loads(body) if body.strip() else {}
    if not isinstance(params, dict):
        raise ValueError("Аргументы должны быть JSON-объектом")
    return getattr(model, name)(**params)


def main() -> None:
    """Печатать приглашение до команды exit или EOF."""
    print("Модель варианта 17. help — команды, exit — выход.")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            return
        if line == "exit":
            return
        if line == "help":
            print("\n".join(FUNCTIONS))
            continue
        if not line:
            continue
        try:
            value = _json_value(execute(line))
            print(json.dumps(value, ensure_ascii=False))
        except (ValueError, TypeError) as error:
            print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
