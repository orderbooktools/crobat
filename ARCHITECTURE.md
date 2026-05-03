# crobat — Architecture & Developer Guide

**crobat** is a Python library that connects to the Coinbase Advanced Trade
WebSocket feed, reconstructs a live Level 2 order book, records limit order
insertions, cancellations, and market orders, and exports the results to
CSV, PKL, or XLSX files.

---

## High-Level System Overview

```mermaid
graph TD
    CB[Coinbase Advanced Trade WebSocket API]
    CB -->|l2_data snapshot + updates| REC[recorder.py — L2Recorder]
    CB -->|market_trades| REC
    CB -->|ticker| REC
    REC -->|initializes| BOOK[orderbook.py — LimitOrderBook]
    REC -->|calls apply_update| BOOK
    BOOK -->|mutates snapshots + appends history| BOOK
    REC -->|on_close| FS[filesave.py — export_session]
    FS -->|writes| OUT["runs/ — CSV / PKL / XLSX"]
    CLI[CLI/crobat_cli.py] -->|launches| REC
```

---

## Module Breakdown

### `crobat/` — Core Library

| File | Responsibility |
|---|---|
| `recorder.py` | `L2Recorder` — WebSocket client. Subscribes to `level2`, `market_trades`, and `ticker` channels. Routes messages to handlers, drives the order book update loop, triggers file export on close. Also defines `SnapshotTimeoutError`. |
| `orderbook.py` | `LimitOrderBook` class — all live order book state and history. Also contains the module-level `apply_update` orchestration function and `price_match`. Backward-compatible aliases `apply_bid_update` / `apply_ask_update` are kept for external callers. |
| `orderbook_helpers.py` | Pure utility functions: `compute_sign`, `compute_signed_position`, `compute_min_decimals`. No state, no side effects. |
| `filesave.py` | Converts `LimitOrderBook` history arrays to DataFrames and writes output files. Called automatically by `L2Recorder.on_close` via `export_session`. |
| `config.py` | Loads Coinbase credentials from `cdp_api_key.json` and recording defaults from `config.ini`. |

### `CLI/` — Command Line Interface

`crobat_cli.py` uses `argparse` to accept recording parameters as flags or
prompt for them interactively, then launches a session. No external
dependencies beyond the crobat package itself.

---

## Message Processing Flow

```mermaid
sequenceDiagram
    participant WS as Coinbase WS
    participant REC as L2Recorder
    participant BOOK as LimitOrderBook
    participant FS as filesave

    WS->>REC: l2_data (snapshot)
    REC->>BOOK: initialise_from_snapshot()
    Note over BOOK: Populates snapshot_bid / snapshot_ask,<br/>bid_range / ask_range, min_dec.<br/>snapshot_received = True

    WS->>REC: ticker
    Note over REC: No-op — mid/spread come from<br/>live L2 book, not ticker cache

    WS->>REC: market_trades
    REC->>BOOK: add_market_order()
    REC->>BOOK: remove_market_cancel_duplicate()

    WS->>REC: l2_data (update)
    REC->>BOOK: apply_update(side, ...)
    Note over BOOK: update_level_depth → remove_price_level<br/>→ _insert_price_level → trim_coordinator<br/>→ append_snapshot_bid/ask<br/>→ append_signed_book<br/>→ remove_market_cancel_duplicate

    Note over REC: recording_duration elapsed
    REC->>FS: export_session(book, position_range, sides, filetype, output_dir)
    FS-->>REC: files written to runs/
```

---

## Snapshot Timeout and Retry Logic

`L2Recorder.start()` polls `snapshot_received` after subscribing. If the
snapshot is not received within `snap_timeout` seconds, the connection is
closed and reopened after `retry_backoff` seconds. At most `1 + max_retries`
total connections are opened.

```mermaid
flowchart TD
    A[ws.open + subscribe] --> B{snapshot_received\nwithin snap_timeout?}
    B -->|Yes| C[start recording timer]
    B -->|No| D{attempts\nexhausted?}
    D -->|No| E[close ws\nwait retry_backoff\nrebuild WSClient]
    E --> A
    D -->|Yes| F[raise SnapshotTimeoutError]
    C --> G[sleep recording_duration]
    G --> H[ws.close → on_close → export_session]
```

---

## Order Book Update Sequence

Each L2 update runs through a fixed four-step mutation sequence with
explicit data flow — each step receives the `_UpdateResult` from the
previous one rather than reading back from shared state.

```mermaid
flowchart TD
    A[l2_data update received] --> B{side?}
    B -->|bid| C[find match_index in bid_range]
    B -->|offer → ask| D[find match_index in ask_range]

    C --> E[apply_update]
    D --> E

    E --> F[update_level_depth\nmodify existing level volume]
    F --> G[remove_price_level\nif new_quantity == 0]
    G --> H[_insert_price_level\ninsert new level if price not found]
    H --> I{trim_coordinator\nabs position within depth_limit?}

    I -->|No| K[discard — not recorded]
    I -->|Yes| L[append_snapshot_bid or append_snapshot_ask]
    L --> M[append_signed_book]
    M --> N[remove_market_cancel_duplicate]
```

---

## `LimitOrderBook` State

```mermaid
classDiagram
    class LimitOrderBook {
        +list bid_history
        +list ask_history
        +list signed_history
        +list snapshot_bid
        +list snapshot_ask
        +list bid_events
        +list ask_events
        +list signed_events
        +str order_type
        +bool token
        +int position
        +float event_size
        +int min_dec

        +bid_range : property
        +ask_range : property
        +mid_price : property
        +spread : property

        +initialise_from_snapshot(msg, timestamp)
        +update_level_depth(snapshot, depth, match_index)
        +remove_price_level(snapshot, depth, match_index, result)
        +_insert_price_level(snapshot, depth, price, descending, prev_result)
        +trim_coordinator(position, depth_limit)
        +append_snapshot_bid(timestamp, price, depth_limit, result)
        +append_snapshot_ask(timestamp, price, depth_limit, result)
        +append_signed_book(timestamp, price, side, depth_limit, result)
        +add_market_order(event, event_log)
        +remove_market_cancel_duplicate(event_log, order_type)
        +last_inserted_order(side)
        +last_canceled_order(side)
        +last_market_order(side)
        +latest_snapshot(side)
        +last_market_depth(side, depth_limit)
    }
```

---

## Output Files

Each session produces up to 9 files in `runs/` depending on `sides` and
`filetype` settings:

```mermaid
graph LR
    FS[export_session] --> BV[L2_orderbook_volm_bid]
    FS --> BP[L2_orderbook_prices_bid]
    FS --> BE[L2_orderbook_events_bid]
    FS --> AV[L2_orderbook_volm_ask]
    FS --> AP[L2_orderbook_prices_ask]
    FS --> AE[L2_orderbook_events_ask]
    FS --> SV[L2_orderbook_volm_signed]
    FS --> SP[L2_orderbook_prices_signed]
    FS --> SE[L2_orderbook_events_signed]
```

**Event record columns (single side):**

| time | order_type | price | size | position | mid_price | spread |
|---|---|---|---|---|---|---|
| datetime | insertion / cancellation / market | float | float | int | float | float |

**Signed events** add a `side` column and use signed `size` and `position`
(negative = bid side), following the convention from
Cont, Kukanov and Stoikov (2011).

| time | order_type | price | size | position | side | mid_price | spread |
|---|---|---|---|---|---|---|---|
| datetime | insertion / cancellation / market | float | ± float | ± int | bid/ask | float | float |

All numeric values are written with 8 decimal places. No scientific notation,
no IEEE 754 float artifacts.

---

## Configuration

| Parameter | Source | Default |
|---|---|---|
| `currency_pair` | `config.ini` | `XRP-USD` |
| `recording_duration` | `config.ini` | `10` |
| `position_range` | `config.ini` | `5` |
| `sides` | `config.ini` | `bid,ask,signed` |
| `filetype` | `config.ini` | `csv` |
| `output_dir` | CLI flag | `runs` |

Credentials are loaded from `cdp_api_key.json` (downloaded from the Coinbase
Developer Portal). If the file is absent, `WSClient` falls back to the
`COINBASE_API_KEY` / `COINBASE_API_SECRET` environment variables.

---

## Documentation Management

Sphinx docs live in `docs/`. The compiled PDF is committed at
`docs/manual/manual.pdf` and should be rebuilt whenever the RST files change.

### Commands

All commands run from the `docs/` directory.

| Command | Effect |
|---|---|
| `make html` | Build HTML docs |
| `make latexpdf` | Build PDF from RST source |
| `make clean` | Delete the `_build/` cache entirely |

### Always `make clean` before rebuilding

Sphinx caches build artifacts in `docs/_build/`. If you change RST files and
run `make latexpdf` without cleaning first, Sphinx may report
`Nothing to do` and produce a stale PDF. Always clean before a rebuild:

```bash
cd docs
make clean && make latexpdf
cp _build/latex/crobat.pdf manual/manual.pdf
```

### When to rebuild

- Any change to `docs/*.rst`
- Any change to docstrings in `crobat/*.py` (autodoc pulls these at build time)
- After adding or removing modules from `docs/api.rst`

### `docs/_build/` is gitignored

Build output is excluded from git. Only `docs/manual/manual.pdf` is committed.
