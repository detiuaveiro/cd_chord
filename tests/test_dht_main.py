"""Unit tests for the DHT launcher."""
import runpy
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import DHT


def test_main_starts_configured_nodes_and_joins_them():
    nodes = [MagicMock() for _ in range(3)]

    with patch("DHT.DHTNode", side_effect=nodes) as node_cls:
        with patch("DHT.time.sleep") as sleep:
            DHT.main(number_nodes=3, timeout=7)

    assert node_cls.call_args_list == [
        call(("localhost", 5000)),
        call(("localhost", 5001), ("localhost", 5000), 7),
        call(("localhost", 5002), ("localhost", 5000), 7),
    ]
    for node in nodes:
        node.start.assert_called_once_with()
        node.join.assert_called_once_with()
    assert sleep.call_args_list == [call(0.2), call(0.2), call(10)]


def test_cli_parses_arguments_and_configures_logging():
    nodes = [MagicMock() for _ in range(2)]
    script = Path(__file__).parents[1] / "DHT.py"

    with patch.object(
        sys, "argv", ["DHT.py", "--nodes", "2", "--timeout", "7", "--savelog"]
    ):
        with patch("DHTNode.DHTNode", side_effect=nodes) as node_cls:
            with patch("time.sleep") as sleep:
                with patch("logging.basicConfig") as basic_config:
                    runpy.run_path(script, run_name="__main__")

    assert node_cls.call_args_list == [
        call(("localhost", 5000)),
        call(("localhost", 5001), ("localhost", 5000), 7),
    ]
    assert sleep.call_args_list == [call(0.2), call(10)]
    basic_config.assert_called_once()
    assert basic_config.call_args.kwargs["filename"] == "dht.txt"
    assert basic_config.call_args.kwargs["filemode"] == "w"
