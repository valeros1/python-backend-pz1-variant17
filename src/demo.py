"""Показать все 13 удалённых вызовов и обработку ошибки."""

import os
import time

from src.client import RpcClient, RpcError


def main():
    """Выполнить последовательность действий через TCP-клиент."""
    host = os.getenv("RPC_HOST", "127.0.0.1")
    port = int(os.getenv("RPC_PORT", "5017"))
    with RpcClient(host, port) as client:
        member = client.create_member("127.0.0.1", "ru", "Linux")
        print("create_member:", member)
        print("get_members:", client.get_members())
        print("update_member:", client.update_member(
            member["identifier"], {"locale": "en"}))
        query = client.create_query("x + 1", member["identifier"],
                                    "Пример", 0)
        print("create_query:", query)
        print("get_queries:", client.get_queries())
        print("update_query:", client.update_query(
            query["identifier"], {"executing": 1}))
        response = client.create_response({
            "output": "2", "status": "done", "exception": "",
            "query": query["identifier"], "cache_hit": 0,
            "duration": 12, "datetime": int(time.time()) - 420,
        })
        print("create_response:", response)
        print("get_responses:", client.get_responses())
        print("update_response:", client.update_response(
            response["identifier"], {"cache_hit": 1}))
        print("select_recent_responses:",
              client.select_recent_responses(now=response["datetime"] + 420))
        try:
            client.delete_member(member["identifier"])
        except RpcError as error:
            print("Ожидаемая ошибка:", error)
        print("delete_response:",
              client.delete_response(response["identifier"]))
        print("delete_query:", client.delete_query(query["identifier"]))
        print("delete_member:", client.delete_member(member["identifier"]))


if __name__ == "__main__":
    main()
