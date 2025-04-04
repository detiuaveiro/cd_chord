"""Launch DHT Nodes."""
import pytest
import logging
import time
from DHTNode import DHTNode


@pytest.fixture(scope="session")
def server():
    """ Script to launch several DHT nodes. """

    number_nodes = 5
    timeout = 3

    logfile = {"filename": "dht.txt", "filemode": "w"}

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        datefmt="%m-%d %H:%M:%S",
        **logfile
    )

    # logger for the main
    logger = logging.getLogger("DHT")
    # list with all the nodes
    dht = []
    # initial node on DHT
    node = DHTNode(("localhost", 5000))
    node.start()
    dht.append(node)
    logger.info(node)

    for i in range(number_nodes - 1):
        time.sleep(0.2)
        # Create DHT_Node threads on ports 5001++ and with initial DHT_Node on port 5000
        node = DHTNode(("localhost", 5001 + i), ("localhost", 5000), timeout)
        node.start()
        dht.append(node)
        logger.info(node)

    # Await for DHT to get stable
    time.sleep(10)

    yield dht

    # Await for all nodes to stop
    for node in dht:
        node.done = True
        node.join()
