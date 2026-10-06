"""Focused unit tests for DHT node edge branches."""
import socket
from unittest.mock import MagicMock, patch

from DHTNode import DHTNode, FingerTable


def test_recv_returns_address_when_payload_is_empty():
    node = DHTNode(("localhost", 7000))
    node.socket = MagicMock()
    node.socket.recvfrom.return_value = (b"", ("localhost", 9000))

    assert node.recv() == (None, ("localhost", 9000))


def test_recv_returns_none_pair_on_timeout():
    node = DHTNode(("localhost", 7000))
    node.socket = MagicMock()
    node.socket.recvfrom.side_effect = socket.timeout

    assert node.recv() == (None, None)


def test_get_successor_replies_with_self_for_single_node_ring():
    node = DHTNode(("localhost", 7000))

    with patch.object(node, "send") as send:
        node.get_successor({"id": 123, "from": ("localhost", 9000)})

    send.assert_called_once_with(
        ("localhost", 9000),
        {
            "method": "SUCCESSOR_REP",
            "args": {
                "req_id": 123,
                "successor_id": node.identification,
                "successor_addr": node.addr,
            },
        },
    )


def test_stabilize_updates_successor_when_predecessor_is_closer():
    node = DHTNode(("localhost", 7000))
    node.identification = 100
    node.successor_id = 300
    node.successor_addr = ("localhost", 3000)
    node.finger_table.refresh = MagicMock(return_value=[])

    with patch.object(node, "send") as send:
        node.stabilize(200, ("localhost", 2000))

    assert node.successor_id == 200
    assert node.successor_addr == ("localhost", 2000)
    assert node.finger_table.as_list[0] == (200, ("localhost", 2000))
    send.assert_called_once_with(
        ("localhost", 2000),
        {
            "method": "NOTIFY",
            "args": {"predecessor_id": 100, "predecessor_addr": ("localhost", 7000)},
        },
    )


def test_repr_helpers_include_table_and_node_state():
    table = FingerTable(10, ("localhost", 5000), 2)
    node = DHTNode(("localhost", 7000))

    assert repr(table) == str(table._table)
    assert repr(node) == str(node)
    assert "Node ID:" in repr(node)
