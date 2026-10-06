"""Unit tests for the DHT client."""
import pickle
from unittest.mock import MagicMock, patch

from DHTClient import DHTClient


def _mock_socket(reply):
    sock = MagicMock()
    sock.recvfrom.return_value = (pickle.dumps(reply), ("localhost", 5000))
    return sock


def test_put_returns_false_on_non_ack_reply():
    sock = _mock_socket({"method": "NACK"})

    with patch("DHTClient.socket.socket", return_value=sock):
        client = DHTClient(("localhost", 5000))

    assert not client.put("missing", "value")
    sent_payload, sent_addr = sock.sendto.call_args.args
    assert pickle.loads(sent_payload) == {
        "method": "PUT",
        "args": {"key": "missing", "value": "value"},
    }
    assert sent_addr == ("localhost", 5000)


def test_get_returns_none_on_non_ack_reply():
    sock = _mock_socket({"method": "NACK"})

    with patch("DHTClient.socket.socket", return_value=sock):
        client = DHTClient(("localhost", 5000))

    assert client.get("missing") is None
    sent_payload, sent_addr = sock.sendto.call_args.args
    assert pickle.loads(sent_payload) == {"method": "GET", "args": {"key": "missing"}}
    assert sent_addr == ("localhost", 5000)
