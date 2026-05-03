# crobat — Code Review & Design Debt

Analysis through the lens of *A Philosophy of Software Design* (Ousterhout).
Each issue is tagged with the relevant chapter. Issues are ordered by priority.

---

## Bugs

### `last_canceled_order` searches for the wrong order type
**File:** `crobat/orderbook.py`
**Method:** `history.last_canceled_order`
**Chapter:** Ch. 2 — Complexity (unknown unknown)

The method searches for `"insertion"` instead of `"cancelation"`. It is a
copy-paste of `last_inserted_order` with the name changed but not the logic.
Any caller using this method gets insertion events, not cancellations.

---

## Unknown Unknowns

### The `token` flag has a hidden cross-module contract
**Files:** `crobat/orderbook.py`, `crobat/recorder.py`
**Chapter:** Ch. 2 — Unknown unknowns

`self.hist.token` is a boolean that gates whether an order book event is
recorded. Its lifecycle spans two modules:

- `recorder.py` resets it to `False` before each update (`self.hist.token = False`)
- Multiple methods inside `history` set it to `True` or `False` depending on
  what they find
- `trim_coordinator` makes the final decision

A reader of `history` cannot understand `token` without reading `recorder.py`.
A reader of `recorder.py` cannot understand why it resets `token` without
reading `history`. This is a hidden contract through a mutable flag.

**Fix direction:** Document the contract explicitly in both files. Long-term,
the flag should be local to the update sequence, not a persistent attribute on
the history object.

---

### The `[1:]` DataFrame slice has no explanation
**File:** `crobat/filesave.py`
**Functions:** `pd_csv_save`, `pd_pkl_save`, `pd_excel_save`
**Chapter:** Ch. 18 — Obviousness

Every save function does `hist_obj_df = hist_obj_df[1:]` after creating the
DataFrame. No comment explains why. The first row is silently dropped.

The likely reason: the first history entry is the snapshot initialisation
state, not an event, so it shouldn't appear in the output. But this is not
stated anywhere. A developer reading this will stop and wonder if it's a bug.

**Fix direction:** Add a one-line comment. If the reason is the snapshot row,
consider filtering it at the history level instead of the export level.

---

## Information Leakage

### The signed order book convention is implemented in three places
**Files:** `crobat/orderbook.py`, `crobat/orderbook_helpers.py`, `crobat/filesave.py`
**Chapter:** Ch. 5 — Information Hiding

The Cont, Kukanov and Stoikov (2011) signed order book convention — negative
positions for bids, positive for asks, bid volumes negated — appears in:

1. `orderbook.py` `initialize_snap_events`: constructs `snapshot_signed` by
   negating and reversing bids
2. `orderbook_helpers.py` `set_sign` / `set_signed_position`: implements the
   sign rules
3. `filesave.py` `convert_array_to_list_dict_sob`: re-implements the position
   mapping with `bisect`

This is one piece of domain knowledge living in three files. Changing the
convention requires touching all three.

**Fix direction:** The convention belongs in `orderbook_helpers.py`. The other
two files should call helpers rather than re-implementing the logic.

---

### `recorder.py` knows Coinbase's wire format in three separate methods
**File:** `crobat/recorder.py`
**Methods:** `_handle_l2`, `_handle_market_trades`, `_handle_ticker_quotes`
**Chapter:** Ch. 5 — Information Hiding

Coinbase field names (`"price_level"`, `"new_quantity"`, `"event_time"`,
`"BUY"`, `"SELL"`) are hardcoded across three methods. If Coinbase renames a
field, three methods need updating.

**Fix direction:** Concentrate field name knowledge in one place — either
constants at the top of `recorder.py` or a small private parsing function per
channel that extracts the values before the handler logic runs.

---

## Change Amplification

### Spread and mid-price are computed in three separate methods
**File:** `crobat/orderbook.py`
**Methods:** `append_snapshot_bid`, `append_snapshot_ask`, `append_signed_book`
**Chapter:** Ch. 9 — Splitting and Joining

All three methods compute:

```python
mid_price = 0.5 * (self.bid_range[0] + self.ask_range[0])
spread    = self.ask_range[0] - self.bid_range[0]
```

These are derived values. Changing the spread formula requires updating three
methods. They should be computed once, either as properties on `history` or
extracted into a helper.

**Fix direction:** Add `@property` methods `mid_price` and `spread` to
`history` that compute from `bid_range[0]` and `ask_range[0]`. The three
append methods call the properties.

---

## Shallow Interfaces

### `filesaver` uses `**kwargs` for required parameters
**File:** `crobat/filesave.py`
**Function:** `filesaver`
**Chapter:** Ch. 4 — Deep Modules

`filesaver` takes `sides`, `filetype`, and `output_dir` as `**kwargs`. This
means:

- No type checking at the call site
- Misspelling `'filetype'` as `'file_type'` silently writes nothing
- The function prints `"no sides specified"` instead of raising — callers
  cannot detect the failure programmatically

**Fix direction:** Make `sides` and `filetype` explicit keyword arguments with
no defaults (forcing the caller to be explicit), and `output_dir` an explicit
kwarg with a default of `'.'`.

---

## Dead Code

### `pre_level_depth` is passed through the entire update sequence but never used
**Files:** `crobat/orderbook.py`, `crobat/recorder.py`
**Functions:** `UpdateSnapshot_bid_Seq`, `UpdateSnapshot_ask_Seq`,
`update_level_depth`, `update_price_index_buy`, `update_price_index_sell`
**Chapter:** Ch. 9 — Splitting and Joining

`pre_level_depth` is initialised to `0` in `recorder.py`, passed into
`UpdateSnapshot_*_Seq`, threaded through `update_level_depth` and
`update_price_index_*`, and returned — but the returned value is never read by
any caller. It adds a parameter to five function signatures for no benefit.

**Fix direction:** Remove the parameter from all five signatures. The value it
was meant to capture (the volume before an update) is already available as
`snap_array[update_index][1]` inside `update_level_depth` if it's ever needed.

---

### `event_size` parameter in `set_sign` is unused
**File:** `crobat/orderbook_helpers.py`
**Function:** `set_sign`
**Chapter:** Ch. 9 — Splitting and Joining

The function signature is `set_sign(event_size, side, order_type)` but
`event_size` is never referenced in the body. It was kept "for interface
consistency" but adds noise to every call site.

**Fix direction:** Remove the parameter. Update all call sites (two: in
`append_signed_book` in `orderbook.py`).

---

## Priority Summary

| Issue | Type | Impact | Effort |
|---|---|---|---|
| `last_canceled_order` wrong search term | Bug | High | Trivial |
| `filesaver` kwargs → explicit params | Shallow interface | Medium | Small |
| `[1:]` slice — document or fix | Unknown unknown | Low | Trivial |
| `token` flag — document the contract | Unknown unknown | High | Small |
| `pre_level_depth` — remove dead param | Dead code | Medium | Small |
| `event_size` in `set_sign` — remove | Dead code | Low | Trivial |
| Spread/mid-price duplication | Change amplification | Medium | Small |
| Signed convention consolidation | Information leakage | Medium | Medium |
| Coinbase field names — concentrate | Information leakage | Medium | Small |
