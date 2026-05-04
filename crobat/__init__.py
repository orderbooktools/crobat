"""
crobat — Cryptocurrency Order Book Analysis Tool.

Connects to the Coinbase Advanced Trade WebSocket feed, reconstructs a
live Level 2 limit order book, and records insertions, cancellations, and
market orders as structured time series files.

Public API
----------
Primary entry point::

    from crobat import L2Recorder, SnapshotTimeoutError

    recorder = L2Recorder(settings)
    recorder.start()

Direct access to the order book state::

    from crobat import LimitOrderBook

Lower-level imports::

    from crobat.recorder import L2Recorder
    from crobat.orderbook import LimitOrderBook
    from crobat.config import recording_defaults, coinbase_credentials
    from crobat.filesave import export_session
"""

from .recorder import L2Recorder, SnapshotTimeoutError
from .orderbook import LimitOrderBook

__all__ = ["L2Recorder", "SnapshotTimeoutError", "LimitOrderBook"]
__version__ = "1.0.0"
