"""Test dynamic nodes involving a running DHT."""

from collections import namedtuple
import pytest
import time
from DHTClient import DHTClient
from DHTNode import DHTNode
from utils import dht_hash
from unittest.mock import patch, MagicMock


NODE_FINGER_TABLE = [
    (654, ("localhost", 5004)),
    (654, ("localhost", 5004)),
    (654, ("localhost", 5004)),
    (654, ("localhost", 5004)),
    (654, ("localhost", 5004)),
    (654, ("localhost", 5004)),
    (654, ("localhost", 5004)),
    (752, ("localhost", 3000)),
    (895, ("localhost", 6000)),
    (257, ("localhost", 5003)),
]

NODE1_FINGER_TABLE = [
    (959, ("localhost", 5001)),
    (959, ("localhost", 5001)),
    (959, ("localhost", 5001)),
    (959, ("localhost", 5001)),
    (959, ("localhost", 5001)),
    (959, ("localhost", 5001)),
    (959, ("localhost", 5001)),
    (257, ("localhost", 5003)),
    (257, ("localhost", 5003)),
    (581, ("localhost", 4000)),
]

NODE2_FINGER_TABLE = [
    (770, ("localhost", 5000)),
    (770, ("localhost", 5000)),
    (770, ("localhost", 5000)),
    (770, ("localhost", 5000)),
    (770, ("localhost", 5000)),
    (895, ("localhost", 6000)),
    (895, ("localhost", 6000)),
    (895, ("localhost", 6000)),
    (257, ("localhost", 5003)),
    (257, ("localhost", 5003)),
]

RingMember = namedtuple("RingMember", ["identification", "addr"])

BASE_RING_MEMBERS = [
    RingMember(770, ("localhost", 5000)),
    RingMember(959, ("localhost", 5001)),
    RingMember(260, ("localhost", 5002)),
    RingMember(257, ("localhost", 5003)),
    RingMember(654, ("localhost", 5004)),
]


def wait_until(assertion, timeout=30, interval=0.1):
    deadline = time.monotonic() + timeout
    last_error = None

    while time.monotonic() < deadline:
        try:
            assertion()
            return
        except AssertionError as error:
            last_error = error
            time.sleep(interval)

    if last_error is not None:
        raise last_error
    assertion()


def chord_nodes(*node_groups):
    nodes = []
    for group in node_groups:
        if isinstance(group, (DHTNode, RingMember)):
            nodes.append(group)
        else:
            nodes.extend(group)
    return sorted(nodes, key=lambda node: node.identification)


def expected_ring(*dynamic_nodes):
    return chord_nodes(BASE_RING_MEMBERS, *dynamic_nodes)


def successor_for(identification, nodes):
    ring = chord_nodes(nodes)
    for node in ring:
        if identification <= node.identification:
            return node
    return ring[0]


def expected_finger_table(node, nodes):
    table = []
    for finger in range(10):
        start = (node.identification + 2 ** finger) % 2 ** 10
        successor = successor_for(start, nodes)
        table.append((successor.identification, successor.addr))
    return table


def assert_node_links_match_ring(nodes, owned_nodes):
    ring = chord_nodes(nodes)
    for current in owned_nodes:
        index = ring.index(current)
        predecessor = ring[index - 1]
        successor = ring[(index + 1) % len(ring)]

        assert current.predecessor_id == predecessor.identification
        assert current.predecessor_addr == predecessor.addr
        assert current.successor_id == successor.identification
        assert current.successor_addr == successor.addr


def key_for_owner(owner, nodes):
    for index in range(10000):
        key = "{}-{}".format(owner.identification, index)
        if successor_for(dht_hash(key), nodes) is owner:
            return key
    raise AssertionError("could not find key for node {}".format(owner.identification))


def client_for(address):
    client = DHTClient(address)
    client.socket.settimeout(5)
    return client


@pytest.fixture(scope="session", autouse=True)
def node(server):
    node = DHTNode(("localhost", 4000), ("localhost", 5000))
    node.start()
    time.sleep(6)
    yield node
    node.done = True
    node.join()


@pytest.fixture(scope="session", autouse=True)
def node1(server):
    node = DHTNode(("localhost", 6000), ("localhost", 5000))
    node.start()
    time.sleep(6)
    yield node
    node.done = True
    node.join()


@pytest.fixture(scope="session", autouse=True)
def node2(server):
    node = DHTNode(("localhost", 3000), ("localhost", 5000))
    node.start()
    time.sleep(15)
    yield node
    node.done = True
    node.join()


@pytest.fixture()
def client():
    return client_for(("localhost", 5000))


def test_put_keystore(server, node, client):
    assert client.put("10", "Aveiro")

    def assert_node_ready():
        assert node.predecessor_id == 260
        assert node.identification == 581
        assert node.successor_id == 654
        assert node.keystore["10"] == "Aveiro"

    wait_until(assert_node_ready)


def test_ring_links_are_consistent(server, node, node1, node2):
    nodes = expected_ring(node, node1, node2)
    owned_nodes = [node, node1, node2]

    def assert_stable_ring():
        assert_node_links_match_ring(nodes, owned_nodes)

    wait_until(assert_stable_ring)


def test_actual_node_finger_table(server, node1, node2):
    assert isinstance(node1.finger_table.as_list, list)

    def assert_nodes_ready():
        assert node1.identification == 895
        assert node1.successor_id == 959
        assert node1.finger_table.as_list == NODE1_FINGER_TABLE
        assert node2.identification == 752
        assert node2.successor_id == 770
        assert node2.finger_table.as_list == NODE2_FINGER_TABLE

    wait_until(assert_nodes_ready)


def test_finger_tables_follow_chord_successor_rule(server, node, node1, node2):
    nodes = expected_ring(node, node1, node2)

    def assert_finger_tables():
        for current in [node, node1, node2]:
            assert current.finger_table.as_list == expected_finger_table(current, nodes)

    wait_until(assert_finger_tables)


def test_late_join_updates_existing_routing_state(server, node, node1, node2):
    nodes = expected_ring(node, node1, node2)
    entry_for_late_node = (node2.identification, node2.addr)

    def assert_late_join_visible():
        assert entry_for_late_node in node.finger_table.as_list
        assert node2.successor_id == 770
        assert node2.successor_addr == ("localhost", 5000)
        assert node.finger_table.as_list == expected_finger_table(node, nodes)

    wait_until(assert_late_join_visible)


def test_keys_are_stored_on_responsible_nodes(server, node, node1, node2, client):
    nodes = expected_ring(node, node1, node2)
    owned_nodes = [node, node1, node2]

    def assert_stable_ring():
        assert_node_links_match_ring(nodes, owned_nodes)

    wait_until(assert_stable_ring)

    for owner in owned_nodes:
        key = key_for_owner(owner, nodes)
        value = "value-for-{}".format(owner.identification)

        assert client.put(key, value)

        def assert_key_owned_by_expected_node():
            for current in owned_nodes:
                assert (key in current.keystore) is (current is owner)
            assert owner.keystore[key] == value

        wait_until(assert_key_owned_by_expected_node)


def test_put_and_get_work_from_every_entry_point(server, node, node1, node2):
    nodes = expected_ring(node, node1, node2)

    def assert_stable_ring():
        assert_node_links_match_ring(nodes, [node, node1, node2])

    wait_until(assert_stable_ring)

    for index, entry in enumerate(nodes):
        read_entry = nodes[(index + 1) % len(nodes)]
        key = "entry-point-{}".format(entry.identification)
        value = "stored-through-{}".format(entry.identification)

        assert client_for(entry.addr).put(key, value)
        assert client_for(read_entry.addr).get(key) == value


def test_finger_table_used(server, client, node1, node2):
    def assert_nodes_ready():
        assert node1.identification == 895
        assert node1.successor_id == 959
        assert node1.finger_table.as_list == NODE1_FINGER_TABLE
        assert node2.identification == 752
        assert node2.successor_id == 770
        assert node2.finger_table.as_list == NODE2_FINGER_TABLE

    wait_until(assert_nodes_ready)

    with patch.object(node1, "put", MagicMock(side_effect=node1.put)) as put1:
        with patch.object(node2, "put", MagicMock(side_effect=node2.put)) as put2:

            assert client.put("d", "That tickles")  # dht_hash("d") = 115

            assert put1.call_count == 0
            assert put2.call_count == 0

            assert client.put("f", "No sweat")  # dht_hash("f") = 921
            assert put1.call_count == 1
            assert put2.call_count == 0

            with patch.object(node1, "get", MagicMock(side_effect=node1.get)) as get1:
                with patch.object(
                    node2, "get", MagicMock(side_effect=node2.get)
                ) as get2:
                    assert client.get("f") == "No sweat"
                    assert get1.call_count == 1
                    assert get2.call_count == 0
