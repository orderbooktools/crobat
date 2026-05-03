"""
crobat/config.py

Loads Coinbase API credentials and recording defaults for a session.

Credentials are read from ``cdp_api_key.json`` in the project root
(downloaded from the Coinbase Developer Portal). If the file is absent,
:func:`coinbase_credentials` returns an empty dict and the
``coinbase-advanced-py`` ``WSClient`` falls back to the
``COINBASE_API_KEY`` / ``COINBASE_API_SECRET`` environment variables.

Recording defaults are read from the ``[recording]`` section of
``config.ini`` in the project root.

Usage::

    from crobat.config import coinbase_credentials, recording_defaults

    creds    = coinbase_credentials()   # passed directly to WSClient
    defaults = recording_defaults()     # dict of session parameters
"""

import configparser
import os

_ROOT = os.path.join(os.path.dirname(__file__), '..')
_KEY_FILE = os.path.join(_ROOT, 'cdp_api_key.json')
_CONFIG_PATH = os.path.join(_ROOT, 'config.ini')

_cfg = configparser.ConfigParser()
_cfg.read(_CONFIG_PATH)


def coinbase_credentials() -> dict:
    """
    Return the keyword arguments needed to authenticate a ``WSClient``.

    Looks for ``cdp_api_key.json`` in the project root. If found, returns
    ``{'key_file': <path>}``. If not found, returns ``{}`` so that
    ``WSClient`` falls back to the ``COINBASE_API_KEY`` and
    ``COINBASE_API_SECRET`` environment variables.

    Returns
    -------
    dict
        Either ``{'key_file': str}`` or ``{}``.
    """
    if os.path.exists(_KEY_FILE):
        return {'key_file': _KEY_FILE}
    return {}


def recording_defaults() -> dict:
    """
    Return recording session defaults from ``config.ini``.

    Reads the ``[recording]`` section. If the section is absent, returns
    an empty dict and callers should supply their own values.

    Returns
    -------
    dict
        Keys and their fallback values if not set in ``config.ini``:

        - ``currency_pair`` (str): ``'XRP-USD'``
        - ``position_range`` (int): ``5``
        - ``recording_duration`` (int): ``10``
        - ``sides`` (list of str): ``['bid', 'ask', 'signed']``
        - ``filetype`` (list of str): ``['csv']``
    """
    if not _cfg.has_section('recording'):
        return {}

    return {
        'currency_pair':      _cfg.get('recording', 'currency_pair',         fallback='XRP-USD'),
        'position_range':     _cfg.getint('recording', 'position_range',     fallback=5),
        'recording_duration': _cfg.getint('recording', 'recording_duration', fallback=10),
        'sides':    [s.strip() for s in _cfg.get('recording', 'sides',    fallback='bid,ask,signed').split(',')],
        'filetype': [s.strip() for s in _cfg.get('recording', 'filetype', fallback='csv').split(',')],
    }
