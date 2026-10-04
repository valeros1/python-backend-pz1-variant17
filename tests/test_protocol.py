"""Проверка границ сообщений при частичном чтении TCP-потока."""

from src import protocol


class FragmentedSocket:
    """Возвращать не более одного байта на каждый recv."""

    def __init__(self, data):
        self.data = data

    def recv(self, count):
        chunk, self.data = self.data[:1], self.data[1:]
        return chunk


def test_fragmented_request_and_response():
    """Проверить оба заголовка и UTF-8 при чтении по одному байту."""
    request = protocol.pack_request(7, {"status": "готово"})
    assert request[:2] == bytes((1, 7))
    assert int.from_bytes(request[2:7], "big") == len(request) - 7
    assert protocol.read_request(FragmentedSocket(request)) == (
        1, 7, {"status": "готово"})
    response = protocol.pack_response(7, {"result": "готово"})
    assert int.from_bytes(response[:4], "big") == len(response) - 5
    assert protocol.read_response(FragmentedSocket(response)) == (
        7, {"result": "готово"})
