# Order Book Sub-Architecture

This document describes how the three parallel order book representations
inside `LimitOrderBook` are constructed, maintained, and recorded. The three
representations — bid-side, ask-side, and signed — operate largely
independently of each other. They share the same underlying snapshot state
but produce separate event logs, separate snapshot histories, and use
different position conventions.

---

## The Three Representations

```
                    ┌─────────────────────────────────────────┐
                    │           LimitOrderBook                │
                    │                                         │
  snapshot_bid ─────┤──► bid_history   bid_events            │
  snapshot_ask ─────┤──► ask_history   ask_events            │
                    │──► signed_history signed_events         │
                    └─────────────────────────────────────────┘
```

All three read from the same two live snapshots (`snapshot_bid`,
`snapshot_ask`). But each representation has its own history list, its own
event log, its own position convention, and its own sign convention for size.

---

## 1. The Live Snapshots

`snapshot_bid` and `snapshot_ask` are the single source of truth for the
current state of the order book. Everything else is derived from them.

```
snapshot_bid = [ [price, volume], [price, volume], ... ]   # descending price
snapshot_ask = [ [price, volume], [price, volume], ... ]   # ascending price
```

Both are plain Python lists of `[price, volume]` pairs. They are mutated
in-place on every L2 update. The index into the list is the **snapshot
index** — 0 is always the best price (best bid or best ask).

`bid_range` and `ask_range` are read-only properties that extract just the
price column. They are never stored separately; the snapshot is always the
source of truth.

### Initialisation

On the first `snapshot` message from Coinbase, `initialise_from_snapshot`
populates both snapshots from the wire data (up to 3800 levels each) and
appends the initial state to all three history lists. The `min_dec` value
(volume rounding precision) is computed once here from the best bid price
and used for all volume rounding throughout the session.

---

## 2. The Bid-Side Representation

### Snapshot history

`bid_history` is a time series of snapshots. Each entry is
`[timestamp, snapshot_copy]` where `snapshot_copy` is a deep copy of
`snapshot_bid[:depth_limit]` at the moment the event was recorded.

```
bid_history[0]  = [session_start, initial_snapshot]   # init state
bid_history[1]  = [t1, snapshot_after_first_update]
bid_history[2]  = [t2, snapshot_after_second_update]
...
```

The init row is always present. `filesave` drops it when writing to disk
(the `drop_init_row=True` flag) so the output file starts from the first
real event.

### Event log

`bid_events` records every L2 change on the bid side that falls within
`depth_limit`. Each entry is:

```
[timestamp, order_type, price, size, position, mid_price, spread]
```

Market orders that hit the bid side are also appended here (from
`_handle_market_trades`), with the same column structure.

### Position convention

The `position` column in `bid_events` is the **snapshot index + 1**:

```
snapshot_index 0  →  position 1   (best bid)
snapshot_index 1  →  position 2
snapshot_index 2  →  position 3
...
```

Market orders on the bid side use position `-1` (hardcoded in
`_handle_market_trades`). This is a sentinel that distinguishes market
fills from L2 limit order events in the same log.

### Size convention

Size is always **positive** in `bid_events`, regardless of event type.
It represents the absolute change in volume at that price level.

---

## 3. The Ask-Side Representation

Structurally identical to the bid side, with two differences.

### Position convention

The `position` column in `ask_events` is the **snapshot index + 1**,
identical to the bid side:

```
snapshot_index 0  →  position 1   (best ask)
snapshot_index 1  →  position 2
snapshot_index 2  →  position 3
...
```

Market orders on the ask side use position `+1` (hardcoded in
`_handle_market_trades`). This is the sentinel for ask-side fills.

Both sides now use the same 1-based depth index. Position 1 means best
price on whichever side the event belongs to. The `order_type` and the
file name (`events_bid` vs `events_ask`) are what distinguish the two logs,
not the position value.

### Size convention

Size is always **positive** in `ask_events`, same as bid.

---

## 4. The Signed Representation

The signed book is the unified cross-side view. It follows the order flow
convention from Cont, Kukanov and Stoikov (2011): bid-side activity is
negative, ask-side activity is positive.

### Snapshot history

`signed_history` stores a combined snapshot at each event. Each entry is
`[timestamp, signed_snapshot]` where `signed_snapshot` is:

```
[ bid levels reversed, negated ]  +  [ ask levels ]
```

Specifically, `append_signed_book` builds it as:

```python
snap_bid = [[p, -v] for p, v in snapshot_bid[:(depth_limit-1)]][::-1]
snap_ask = snapshot_ask[:(depth_limit-1)]
signed_snapshot = snap_bid + snap_ask
```

The bid side is negated (volumes become negative) and reversed so that
the deepest bid is at index 0 and the best bid is adjacent to the best ask
in the middle of the list. The ask side follows in ascending order.

Note: `depth_limit - 1` levels are taken from each side (not `depth_limit`),
so a `position_range=5` session produces 4 bid levels + 4 ask levels = 8
levels per signed snapshot.

### Event log

`signed_events` records every L2 change on either side, plus all market
orders. Each entry is:

```
[timestamp, order_type, price, size, position, side, mid_price, spread]
```

The extra `side` column (`'bid'` or `'ask'`) is what distinguishes this
from the single-sided logs.

### Position convention

Signed positions are computed by `compute_signed_position`:

```
bid side:  -(snapshot_index + 1)   →  -1, -2, -3 ...  (best bid = -1)
ask side:  +(snapshot_index + 1)   →  +1, +2, +3 ...  (best ask = +1)
```

Position 0 is skipped. The signed position space is:

```
... -3, -2, -1 | +1, +2, +3 ...
     ← bid      |  ask →
```

Market orders use `-1` (bid hit) or `+1` (ask hit) — the same sentinels
as the signed L2 positions for the best price levels. In the signed log,
a market order and a best-level L2 event share the same position value,
which is why `remove_market_cancel_duplicate` is needed to deduplicate
fill confirmations.

### Size convention

Size is **signed** in `signed_events`:

```
ask insertion    → positive size   (liquidity added on ask)
ask cancellation → negative size   (liquidity removed on ask)
ask market order → negative size   (liquidity consumed on ask)
bid insertion    → negative size   (liquidity added on bid, sign flipped)
bid cancellation → positive size   (liquidity removed on bid, sign flipped)
bid market order → positive size   (liquidity consumed on bid, sign flipped)
```

The sign is computed by `compute_sign(side, order_type)`. The convention
encodes order flow direction: positive = buy pressure, negative = sell
pressure.

---

## 5. How the Three Representations Diverge

The same L2 update triggers writes to all three representations, but each
write is independent:

```
apply_update(side='bid', ...)
    → append_snapshot_bid()    writes to bid_history, bid_events
    → append_signed_book()     writes to signed_history, signed_events
    (no write to ask_history or ask_events)

apply_update(side='ask', ...)
    → append_snapshot_ask()    writes to ask_history, ask_events
    → append_signed_book()     writes to signed_history, signed_events
    (no write to bid_history or bid_events)

_handle_market_trades(trade)
    → add_market_order()       writes to signed_events
    → add_market_order()       writes to bid_events OR ask_events (not both)
    (no write to bid_history or ask_history or signed_history)
```

Market orders never touch the snapshot histories. They only appear in the
event logs. This is why `bid_history` and `bid_events` grow in lockstep
for L2 events, but `bid_events` can have more entries than
`bid_history - 1` when market orders are present.

---

## 6. Position Convention Summary

| Log | Event type | Position value | Meaning |
|---|---|---|---|
| `bid_events` | L2 insertion / cancellation | `snapshot_index + 1` | depth from best bid, 1-based |
| `bid_events` | market order | `-1` | sentinel: fill hit the bid |
| `ask_events` | L2 insertion / cancellation | `snapshot_index + 1` | depth from best ask, 1-based |
| `ask_events` | market order | `+1` | sentinel: fill hit the ask |
| `signed_events` | bid L2 | `-(snapshot_index + 1)` | negative = bid side |
| `signed_events` | ask L2 | `+(snapshot_index + 1)` | positive = ask side |
| `signed_events` | market bid hit | `-1` | same as best bid L2 position |
| `signed_events` | market ask hit | `+1` | same as best ask L2 position |

---

## 7. Deduplication

When a market order fills at the best price, Coinbase sends two messages
nearly simultaneously:

1. A `market_trades` event with the fill size
2. An `l2_data` update removing the same volume from the best level
   (the exchange's confirmation of the fill)

Without deduplication, both would be recorded as separate events.
`remove_market_cancel_duplicate` checks the last two entries in an event
log after each append. If they form a `(market, cancellation)` or
`(cancellation, market)` pair with matching absolute sizes, the
cancellation is removed. This runs on `bid_events`, `ask_events`, and
`signed_events` independently after every relevant append.

---

## 8. Output Files

Each representation produces its own set of output files:

| Files | Source |
|---|---|
| `L2_orderbook_volm_bid`, `L2_orderbook_prices_bid` | `bid_history` |
| `L2_orderbook_events_bid` | `bid_events` |
| `L2_orderbook_volm_ask`, `L2_orderbook_prices_ask` | `ask_history` |
| `L2_orderbook_events_ask` | `ask_events` |
| `L2_orderbook_volm_signed`, `L2_orderbook_prices_signed` | `signed_history` |
| `L2_orderbook_events_signed` | `signed_events` |

Snapshot files drop the init row (index 0) on export. Event files do not
have an init row to drop.
