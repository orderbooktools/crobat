"""
tests/test_recorder.py

Unit tests for crobat/recorder.py.
No network connection required — WSClient is never opened.

Run with:  pytest tests/test_recorder.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import pytest
from unittest.mock import MagicMock, patch

from tests.mockobjects import cdp_messages


# ---------------------------------------------------------------------------
# Fixture — L2Recorder instance with WSClient mocked out
# ---------------------------------------------------------------------------

class FakeSettings:
    currency_pair      = "MKC-USD"
    position_range     = 5
    recording_duration = 10
    sides              = ["bid", "ask", "signed"]
    filetype           = ["csv"]


@pytest.fixture
def recorder():
    """
    Return an L2Recorder whose WSClient is replaced with a MagicMock so no
    network connection is ever attempted.
    """
    with patch("coinbase.websocket.WSClient", return_value=MagicMock()):
        from crobat.recorder import L2Recorder
        return L2Recorder(FakeSettings())


# ===========================================================================
# 1. on_message routing
# ===========================================================================

class TestOnMessageRouting:
    def test_l2_data_routes_to_handle_l2_data(self, recorder):
        recorder._handle_l2_data = MagicMock()
        recorder.on_message(cdp_messages.snapshot())
        recorder._handle_l2_data.assert_called_once()

    def test_market_trades_routes_to_handle_market_trades(self, recorder):
        recorder._handle_market_trades = MagicMock()
        recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        recorder._handle_market_trades.assert_called_once()

    def test_ticker_routes_to_handle_ticker_quotes(self, recorder):
        recorder._handle_ticker_quotes = MagicMock()
        recorder.on_message(cdp_messages.ticker("0.99", "1.01"))
        recorder._handle_ticker_quotes.assert_called_once()

    def test_unknown_channel_does_not_raise(self, recorder):
        recorder.on_message(json.dumps({"channel": "heartbeats", "events": []}))


# ===========================================================================
# 2. _handle_l2_data — snapshot
# ===========================================================================

class TestHandleL2DataSnapshot:

    def test_snapshot_received_becomes_true(self, recorder):
        assert recorder.snapshot_received is False
        recorder.on_message(cdp_messages.snapshot())
        assert recorder.snapshot_received is True

    def test_bid_range_populated(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert len(recorder.book.bid_range) > 0

    def test_ask_range_populated(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert len(recorder.book.ask_range) > 0

    def test_bid_range_descending(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert recorder.book.bid_range == sorted(recorder.book.bid_range, reverse=True)

    def test_ask_range_ascending(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert recorder.book.ask_range == sorted(recorder.book.ask_range)

    def test_best_bid_below_best_ask(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert recorder.book.bid_range[0] < recorder.book.ask_range[0]

    def test_decimal_places_set_from_snapshot(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert isinstance(recorder.decimal_places, int)
        assert recorder.decimal_places >= 0

    def test_offer_side_maps_to_ask(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        assert len(recorder.book.snapshot_ask) > 0
        assert len(recorder.book.snapshot_bid) > 0


# ===========================================================================
# 3. _handle_l2_data — update
# ===========================================================================

class TestHandleL2DataUpdate:

    @pytest.fixture(autouse=True)
    def init_snapshot(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        self.recorder = recorder

    def test_bid_update_modifies_snapshot_bid(self):
        price = self.recorder.book.bid_range[0]
        old_vol = self.recorder.book.snapshot_bid[0][1]
        self.recorder.on_message(cdp_messages.l2update("bid", price, old_vol - 0.1))
        assert self.recorder.book.snapshot_bid[0][1] < old_vol

    def test_offer_update_modifies_snapshot_ask(self):
        price = self.recorder.book.ask_range[0]
        old_vol = self.recorder.book.snapshot_ask[0][1]
        self.recorder.on_message(cdp_messages.l2update("offer", price, old_vol - 0.1))
        assert self.recorder.book.snapshot_ask[0][1] < old_vol

    def test_bid_update_within_range_appends_event(self):
        price = self.recorder.book.bid_range[0]
        old_vol = self.recorder.book.snapshot_bid[0][1]
        before = len(self.recorder.book.bid_events)
        self.recorder.on_message(cdp_messages.l2update("bid", price, old_vol - 0.1))
        assert len(self.recorder.book.bid_events) == before + 1

    def test_bid_removal_shrinks_snapshot(self):
        price = self.recorder.book.bid_range[0]
        before = len(self.recorder.book.snapshot_bid)
        self.recorder.on_message(cdp_messages.l2update("bid", price, 0.0))
        assert len(self.recorder.book.snapshot_bid) == before - 1

    def test_bid_range_stays_descending_after_update(self):
        price = self.recorder.book.bid_range[1]
        self.recorder.on_message(cdp_messages.l2update("bid", price, 0.0))
        assert self.recorder.book.bid_range == sorted(self.recorder.book.bid_range, reverse=True)

    def test_ask_range_stays_ascending_after_update(self):
        price = self.recorder.book.ask_range[1]
        self.recorder.on_message(cdp_messages.l2update("offer", price, 0.0))
        assert self.recorder.book.ask_range == sorted(self.recorder.book.ask_range)


# ===========================================================================
# 4. _handle_market_trades
# ===========================================================================

class TestHandleMarketTrades:

    @pytest.fixture(autouse=True)
    def init_snapshot(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        recorder.on_message(cdp_messages.ticker("0.99", "1.01"))
        self.recorder = recorder

    def test_buy_taker_appends_to_ask_events(self):
        before = len(self.recorder.book.ask_events)
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        assert len(self.recorder.book.ask_events) == before + 1

    def test_sell_taker_appends_to_bid_events(self):
        before = len(self.recorder.book.bid_events)
        self.recorder.on_message(cdp_messages.market_trade("SELL", 0.99, 0.5))
        assert len(self.recorder.book.bid_events) == before + 1

    def test_trade_appends_to_signed_events(self):
        before = len(self.recorder.book.signed_events)
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        assert len(self.recorder.book.signed_events) == before + 1

    def test_event_order_type_is_market(self):
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        assert self.recorder.book.ask_events[-1][1] == "market"

    def test_buy_taker_size_is_negative_in_signed_events(self):
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        assert self.recorder.book.signed_events[-1][3] < 0

    def test_sell_taker_size_is_positive_in_signed_events(self):
        self.recorder.on_message(cdp_messages.market_trade("SELL", 0.99, 0.5))
        assert self.recorder.book.signed_events[-1][3] > 0

    def test_zero_size_trade_is_not_recorded(self):
        """
        A trade whose size rounds to zero after decimal quantisation must be
        silently dropped. A zero-size market order is not a trade.
        """
        before_ask = len(self.recorder.book.ask_events)
        before_signed = len(self.recorder.book.signed_events)
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.0))
        assert len(self.recorder.book.ask_events) == before_ask
        assert len(self.recorder.book.signed_events) == before_signed

    def test_zero_size_sell_trade_is_not_recorded(self):
        """Same guard for the sell (bid) side."""
        before_bid = len(self.recorder.book.bid_events)
        before_signed = len(self.recorder.book.signed_events)
        self.recorder.on_message(cdp_messages.market_trade("SELL", 0.99, 0.0))
        assert len(self.recorder.book.bid_events) == before_bid
        assert len(self.recorder.book.signed_events) == before_signed

    def test_all_recorded_market_sizes_are_strictly_positive(self):
        """
        After several trades, every size in ask_events, bid_events, and
        signed_events must be non-zero (absolute value > 0).
        """
        self.recorder.on_message(cdp_messages.market_trade("BUY",  1.01, 1.0))
        self.recorder.on_message(cdp_messages.market_trade("SELL", 0.99, 2.0))
        self.recorder.on_message(cdp_messages.market_trade("BUY",  1.01, 0.5))
        for event in self.recorder.book.ask_events:
            assert abs(event[3]) > 0, f"zero-size ask event: {event}"
        for event in self.recorder.book.bid_events:
            assert abs(event[3]) > 0, f"zero-size bid event: {event}"
        for event in self.recorder.book.signed_events:
            assert abs(event[3]) > 0, f"zero-size signed event: {event}"


# ===========================================================================
# standalone pre-snapshot guard tests
# ===========================================================================

def test_l2update_before_snapshot_is_ignored(recorder):
    assert recorder.snapshot_received is False
    recorder.on_message(cdp_messages.l2update("bid", 0.99, 1.0))
    assert len(recorder.book.bid_events) == 0


def test_trade_before_snapshot_does_not_raise(recorder):
    assert recorder.snapshot_received is False
    recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
    assert len(recorder.book.signed_events) == 0


# ===========================================================================
# 5. _handle_ticker_quotes
# ===========================================================================

class TestHandleTickerQuotes:
    """
    The ticker channel is subscribed to keep the connection active.
    Mid-price and spread are computed from the live L2 book, not from
    ticker data, so the handler is a no-op. These tests verify it
    processes ticker messages without raising.
    """

    def test_ticker_message_does_not_raise(self, recorder):
        recorder.on_message(cdp_messages.ticker("0.98", "1.02"))

    def test_subsequent_ticker_does_not_raise(self, recorder):
        recorder.on_message(cdp_messages.ticker("0.98", "1.02"))
        recorder.on_message(cdp_messages.ticker("0.97", "1.03"))

    def test_partial_ticker_does_not_raise(self, recorder):
        msg = json.dumps({
            "channel": "ticker",
            "events": [{"type": "update", "tickers": [{"best_ask": "1.05"}]}],
        })
        recorder.on_message(msg)


# ===========================================================================
# 6. mid_price and spread accuracy across event types
# ===========================================================================

class TestMidPriceSpreadAccuracy:
    """
    Verify that mid_price and spread recorded in events always reflect the
    current best bid and best ask at the time of the event.

    The snapshot fixture has:
        best bid = 0.99, best ask = 1.01
        mid_price = 1.00, spread = 0.02
    """

    @pytest.fixture(autouse=True)
    def init(self, recorder):
        recorder.on_message(cdp_messages.snapshot())
        self.recorder = recorder
        # Snapshot best bid/ask from cdp_messages constants
        self.initial_best_bid = 0.99
        self.initial_best_ask = 1.01
        self.initial_mid   = 0.5 * (self.initial_best_bid + self.initial_best_ask)
        self.initial_spread = self.initial_best_ask - self.initial_best_bid

    # --- L2 update events carry the correct initial mid/spread ---

    def test_l2_bid_event_records_correct_initial_mid(self):
        price = self.recorder.book.bid_range[0]
        old_vol = self.recorder.book.snapshot_bid[0][1]
        self.recorder.on_message(cdp_messages.l2update("bid", price, old_vol - 0.1))
        recorded_mid = self.recorder.book.bid_events[-1][-2]
        assert recorded_mid == pytest.approx(self.initial_mid, abs=1e-9)

    def test_l2_ask_event_records_correct_initial_spread(self):
        price = self.recorder.book.ask_range[0]
        old_vol = self.recorder.book.snapshot_ask[0][1]
        self.recorder.on_message(cdp_messages.l2update("offer", price, old_vol - 0.1))
        recorded_spread = self.recorder.book.ask_events[-1][-1]
        assert recorded_spread == pytest.approx(self.initial_spread, abs=1e-9)

    # --- After best bid moves, the next event reflects the new mid/spread ---

    def test_mid_updates_after_best_bid_insertion(self):
        """A new best bid above the old one must raise mid_price."""
        new_best_bid = round(self.initial_best_bid + 0.005, 3)  # 0.995
        self.recorder.on_message(cdp_messages.l2update("bid", new_best_bid, 1.0))
        expected_mid = 0.5 * (new_best_bid + self.initial_best_ask)
        recorded_mid = self.recorder.book.bid_events[-1][-2]
        assert recorded_mid == pytest.approx(expected_mid, abs=1e-9)

    def test_spread_narrows_after_best_bid_insertion(self):
        new_best_bid = round(self.initial_best_bid + 0.005, 3)
        self.recorder.on_message(cdp_messages.l2update("bid", new_best_bid, 1.0))
        expected_spread = self.initial_best_ask - new_best_bid
        recorded_spread = self.recorder.book.bid_events[-1][-1]
        assert recorded_spread == pytest.approx(expected_spread, abs=1e-9)

    def test_mid_updates_after_best_ask_insertion(self):
        """A new best ask below the old one must lower mid_price."""
        new_best_ask = round(self.initial_best_ask - 0.005, 3)  # 1.005
        self.recorder.on_message(cdp_messages.l2update("offer", new_best_ask, 1.0))
        expected_mid = 0.5 * (self.initial_best_bid + new_best_ask)
        recorded_mid = self.recorder.book.ask_events[-1][-2]
        assert recorded_mid == pytest.approx(expected_mid, abs=1e-9)

    # --- Market trade events use the live book mid/spread, not stale ticker ---

    def test_market_trade_mid_matches_live_book(self):
        """
        A market trade event must record the mid_price from the live order book,
        not from a potentially stale ticker cache.
        """
        # Send a ticker with a stale (wrong) best bid/ask
        self.recorder.on_message(cdp_messages.ticker("0.50", "1.50"))
        # Then send a market trade — mid should come from the live book, not the ticker
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        recorded_mid = self.recorder.book.ask_events[-1][-2]
        assert recorded_mid == pytest.approx(self.initial_mid, abs=1e-9), (
            f"Market trade recorded mid={recorded_mid} but live book mid={self.initial_mid}. "
            "Stale ticker cache is leaking into event records."
        )

    def test_market_trade_spread_matches_live_book(self):
        """Same as above but for spread."""
        self.recorder.on_message(cdp_messages.ticker("0.50", "1.50"))
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        recorded_spread = self.recorder.book.ask_events[-1][-1]
        assert recorded_spread == pytest.approx(self.initial_spread, abs=1e-9), (
            f"Market trade recorded spread={recorded_spread} but live book spread={self.initial_spread}. "
            "Stale ticker cache is leaking into event records."
        )

    def test_market_trade_mid_reflects_l2_change(self):
        """
        If the best bid changes via an L2 update, the next market trade event
        must reflect the updated mid, not the pre-update value.
        """
        new_best_bid = round(self.initial_best_bid + 0.005, 3)
        self.recorder.on_message(cdp_messages.l2update("bid", new_best_bid, 1.0))
        expected_mid = 0.5 * (new_best_bid + self.initial_best_ask)
        self.recorder.on_message(cdp_messages.market_trade("BUY", 1.01, 0.5))
        recorded_mid = self.recorder.book.ask_events[-1][-2]
        assert recorded_mid == pytest.approx(expected_mid, abs=1e-9), (
            f"Market trade mid={recorded_mid} did not update after L2 best-bid change. "
            f"Expected {expected_mid}."
        )
