API Reference
=============

crobat.recorder
---------------

The main entry point for live recording sessions. Defines
:class:`~crobat.recorder.L2Recorder` and
:exc:`~crobat.recorder.SnapshotTimeoutError`.

.. automodule:: crobat.recorder
   :members:
   :undoc-members:
   :show-inheritance:

crobat.orderbook
----------------

:class:`~crobat.orderbook.LimitOrderBook` maintains all live order book
state and history during a session. The module-level
:func:`~crobat.orderbook.apply_update` function orchestrates each L2
update through the full mutation sequence.

.. automodule:: crobat.orderbook
   :members:
   :undoc-members:
   :show-inheritance:

crobat.orderbook_helpers
------------------------

Pure utility functions used internally by :mod:`crobat.orderbook`.
No state, no side effects.

.. automodule:: crobat.orderbook_helpers
   :members:
   :undoc-members:
   :show-inheritance:

crobat.filesave
---------------

Converts :class:`~crobat.orderbook.LimitOrderBook` history arrays to
DataFrames and writes output files. Called automatically by
:meth:`~crobat.recorder.L2Recorder.on_close` via
:func:`~crobat.filesave.export_session`.

.. automodule:: crobat.filesave
   :members:
   :undoc-members:
   :show-inheritance:

crobat.config
-------------

Loads Coinbase credentials and recording defaults from ``config.ini``
and ``cdp_api_key.json``.

.. automodule:: crobat.config
   :members:
   :undoc-members:
   :show-inheritance:
