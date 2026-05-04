"""
crobat/filesave.py

Converts a completed :class:`crobat.orderbook.LimitOrderBook` session object
into pandas DataFrames and writes them to disk as CSV, PKL, or XLSX files.

Called automatically by :meth:`crobat.recorder.L2Recorder.on_close` at the
end of every recording session. Can also be called directly for post-hoc
export of a history object.
"""
import os
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# All float values in output files are rounded to this precision.
# 8 decimal places covers the smallest tradable quantity for any crypto asset
# and eliminates IEEE 754 artifacts such as 1.3878499999999998 or 9.999e-05.
# Integers (e.g. position) are written as-is.
_OUTPUT_PRECISION = Decimal("0.00000001")


def _to_decimal(value):
    """
    Round a float to ``_OUTPUT_PRECISION``.

    Integers pass through unchanged — position is a signed integer index and
    must not gain decimal places. Non-numeric values (timestamps, strings)
    also pass through unchanged.

    Uses ``repr()`` before constructing the Decimal to avoid inheriting the
    float's binary representation error.
    """
    if isinstance(value, float):
        d = Decimal(repr(value)).quantize(_OUTPUT_PRECISION, rounding=ROUND_HALF_UP)
        # Decimal represents zero as 0E-8 in scientific notation.
        # Return the fixed-point string so pandas writes '0.00000000' to CSV.
        return '0.00000000' if d == 0 else d
    return value


def snapshot_history_to_records(history, pos_limit=5):
    """
    Convert a single-sided order book history into two lists of dicts
    suitable for DataFrame construction.

    Each entry in ``history`` is a ``[timestamp, snapshot]`` pair where
    ``snapshot`` is a list of ``[price, volume]`` pairs ordered best-to-worst.

    Parameters
    ----------
    history : list of list
        Use ``bid_history`` or ``ask_history`` from a
        :class:`crobat.orderbook.LimitOrderBook` instance.
    pos_limit : int, optional
        Number of price levels to include per snapshot. Default ``5``.

    Returns
    -------
    volume_records : list of dict
        Keys: ``'time'``, ``'1'`` … ``str(pos_limit)``.
    price_records : list of dict
        Same structure, values are prices instead of volumes.
    """
    volume_records = []
    price_records = []
    for timestamp, snapshot in history:
        vol_row   = {"time": timestamp}
        price_row = {"time": timestamp}
        for n in range(pos_limit):
            vol_row[str(n + 1)]   = _to_decimal(snapshot[n][1])
            price_row[str(n + 1)] = _to_decimal(snapshot[n][0])
        volume_records.append(vol_row)
        price_records.append(price_row)
    return volume_records, price_records


def signed_history_to_records(history, pos_limit=5):
    """
    Convert a signed order book history into two lists of dicts suitable
    for DataFrame construction.

    Bid levels carry negative positions and negated volumes; ask levels carry
    positive positions. Follows Cont, Kukanov and Stoikov (2011).

    Parameters
    ----------
    history : list of list
        Use ``signed_history`` from a
        :class:`crobat.orderbook.LimitOrderBook` instance.
    pos_limit : int, optional
        Number of price levels per side. Default ``5``.

    Returns
    -------
    volume_records : list of dict
    price_records : list of dict
    """
    volume_records = []
    price_records = []

    # history[0] is the init-state snapshot; it has no corresponding event,
    # so we start iterating from history[1].
    for i in range(len(history) - 1):
        timestamp, snapshot = history[i + 1]
        vol_row   = {"time": timestamp}
        price_row = {"time": timestamp}
        for n in range(len(snapshot)):
            dict_key = n - pos_limit
            if dict_key == 0:
                dict_key += 1
            vol_row[str(dict_key)]   = _to_decimal(snapshot[n][1])
            price_row[str(dict_key)] = _to_decimal(snapshot[n][0])
        volume_records.append(vol_row)
        price_records.append(price_row)

    return volume_records, price_records


def events_to_records(events, signed=False):
    """
    Convert a raw event log into a list of dicts with human-readable column
    names, suitable for DataFrame construction.

    Parameters
    ----------
    events : list of list
        Each element is either:

        - ``[time, order_type, price, size, position, mid_price, spread]``
          for bid/ask events, or
        - ``[time, order_type, price, size, position, side, mid_price, spread]``
          for signed events.

    signed : bool, optional
        ``True`` for signed event logs, which carry an extra ``side`` field.

    Returns
    -------
    list of dict
    """
    if signed:
        keys = ["time", "order_type", "price", "size", "position",
                "side", "mid_price", "spread"]
    else:
        keys = ["time", "order_type", "price", "size", "position",
                "mid_price", "spread"]

    records = []
    for row in events:
        records.append(dict(zip(keys, [_to_decimal(v) for v in row])))
    return records


def clear_output_dir(output_dir):
    """
    Delete all files in ``output_dir``, leaving the directory itself intact.

    Only regular files are removed. Subdirectories are left untouched.
    If the directory does not exist, this is a no-op.

    Parameters
    ----------
    output_dir : str

    Returns
    -------
    int
        Number of files deleted.
    """
    if not os.path.isdir(output_dir):
        return 0
    deleted = 0
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
            deleted += 1
    return deleted


def _save(title, records, output_dir, drop_init_row, fmt):
    """
    Write ``records`` to disk in the requested format.

    Parameters
    ----------
    title : str
        Output filename without extension.
    records : list of dict
    output_dir : str
    drop_init_row : bool
        ``True`` for snapshot files (drops the init-state row).
        ``False`` for event files, which have no init row.
    fmt : str
        One of ``'csv'``, ``'pkl'``, ``'xlsx'``.
    """
    df = pd.DataFrame(records)
    if drop_init_row:
        df = df[1:]
    path = os.path.join(output_dir, title + "." + fmt)
    if fmt == 'csv':
        df.to_csv(path, index=False)
    elif fmt == 'pkl':
        df.to_pickle(path)
    elif fmt == 'xlsx':
        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Sheet1')
        writer.save()


def save_pickle(title, records, output_dir=".", drop_init_row=True):
    """Save a list of dicts to a ``.pkl`` file."""
    _save(title, records, output_dir, drop_init_row, 'pkl')


def save_csv(title, records, output_dir=".", drop_init_row=True):
    """Save a list of dicts to a ``.csv`` file."""
    _save(title, records, output_dir, drop_init_row, 'csv')


def save_excel(title, records, output_dir=".", drop_init_row=True):
    """Save a list of dicts to a ``.xlsx`` file."""
    _save(title, records, output_dir, drop_init_row, 'xlsx')


def export_session(book, position_range, sides, filetype, include_events=True, output_dir="."):
    """
    Export a completed session to disk.

    Writes one volume file, one price file, and (optionally) one events file
    per requested side, in each requested format.

    Called automatically by :meth:`crobat.recorder.L2Recorder.on_close`.

    Parameters
    ----------
    book : crobat.orderbook.LimitOrderBook
    position_range : int
        Number of price levels per side per snapshot row.
    sides : list of str
        Any combination of ``'bid'``, ``'ask'``, ``'signed'``.
    filetype : list of str
        Any combination of ``'csv'``, ``'pkl'``, ``'xlsx'``.
    include_events : bool, optional
        Write event log files in addition to snapshot files. Default ``True``.
    output_dir : str, optional
        Directory to write into. Created if absent. Default ``'.'``.
    """
    session_time = datetime.utcnow()
    os.makedirs(output_dir, exist_ok=True)

    # Each batch: (records, title, is_event_file).
    # Snapshot files drop their first (init-state) row; event files do not.
    export_batches = []

    if 'bid' in sides:
        vol_records, price_records = snapshot_history_to_records(book.bid_history, position_range)
        ts = str(session_time)
        export_batches.append((vol_records,   "L2_orderbook_volm_bid"   + ts, False))
        export_batches.append((price_records, "L2_orderbook_prices_bid" + ts, False))
        if include_events:
            export_batches.append((events_to_records(book.bid_events),
                                   "L2_orderbook_events_bid" + ts, True))

    if 'ask' in sides:
        vol_records, price_records = snapshot_history_to_records(book.ask_history, position_range)
        ts = str(session_time)
        export_batches.append((vol_records,   "L2_orderbook_volm_ask"   + ts, False))
        export_batches.append((price_records, "L2_orderbook_prices_ask" + ts, False))
        if include_events:
            export_batches.append((events_to_records(book.ask_events),
                                   "L2_orderbook_events_ask" + ts, True))

    if 'signed' in sides:
        vol_records, price_records = signed_history_to_records(
            book.signed_history, position_range
        )
        ts = str(session_time)
        export_batches.append((vol_records,   "L2_orderbook_volm_signed"   + ts, False))
        export_batches.append((price_records, "L2_orderbook_prices_signed" + ts, False))
        if include_events:
            export_batches.append((events_to_records(book.signed_events, signed=True),
                                   "L2_orderbook_events_signed" + ts, True))

    for records, title, is_event_file in export_batches:
        drop = not is_event_file
        if 'csv' in filetype:
            save_csv(title, records, output_dir, drop_init_row=drop)
        if 'pkl' in filetype:
            save_pickle(title, records, output_dir, drop_init_row=drop)
        if 'xlsx' in filetype:
            save_excel(title, records, output_dir, drop_init_row=drop)
