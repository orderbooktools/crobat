import copy
import bisect
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from crobat import orderbook_helpers as obh


@dataclass
class _UpdateResult:
    """
    Carries the outcome of a single snapshot mutation sequence.

    Passed forward through :func:`apply_update` so each step receives
    explicit inputs rather than reading back side effects from shared
    instance state.

    Attributes
    ----------
    recorded : bool
        ``True`` when a recordable change was found and is within depth.
    position : int
        0-based snapshot index where the change occurred.
    event_size : float
        Absolute size of the change.
    order_type : Optional[str]
        ``'insertion'``, ``'cancellation'``, or ``None`` if no change.
    """
    recorded: bool = False
    position: int = 0
    event_size: float = 0.0
    order_type: Optional[str] = None


class LimitOrderBook:
    """
    Maintains the state and full history of a Level 2 limit order book.

    Attributes
    ----------
    bid_history : list of list
        Time series of bid-side snapshots. Each entry is ``[datetime, snapshot]``.
    ask_history : list of list
        Time series of ask-side snapshots. Each entry is ``[datetime, snapshot]``.
    signed_history : list of list
        Time series of signed order book snapshots (bids negative, asks positive).
    snapshot_bid : list of list
        Current bid-side snapshot as ``[[price, volume], ...]`` best-to-worst.
    snapshot_ask : list of list
        Current ask-side snapshot as ``[[price, volume], ...]`` best-to-worst.
    bid_events : list of list
        Log of recorded bid-side order book changes.
    ask_events : list of list
        Log of recorded ask-side order book changes.
    signed_events : list of list
        Log of recorded signed order book changes.
    order_type : str or None
        Type of the most recent event: ``'insertion'``, ``'cancellation'``,
        or ``'market'``. Written by :func:`apply_update` after each L2 update.
    token : bool
        ``True`` if the most recent update was recorded (within depth limit).
        Written by :func:`apply_update`.
    position : int
        0-based snapshot index of the most recent change. Written by
        :func:`apply_update`.
    event_size : float
        Absolute size of the most recent order book change. Written by
        :func:`apply_update`.most recent order book change.
    min_dec : int
        Number of decimal places used to round volumes. Set by
        :meth:`initialise_from_snapshot`.

    Notes
    -----
    ``bid_range`` and ``ask_range`` are read-only properties derived from the
    price column of ``snapshot_bid`` and ``snapshot_ask`` respectively. They
    are never stored separately — the snapshot is always the source of truth.
    """

    def __init__(self):
        self.bid_history = []
        self.ask_history = []
        self.signed_history = []
        self.snapshot_bid = []
        self.snapshot_ask = []
        self.bid_events = []
        self.ask_events = []
        self.signed_events = []
        self.order_type = None
        self.token = False
        self.position = 0
        self.event_size = 0

    # ------------------------------------------------------------------
    # Derived price ranges — always in sync with the snapshot
    # ------------------------------------------------------------------

    @property
    def bid_range(self):
        """Prices of the current bid-side snapshot, best-to-worst (descending)."""
        return [row[0] for row in self.snapshot_bid]

    @property
    def ask_range(self):
        """Prices of the current ask-side snapshot, best-to-worst (ascending)."""
        return [row[0] for row in self.snapshot_ask]

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialise_from_snapshot(self, msg, timestamp):
        """
        Initialise the order book from a Level 2 snapshot message.

        Populates ``snapshot_bid``, ``snapshot_ask``, and ``min_dec`` from
        the snapshot data. Appends the initial state to ``bid_history``,
        ``ask_history``, and ``signed_history``.

        Called once per session by
        :meth:`crobat.recorder.L2Recorder._handle_l2_data` when the first
        ``snapshot`` event arrives.

        Parameters
        ----------
        msg : dict
            Snapshot dict with keys ``'bids'`` and ``'asks'``, each a list
            of ``[price_str, quantity_str]`` pairs ordered from best to worst.
        timestamp : datetime
            UTC timestamp at session start, used as the first history entry.
        """
        bid_prices = [float(row[0]) for row in msg['bids'][:3800]]
        ask_prices = [float(row[0]) for row in msg['asks'][:3800]]
        self.min_dec = obh.compute_min_decimals(0.01, bid_prices[0])
        bid_volumes = np.round([float(row[1]) for row in msg['bids'][:3800]], decimals=self.min_dec)
        ask_volumes = np.round([float(row[1]) for row in msg['asks'][:3800]], decimals=self.min_dec)
        self.snapshot_bid = [[bid_prices[i], bid_volumes[i]] for i in range(len(bid_prices))]
        self.snapshot_ask = [[ask_prices[i], ask_volumes[i]] for i in range(len(ask_prices))]
        # Signed book init snapshot: bids negated and reversed, then asks appended
        signed_init = [[p, -v] for p, v in self.snapshot_bid][::-1] + self.snapshot_ask
        self.bid_history.append([timestamp, self.snapshot_bid])
        self.ask_history.append([timestamp, self.snapshot_ask])
        self.signed_history.append([timestamp, signed_init])

    # ------------------------------------------------------------------
    # Market order aggregation
    # ------------------------------------------------------------------

    def add_market_order(self, event, event_log):
        """
        Append a market order event to ``event_log``, aggregating consecutive
        events at the same timestamp into a single entry.

        If aggregation produces a net size of zero — which happens when a buy
        and sell of equal size arrive at the same timestamp — the combined
        entry is removed entirely. A zero-size market event carries no
        information about order flow direction.

        Parameters
        ----------
        event : list
            The new market order event to append.
        event_log : list of list
            The event log to append to (e.g. ``signed_events``).

        Returns
        -------
        list of list
            Updated event log.
        """
        event_log.append(event)
        # Only attempt aggregation when there are at least two entries to compare.
        if len(event_log) < 2:
            return event_log
        i = len(event_log) - 1
        if event_log[i][0] == event_log[i - 1][0]:
            event_log[i][3] += event_log[i - 1][3]
            del event_log[i - 1]
            # Net size of zero means equal and opposite fills at the same
            # timestamp — drop the combined entry, it carries no directional info.
            if event_log[-1][3] == 0:
                del event_log[-1]
        return event_log

    # ------------------------------------------------------------------
    # Snapshot mutation methods
    # ------------------------------------------------------------------

    def remove_price_level(self, snapshot, level_depth, match_index, result):
        """
        Remove a price level from ``snapshot`` when its depth reaches zero.

        Always runs after :meth:`update_level_depth`. If the level was found
        and its new depth is zero, it is deleted and ``result.recorded`` is
        set to ``True`` with the removal position.

        Parameters
        ----------
        snapshot : list of list
        level_depth : float
        match_index : int or None
        result : _UpdateResult
            Result from :meth:`update_level_depth`. Returned unchanged if
            ``level_depth != 0`` or ``match_index is None``.

        Returns
        -------
        list of list
            Updated snapshot.
        _UpdateResult
            Updated result.
        """
        if level_depth == 0 and match_index is not None:
            del snapshot[match_index]
            result = _UpdateResult(
                recorded=True,
                position=match_index,
                event_size=result.event_size,
                order_type=result.order_type,
            )
        return snapshot, result

    def update_level_depth(self, snapshot, level_depth, match_index):
        """
        Update the volume of an existing price level in ``snapshot``.

        Parameters
        ----------
        snapshot : list of list
            The snapshot being edited.
        level_depth : float
            New quantity from the message.
        match_index : int or None
            Index of the matched price level, or ``None`` if not found.

        Returns
        -------
        list of list
            Updated snapshot.
        _UpdateResult
            Carries ``recorded``, ``position``, ``event_size``,
            ``order_type``. ``recorded`` is ``False`` when the price was not
            found or the quantity was unchanged.
        """
        result = _UpdateResult()
        if match_index is not None:
            event_size = abs(snapshot[match_index][1] - level_depth)
            if snapshot[match_index][1] < level_depth:
                order_type = 'insertion'
            elif snapshot[match_index][1] > level_depth:
                order_type = 'cancellation'
            else:
                order_type = None
            snapshot[match_index][1] = level_depth
            # Zero event_size means the exchange resent the same quantity —
            # no actual change. Leave recorded=False so it is not appended.
            if event_size > 0:
                result = _UpdateResult(
                    recorded=True,
                    position=match_index,
                    event_size=event_size,
                    order_type=order_type,
                )
        return snapshot, result

    def _insert_price_level(self, snapshot, level_depth, price_level, descending, prev_result):
        """
        Insert a new price level into ``snapshot`` when the price was not
        found by :meth:`update_level_depth` (``prev_result.recorded`` is
        ``False``).

        Parameters
        ----------
        snapshot : list of list
            The snapshot being edited (bid or ask side), mutated in place.
        level_depth : float
            New quantity from the message.
        price_level : float
            Price of the new level.
        descending : bool
            ``True`` for the bid side (prices high-to-low);
            ``False`` for the ask side (prices low-to-high).
        prev_result : _UpdateResult
            Result from the preceding mutation step. Returned unchanged if
            ``prev_result.recorded`` is already ``True``.

        Returns
        -------
        list of list
            Updated snapshot.
        _UpdateResult
            Updated result.
        """
        if prev_result.recorded:
            return snapshot, prev_result

        order_type = 'cancellation' if level_depth == 0 else prev_result.order_type
        event_size = level_depth
        result = _UpdateResult(order_type=order_type, event_size=event_size)

        if descending:
            best, worst = snapshot[0][0], snapshot[-1][0]
            if price_level > best:
                snapshot.insert(0, [price_level, level_depth])
                result = _UpdateResult(recorded=True, position=0,
                                       event_size=event_size, order_type='insertion')
            elif price_level < worst:
                pass  # out of range — recorded stays False
            else:
                neg_prices = [-row[0] for row in snapshot]
                pos = bisect.bisect_left(neg_prices, -price_level)
                if 0 < pos < len(snapshot):
                    snapshot.insert(pos, [price_level, level_depth])
                    result = _UpdateResult(recorded=True, position=pos,
                                          event_size=event_size, order_type='insertion')
        else:
            best, worst = snapshot[0][0], snapshot[-1][0]
            if price_level < best:
                snapshot.insert(0, [price_level, level_depth])
                result = _UpdateResult(recorded=True, position=0,
                                       event_size=event_size, order_type='insertion')
            elif price_level > worst:
                pass  # out of range — recorded stays False
            else:
                pos = bisect.bisect_left([row[0] for row in snapshot], price_level)
                if pos > 0:
                    snapshot.insert(pos, [price_level, level_depth])
                    result = _UpdateResult(recorded=True, position=pos,
                                          event_size=event_size, order_type='insertion')

        return snapshot, result

    # ------------------------------------------------------------------
    # Derived values
    # ------------------------------------------------------------------

    @property
    def mid_price(self):
        """Best-bid/best-ask midpoint."""
        return 0.5 * (self.snapshot_bid[0][0] + self.snapshot_ask[0][0])

    @property
    def spread(self):
        """Best-ask minus best-bid."""
        return self.snapshot_ask[0][0] - self.snapshot_bid[0][0]

    # ------------------------------------------------------------------
    # Recording gate
    # ------------------------------------------------------------------

    def trim_coordinator(self, position, depth_limit):
        """
        Return ``True`` if ``position`` is within ``depth_limit`` levels of
        the best price, ``False`` otherwise.

        Parameters
        ----------
        position : int
            Index where the change occurred.
        depth_limit : int
            Maximum recordable depth from the best price.

        Returns
        -------
        bool
        """
        return abs(position) <= depth_limit

    # ------------------------------------------------------------------
    # History append methods
    # ------------------------------------------------------------------

    def append_snapshot_bid(self, timestamp, price_level, depth_limit, result):
        """
        Append the current bid snapshot and event to history.

        Parameters
        ----------
        timestamp : datetime
        price_level : float
        depth_limit : int
        result : _UpdateResult
            Carries ``position``, ``event_size``, ``order_type`` for the event.
        """
        snapshot_copy = copy.deepcopy(self.snapshot_bid[:depth_limit])
        self.bid_history.append([timestamp, snapshot_copy])
        self.bid_events.append([
            timestamp, result.order_type, price_level, result.event_size,
            result.position + 1, self.mid_price, self.spread,
        ])

    def append_snapshot_ask(self, timestamp, price_level, depth_limit, result):
        """
        Append the current ask snapshot and event to history.

        Parameters
        ----------
        timestamp : datetime
        price_level : float
        depth_limit : int
        result : _UpdateResult
            Carries ``position``, ``event_size``, ``order_type`` for the event.
        """
        snapshot_copy = copy.deepcopy(self.snapshot_ask[:depth_limit])
        self.ask_history.append([timestamp, snapshot_copy])
        self.ask_events.append([
            timestamp, result.order_type, price_level, result.event_size,
            result.position + 1, self.mid_price, self.spread,
        ])

    def append_signed_book(self, timestamp, price_level, side, depth_limit, result):
        """
        Append the current signed snapshot and event to history.

        Parameters
        ----------
        timestamp : datetime
        price_level : float
        side : str
            ``'bid'`` or ``'ask'``
        depth_limit : int
        result : _UpdateResult
            Carries ``position``, ``event_size``, ``order_type`` for the event.
        """
        sign = obh.compute_sign(side, result.order_type)
        signed_size = result.event_size * sign
        signed_position = obh.compute_signed_position(result.position, side)
        snap_bid = [[p, -v] for p, v in copy.deepcopy(self.snapshot_bid[:(depth_limit - 1)])][::-1]
        snap_ask = copy.deepcopy(self.snapshot_ask[:(depth_limit - 1)])
        self.signed_history.append([timestamp, snap_bid + snap_ask])
        self.signed_events.append([
            timestamp, result.order_type, price_level, signed_size,
            signed_position, side, self.mid_price, self.spread,
        ])

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def remove_market_cancel_duplicate(self, event_log, order_type):
        """
        Remove a duplicate event when a market order and a cancellation of the
        same size arrive back-to-back (the cancellation is the exchange's
        confirmation of the fill, not a separate order).

        Checks the last two events in ``event_log``. If their sizes match and
        the pair is a ``(market, cancellation)`` or ``(cancellation, market)``
        sequence, the redundant entry is deleted in-place.

        Parameters
        ----------
        event_log : list of list
            The event log to check (e.g. ``bid_events``).
        order_type : str
            The type of the event that just triggered this check.
        """
        if len(event_log) <= 2:
            return
        last_two = event_log[-2:]
        types = [last_two[0][1], last_two[1][1]]
        sizes = [last_two[0][3], last_two[1][3]]
        # Compare absolute sizes: signed events negate one side, so a raw
        # subtraction would give 2x the size instead of zero.
        if abs(abs(sizes[0]) - abs(sizes[1])) < 1e-9:
            if order_type == 'market':
                del event_log[-2]
            elif order_type == 'cancellation' and types[0] == 'market':
                del event_log[-1]

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def last_inserted_order(self, side='signed'):
        """
        Return the most recent insertion event within the last 30 events.

        Returns ``None`` if no insertion is found.
        """
        return self._last_event_of_type('insertion', side)

    def last_canceled_order(self, side='signed'):
        """
        Return the most recent cancellation event within the last 30 events.

        Returns ``None`` if no cancellation is found.
        """
        return self._last_event_of_type('cancellation', side)

    def last_market_order(self, side='signed'):
        """
        Return the most recent market order event within the last 30 events.

        Returns ``None`` if no market order is found.
        """
        return self._last_event_of_type('market', side)

    def _last_event_of_type(self, event_type, side):
        """
        Shared implementation for the last_*_order accessors.

        Returns the matching event list, or ``None`` if not found within the
        last 30 events.
        """
        if side == 'buy':
            event_log = self.bid_events
        elif side == 'sell':
            event_log = self.ask_events
        else:
            event_log = self.signed_events

        for event in reversed(event_log[-30:]):
            if event[1] == event_type:
                return event
        return None

    def latest_snapshot(self, side='signed'):
        """
        Return the most recent order book snapshot.

        Parameters
        ----------
        side : str
            ``'buy'``, ``'sell'``, or ``'signed'``. Default ``'signed'``.

        Returns
        -------
        list
            ``[datetime, snapshot]``
        """
        if side == 'buy':
            return self.bid_history[-1]
        elif side == 'sell':
            return self.ask_history[-1]
        return self.signed_history[-1]

    def last_market_depth(self, side, depth_limit='all'):
        """
        Compute the total notional depth (price × volume) of the order book.

        Parameters
        ----------
        side : str
            ``'buy'`` or ``'sell'``.
        depth_limit : int or ``'all'``, optional
            Number of levels to include. Default is all levels.

        Returns
        -------
        float
            Total notional depth.

        Raises
        ------
        ValueError
            If ``side`` is not ``'buy'`` or ``'sell'``.
        """
        if side == 'buy':
            snapshot = self.bid_history[-1][1]
        elif side == 'sell':
            snapshot = self.ask_history[-1][1]
        else:
            raise ValueError(f"last_market_depth: side must be 'buy' or 'sell', got {side!r}")
        if depth_limit != 'all':
            snapshot = snapshot[:depth_limit]
        return sum(price * volume for price, volume in snapshot)


# ---------------------------------------------------------------------------
# Module-level update sequence
# ---------------------------------------------------------------------------

def apply_update(book, timestamp, side, price_level, level_depth, match_index, depth_limit):
    """
    Apply a single L2 update to ``book`` for either the bid or ask side.

    Runs the full mutation sequence with explicit data flow — each step
    receives the result of the previous one rather than reading back from
    shared instance state:

    1. Update volume of an existing level (:meth:`~LimitOrderBook.update_level_depth`)
    2. Remove the level if volume is zero (:meth:`~LimitOrderBook.remove_price_level`)
    3. Insert a new level if the price was not found
       (:meth:`~LimitOrderBook._insert_price_level`)
    4. Gate recording by depth (:meth:`~LimitOrderBook.trim_coordinator`)
    5. Append to history and check for market/cancel duplicates if within depth.

    The ``token``, ``position``, ``event_size``, and ``order_type`` attributes
    on ``book`` are written once at the end from the final result, so the
    public accessors (``last_inserted_order`` etc.) always reflect the most
    recent update.

    Parameters
    ----------
    book : LimitOrderBook
    timestamp : datetime
    side : str
        ``'bid'`` or ``'ask'``
    price_level : float
    level_depth : float
    match_index : int or None
        Index of the matched price level in the snapshot, or ``None``.
    depth_limit : int
    """
    if side == 'bid':
        book.snapshot_bid, result = book.update_level_depth(book.snapshot_bid, level_depth, match_index)
        book.snapshot_bid, result = book.remove_price_level(book.snapshot_bid, level_depth, match_index, result)
        book.snapshot_bid, result = book._insert_price_level(book.snapshot_bid, level_depth, price_level, descending=True, prev_result=result)
        within_depth = result.recorded and book.trim_coordinator(result.position, depth_limit)
        if within_depth:
            book.append_snapshot_bid(timestamp, price_level, depth_limit, result)
            book.append_signed_book(timestamp, price_level, side, depth_limit, result)
            book.remove_market_cancel_duplicate(book.bid_events, result.order_type)
            book.remove_market_cancel_duplicate(book.signed_events, result.order_type)
    else:
        book.snapshot_ask, result = book.update_level_depth(book.snapshot_ask, level_depth, match_index)
        book.snapshot_ask, result = book.remove_price_level(book.snapshot_ask, level_depth, match_index, result)
        book.snapshot_ask, result = book._insert_price_level(book.snapshot_ask, level_depth, price_level, descending=False, prev_result=result)
        within_depth = result.recorded and book.trim_coordinator(result.position, depth_limit)
        if within_depth:
            book.append_snapshot_ask(timestamp, price_level, depth_limit, result)
            book.append_signed_book(timestamp, price_level, side, depth_limit, result)
            book.remove_market_cancel_duplicate(book.ask_events, result.order_type)
            book.remove_market_cancel_duplicate(book.signed_events, result.order_type)

    # Write back to book attributes so public accessors reflect the last update.
    book.token = within_depth if result.recorded else False
    book.position = result.position
    book.event_size = result.event_size
    book.order_type = result.order_type


# Keep the old names as thin aliases so any external code that imported them
# directly continues to work without modification. The ``side`` parameter
# these aliases previously accepted is dropped — it was always ignored.
def apply_bid_update(book, timestamp, price_level, level_depth, match_index, depth_limit):
    """Alias for :func:`apply_update` with ``side='bid'``."""
    apply_update(book, timestamp, 'bid', price_level, level_depth, match_index, depth_limit)


def apply_ask_update(book, timestamp, price_level, level_depth, match_index, depth_limit):
    """Alias for :func:`apply_update` with ``side='ask'``."""
    apply_update(book, timestamp, 'ask', price_level, level_depth, match_index, depth_limit)


def price_match(x, y):
    """Return ``True`` if two prices are equal."""
    return x == y


if __name__ == '__main__':
    pass
