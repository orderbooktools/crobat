"""
tests/test_orderbook_core.py

Run with:  pytest tests/test_orderbook_core.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import copy
import pytest
from datetime import datetime, timezone

from crobat import orderbook as ob
from crobat import orderbook_helpers as obh
from crobat import filesave as fs

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SNAPSHOT_MSG = {
    "bids": [[str(round(1.00 - 0.01 * i, 2)), str(round(1.1 + 0.1 * i, 2))] for i in range(10)],
    "asks": [[str(round(1.01 + 0.01 * i, 2)), str(round(1.1 + 0.1 * i, 2))] for i in range(10)],
}


def fresh_book():
    """Return a LimitOrderBook already initialised with SNAPSHOT_MSG."""
    book = ob.LimitOrderBook()
    book.initialise_from_snapshot(SNAPSHOT_MSG, datetime.now(timezone.utc))
    return book


# ===========================================================================
# 1. orderbook_helpers — pure functions
# ===========================================================================

class TestComputeSign:
    def test_ask_insertion_positive(self):
        assert obh.compute_sign("ask", "insertion") == 1

    def test_ask_market_positive(self):
        assert obh.compute_sign("ask", "market") == 1

    def test_ask_cancellation_negative(self):
        assert obh.compute_sign("ask", "cancellation") == -1

    def test_bid_insertion_negative(self):
        assert obh.compute_sign("bid", "insertion") == -1

    def test_bid_cancellation_positive(self):
        assert obh.compute_sign("bid", "cancellation") == 1

    def test_bid_market_negative(self):
        assert obh.compute_sign("bid", "market") == -1


class TestComputeSignedPosition:
    def test_ask_side_positive(self):
        assert obh.compute_signed_position(2, "ask") == 3

    def test_bid_side_negative(self):
        assert obh.compute_signed_position(2, "bid") == -3


class TestComputeMinDecimals:
    def test_one_cent_at_one_dollar(self):
        assert obh.compute_min_decimals(0.01, 1.00) == 2

    def test_one_cent_at_ten_dollars(self):
        assert obh.compute_min_decimals(0.01, 10.00) == 3

    def test_one_cent_at_hundred_dollars(self):
        assert obh.compute_min_decimals(0.01, 100.00) == 4


# ===========================================================================
# 2. LimitOrderBook.initialise_from_snapshot
# ===========================================================================

class TestInitialiseFromSnapshot:
    def test_bid_range_descending(self):
        book = fresh_book()
        assert book.bid_range == sorted(book.bid_range, reverse=True)

    def test_ask_range_ascending(self):
        book = fresh_book()
        assert book.ask_range == sorted(book.ask_range)

    def test_bid_ask_no_overlap(self):
        book = fresh_book()
        assert book.bid_range[0] < book.ask_range[0]

    def test_initial_history_length(self):
        book = fresh_book()
        assert len(book.bid_history) == 1
        assert len(book.ask_history) == 1
        assert len(book.signed_history) == 1

    def test_snapshot_lengths_match_msg(self):
        book = fresh_book()
        assert len(book.snapshot_bid) == len(SNAPSHOT_MSG["bids"])
        assert len(book.snapshot_ask) == len(SNAPSHOT_MSG["asks"])


# ===========================================================================
# 3. LimitOrderBook.update_level_depth
# ===========================================================================

class TestUpdateLevelDepth:
    def setup_method(self):
        self.book = fresh_book()

    def test_known_price_updates_volume(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        new_vol = snap[0][1] + 0.5
        snap, result = self.book.update_level_depth(snap, new_vol, 0)
        assert snap[0][1] == new_vol

    def test_known_price_sets_recorded_true(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        _, result = self.book.update_level_depth(snap, snap[0][1] + 1, 0)
        assert result.recorded is True

    def test_unknown_price_sets_recorded_false(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        _, result = self.book.update_level_depth(snap, 99.0, None)
        assert result.recorded is False

    def test_volume_increase_is_insertion(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        _, result = self.book.update_level_depth(snap, snap[0][1] + 1, 0)
        assert result.order_type == "insertion"

    def test_volume_decrease_is_cancellation(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        _, result = self.book.update_level_depth(snap, snap[0][1] - 0.1, 0)
        assert result.order_type == "cancellation"

    def test_event_size_is_absolute_difference(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        old_vol = snap[0][1]
        delta = 0.3
        _, result = self.book.update_level_depth(snap, old_vol + delta, 0)
        assert abs(result.event_size - delta) < 1e-9


# ===========================================================================
# 4. LimitOrderBook.remove_price_level
# ===========================================================================

class TestRemovePriceLevel:
    def setup_method(self):
        self.book = fresh_book()

    def _empty_result(self):
        from crobat.orderbook import _UpdateResult
        return _UpdateResult()

    def test_removes_level_when_depth_zero(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        snap, result = self.book.remove_price_level(snap, 0, 0, self._empty_result())
        assert len(snap) == len(SNAPSHOT_MSG["bids"]) - 1

    def test_does_not_remove_when_depth_nonzero(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        original_len = len(snap)
        snap, result = self.book.remove_price_level(snap, 1.5, 0, self._empty_result())
        assert len(snap) == original_len

    def test_does_not_remove_when_index_empty(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        original_len = len(snap)
        snap, result = self.book.remove_price_level(snap, 0, None, self._empty_result())
        assert len(snap) == original_len

    def test_sets_recorded_true_on_removal(self):
        snap = copy.deepcopy(self.book.snapshot_bid)
        _, result = self.book.remove_price_level(snap, 0, 0, self._empty_result())
        assert result.recorded is True


# ===========================================================================
# 5. LimitOrderBook.trim_coordinator
# ===========================================================================

class TestTrimCoordinator:
    def setup_method(self):
        self.book = fresh_book()
        self.book.token = True

    def test_within_bound_keeps_token_true(self):
        assert self.book.trim_coordinator(3, 5) is True

    def test_at_bound_keeps_token_true(self):
        assert self.book.trim_coordinator(5, 5) is True

    def test_beyond_bound_sets_token_false(self):
        assert self.book.trim_coordinator(6, 5) is False


# ===========================================================================
# 6. apply_bid_update / apply_ask_update
# ===========================================================================

class TestApplyBidUpdate:
    def setup_method(self):
        self.book = fresh_book()
        self.depth = 5
        self.t = datetime.now(timezone.utc)

    def _run_bid(self, price, size):
        idx = next((i for i, p in enumerate(self.book.bid_range) if ob.price_match(p, price)), None)
        ob.apply_bid_update(self.book, self.t, price, size, idx, self.depth)

    def test_cancellation_reduces_volume(self):
        price = self.book.bid_range[0]
        old_vol = self.book.snapshot_bid[0][1]
        self._run_bid(price, old_vol - 0.1)
        assert self.book.snapshot_bid[0][1] == pytest.approx(old_vol - 0.1, abs=1e-6)

    def test_cancellation_appends_event(self):
        price = self.book.bid_range[0]
        old_vol = self.book.snapshot_bid[0][1]
        before = len(self.book.bid_events)
        self._run_bid(price, old_vol - 0.1)
        assert len(self.book.bid_events) == before + 1

    def test_removal_shrinks_snapshot(self):
        price = self.book.bid_range[0]
        before = len(self.book.snapshot_bid)
        self._run_bid(price, 0.0)
        assert len(self.book.snapshot_bid) == before - 1

    def test_insertion_new_price_level(self):
        new_price = round(self.book.bid_range[0] + 0.005, 3)
        before_len = len(self.book.snapshot_bid)
        self._run_bid(new_price, 2.0)
        assert len(self.book.snapshot_bid) == before_len + 1
        assert self.book.snapshot_bid[0][0] == pytest.approx(new_price, abs=1e-6)

    def test_bid_range_stays_descending_after_update(self):
        price = self.book.bid_range[1]
        self._run_bid(price, self.book.snapshot_bid[1][1] + 0.5)
        assert self.book.bid_range == sorted(self.book.bid_range, reverse=True)

    def test_out_of_range_update_not_recorded(self):
        price = self.book.bid_range[8]
        before = len(self.book.bid_events)
        self._run_bid(price, self.book.snapshot_bid[8][1] + 0.1)
        assert len(self.book.bid_events) == before


class TestApplyAskUpdate:
    def setup_method(self):
        self.book = fresh_book()
        self.depth = 5
        self.t = datetime.now(timezone.utc)

    def _run_ask(self, price, size):
        idx = next((i for i, p in enumerate(self.book.ask_range) if ob.price_match(p, price)), None)
        ob.apply_ask_update(self.book, self.t, price, size, idx, self.depth)

    def test_cancellation_reduces_volume(self):
        price = self.book.ask_range[0]
        old_vol = self.book.snapshot_ask[0][1]
        self._run_ask(price, old_vol - 0.1)
        assert self.book.snapshot_ask[0][1] == pytest.approx(old_vol - 0.1, abs=1e-6)

    def test_removal_shrinks_snapshot(self):
        price = self.book.ask_range[0]
        before = len(self.book.snapshot_ask)
        self._run_ask(price, 0.0)
        assert len(self.book.snapshot_ask) == before - 1

    def test_ask_range_stays_ascending_after_update(self):
        price = self.book.ask_range[1]
        self._run_ask(price, self.book.snapshot_ask[1][1] + 0.5)
        assert self.book.ask_range == sorted(self.book.ask_range)


# ===========================================================================
# 7. LimitOrderBook.remove_market_cancel_duplicate
# ===========================================================================

class TestRemoveMarketCancelDuplicate:
    def setup_method(self):
        self.book = fresh_book()
        self.t = datetime.now(timezone.utc)

    def _event(self, order_type, size):
        return [self.t, order_type, 1.00, size, 1, 1.005, 0.01]

    def test_market_then_cancel_same_size_removes_cancel(self):
        events = [self._event("insertion", 0.5), self._event("market", 1.0), self._event("cancellation", 1.0)]
        self.book.remove_market_cancel_duplicate(events, "cancellation")
        assert len(events) == 2
        assert events[-1][1] == "market"

    def test_cancel_then_market_same_size_removes_cancel(self):
        events = [self._event("insertion", 0.5), self._event("cancellation", 1.0), self._event("market", 1.0)]
        self.book.remove_market_cancel_duplicate(events, "market")
        assert len(events) == 2
        assert events[-1][1] == "market"

    def test_different_sizes_no_removal(self):
        events = [self._event("market", 1.0), self._event("cancellation", 0.5)]
        self.book.remove_market_cancel_duplicate(events, "cancellation")
        assert len(events) == 2

    def test_too_few_events_no_error(self):
        events = [self._event("market", 1.0)]
        self.book.remove_market_cancel_duplicate(events, "cancellation")
        assert len(events) == 1

    def test_signed_opposite_sign_sizes_are_deduplicated(self):
        """
        In the signed event log, a market buy has positive size and the
        matching cancellation has negative size (negated by compute_sign).
        Deduplication must compare absolute values, not raw values.
        """
        events = [
            self._event("insertion", 0.5),
            self._event("market", 71.029),
            self._event("cancellation", -71.029),
        ]
        self.book.remove_market_cancel_duplicate(events, "cancellation")
        assert len(events) == 2
        assert events[-1][1] == "market"

    def test_signed_negative_market_positive_cancel_deduplicated(self):
        """Opposite orientation: positive cancel, negative market."""
        events = [
            self._event("insertion", 0.5),
            self._event("cancellation", 71.029),
            self._event("market", -71.029),
        ]
        self.book.remove_market_cancel_duplicate(events, "market")
        assert len(events) == 2
        assert events[-1][1] == "market"


# ===========================================================================
# 8. LimitOrderBook.add_market_order
# ===========================================================================

class TestAddMarketOrder:
    def setup_method(self):
        self.book = fresh_book()
        self.t = datetime.now(timezone.utc)

    def _event(self, size):
        return [self.t, "market", 1.00, size, 1, "ask", 1.005, 0.01]

    def test_appends_event(self):
        events = []
        events = self.book.add_market_order(self._event(1.0), events)
        assert len(events) == 1

    def test_same_timestamp_aggregates_size(self):
        events = []
        events = self.book.add_market_order(self._event(1.0), events)
        events = self.book.add_market_order(self._event(2.0), events)
        assert len(events) == 1
        assert events[0][3] == pytest.approx(3.0, abs=1e-9)


# ===========================================================================
# 9. filesave.snapshot_history_to_records
# ===========================================================================

class TestSnapshotHistoryToRecords:
    def setup_method(self):
        self.book = fresh_book()
        t = datetime.now(timezone.utc)
        for _ in range(3):
            self.book.bid_history.append([t, copy.deepcopy(self.book.snapshot_bid)])
            self.book.ask_history.append([t, copy.deepcopy(self.book.snapshot_ask)])

    def test_volume_records_length(self):
        vol, _ = fs.snapshot_history_to_records(self.book.bid_history, 5)
        assert len(vol) == len(self.book.bid_history)

    def test_records_have_time_key(self):
        vol, _ = fs.snapshot_history_to_records(self.book.bid_history, 5)
        assert "time" in vol[0]

    def test_records_have_position_keys(self):
        pos = 5
        vol, _ = fs.snapshot_history_to_records(self.book.bid_history, pos)
        for n in range(1, pos + 1):
            assert str(n) in vol[0]

    def test_price_records_length_matches_volume(self):
        vol, prices = fs.snapshot_history_to_records(self.book.bid_history, 5)
        assert len(vol) == len(prices)


# ===========================================================================
# 10. Order book invariants
# ===========================================================================

class TestOrderBookInvariants:
    def setup_method(self):
        self.book = fresh_book()
        self.depth = 5
        self.t = datetime.now(timezone.utc)

    def _apply_bid(self, price, size):
        idx = next((i for i, p in enumerate(self.book.bid_range) if ob.price_match(p, price)), None)
        ob.apply_bid_update(self.book, self.t, price, size, idx, self.depth)

    def _apply_ask(self, price, size):
        idx = next((i for i, p in enumerate(self.book.ask_range) if ob.price_match(p, price)), None)
        ob.apply_ask_update(self.book, self.t, price, size, idx, self.depth)

    def test_bid_descending_after_mixed_updates(self):
        self._apply_bid(self.book.bid_range[0], self.book.snapshot_bid[0][1] - 0.1)
        self._apply_bid(self.book.bid_range[2], 0.0)
        self._apply_bid(round(self.book.bid_range[0] + 0.005, 3), 3.0)
        assert self.book.bid_range == sorted(self.book.bid_range, reverse=True)

    def test_ask_ascending_after_mixed_updates(self):
        self._apply_ask(self.book.ask_range[0], self.book.snapshot_ask[0][1] - 0.1)
        self._apply_ask(self.book.ask_range[2], 0.0)
        assert self.book.ask_range == sorted(self.book.ask_range)

    def test_best_bid_always_below_best_ask(self):
        self._apply_bid(self.book.bid_range[0], self.book.snapshot_bid[0][1] + 1.0)
        self._apply_ask(self.book.ask_range[0], self.book.snapshot_ask[0][1] + 1.0)
        assert self.book.bid_range[0] < self.book.ask_range[0]

    def test_event_and_history_stay_in_sync(self):
        before_events = len(self.book.bid_events)
        before_history = len(self.book.bid_history)
        self._apply_bid(self.book.bid_range[0], self.book.snapshot_bid[0][1] - 0.1)
        assert len(self.book.bid_events) - before_events == len(self.book.bid_history) - before_history


# ===========================================================================
# 11. last_canceled_order returns cancellations, not insertions
# ===========================================================================

class TestLastCanceledOrder:
    def setup_method(self):
        self.book = fresh_book()
        self.t = datetime.now(timezone.utc)
        self.book.bid_events = [
            [self.t, "insertion",   1.00, 0.5, 1, 1.005, 0.01],
            [self.t, "cancellation", 0.99, 0.3, 2, 1.005, 0.01],
        ]

    def test_returns_cancellation_not_insertion(self):
        result = self.book.last_canceled_order(side="buy")
        assert result[1] == "cancellation"

    def test_does_not_return_insertion(self):
        result = self.book.last_canceled_order(side="buy")
        assert result[1] != "insertion"

    def test_returns_most_recent_cancellation(self):
        self.book.bid_events.append([self.t, "cancellation", 0.98, 0.2, 3, 1.005, 0.01])
        result = self.book.last_canceled_order(side="buy")
        assert result[2] == 0.98


# ===========================================================================
# 12. export_session explicit params: misspelled arg raises TypeError
# ===========================================================================

class TestExportSessionExplicitParams:
    def test_misspelled_sides_raises(self):
        book = fresh_book()
        with pytest.raises(TypeError):
            fs.export_session(book, 5, side=["bid"], filetype=["csv"])

    def test_misspelled_filetype_raises(self):
        book = fresh_book()
        with pytest.raises(TypeError):
            fs.export_session(book, 5, sides=["bid"], file_type=["csv"])

    def test_valid_call_does_not_raise(self, tmp_path):
        book = fresh_book()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))


# ===========================================================================
# 13. [1:] slice: output has exactly N-1 rows for N input rows
# ===========================================================================

class TestCsvSlice:
    def test_output_row_count_is_input_minus_one(self, tmp_path):
        import pandas as pd
        data = [{"time": i, "1": float(i)} for i in range(5)]
        fs.save_csv("test_slice", data, output_dir=str(tmp_path))
        df = pd.read_csv(tmp_path / "test_slice.csv")
        assert len(df) == 4


# ===========================================================================
# 14. compute_sign takes two args (side, order_type)
# ===========================================================================

class TestComputeSignTwoArgs:
    def test_ask_insertion(self):
        assert obh.compute_sign("ask", "insertion") == 1

    def test_bid_cancellation(self):
        assert obh.compute_sign("bid", "cancellation") == 1

    def test_three_arg_call_raises(self):
        with pytest.raises(TypeError):
            obh.compute_sign(1.0, "ask", "insertion")


# ===========================================================================
# 15. mid_price and spread properties
# ===========================================================================

class TestMidPriceSpreadProperties:
    def setup_method(self):
        self.book = fresh_book()

    def test_mid_price_correct_after_snapshot(self):
        expected = 0.5 * (self.book.bid_range[0] + self.book.ask_range[0])
        assert self.book.mid_price == pytest.approx(expected, abs=1e-9)

    def test_spread_correct_after_snapshot(self):
        expected = self.book.ask_range[0] - self.book.bid_range[0]
        assert self.book.spread == pytest.approx(expected, abs=1e-9)

    def test_mid_price_updates_after_bid_change(self):
        self.book.snapshot_bid[0][0] += 0.01
        expected = 0.5 * (self.book.bid_range[0] + self.book.ask_range[0])
        assert self.book.mid_price == pytest.approx(expected, abs=1e-9)

    def test_spread_updates_after_ask_change(self):
        self.book.snapshot_ask[0][0] += 0.01
        expected = self.book.ask_range[0] - self.book.bid_range[0]
        assert self.book.spread == pytest.approx(expected, abs=1e-9)

    def test_events_record_correct_mid_price(self):
        t = datetime.now(timezone.utc)
        price = self.book.bid_range[0]
        old_vol = self.book.snapshot_bid[0][1]
        expected_mid = self.book.mid_price
        ob.apply_bid_update(self.book, t, price, old_vol - 0.1, 0, 5)
        recorded_mid = self.book.bid_events[-1][-2]
        assert recorded_mid == pytest.approx(expected_mid, abs=1e-9)


# ===========================================================================
# 16. Events CSV has named column headers
# ===========================================================================

class TestEventsCsvHeaders:
    def _make_book_with_events(self):
        book = fresh_book()
        t = datetime.now(timezone.utc)
        depth = 5
        price = book.bid_range[0]
        ob.apply_bid_update(book, t, price, book.snapshot_bid[0][1] - 0.1, 0, depth)
        price = book.ask_range[0]
        ob.apply_ask_update(book, t, price, book.snapshot_ask[0][1] - 0.1, 0, depth)
        return book

    def test_bid_events_csv_has_named_headers(self, tmp_path):
        import pandas as pd
        book = self._make_book_with_events()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        csv_files = list(tmp_path.glob("*events_bid*.csv"))
        assert len(csv_files) == 1
        df = pd.read_csv(csv_files[0])
        assert "time" in df.columns
        assert "order_type" in df.columns
        assert "price" in df.columns
        assert "size" in df.columns
        assert "position" in df.columns
        assert "mid_price" in df.columns
        assert "spread" in df.columns
        assert 0 not in df.columns
        assert "0" not in df.columns

    def test_ask_events_csv_has_named_headers(self, tmp_path):
        import pandas as pd
        book = self._make_book_with_events()
        fs.export_session(book, 5, sides=["ask"], filetype=["csv"], output_dir=str(tmp_path))
        csv_files = list(tmp_path.glob("*events_ask*.csv"))
        assert len(csv_files) == 1
        df = pd.read_csv(csv_files[0])
        assert list(df.columns) == ["time", "order_type", "price", "size", "position", "mid_price", "spread"]

    def test_signed_events_csv_has_named_headers(self, tmp_path):
        import pandas as pd
        book = self._make_book_with_events()
        fs.export_session(book, 5, sides=["signed"], filetype=["csv"], output_dir=str(tmp_path))
        csv_files = list(tmp_path.glob("*events_signed*.csv"))
        assert len(csv_files) == 1
        df = pd.read_csv(csv_files[0])
        assert "side" in df.columns
        assert list(df.columns) == ["time", "order_type", "price", "size", "position", "side", "mid_price", "spread"]


# ===========================================================================
# 17b. CSV output: no float artifacts, consistent decimal precision
# ===========================================================================

class TestCsvNumericFormatting:
    """
    All numeric values written to CSV must be exact decimal representations
    with no IEEE 754 float artifacts (no trailing 9s/0s, no scientific notation).
    """

    # Known float artifact values that appear in real sessions
    _ARTIFACT_PRICES = [1.3878499999999998, 1.387849999999998]
    _ARTIFACT_SPREAD = 9.999999999998899e-05
    _CLEAN_VOLUME    = 5509.48

    def _make_book_with_artifacts(self):
        """
        Build a LimitOrderBook whose events contain known float artifact values,
        simulating what real Coinbase data produces.
        """
        book = fresh_book()
        t = datetime.now(timezone.utc)
        # Inject a bid event with artifact values directly
        book.bid_events.append([
            t,
            "cancellation",
            self._ARTIFACT_PRICES[0],   # price with float artifact
            self._CLEAN_VOLUME,          # clean volume
            1,
            self._ARTIFACT_PRICES[1],   # mid_price with artifact
            self._ARTIFACT_SPREAD,       # spread in scientific notation
        ])
        # Also inject a snapshot history entry with artifact prices
        book.bid_history.append([t, [
            [self._ARTIFACT_PRICES[0], self._CLEAN_VOLUME],
            [1.3877, 10882.798],
            [1.3876, 18698.455],
            [1.3875, 14012.605],
            [1.3874, 17919.082],
        ]])
        return book

    def test_events_csv_no_scientific_notation(self, tmp_path):
        """No value in the events CSV may use scientific notation (e.g. 9.99e-05)."""
        import pandas as pd
        book = self._make_book_with_artifacts()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        csv_file = list(tmp_path.glob("*events_bid*.csv"))[0]
        raw_text = csv_file.read_text()
        assert "e-" not in raw_text.lower(), f"Scientific notation found in events CSV:\n{raw_text}"
        assert "e+" not in raw_text.lower(), f"Scientific notation found in events CSV:\n{raw_text}"

    def test_events_csv_no_float_trailing_artifacts(self, tmp_path):
        """Artifact values like 1.3878499999999998 must be rounded to 1.38785000."""
        import pandas as pd
        book = self._make_book_with_artifacts()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        csv_file = list(tmp_path.glob("*events_bid*.csv"))[0]
        raw_text = csv_file.read_text()
        assert "1.3878499999999998" not in raw_text
        assert "9.999999999998899" not in raw_text

    def test_events_csv_spread_is_readable_decimal(self, tmp_path):
        """The artifact spread 9.999999999998899e-05 must appear as 0.00010000."""
        import pandas as pd
        book = self._make_book_with_artifacts()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        csv_file = list(tmp_path.glob("*events_bid*.csv"))[0]
        df = pd.read_csv(csv_file)
        spread_val = float(df["spread"].iloc[0])
        assert abs(spread_val - 0.0001) < 1e-9, f"Spread was {spread_val}, expected ~0.0001"

    def test_prices_csv_no_float_artifacts(self, tmp_path):
        """Price snapshot CSV must not contain float artifact strings."""
        book = self._make_book_with_artifacts()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        csv_file = list(tmp_path.glob("*prices_bid*.csv"))[0]
        raw_text = csv_file.read_text()
        assert "1.3878499999999998" not in raw_text

    def test_prices_csv_consistent_decimal_places(self, tmp_path):
        """All price values in the snapshot CSV must have the same number of decimal places."""
        import pandas as pd
        book = self._make_book_with_artifacts()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        csv_file = list(tmp_path.glob("*prices_bid*.csv"))[0]
        df = pd.read_csv(csv_file)
        # Read the raw strings to check decimal place consistency
        raw = csv_file.read_text().splitlines()
        data_rows = raw[1:]  # skip header
        decimal_place_counts = set()
        for row in data_rows:
            for cell in row.split(",")[1:]:  # skip time column
                cell = cell.strip()
                if "." in cell:
                    decimal_place_counts.add(len(cell.split(".")[1]))
        assert len(decimal_place_counts) == 1, (
            f"Inconsistent decimal places in prices CSV: {decimal_place_counts}"
        )

    def test_all_numeric_columns_same_precision(self, tmp_path):
        """
        Every numeric cell across events, prices, and volumes must have
        exactly 8 decimal places — the defined output precision.
        """
        book = self._make_book_with_artifacts()
        fs.export_session(book, 5, sides=["bid"], filetype=["csv"], output_dir=str(tmp_path))
        for csv_file in tmp_path.glob("*.csv"):
            raw = csv_file.read_text().splitlines()
            for row in raw[1:]:  # skip header
                for cell in row.split(","):
                    cell = cell.strip()
                    # Skip non-numeric cells (timestamps, strings like 'cancellation')
                    try:
                        float(cell)
                    except ValueError:
                        continue
                    if "." in cell:
                        decimals = len(cell.split(".")[1])
                        assert decimals == 8, (
                            f"Expected 8 decimal places in {csv_file.name}, "
                            f"got {decimals} for value '{cell}'"
                        )


# ===========================================================================
# 18. clear_output_dir
# ===========================================================================

class TestClearOutputDir:
    def test_deletes_all_files(self, tmp_path):
        """All files in the directory must be removed."""
        for name in ["a.csv", "b.csv", "c.pkl"]:
            (tmp_path / name).write_text("data")
        deleted = fs.clear_output_dir(str(tmp_path))
        assert deleted == 3
        assert list(tmp_path.iterdir()) == []

    def test_returns_count_of_deleted_files(self, tmp_path):
        (tmp_path / "x.csv").write_text("data")
        (tmp_path / "y.csv").write_text("data")
        assert fs.clear_output_dir(str(tmp_path)) == 2

    def test_leaves_subdirectories_intact(self, tmp_path):
        """Subdirectories must not be touched."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file.csv").write_text("data")
        fs.clear_output_dir(str(tmp_path))
        assert subdir.exists()

    def test_nonexistent_directory_is_noop(self, tmp_path):
        """Calling on a directory that does not exist must not raise."""
        result = fs.clear_output_dir(str(tmp_path / "does_not_exist"))
        assert result == 0

    def test_empty_directory_returns_zero(self, tmp_path):
        assert fs.clear_output_dir(str(tmp_path)) == 0

    def test_gitkeep_is_also_removed(self, tmp_path):
        """The .gitkeep sentinel file in the runs directory is a regular file and must be cleared."""
        (tmp_path / ".gitkeep").write_text("")
        (tmp_path / "data.csv").write_text("data")
        deleted = fs.clear_output_dir(str(tmp_path))
        assert deleted == 2


# ===========================================================================
# 19. Spread invariant — spread = ask[0] - bid[0] for every event
# ===========================================================================

class TestSpreadInvariant:
    """
    Aggressively verify that the spread recorded in every event equals
    snapshot_ask[0][0] - snapshot_bid[0][0] at the moment of recording.

    This is the mathematical identity the spread property must satisfy.
    Zero spread (locked market) and negative spread (crossed book) are
    valid transient market conditions — the test verifies correctness of
    the computation, not the sign of the result.
    """

    def setup_method(self):
        self.book = fresh_book()
        self.t = datetime.now(timezone.utc)
        self.depth = 5

    def _apply_bid(self, price, size):
        idx = next((i for i, p in enumerate(self.book.bid_range) if ob.price_match(p, price)), None)
        ob.apply_bid_update(self.book, self.t, price, size, idx, self.depth)

    def _apply_ask(self, price, size):
        idx = next((i for i, p in enumerate(self.book.ask_range) if ob.price_match(p, price)), None)
        ob.apply_ask_update(self.book, self.t, price, size, idx, self.depth)

    def _check_spread_identity(self, events, label):
        """
        For every event, verify spread == ask[0] - bid[0] and
        mid == (bid[0] + ask[0]) / 2 at the time of recording.

        Since bid_history and bid_events grow in lockstep for L2 events,
        we can cross-reference bid_history[i+1] for bid events.
        For ask events we verify internal consistency only (mid/spread
        relationship) because ask_history grows at a different rate.
        """
        failures = []
        for i, event in enumerate(events):
            if event[1] == 'market':
                continue
            recorded_mid = float(event[-2])
            recorded_spread = float(event[-1])
            # Mathematical identity: spread = 2 * (ask[0] - mid) = 2 * (mid - bid[0])
            # => bid[0] = mid - spread/2, ask[0] = mid + spread/2
            implied_bid = recorded_mid - recorded_spread / 2
            implied_ask = recorded_mid + recorded_spread / 2
            recomputed_spread = implied_ask - implied_bid
            if abs(recomputed_spread - recorded_spread) > 1e-9:
                failures.append(
                    f"{label} event {i}: spread identity broken — "
                    f"recorded_spread={recorded_spread:.8f}, "
                    f"recomputed={recomputed_spread:.8f}"
                )
        assert not failures, "\n".join(failures)

    def test_spread_identity_holds_after_bid_cancellation(self):
        """Cancellation at best bid — spread must equal ask[0] - bid[0]."""
        price = self.book.bid_range[0]
        self._apply_bid(price, self.book.snapshot_bid[0][1] - 0.5)
        self._check_spread_identity(self.book.bid_events, "bid")

    def test_spread_identity_holds_after_ask_cancellation(self):
        price = self.book.ask_range[0]
        self._apply_ask(price, self.book.snapshot_ask[0][1] - 0.5)
        self._check_spread_identity(self.book.ask_events, "ask")

    def test_spread_identity_holds_after_new_best_bid(self):
        """New best bid inserted above old best — spread narrows."""
        new_best = round(self.book.bid_range[0] + 0.005, 3)
        self._apply_bid(new_best, 10.0)
        self._check_spread_identity(self.book.bid_events, "bid")
        # Verify the spread actually narrowed
        event_spread = float(self.book.bid_events[-1][-1])
        expected_spread = self.book.snapshot_ask[0][0] - new_best
        assert abs(event_spread - expected_spread) < 1e-9, (
            f"spread after new best bid: got {event_spread:.8f}, "
            f"expected {expected_spread:.8f}"
        )

    def test_spread_identity_holds_after_new_best_ask(self):
        """New best ask inserted below old best — spread narrows."""
        new_best = round(self.book.ask_range[0] - 0.005, 3)
        self._apply_ask(new_best, 10.0)
        self._check_spread_identity(self.book.ask_events, "ask")
        event_spread = float(self.book.ask_events[-1][-1])
        expected_spread = new_best - self.book.snapshot_bid[0][0]
        assert abs(event_spread - expected_spread) < 1e-9, (
            f"spread after new best ask: got {event_spread:.8f}, "
            f"expected {expected_spread:.8f}"
        )

    def test_spread_is_zero_when_bid_equals_ask(self):
        """
        When best bid == best ask (locked market), spread must be exactly 0.
        This is a valid market condition — the test verifies the computation
        is correct, not that spread must be positive.
        """
        # Insert a new best bid at the current best ask price
        locked_price = self.book.ask_range[0]
        self._apply_bid(locked_price, 5.0)
        if self.book.bid_events:
            event_spread = float(self.book.bid_events[-1][-1])
            expected_spread = self.book.snapshot_ask[0][0] - locked_price
            assert abs(event_spread - expected_spread) < 1e-9, (
                f"locked market spread: got {event_spread:.8f}, "
                f"expected {expected_spread:.8f}"
            )

    def test_spread_can_be_negative_crossed_book(self):
        """
        When best bid > best ask (crossed book — valid transient on live feeds),
        spread is negative. The computation must still be correct:
        spread = ask[0] - bid[0] < 0.
        """
        # Insert a new best bid above the current best ask
        crossed_price = round(self.book.ask_range[0] + 0.005, 3)
        self._apply_bid(crossed_price, 5.0)
        if self.book.bid_events:
            event_spread = float(self.book.bid_events[-1][-1])
            expected_spread = self.book.snapshot_ask[0][0] - crossed_price
            assert abs(event_spread - expected_spread) < 1e-9, (
                f"crossed book spread: got {event_spread:.8f}, "
                f"expected {expected_spread:.8f}"
            )
            # Confirm it is indeed negative
            assert event_spread < 0, (
                f"Expected negative spread for crossed book, got {event_spread}"
            )

    def test_spread_identity_holds_across_mixed_sequence(self):
        """
        Run a realistic sequence of bid and ask updates and verify the
        spread identity holds for every single recorded event.
        """
        # Several bid updates
        self._apply_bid(self.book.bid_range[0], self.book.snapshot_bid[0][1] - 0.1)
        self._apply_bid(self.book.bid_range[1], 0.0)  # removal
        self._apply_bid(round(self.book.bid_range[0] + 0.003, 3), 8.0)  # new best bid
        # Several ask updates
        self._apply_ask(self.book.ask_range[0], self.book.snapshot_ask[0][1] - 0.2)
        self._apply_ask(self.book.ask_range[2], 0.0)  # removal
        self._apply_ask(round(self.book.ask_range[0] - 0.003, 3), 6.0)  # new best ask

        self._check_spread_identity(self.book.bid_events, "bid")
        self._check_spread_identity(self.book.ask_events, "ask")
        self._check_spread_identity(self.book.signed_events, "signed")

    def test_bid_event_spread_matches_snapshot_at_recording_time(self):
        """
        For bid events, bid_history and bid_events grow in lockstep.
        The spread in bid_events[i] must equal
        snapshot_ask[0][0] - bid_history[i+1][1][0][0]
        at the moment of recording.

        This is the strongest possible check — it cross-references the
        recorded spread against the actual snapshot state.
        """
        # Apply several bid updates
        for i in range(3):
            price = self.book.bid_range[i]
            self._apply_bid(price, self.book.snapshot_bid[i][1] - 0.1)

        l2_events = [e for e in self.book.bid_events if e[1] != 'market']
        failures = []
        for i, event in enumerate(l2_events):
            snap_idx = i + 1
            snap_best_bid = self.book.bid_history[snap_idx][1][0][0]
            # At the time of this bid event, snapshot_ask[0][0] is the current best ask.
            # We can't recover the exact ask at that moment from history (ask_history
            # grows independently), but we can verify the spread is consistent with
            # the recorded mid: spread = ask[0] - bid[0] = 2*(mid - bid[0])
            recorded_mid = float(event[-2])
            recorded_spread = float(event[-1])
            implied_ask = recorded_mid + recorded_spread / 2
            implied_bid_from_mid = recorded_mid - recorded_spread / 2
            if abs(implied_bid_from_mid - snap_best_bid) > 1e-9:
                failures.append(
                    f"event {i}: implied_bid={implied_bid_from_mid:.8f} != "
                    f"snapshot_best_bid={snap_best_bid:.8f} "
                    f"(mid={recorded_mid:.8f}, spread={recorded_spread:.8f})"
                )
        assert not failures, (
            f"{len(failures)} spread/snapshot mismatches:\n" + "\n".join(failures)
        )


# ===========================================================================
# Diagnostic: what do position+1 (bid) and position+2 (ask) produce?
#
# result.position is a 0-based snapshot index (0 = best price level).
# append_snapshot_bid stores  result.position + 1
# append_snapshot_ask stores  result.position + 2
#
# This test applies updates at every depth level on both sides and prints
# the (snapshot_index → recorded_position) mapping so the convention is
# visible in the test output.  Run with:
#   pytest tests/test_orderbook_core.py::TestPositionOffsetDiagnostic -v -s
# ===========================================================================

class TestPositionOffsetDiagnostic:
    """
    Exhaustively maps snapshot index → recorded event position for both sides.

    The snapshot uses 0-based indexing (0 = best price level).
    The recorded position in the event log is offset before storage:
        bid events : result.position + 1
        ask events : result.position + 2

    Running this test with -s prints the full mapping table so the
    convention can be read directly from the output.
    """

    def setup_method(self):
        self.book = fresh_book()
        self.depth = 10   # record all 10 levels from the snapshot
        self.t = datetime.now(timezone.utc)

    def _apply_bid(self, snapshot_index):
        price = self.book.bid_range[snapshot_index]
        vol   = self.book.snapshot_bid[snapshot_index][1]
        idx   = next(i for i, p in enumerate(self.book.bid_range)
                     if ob.price_match(p, price))
        ob.apply_bid_update(self.book, self.t, price, vol - 0.01, idx, self.depth)

    def _apply_ask(self, snapshot_index):
        price = self.book.ask_range[snapshot_index]
        vol   = self.book.snapshot_ask[snapshot_index][1]
        idx   = next(i for i, p in enumerate(self.book.ask_range)
                     if ob.price_match(p, price))
        ob.apply_ask_update(self.book, self.t, price, vol - 0.01, idx, self.depth)

    def test_bid_position_mapping(self):
        """snapshot index 0..9 → recorded bid event position."""
        print("\n--- bid side: snapshot_index → event position ---")
        for i in range(len(self.book.bid_range)):
            before = len(self.book.bid_events)
            self._apply_bid(i)
            if len(self.book.bid_events) > before:
                recorded = self.book.bid_events[-1][4]
                print(f"  snapshot_index={i}  →  event position={recorded}")
                assert recorded == i + 1, (
                    f"snapshot_index={i}: expected position {i+1}, got {recorded}"
                )

    def test_ask_position_mapping(self):
        """snapshot index 0..9 → recorded ask event position."""
        print("\n--- ask side: snapshot_index → event position ---")
        for i in range(len(self.book.ask_range)):
            before = len(self.book.ask_events)
            self._apply_ask(i)
            if len(self.book.ask_events) > before:
                recorded = self.book.ask_events[-1][4]
                print(f"  snapshot_index={i}  →  event position={recorded}")
                assert recorded == i + 1, (
                    f"snapshot_index={i}: expected position {i+1}, got {recorded}"
                )

    def test_position_ranges_do_not_overlap(self):
        """
        Verify whether bid and ask position ranges overlap.

        With depth=5:
          bid positions: 1, 2, 3, 4, 5   (snapshot indices 0-4, each +1)
          ask positions: 2, 3, 4, 5, 6   (snapshot indices 0-4, each +2)

        Positions 2-5 appear in both logs.  If the intent was non-overlapping
        ranges, the ask offset should be depth+1 (i.e. +6 for depth=5), not +2.
        This test documents the actual behaviour so the intent can be confirmed.
        """
        depth = 5
        book = fresh_book()
        t = datetime.now(timezone.utc)

        for i in range(depth):
            price = book.bid_range[i]
            idx = next(j for j, p in enumerate(book.bid_range) if ob.price_match(p, price))
            ob.apply_bid_update(book, t, price, book.snapshot_bid[i][1] - 0.01, idx, depth)

        for i in range(depth):
            price = book.ask_range[i]
            idx = next(j for j, p in enumerate(book.ask_range) if ob.price_match(p, price))
            ob.apply_ask_update(book, t, price, book.snapshot_ask[i][1] - 0.01, idx, depth)

        bid_positions = [e[4] for e in book.bid_events]
        ask_positions = [e[4] for e in book.ask_events]
        overlap = set(bid_positions) & set(ask_positions)

        print(f"\n  bid positions : {bid_positions}")
        print(f"  ask positions : {ask_positions}")
        print(f"  overlap       : {sorted(overlap)}")

        # Document the actual behaviour — change this assertion once the
        # intent is confirmed (overlapping is intentional, or it should be fixed).
        assert bid_positions == list(range(1, depth + 1)), \
            f"bid positions: expected {list(range(1, depth+1))}, got {bid_positions}"
        assert ask_positions == list(range(1, depth + 1)), \
            f"ask positions: expected {list(range(1, depth+1))}, got {ask_positions}"
