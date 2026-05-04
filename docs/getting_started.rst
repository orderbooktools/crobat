Getting Started
===============

Prerequisites
-------------

- Python 3.10 or higher
- A Coinbase Advanced Trade account with API credentials
  (``cdp_api_key.json`` downloaded from the Coinbase Developer Portal)

Dependencies are declared in ``setup.py``. Key packages:

- ``coinbase-advanced-py==1.8.2``
- ``numpy``
- ``pandas``

Installation
------------

Clone the repository::

    git clone https://github.com/orderbooktools/crobat.git
    cd crobat

Place your ``cdp_api_key.json`` in the project root. The ``config.ini``
file controls default recording settings::

    [recording]
    currency_pair      = XRP-USD
    position_range     = 5
    recording_duration = 10
    sides              = bid,ask,signed
    filetype           = csv

Install the package in editable mode so the ``crobat`` CLI command is
available system-wide::

    pip install -e .

Using the CLI
-------------

Run from the project root::

    # Use defaults from config.ini
    python CLI/crobat_cli.py

    # Override specific parameters
    python CLI/crobat_cli.py --pair BTC-USD --duration 30

    # Prompt for each parameter interactively
    python CLI/crobat_cli.py --interactive

    # Clear the output directory before recording
    python CLI/crobat_cli.py --clear-runs

Available options::

    --pair TEXT         Currency pair, e.g. XRP-USD
    --duration INTEGER  Recording duration in seconds
    --range INTEGER     Order book depth (number of price levels per side)
    --sides TEXT        Comma-separated sides to record: bid,ask,signed
    --filetype TEXT     Comma-separated output formats: csv,pkl,xlsx
    --output-dir TEXT   Directory where output files are written [default: runs]
    --clear-runs        Delete all existing files in the output directory before recording
    --interactive       Prompt for each parameter (Enter to accept the shown default)

Output files are written to the ``runs/`` directory by default, with
UTC timestamps in the filename.

Using the Python API
--------------------

You can integrate crobat directly into your own scripts::

    from crobat import L2Recorder, SnapshotTimeoutError
    from crobat.config import recording_defaults

    class Settings:
        d = recording_defaults()
        currency_pair      = d['currency_pair']
        position_range     = d['position_range']
        recording_duration = d['recording_duration']
        sides              = d['sides']
        filetype           = d['filetype']
        output_dir         = 'runs'

    recorder = L2Recorder(Settings())
    recorder.start()

After ``start()`` returns, the full session history is available on
``recorder.book`` — a :class:`~crobat.orderbook.LimitOrderBook` instance::

    # Most recent order book snapshot
    recorder.book.latest_snapshot(side='signed')

    # All bid-side events
    recorder.book.bid_events

    # All ask-side events
    recorder.book.ask_events

    # All signed events (includes market orders)
    recorder.book.signed_events

    # Most recent insertion, cancellation, or market order
    recorder.book.last_inserted_order()
    recorder.book.last_canceled_order()
    recorder.book.last_market_order()

    # Current mid-price and spread
    recorder.book.mid_price
    recorder.book.spread

Handling snapshot timeouts
--------------------------

If the WebSocket connection fails to deliver the initial snapshot,
:exc:`~crobat.recorder.SnapshotTimeoutError` is raised after all retry
attempts are exhausted::

    from crobat import L2Recorder, SnapshotTimeoutError

    try:
        recorder = L2Recorder(Settings())
        recorder.start(snap_timeout=8.0, max_retries=2, retry_backoff=5.0)
    except SnapshotTimeoutError as e:
        print(f"Failed to connect: {e}")

.. note::
   On slow connections, increase ``snap_timeout``. The default 8 seconds
   is sufficient for most conditions. At most ``1 + max_retries`` total
   connections are opened to avoid rate-limiting by Coinbase.
