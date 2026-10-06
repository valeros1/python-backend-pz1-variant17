"""Сравнение RPC-сервера с независимой моделью на словарях."""

import atexit
import tempfile
import threading

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant
from hypothesis.stateful import precondition, rule

from src import model
from src.client import RpcClient, RpcError
from src.server import RpcServer

NOW = 2000
MISSING_ID = 999999
TEXT = st.text(max_size=12)
TIMESTAMPS = st.sampled_from([NOW, NOW - 420, NOW - 421])

_journal_dir = tempfile.TemporaryDirectory()
atexit.register(_journal_dir.cleanup)
SERVER = RpcServer(("127.0.0.1", 0),
                   journal_path=f"{_journal_dir.name}/journal.log")
threading.Thread(target=SERVER.serve_forever, daemon=True).start()
HOST, PORT = SERVER.server_address
atexit.register(SERVER.server_close)
atexit.register(SERVER.shutdown)


class RpcMachine(RuleBasedStateMachine):
    """Генерировать операции и сверять сервер с простой моделью."""

    def __init__(self):
        super().__init__()
        model.reset()
        self.client = RpcClient(HOST, PORT)
        self.rows = {"members": {}, "queries": {}, "responses": {}}
        self.next_ids = {name: 1 for name in self.rows}

    def teardown(self):
        self.client.close()

    def remember(self, table, fields, result):
        identifier = self.next_ids[table]
        self.next_ids[table] += 1
        expected = {"identifier": identifier, **fields}
        assert result == expected
        self.rows[table][identifier] = expected
        return identifier

    def choose(self, data, table):
        keys = sorted(self.rows[table])
        return data.draw(st.sampled_from(keys))

    def expected_recent(self):
        result = []
        for query in self.rows["queries"].values():
            for response in self.rows["responses"].values():
                if response["query"] != query["identifier"]:
                    continue
                if response["datetime"] >= NOW - 420:
                    result.append({
                        "argument": query["argument"],
                        "cache_hit": response["cache_hit"],
                        "status": response["status"],
                    })
        unique = {tuple(sorted(row.items())): row for row in result}
        return list(unique.values())

    @initialize(ip=TEXT, argument=TEXT, status=TEXT)
    def seed_chain(self, ip, argument, status):
        member = self.client.create_member(ip, "ru", "Linux", NOW)
        member_id = self.remember("members", {
            "datetime": NOW, "ip": ip, "locale": "ru",
            "platform": "Linux",
        }, member)
        query = self.client.create_query(argument, member_id, "seed", 0,
                                         NOW)
        query_id = self.remember("queries", {
            "datetime": NOW, "argument": argument, "member": member_id,
            "description": "seed", "executing": 0,
        }, query)
        response = self.client.create_response({
            "output": "ok", "status": status, "exception": "",
            "query": query_id, "cache_hit": 0, "duration": 1,
            "datetime": NOW - 420,
        })
        self.remember("responses", {
            "datetime": NOW - 420, "output": "ok", "status": status,
            "exception": "", "query": query_id, "cache_hit": 0,
            "duration": 1,
        }, response)

    @rule(ip=TEXT, locale=TEXT, platform=TEXT)
    def create_member(self, ip, locale, platform):
        fields = {"datetime": NOW, "ip": ip, "locale": locale,
                  "platform": platform}
        result = self.client.create_member(ip, locale, platform, NOW)
        self.remember("members", fields, result)

    @precondition(lambda self: bool(self.rows["members"]))
    @rule(data=st.data(), argument=TEXT, description=TEXT,
          executing=st.integers(-2, 2))
    def create_query(self, data, argument, description, executing):
        member = self.choose(data, "members")
        fields = {"datetime": NOW, "argument": argument,
                  "member": member, "description": description,
                  "executing": executing}
        result = self.client.create_query(
            argument, member, description, executing, NOW)
        self.remember("queries", fields, result)

    @precondition(lambda self: bool(self.rows["queries"]))
    @rule(data=st.data(), status=TEXT, cache_hit=st.integers(0, 1),
          timestamp=TIMESTAMPS)
    def create_response(self, data, status, cache_hit, timestamp):
        query = self.choose(data, "queries")
        fields = {"datetime": timestamp, "output": "result",
                  "status": status, "exception": "", "query": query,
                  "cache_hit": cache_hit, "duration": 1}
        result = self.client.create_response({
            "output": "result", "status": status, "exception": "",
            "query": query, "cache_hit": cache_hit, "duration": 1,
            "datetime": timestamp,
        })
        self.remember("responses", fields, result)

    @precondition(lambda self: bool(self.rows["members"]))
    @rule(data=st.data(), locale=TEXT)
    def update_member(self, data, locale):
        identifier = self.choose(data, "members")
        expected = self.rows["members"][identifier]
        expected["locale"] = locale
        assert self.client.update_member(
            identifier, {"locale": locale}) == expected

    @precondition(lambda self: bool(self.rows["queries"]))
    @rule(data=st.data(), argument=TEXT)
    def update_query(self, data, argument):
        identifier = self.choose(data, "queries")
        expected = self.rows["queries"][identifier]
        expected["argument"] = argument
        assert self.client.update_query(
            identifier, {"argument": argument}) == expected

    @precondition(lambda self: bool(self.rows["queries"]))
    @rule(data=st.data())
    def move_query_to_member(self, data):
        identifier = self.choose(data, "queries")
        member = self.choose(data, "members")
        expected = self.rows["queries"][identifier]
        expected["member"] = member
        assert self.client.update_query(
            identifier, {"member": member}) == expected

    @precondition(lambda self: bool(self.rows["responses"]))
    @rule(data=st.data(), status=TEXT)
    def update_response(self, data, status):
        identifier = self.choose(data, "responses")
        expected = self.rows["responses"][identifier]
        expected["status"] = status
        assert self.client.update_response(
            identifier, {"status": status}) == expected

    @precondition(lambda self: bool(self.rows["responses"]))
    @rule(data=st.data())
    def move_response_to_query(self, data):
        identifier = self.choose(data, "responses")
        query = self.choose(data, "queries")
        expected = self.rows["responses"][identifier]
        expected["query"] = query
        assert self.client.update_response(
            identifier, {"query": query}) == expected

    @precondition(lambda self: bool(self.rows["responses"]))
    @rule(data=st.data())
    def delete_response(self, data):
        identifier = self.choose(data, "responses")
        expected = self.rows["responses"].pop(identifier)
        assert self.client.delete_response(identifier) == expected

    def free_queries(self):
        used = {row["query"] for row in self.rows["responses"].values()}
        return sorted(set(self.rows["queries"]) - used)

    @precondition(lambda self: bool(self.free_queries()))
    @rule(data=st.data())
    def delete_query(self, data):
        identifier = data.draw(st.sampled_from(self.free_queries()))
        expected = self.rows["queries"].pop(identifier)
        assert self.client.delete_query(identifier) == expected

    def free_members(self):
        used = {row["member"] for row in self.rows["queries"].values()}
        return sorted(set(self.rows["members"]) - used)

    @precondition(lambda self: bool(self.free_members()))
    @rule(data=st.data())
    def delete_member(self, data):
        identifier = data.draw(st.sampled_from(self.free_members()))
        expected = self.rows["members"].pop(identifier)
        assert self.client.delete_member(identifier) == expected

    @rule()
    def reject_missing_member(self):
        with pytest.raises(RpcError, match="Member"):
            self.client.create_query("bad", MISSING_ID, "", 0, NOW)

    @precondition(lambda self: bool(self.rows["queries"]))
    @rule(data=st.data())
    def reject_delete_referenced_member(self, data):
        query = self.rows["queries"][self.choose(data, "queries")]
        with pytest.raises(RpcError, match="связанными Query"):
            self.client.delete_member(query["member"])

    @precondition(lambda self: bool(self.rows["responses"]))
    @rule(data=st.data())
    def reject_delete_referenced_query(self, data):
        response = self.rows["responses"][self.choose(data, "responses")]
        with pytest.raises(RpcError, match="связанными Response"):
            self.client.delete_query(response["query"])

    @precondition(lambda self: bool(self.rows["members"]))
    @rule(data=st.data())
    def reject_bad_update(self, data):
        identifier = self.choose(data, "members")
        with pytest.raises(RpcError, match="Неизвестные поля"):
            self.client.update_member(identifier, {"missing": "x"})
        with pytest.raises(RpcError, match="изменяемые поля"):
            self.client.update_member(identifier, {})

    @invariant()
    def state_matches(self):
        assert self.client.get_members() == list(
            self.rows["members"].values())
        assert self.client.get_queries() == list(
            self.rows["queries"].values())
        assert self.client.get_responses() == list(
            self.rows["responses"].values())
        assert self.client.select_recent_responses(NOW) == (
            self.expected_recent())


TestRpc = RpcMachine.TestCase
TestRpc.settings = settings(max_examples=80, stateful_step_count=25,
                            deadline=None, derandomize=True)
