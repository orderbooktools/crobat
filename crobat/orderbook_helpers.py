"""
crobat/orderbook_helpers.py

Pure utility functions used by :class:`crobat.orderbook.LimitOrderBook`.
No state, no side effects — each function takes plain values and returns
a result.
"""


def compute_sign(side, order_type):
    """
    Return the sign (+1 or -1) for an order book event in the signed order book.

    Follows the order flow convention from Cont, Kukanov and Stoikov (2011):

    - **Ask side:** insertions and market orders are positive; cancellations
      are negative.
    - **Bid side:** the sign is flipped relative to the ask side.

    Parameters
    ----------
    side : str
        Side of the order book where the event occurred. ``'ask'`` or
        ``'bid'``.
    order_type : str
        Type of order book event. One of ``'insertion'``, ``'cancellation'``,
        or ``'market'``.

    Returns
    -------
    int
        ``1`` or ``-1``.
    """
    sign = 1
    if order_type == "cancellation":
        sign = -1
    if side == "bid":
        sign *= -1
    return sign


def compute_signed_position(position, side):
    """
    Convert a zero-indexed ordinal position to a signed position.

    The signed order book uses negative positions for the bid side and
    positive positions for the ask side, with position 0 skipped (best bid
    is ``-1``, best ask is ``1``).

    Parameters
    ----------
    position : int
        Zero-indexed ordinal distance from the best bid or best ask.
    side : str
        Side of the order book. ``'bid'`` or ``'ask'``.

    Returns
    -------
    int
        Signed position: negative for bid, positive for ask.
    """
    position += 1
    if side == "bid":
        position *= -1
    return position


def compute_min_decimals(min_currency_denom, min_asset_value):
    """
    Compute the number of decimal places needed to represent the smallest
    tradable quantity at the current price.

    Uses the worst (deepest) bid price as a conservative floor. The result
    is used to round all volume values consistently throughout a session.

    Parameters
    ----------
    min_currency_denom : float
        Minimum currency denomination of the quote currency (e.g., ``0.01``
        for one cent in USD).
    min_asset_value : float
        Lowest observed price of the base asset in the quote currency
        (e.g., the worst bid price in the order book snapshot).

    Returns
    -------
    int
        Number of decimal places for the smallest tradable amount at the
        given price. Capped at 10 to avoid runaway precision on very cheap
        assets.

    Raises
    ------
    TypeError
        If non-numeric values are passed. Ensure prices are cast to
        ``float`` before calling (e.g., ``float(msg['price'])``).
    """
    min_tradable_amount = min_currency_denom / min_asset_value
    decimals = 0
    while min_tradable_amount < 1:
        min_tradable_amount *= 10
        decimals += 1
        if decimals > 10:
            break
    return decimals


if __name__ == '__main__':
    pass
