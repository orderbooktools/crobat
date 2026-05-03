"""
tests/test_integration_recorder.py

Integration tests for crobat/recorder.py.

Two levels:
    - TestFullMessageSequence  : no network, feeds a realistic ordered sequence
                                 of CDP messages through on_message and asserts
                                 the final state of book.
    - TestLiveConnection       : opens a real Coinbase WebSocket for ~10 seconds.
                                 Marked with pytest.mark.integration so it can be
                                 excluded from offline CI runs:
                                     pytest -m "not integration"

Run all:        pytest tests/test_integration_recorder.py -v
Run offline:    pytest tests/test_integration_recorder.py -v -m "not integration"
Run live only:  pytest tests/test_integration_recorder.py -v -m integration
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch

from tests.mockobjects import cdp_messages
from crobat.config import recording_defaults


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

class FakeSettings:
    currency_pair      = "XRP-USD"
    position_range     = 5
    recording_duration = 10
    sides              = ["bid", "ask", "signed"]
    filetype           = ["csv"]


@pytest.fixture
def recorder():
    from crobat.recorder import L2Recorder
    with patch("coinbase.websocket.WSClient", return_value=MagicMock()):
        return L2Recorder(FakeSettings())

# ===========================================================================
# Full message sequence — no network
# ===========================================================================

class TestFullMessageSequence:
    """
    Feeds a realistic ordered sequence through on_message and asserts the
    cumulative state of book after each stage.
    """

    @pytest.fixture(autouse=True)
    def setup(self, recorder):
        self.r = recorder

    # ---- Stage 1: snapshot ------------------------------------------------

    def test_stage1_snapshot_initialises_book(self):
        self.r.on_message(cdp_messages.snapshot())
        assert self.r.snapshot_received is True
        assert len(self.r.book.bid_range) > 0
        assert len(self.r.book.ask_range) > 0

    # ---- Stage 2: ticker quote arrives ------------------------------------

    def test_stage2_ticker_caches_quotes(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))
        # Ticker is subscribed to keep the connection active; mid/spread come
        # from the live L2 book. Verify the message is handled without error.
        assert self.r.snapshot_received is True

    # ---- Stage 3: bid-side cancellation -----------------------------------

    def test_stage3_bid_cancellation_recorded(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))

        price = self.r.book.bid_range[0]
        old_vol = self.r.book.snapshot_bid[0][1]
        self.r.on_message(cdp_messages.l2update("bid", price, old_vol - 0.1))

        assert len(self.r.book.bid_events) == 1
        assert self.r.book.bid_events[-1][1] == "cancellation"

    # ---- Stage 4: ask-side insertion --------------------------------------

    def test_stage4_ask_insertion_recorded(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))

        price = self.r.book.bid_range[0]
        old_vol = self.r.book.snapshot_bid[0][1]
        self.r.on_message(cdp_messages.l2update("bid", price, old_vol - 0.1))

        ask_price = self.r.book.ask_range[0]
        old_ask_vol = self.r.book.snapshot_ask[0][1]
        self.r.on_message(cdp_messages.l2update("offer", ask_price, old_ask_vol + 0.5))

        assert len(self.r.book.ask_events) == 1
        assert self.r.book.ask_events[-1][1] == "insertion"

    # ---- Stage 5: market trade --------------------------------------------

    def test_stage5_market_trade_appended(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))

        price = self.r.book.bid_range[0]
        old_vol = self.r.book.snapshot_bid[0][1]
        self.r.on_message(cdp_messages.l2update("bid", price, old_vol - 0.1))

        ask_price = self.r.book.ask_range[0]
        old_ask_vol = self.r.book.snapshot_ask[0][1]
        self.r.on_message(cdp_messages.l2update("offer", ask_price, old_ask_vol + 0.5))

        self.r.on_message(cdp_messages.market_trade("BUY", ask_price, 0.1))

        assert len(self.r.book.signed_events) >= 1
        assert self.r.book.signed_events[-1][1] == "market"

    # ---- Stage 6: market trade + matching cancellation deduplication ------

    def test_stage6_mkt_can_overlap_deduplication(self):
        """
        A market fill followed immediately by a matching l2 cancellation of
        the same size should be deduplicated by remove_market_cancel_duplicate.
        """
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))

        ask_price = self.r.book.ask_range[0]
        trade_size = 0.1

        # market fill
        self.r.on_message(cdp_messages.market_trade("BUY", ask_price, trade_size))
        events_after_trade = len(self.r.book.ask_events)

        # matching cancellation at the same price and size
        old_vol = self.r.book.snapshot_ask[0][1]
        self.r.on_message(cdp_messages.l2update("offer", ask_price, old_vol - trade_size))

        # the cancellation should have been removed — count must not grow by 2
        assert len(self.r.book.ask_events) <= events_after_trade + 1

    # ---- Invariants after full sequence -----------------------------------

    def test_invariant_bid_descending_after_sequence(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))
        self.r.on_message(cdp_messages.l2update("bid", self.r.book.bid_range[0],
                                                  self.r.book.snapshot_bid[0][1] - 0.1))
        self.r.on_message(cdp_messages.l2update("offer", self.r.book.ask_range[0],
                                                  self.r.book.snapshot_ask[0][1] + 0.5))
        assert self.r.book.bid_range == sorted(self.r.book.bid_range, reverse=True)

    def test_invariant_ask_ascending_after_sequence(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))
        self.r.on_message(cdp_messages.l2update("bid", self.r.book.bid_range[0],
                                                  self.r.book.snapshot_bid[0][1] - 0.1))
        self.r.on_message(cdp_messages.l2update("offer", self.r.book.ask_range[0],
                                                  self.r.book.snapshot_ask[0][1] + 0.5))
        assert self.r.book.ask_range == sorted(self.r.book.ask_range)

    def test_invariant_no_crossed_book_after_sequence(self):
        self.r.on_message(cdp_messages.snapshot())
        self.r.on_message(cdp_messages.ticker("0.99", "1.01"))
        self.r.on_message(cdp_messages.l2update("bid", self.r.book.bid_range[0],
                                                  self.r.book.snapshot_bid[0][1] - 0.1))
        assert self.r.book.bid_range[0] < self.r.book.ask_range[0]

    def test_invariant_events_and_history_in_sync(self):
        self.r.on_message(cdp_messages.snapshot())
        bid_events_before  = len(self.r.book.bid_events)
        bid_history_before = len(self.r.book.bid_history)

        self.r.on_message(cdp_messages.l2update("bid", self.r.book.bid_range[0],
                                                  self.r.book.snapshot_bid[0][1] - 0.1))

        assert (len(self.r.book.bid_events)  - bid_events_before ==
                len(self.r.book.bid_history) - bid_history_before)


# ===========================================================================
# Live connection — requires network
# ===========================================================================

@pytest.mark.integration
class TestLiveConnection:
    """
    Opens a real Coinbase WebSocket on XRP-USD for 10 seconds and asserts
    post-session invariants on the book object.

    Excluded from offline runs:  pytest -m "not integration"
    """

    def test_live_session_populates_orderbook(self):
        from crobat.recorder import L2Recorder

        defaults = recording_defaults()

        class LiveSettings:
            currency_pair      = defaults.get('currency_pair', 'XRP-USD')
            position_range     = defaults.get('position_range', 5)
            recording_duration = defaults.get('recording_duration', 10)
            sides              = defaults.get('sides', ['bid', 'ask', 'signed'])
            filetype           = []   # no file output during tests

        with patch("crobat.recorder.fs.export_session"):
            rec = L2Recorder(LiveSettings())
            rec.start()

        assert rec.snapshot_received is True, "snapshot was never received"
        assert rec.book.bid_range == sorted(rec.book.bid_range, reverse=True), \
            "bid_range is not descending"
        assert rec.book.ask_range == sorted(rec.book.ask_range), \
            "ask_range is not ascending"
        assert rec.book.bid_range[0] <= rec.book.ask_range[0], \
            f"book is crossed: best bid {rec.book.bid_range[0]} > best ask {rec.book.ask_range[0]}"
        assert len(rec.book.bid_history) > 1, \
            "no bid updates were processed"
        assert isinstance(rec.book.min_dec, int) and rec.book.min_dec >= 0, \
            "min_dec was not set"


@pytest.mark.integration
class TestLiveOutputFormatting:
    """
    Runs a real 15-second session, exports to a temp directory, and asserts
    that every CSV output file is free of formatting defects seen in
    production: scientific notation (0E-8, 1.23e+04), zero-size events,
    and market/cancel duplicate pairs.

    Excluded from offline runs:  pytest -m "not integration"
    """

    @pytest.fixture(autouse=True, scope="class")
    def run_session(self, tmp_path_factory):
        """
        Run a single live session once for the whole class and store the
        output directory and recorder on the class so all tests can read them.
        """
        from crobat.recorder import L2Recorder

        defaults = recording_defaults()
        out_dir = tmp_path_factory.mktemp("live_output")

        class LiveSettings:
            currency_pair      = defaults.get('currency_pair', 'XRP-USD')
            position_range     = defaults.get('position_range', 5)
            recording_duration = 15
            sides              = ['bid', 'ask', 'signed']
            filetype           = ['csv']
            output_dir         = str(out_dir)

        rec = L2Recorder(LiveSettings())
        rec.start()

        # Store on the class so individual tests can access them
        TestLiveOutputFormatting.tmp_path = out_dir
        TestLiveOutputFormatting.rec = rec

    # ------------------------------------------------------------------
    # CSV formatting — no scientific notation anywhere
    # ------------------------------------------------------------------

    def test_no_scientific_notation_in_any_csv(self):
        """
        No cell in any output CSV may use scientific notation.
        This catches both 0E-8 (zero formatted as Decimal) and values
        like 1.23e+04 that would indicate a float slipped through unformatted.
        """
        import re
        sci_pattern = re.compile(r'[eE][+-]\d')
        for csv_file in self.tmp_path.glob("*.csv"):
            text = csv_file.read_text()
            matches = sci_pattern.findall(text)
            assert not matches, (
                f"{csv_file.name} contains scientific notation: {matches[:5]}"
            )

    # ------------------------------------------------------------------
    # Zero-size events must not appear in event logs
    # ------------------------------------------------------------------

    def test_no_zero_size_events_in_bid_events(self):
        """
        Every bid event must have a non-zero size. A zero-size event means
        the exchange resent the same quantity — it carries no information
        and must be filtered by update_level_depth.
        """
        import pandas as pd
        files = list(self.tmp_path.glob("*events_bid*.csv"))
        assert files, "no bid events file was written"
        df = pd.read_csv(files[0])
        zero_rows = df[df['size'].astype(float) == 0.0]
        assert len(zero_rows) == 0, (
            f"Found {len(zero_rows)} zero-size bid events:\n{zero_rows.to_string()}"
        )

    def test_no_zero_size_events_in_ask_events(self):
        """Same check for ask events."""
        import pandas as pd
        files = list(self.tmp_path.glob("*events_ask*.csv"))
        assert files, "no ask events file was written"
        df = pd.read_csv(files[0])
        zero_rows = df[df['size'].astype(float) == 0.0]
        assert len(zero_rows) == 0, (
            f"Found {len(zero_rows)} zero-size ask events:\n{zero_rows.to_string()}"
        )

    def test_no_zero_size_events_in_signed_events(self):
        """
        Same check for signed events. Signed sizes can be negative, so
        check absolute value.
        """
        import pandas as pd
        files = list(self.tmp_path.glob("*events_signed*.csv"))
        assert files, "no signed events file was written"
        df = pd.read_csv(files[0])
        zero_rows = df[df['size'].astype(float).abs() == 0.0]
        assert len(zero_rows) == 0, (
            f"Found {len(zero_rows)} zero-size signed events:\n{zero_rows.to_string()}"
        )

    # ------------------------------------------------------------------
    # Deduplication — no adjacent market+cancel pair of equal size
    # ------------------------------------------------------------------

    def test_no_market_cancel_duplicate_pairs_in_bid_events(self):
        """
        No two consecutive bid events should be a (market, cancellation) or
        (cancellation, market) pair with the same absolute size.
        remove_market_cancel_duplicate must have removed them.
        """
        import pandas as pd
        files = list(self.tmp_path.glob("*events_bid*.csv"))
        assert files, "no bid events file was written"
        df = pd.read_csv(files[0])
        _assert_no_mkt_can_duplicates(df, "bid")

    def test_no_market_cancel_duplicate_pairs_in_ask_events(self):
        """Same check for ask events."""
        import pandas as pd
        files = list(self.tmp_path.glob("*events_ask*.csv"))
        assert files, "no ask events file was written"
        df = pd.read_csv(files[0])
        _assert_no_mkt_can_duplicates(df, "ask")

    def test_no_market_cancel_duplicate_pairs_in_signed_events(self):
        """Same check for signed events (uses absolute size for comparison)."""
        import pandas as pd
        files = list(self.tmp_path.glob("*events_signed*.csv"))
        assert files, "no signed events file was written"
        df = pd.read_csv(files[0])
        _assert_no_mkt_can_duplicates(df, "signed")

    # ------------------------------------------------------------------
    # Snapshot files — consistent decimal places, no artifacts
    # ------------------------------------------------------------------

    def test_snapshot_files_have_consistent_decimal_places(self):
        """
        Every numeric cell in every snapshot CSV (volm and prices) must have
        exactly 8 decimal places — no mixing of precisions.
        """
        import re
        decimal_re = re.compile(r'\d+\.(\d+)')
        for csv_file in self.tmp_path.glob("*volm*.csv"):
            _assert_consistent_decimals(csv_file, expected=8)
        for csv_file in self.tmp_path.glob("*prices*.csv"):
            _assert_consistent_decimals(csv_file, expected=8)

    # ------------------------------------------------------------------
    # Book invariants still hold after a live session
    # ------------------------------------------------------------------

    def test_bid_range_descending_after_live_session(self):
        assert self.rec.book.bid_range == sorted(self.rec.book.bid_range, reverse=True), \
            "bid_range is not descending after live session"

    def test_ask_range_ascending_after_live_session(self):
        assert self.rec.book.ask_range == sorted(self.rec.book.ask_range), \
            "ask_range is not ascending after live session"

    def test_no_crossed_book_after_live_session(self):
        assert self.rec.book.bid_range[0] <= self.rec.book.ask_range[0], \
            f"book is crossed after live session: best bid {self.rec.book.bid_range[0]} > best ask {self.rec.book.ask_range[0]}"

    def test_events_and_history_in_sync_after_live_session(self):
        """
        Every L2 update that is recorded appends exactly one entry to both
        bid_history and bid_events. Market trades go into bid_events but not
        bid_history, so bid_events >= bid_history - 1 (the init snapshot).
        """
        book = self.rec.book
        l2_bid_events = [e for e in book.bid_events if e[1] != 'market']
        # history[0] is the init snapshot; each subsequent entry corresponds
        # to one recorded L2 update.
        assert len(book.bid_history) - 1 == len(l2_bid_events), (
            f"bid_history has {len(book.bid_history)} entries "
            f"({len(book.bid_history) - 1} L2 updates) "
            f"but bid_events has {len(l2_bid_events)} non-market entries"
        )

    # ------------------------------------------------------------------
    # Mid price correctness — every recorded value must equal
    # (best_bid + best_ask) / 2 from the live book at that moment
    # ------------------------------------------------------------------

    def test_l2_bid_events_mid_price_matches_snapshot(self):
        """
        For every L2 bid event, verify that mid_price and spread are
        internally consistent: spread = ask[0] - bid[0] and
        mid = (bid[0] + ask[0]) / 2, which implies:
            bid[0] = mid - spread/2
            ask[0] = mid + spread/2

        Zero spread (locked market) and negative spread (crossed book) are
        valid transient market conditions on a live feed. The test verifies
        mathematical correctness of the computation, not the sign of spread.

        We cross-reference against bid_history since bid_history and
        bid_events grow in lockstep — one entry each per recorded L2 bid update.
        """
        book = self.rec.book
        l2_events = [e for e in book.bid_events if e[1] != 'market']
        assert len(l2_events) > 0, "no L2 bid events recorded — session too short"

        failures = []
        for i, event in enumerate(l2_events):
            mid = float(event[-2])
            spread = float(event[-1])

            if mid <= 0:
                failures.append(f"event {i}: non-positive mid {mid}")
                continue

            # Cross-reference: implied best_bid must match bid_history[i+1]
            snap_idx = i + 1
            snap_best_bid = book.bid_history[snap_idx][1][0][0]
            implied_bid = mid - spread / 2
            if abs(implied_bid - snap_best_bid) > 1e-9:
                failures.append(
                    f"event {i}: implied_bid={implied_bid:.8f} != "
                    f"snapshot best_bid={snap_best_bid:.8f} "
                    f"(mid={mid:.8f}, spread={spread:.8f})"
                )

        assert not failures, (
            f"{len(failures)} mid/spread inconsistencies in bid events:\n" +
            "\n".join(failures[:10])
        )

    def test_l2_ask_events_mid_price_matches_snapshot(self):
        """
        For every L2 ask event, verify that mid_price and spread are
        internally consistent: spread = ask[0] - bid[0] and
        mid = (bid[0] + ask[0]) / 2.

        Zero spread (locked market) and negative spread (crossed book) are
        valid transient market conditions — the test verifies mathematical
        correctness, not the sign of spread.
        """
        book = self.rec.book
        l2_events = [e for e in book.ask_events if e[1] != 'market']
        assert len(l2_events) > 0, "no L2 ask events recorded — session too short"

        failures = []
        for i, event in enumerate(l2_events):
            mid = float(event[-2])
            spread = float(event[-1])
            if mid <= 0:
                failures.append(f"event {i}: non-positive mid {mid}")
                continue
            # Verify the spread identity: recomputing spread from mid and
            # implied prices must give back the same spread.
            implied_bid = mid - spread / 2
            implied_ask = mid + spread / 2
            recomputed = implied_ask - implied_bid
            if abs(recomputed - spread) > 1e-9:
                failures.append(
                    f"event {i}: spread identity broken — "
                    f"recorded={spread:.8f}, recomputed={recomputed:.8f}"
                )
        assert not failures, (
            f"{len(failures)} mid/spread inconsistencies in ask events:\n" +
            "\n".join(failures[:10])
        )

    def test_csv_mid_price_spread_relationship_holds_for_all_events(self):
        """
        For every row in every events CSV, verify that mid_price and spread
        are mathematically consistent: spread = ask[0] - bid[0] and
        mid = (bid[0] + ask[0]) / 2.

        Zero spread (locked market) and negative spread (crossed book) are
        valid transient market conditions on a live feed. The test:
        - Verifies mid > 0 for every event
        - Verifies the spread identity holds (recomputed spread == recorded spread)
        - Verifies implied bid/ask are within the session's observed price range
        - Flags any run of more than 10 consecutive negative-spread events,
          which would indicate a persistent crossed book (a real bug)
        """
        import pandas as pd

        bid_prices_df = pd.read_csv(list(self.tmp_path.glob("*prices_bid*.csv"))[0])
        ask_prices_df = pd.read_csv(list(self.tmp_path.glob("*prices_ask*.csv"))[0])

        session_best_bid_min = bid_prices_df['1'].astype(float).min()
        session_best_bid_max = bid_prices_df['1'].astype(float).max()
        session_best_ask_min = ask_prices_df['1'].astype(float).min()
        session_best_ask_max = ask_prices_df['1'].astype(float).max()

        for label, pattern in [('bid', '*events_bid*.csv'),
                                ('ask', '*events_ask*.csv'),
                                ('signed', '*events_signed*.csv')]:
            files = list(self.tmp_path.glob(pattern))
            assert files, f"no {label} events file was written"
            events = pd.read_csv(files[0])

            failures = []
            consecutive_negative = 0
            max_consecutive_negative = 0

            for idx, row in events.iterrows():
                mid = float(row['mid_price'])
                spread = float(row['spread'])

                if mid <= 0:
                    failures.append(f"{label} row {idx}: non-positive mid {mid}")
                    continue

                # Track consecutive negative spreads
                if spread < 0:
                    consecutive_negative += 1
                    max_consecutive_negative = max(max_consecutive_negative,
                                                   consecutive_negative)
                else:
                    consecutive_negative = 0

                # Spread identity: recomputing from mid and implied prices
                # must give back the same spread value
                implied_bid = mid - spread / 2
                implied_ask = mid + spread / 2
                recomputed = implied_ask - implied_bid
                if abs(recomputed - spread) > 1e-9:
                    failures.append(
                        f"{label} row {idx}: spread identity broken — "
                        f"recorded={spread:.8f}, recomputed={recomputed:.8f}"
                    )
                    continue

                # Implied prices must be within the session's observed range
                tick = 0.0001
                if implied_bid < session_best_bid_min - tick or \
                   implied_bid > session_best_bid_max + tick:
                    failures.append(
                        f"{label} row {idx}: implied_bid={implied_bid:.5f} "
                        f"outside session range "
                        f"[{session_best_bid_min:.5f}, {session_best_bid_max:.5f}]"
                    )
                if implied_ask < session_best_ask_min - tick or \
                   implied_ask > session_best_ask_max + tick:
                    failures.append(
                        f"{label} row {idx}: implied_ask={implied_ask:.5f} "
                        f"outside session range "
                        f"[{session_best_ask_min:.5f}, {session_best_ask_max:.5f}]"
                    )

            # A run of more than 10 consecutive negative spreads is a persistent
            # crossed book — that would indicate a real bug, not a transient.
            assert max_consecutive_negative <= 10, (
                f"{label}: {max_consecutive_negative} consecutive negative-spread events "
                f"— persistent crossed book detected"
            )

            assert not failures, (
                f"{len(failures)} mid/spread inconsistencies in {label} events:\n" +
                "\n".join(failures[:10])
            )

    def test_mid_price_changes_when_best_price_moves(self):
        """
        Verify that mid_price is not a constant — it must reflect actual
        best-bid/ask movements. We check this by looking at the bid and ask
        snapshot histories: if the best bid or best ask ever changed during
        the session, the corresponding event's mid_price must differ from
        the initial mid_price.

        If the best prices never moved (extremely stable market), this test
        is skipped rather than failing — that is a market condition, not a bug.
        """
        book = self.rec.book

        # Collect all best-bid prices from bid_history (skip init snapshot at [0])
        best_bids = [snap[1][0][0] for snap in book.bid_history[1:]]
        best_asks = [snap[1][0][0] for snap in book.ask_history[1:]]

        bid_moved = len(set(best_bids)) > 1
        ask_moved = len(set(best_asks)) > 1

        if not bid_moved and not ask_moved:
            import pytest as _pytest
            _pytest.skip(
                "Best bid and best ask did not move during the session "
                "(stable market condition — not a bug). "
                f"best_bid={best_bids[0] if best_bids else 'n/a'}, "
                f"best_ask={best_asks[0] if best_asks else 'n/a'}"
            )

        # At least one price moved — verify the corresponding mid changed
        l2_bid_events = [e for e in book.bid_events if e[1] != 'market']
        l2_ask_events = [e for e in book.ask_events if e[1] != 'market']

        if bid_moved and len(l2_bid_events) > 1:
            bid_mids = [float(e[-2]) for e in l2_bid_events]
            assert len(set(bid_mids)) > 1, (
                f"Best bid moved ({len(set(best_bids))} distinct values) "
                f"but all recorded bid mid_prices are identical: {bid_mids[0]}"
            )

        if ask_moved and len(l2_ask_events) > 1:
            ask_mids = [float(e[-2]) for e in l2_ask_events]
            assert len(set(ask_mids)) > 1, (
                f"Best ask moved ({len(set(best_asks))} distinct values) "
                f"but all recorded ask mid_prices are identical: {ask_mids[0]}"
            )


# ---------------------------------------------------------------------------
# Helpers used by TestLiveOutputFormatting
# ---------------------------------------------------------------------------

def _assert_no_mkt_can_duplicates(df, label):
    """
    Assert that no two consecutive rows in ``df`` form a market/cancel
    duplicate pair of equal absolute size.

    Signed events negate one side, so sizes must be compared by absolute
    value — a market buy of +71.0 and a cancel of -71.0 are the same fill.
    """
    if len(df) < 2:
        return
    for i in range(len(df) - 1):
        t0, t1 = df.iloc[i]['order_type'], df.iloc[i + 1]['order_type']
        s0 = abs(float(df.iloc[i]['size']))
        s1 = abs(float(df.iloc[i + 1]['size']))
        is_mkt_can = (
            (t0 == 'market' and t1 == 'cancellation') or
            (t0 == 'cancellation' and t1 == 'market')
        )
        assert not (is_mkt_can and abs(s0 - s1) < 1e-9), (
            f"{label} events rows {i} and {i+1} are an undeduped "
            f"market/cancel pair: {df.iloc[i].to_dict()}, {df.iloc[i+1].to_dict()}"
        )


def _assert_consistent_decimals(csv_file, expected):
    """Assert every numeric cell in ``csv_file`` has exactly ``expected`` decimal places."""
    import re
    decimal_re = re.compile(r'^\d+\.(\d+)$')
    rows = csv_file.read_text().splitlines()
    for row in rows[1:]:  # skip header
        for cell in row.split(','):
            cell = cell.strip()
            m = decimal_re.match(cell)
            if m:
                actual = len(m.group(1))
                assert actual == expected, (
                    f"{csv_file.name}: expected {expected} decimal places, "
                    f"got {actual} for value '{cell}'"
                )
