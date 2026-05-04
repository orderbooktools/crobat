import json
import time
from datetime import datetime, timezone

from coinbase.websocket import WSClient
import numpy as np
import gc

from crobat import orderbook as ob
from crobat import filesave as fs
from crobat.config import coinbase_credentials

# ---------------------------------------------------------------------------
# Coinbase Advanced Trade WebSocket field names — concentrated here so that
# a wire-format change only requires an update in one place.
# ---------------------------------------------------------------------------
_SIDE         = "side"
_PRICE_LEVEL  = "price_level"
_NEW_QUANTITY = "new_quantity"
_EVENT_TIME   = "event_time"
_TRADE_PRICE  = "price"
_TRADE_SIZE   = "size"
_TRADE_TIME   = "time"
_SIDE_BID     = "bid"
_SIDE_OFFER   = "offer"
_TAKER_BUY    = "BUY"
_TAKER_SELL   = "SELL"


class SnapshotTimeoutError(Exception):
    """Raised when the l2_data snapshot is not received within the allowed time."""


class L2Recorder:
    """
    Connects to the Coinbase Advanced Trade WebSocket feed and maintains a
    live Level 2 limit order book using the coinbase-advanced-py WSClient.

    Subscribes to three channels for a given product:
        - level2        : snapshot + incremental order book updates
        - market_trades : market order fills
        - ticker        : best bid / ask quotes, cached for spread calculations

    Attributes
    ----------
    session_start : datetime
        UTC time at initialisation, used as the session start reference.
    book : LimitOrderBook
        The live limit order book state and history.
    settings : object
        Holds ``currency_pair``, ``position_range``, ``recording_duration``,
        ``sides``, ``filetype``.
    snapshot_received : bool
        Guards against processing updates before the snapshot arrives.
    decimal_places : int
        Volume rounding precision. Set from the snapshot; defaults to 8.
    ws : WSClient
        The underlying coinbase-advanced-py websocket client.
    """

    def __init__(self, settings):
        self.session_start = datetime.now(timezone.utc)
        self.book = ob.LimitOrderBook()
        self.settings = settings
        self.snapshot_received = False
        self.decimal_places = 8  # safe default until snapshot sets it

        self.ws = WSClient(
            **coinbase_credentials(),
            on_message=self.on_message,
            on_open=self.on_open,
            on_close=self.on_close,
        )

    # ------------------------------------------------------------------
    # WSClient callbacks
    # ------------------------------------------------------------------

    def on_open(self):
        print("Connection opened.", self.session_start)

    def on_message(self, raw):
        """
        Route an incoming raw JSON string to the correct channel handler.

        Parameters
        ----------
        raw : str
            Raw JSON string delivered by WSClient.
        """
        msg = json.loads(raw)
        channel = msg.get("channel")

        if channel == "l2_data":
            self._handle_l2_data(msg)
        elif channel == "market_trades":
            self._handle_market_trades(msg)
        elif channel == "ticker":
            self._handle_ticker_quotes(msg)

    def on_close(self):
        print("Connection closed.")
        fs.export_session(
            self.book,
            self.settings.position_range,
            sides=self.settings.sides,
            filetype=self.settings.filetype,
            output_dir=getattr(self.settings, 'output_dir', '.'),
        )
        gc.collect()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def start(self, snap_timeout=8.0, max_retries=2, retry_backoff=5.0):
        """
        Open the WebSocket, subscribe to all channels, wait for
        ``recording_duration`` seconds, then close cleanly.

        The recording timer only starts once the l2_data snapshot is confirmed.
        If the snapshot is not received within ``snap_timeout`` seconds, the
        connection is closed and reopened after ``retry_backoff`` seconds.

        Parameters
        ----------
        snap_timeout : float
            Seconds to wait for the snapshot before treating the attempt as
            failed. Default 8s.
        max_retries : int
            Number of reconnection attempts after the first failure. Default 2.
        retry_backoff : float
            Seconds to wait between a failed attempt and the next reconnect.
            Default 5s.

        Raises
        ------
        SnapshotTimeoutError
            If the snapshot is not received after all attempts are exhausted.
        """
        pair = [self.settings.currency_pair]
        total_attempts = 1 + max_retries

        for attempt in range(1, total_attempts + 1):
            self.snapshot_received = False

            self.ws.open()
            self.ws.level2(pair)
            self.ws.market_trades(pair)
            self.ws.ticker(pair)

            deadline = time.monotonic() + snap_timeout
            while not self.snapshot_received and time.monotonic() < deadline:
                time.sleep(0.1)

            if self.snapshot_received:
                break

            print(f"Snapshot not received (attempt {attempt}/{total_attempts}). Closing connection.")
            try:
                self.ws.close()
            except Exception:
                pass

            if attempt < total_attempts:
                print(f"Waiting {retry_backoff}s before reconnecting.")
                time.sleep(retry_backoff)
                self.ws = WSClient(
                    **coinbase_credentials(),
                    on_message=self.on_message,
                    on_open=self.on_open,
                    on_close=self.on_close,
                )
            else:
                raise SnapshotTimeoutError(
                    f"l2_data snapshot not received after {total_attempts} attempt(s) "
                    f"for {self.settings.currency_pair}."
                )

        try:
            self.ws.sleep_with_exception_check(float(self.settings.recording_duration))
        finally:
            self.ws.close()

    # ------------------------------------------------------------------
    # Private channel handlers
    # ------------------------------------------------------------------

    def _handle_l2_data(self, msg):
        """
        Handle l2_data channel messages.

        The first event with type ``'snapshot'`` initialises the order book.
        Subsequent ``'update'`` events are applied incrementally.

        Coinbase field names (see module-level constants):
            ``side``          ``'bid'`` | ``'offer'``
            ``price_level``   price of the changed level
            ``new_quantity``  new volume (0 = remove the level)
            ``event_time``    ISO-8601 timestamp of the change
        """
        for event in msg.get("events", []):
            if event["type"] == "snapshot":
                bids, asks = [], []
                for u in event.get("updates", []):
                    entry = [u[_PRICE_LEVEL], u[_NEW_QUANTITY]]
                    if u[_SIDE] == _SIDE_BID:
                        bids.append(entry)
                    else:
                        asks.append(entry)
                self.book.initialise_from_snapshot(
                    {"bids": bids, "asks": asks}, self.session_start
                )
                self.snapshot_received = True
                self.decimal_places = self.book.min_dec

            elif event["type"] == "update" and self.snapshot_received:
                for u in event.get("updates", []):
                    side = _SIDE_BID if u[_SIDE] == _SIDE_BID else "ask"
                    price_level = float(u[_PRICE_LEVEL])
                    level_depth = np.around(float(u[_NEW_QUANTITY]), decimals=self.decimal_places)
                    timestamp = datetime.fromisoformat(u[_EVENT_TIME].replace("Z", "+00:00"))

                    price_range = self.book.bid_range if side == "bid" else self.book.ask_range
                    match_index = next(
                        (i for i, p in enumerate(price_range) if ob.price_match(p, price_level)),
                        None,
                    )
                    ob.apply_update(
                        self.book, timestamp, side, price_level, level_depth,
                        match_index, self.settings.position_range,
                    )

    def _handle_market_trades(self, msg):
        """
        Handle market_trades channel messages.

        Coinbase field names (see module-level constants):
            ``side``   ``'BUY'`` | ``'SELL'`` — the aggressor (taker) side
            ``price``  execution price
            ``size``   executed quantity
            ``time``   ISO-8601 timestamp
        """
        if not self.snapshot_received:
            return

        for event in msg.get("events", []):
            for trade in event.get("trades", []):
                timestamp = datetime.fromisoformat(trade[_TRADE_TIME].replace("Z", "+00:00"))
                taker_side = trade[_SIDE].lower()
                # crobat convention: side is the resting order side that was hit
                side = "bid" if taker_side == _TAKER_SELL.lower() else "ask"

                # Use the live order book for mid/spread — always current from L2 updates.
                # The ticker cache (self.best_bid/ask) is intentionally not used here
                # because it can lag behind L2 updates and produce stale values.
                mid_price = self.book.mid_price
                spread = self.book.spread
                position = -1 if side == "bid" else 1

                size = np.around(float(trade[_TRADE_SIZE]), decimals=self.decimal_places)
                # A trade whose size rounds to zero is not a real fill — drop it.
                if size == 0:
                    continue
                size_signed = size if side == "bid" else -size

                signed_event = [timestamp, "market", float(trade[_TRADE_PRICE]), size_signed, position, side, mid_price, spread]
                sided_event  = [timestamp, "market", float(trade[_TRADE_PRICE]), size,        position, mid_price, spread]

                self.book.signed_events = self.book.add_market_order(signed_event, self.book.signed_events)
                self.book.remove_market_cancel_duplicate(self.book.signed_events, "market")

                if side == "ask":
                    self.book.ask_events = self.book.add_market_order(sided_event, self.book.ask_events)
                    self.book.remove_market_cancel_duplicate(self.book.ask_events, "market")
                else:
                    self.book.bid_events = self.book.add_market_order(sided_event, self.book.bid_events)
                    self.book.remove_market_cancel_duplicate(self.book.bid_events, "market")

    def _handle_ticker_quotes(self, msg):
        """
        Receive ticker channel messages.

        The ticker channel is subscribed to keep the WebSocket connection
        active and to receive best-bid/ask updates. Mid-price and spread for
        all event types are computed directly from the live L2 order book
        (``self.book.mid_price`` / ``self.book.spread``) rather than from
        ticker data, so no values are cached here.
        """
        pass


def main():
    pass


if __name__ == "__main__":
    main()
