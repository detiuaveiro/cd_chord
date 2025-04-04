"""Tests two clients."""
import pytest
from DHTClient import DHTClient


@pytest.fixture()
def client():
    return DHTClient(("localhost", 5000))


def test_put_local(server, client):
    """ add object to DHT (this key is in first node -> local search) """
    assert client.put("A", [0, 1, 2])


def test_get_local(server, client):
    """ retrieve from DHT (this key is in first node -> local search) """
    assert client.get("A") == [0, 1, 2]


def test_put_remote(server, client):
    """ add object to DHT (this key is not on the first node -> remote search) """
    assert client.put("2", ("xpto"))


def test_get_remote(server, client):
    """ retrieve from DHT (this key is not on the first node -> remote search) """
    assert client.get("2") == "xpto"
