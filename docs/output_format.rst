Output Format
=============

crobat produces time series files for each recording session. Files are
named with a UTC timestamp suffix and written to the configured output
directory (default: ``runs/``).

Output files
------------

+--------------------------------------------------+-------+----------------------------------------------+
| Filename                                         | Side  | Description                                  |
+==================================================+=======+==============================================+
| ``L2_orderbook_volm_ask<timestamp>``             | ask   | Volume snapshots, ask side                   |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_volm_bid<timestamp>``             | bid   | Volume snapshots, bid side                   |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_volm_signed<timestamp>``          | both  | Volume snapshots, signed order book          |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_prices_ask<timestamp>``           | ask   | Price snapshots, ask side                    |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_prices_bid<timestamp>``           | bid   | Price snapshots, bid side                    |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_prices_signed<timestamp>``        | both  | Price snapshots, signed order book           |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_events_ask<timestamp>``           | ask   | Event time series, ask side                  |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_events_bid<timestamp>``           | bid   | Event time series, bid side                  |
+--------------------------------------------------+-------+----------------------------------------------+
| ``L2_orderbook_events_signed<timestamp>``        | both  | Event time series, signed                    |
+--------------------------------------------------+-------+----------------------------------------------+

Order book snapshots
--------------------

Each snapshot row records the state of the order book at the moment an
event was processed. Columns are ordinal positions from the best bid or
best ask.

Single-sided snapshot (bid or ask):

+------------------------------+---+---+---+-----+----------------+
| Timestamp                    | 1 | 2 | 3 | ... | position_range |
+==============================+===+===+===+=====+================+
| YYYY-MM-DD HH:MM:SS.ffffff   | volume at position 1 → n        |
+------------------------------+---------------------------------+

An associated price snapshot is generated in the same format, with the
price quote (e.g., USD per XRP) at each position.

Signed order book snapshot
--------------------------

The signed order book follows the convention from Cont, Kukanov and
Stoikov (2011). Bid positions are negative, ask positions are positive.
Position 0 is skipped — the best bid is ``-1``, the best ask is ``1``.

+------------------------------+----+----+----+----+----+---+---+---+---+---+
| Timestamp                    | -5 | -4 | -3 | -2 | -1 | 1 | 2 | 3 | 4 | 5 |
+==============================+====+====+====+====+====+===+===+===+===+===+
| YYYY-MM-DD HH:MM:SS.ffffff   | ← bid volume (negative) →  | ← ask volume → |
+------------------------------+----------------------------+----------------+

Bid-side volume is stored as negative. An associated price snapshot is
generated in the same format.

Event recordings
----------------

Events capture each limit order insertion (LO), cancellation (CO), and
market order (MO) as they arrive from the exchange.

Single-sided events (bid or ask):

+------------------------------+------------+-------------+------------+----------+-----------+----------------+
| Timestamp                    | order_type | price_level | event_size | position | mid_price | spread         |
+==============================+============+=============+============+==========+===========+================+
| YYYY-MM-DD HH:MM:SS.ffffff   | LO/CO/MO   | quote ccy   | base ccy   | ordinal  | (ask+bid)/2 | ask - bid    |
+------------------------------+------------+-------------+------------+----------+-----------+----------------+

Signed events add a ``side`` column and sign the event size according to
the order flow convention: positive for buy-side activity (buy MO, sell
CO, buy LO), negative for sell-side activity.

+------------------------------+------------+-------------+------------+------------------+------+-----------+--------+
| Timestamp                    | order_type | price_level | event_size | position         | side | mid_price | spread |
+==============================+============+=============+============+==================+======+===========+========+
| YYYY-MM-DD HH:MM:SS.ffffff   | LO/CO/MO   | quote ccy   | ± base ccy | ± ordinal        | bid/ask | (ask+bid)/2 | ask-bid |
+------------------------------+------------+-------------+------------+------------------+------+-----------+--------+

.. note::
   The ``Demo/`` directory contains example output files from a
   2020 recording session for reference.
