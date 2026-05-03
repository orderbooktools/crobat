[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![GNU GPLv3][license-shield]][license-url]

<br />
<p align="center">
  <img src="https://raw.githubusercontent.com/orderbooktools/crobat/master/images/crobat.png" alt="Logo" width="120" height="80">
  <h3 align="center">crobat</h3>
  <p align="center">
    Cryptocurrency Order Book Analysis Tool
    <br />
    <a href="https://github.com/orderbooktools/crobat"><strong>Explore the docs »</strong></a>
    ·
    <a href="https://github.com/orderbooktools/crobat/issues">Report Bug</a>
    ·
    <a href="https://github.com/orderbooktools/crobat/issues">Request Feature</a>
  </p>
</p>

## Table of Contents

- [About](#about)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Output Format](#output-format)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [References](#references)

## About

crobat is a Python library for recording live Level 2 order book data from the
Coinbase Advanced Trade WebSocket feed. It captures limit order insertions (LO),
cancellations (CO), and market orders (MO) in real time and saves them as
structured time series files.

The project grew out of research on CUSUM statistics applied to Bitcoin
transactions, and the output formats are designed to be compatible with
conventions from the market microstructure literature (see [References](#references)).

<img src="https://raw.githubusercontent.com/orderbooktools/crobat/master/images/figure_1.png">

## Getting Started

### Prerequisites

- Python 3.10+
- A Coinbase Advanced Trade account with API credentials (`cdp_api_key.json`)

### Installation

```bash
git clone https://github.com/orderbooktools/crobat.git
cd crobat
pip install -r requirements.txt   # or: pip install -e .
```

Place your `cdp_api_key.json` in the project root. Configure defaults in `config.ini`:

```ini
[recording]
currency_pair      = XRP-USD
position_range     = 5
recording_duration = 10
sides              = bid,ask,signed
filetype           = csv
```

> **Note:** On busy pairs like BTC-USD, consider recording outside NYSE and LSE
> trading hours to reduce message volume. XRP-USD is a good starting point.

## Usage

### CLI

```bash
# Use defaults from config.ini
python CLI/crobat_cli.py

# Override parameters
python CLI/crobat_cli.py --pair BTC-USD --duration 30 --filetype pkl

# Interactive mode — prompts for each parameter
python CLI/crobat_cli.py --interactive
```

### Python API

```python
from crobat.recorder import L2Recorder
from crobat.config import recording_defaults

class Settings:
    d = recording_defaults()
    currency_pair      = d['currency_pair']
    position_range     = d['position_range']
    recording_duration = d['recording_duration']
    sides              = d['sides']
    filetype           = d['filetype']
    output_dir         = 'runs'

recorder = L2Recorder(Settings())
recorder.start()

# Access session history after recording
recorder.book.bid_events       # bid-side event log
recorder.book.ask_events       # ask-side event log
recorder.book.signed_events    # signed event log
recorder.book.latest_snapshot(side='signed')
```

## Output Format

Each session produces up to 9 files in the output directory (default: `runs/`),
named with a UTC timestamp suffix.

| File | Side | Description |
|------|------|-------------|
| `L2_orderbook_volm_bid<ts>` | bid | Volume snapshots, bid side |
| `L2_orderbook_volm_ask<ts>` | ask | Volume snapshots, ask side |
| `L2_orderbook_volm_signed<ts>` | both | Volume snapshots, signed order book |
| `L2_orderbook_prices_bid<ts>` | bid | Price snapshots, bid side |
| `L2_orderbook_prices_ask<ts>` | ask | Price snapshots, ask side |
| `L2_orderbook_prices_signed<ts>` | both | Price snapshots, signed order book |
| `L2_orderbook_events_bid<ts>` | bid | Event time series, bid side |
| `L2_orderbook_events_ask<ts>` | ask | Event time series, ask side |
| `L2_orderbook_events_signed<ts>` | both | Event time series, signed |

### Snapshot format (single side)

| Timestamp | 1 | 2 | 3 | ... | position_range |
|-----------|---|---|---|-----|----------------|
| YYYY-MM-DD HH:MM:SS.ffffff | vol @ pos 1 | vol @ pos 2 | ... | | vol @ pos n |

An associated price snapshot is generated in the same format.

### Signed order book snapshot

Follows the convention from Cont, Kukanov and Stoikov (2011). Bid positions
are negative, ask positions are positive. Position 0 is skipped.

| Timestamp | -5 | -4 | -3 | -2 | -1 | 1 | 2 | 3 | 4 | 5 |
|-----------|----|----|----|----|----|----|---|---|---|---|
| YYYY-MM-DD HH:MM:SS.ffffff | ← bid vol (negative) → | ← ask vol → |

### Event recordings

| Timestamp | order_type | price_level | event_size | position | mid_price | spread |
|-----------|------------|-------------|------------|----------|-----------|--------|
| YYYY-MM-DD HH:MM:SS.ffffff | LO/CO/MO | quote ccy | base ccy | ordinal | (ask+bid)/2 | ask-bid |

Signed events add a `side` column and sign the event size by order flow
convention: positive for buy-side activity, negative for sell-side.

See `Demo/` for example output files.

## Roadmap

- [x] Live L2 order book recording via Coinbase Advanced Trade WebSocket
- [x] Bid, ask, and signed order book snapshots
- [x] LO, CO, MO event time series
- [x] CSV, pkl, and xlsx output formats
- [x] CLI with config.ini defaults and interactive mode
- [x] Snapshot timeout detection with retry logic
- [ ] Fixed tick order book snapshots
- [ ] Configurable output file naming

## Contributing

Contributions are welcome. Please fork the repo, create a feature branch,
and open a pull request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a pull request

## License

Distributed under the GNU GPLv3 License. See `LICENSE` for more information.

## Contact

Ivan E. Perez — [@IvanEPerez](https://twitter.com/IvanEPerez) — perez.ivan.e@gmail.com

Project Link: [https://github.com/orderbooktools/crobat](https://github.com/orderbooktools/crobat)

## References

1. Huang W., Lehalle C.A. and Rosenbaum M. — [Simulating and analyzing order book data: The queue-reactive model](https://arxiv.org/pdf/1312.0563.pdf)
2. Cont R., Stoikov S. and Talreja R. — [A stochastic model for order book dynamics](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.139.1085&rep=rep1&type=pdf)
3. Cont R., Kukanov A. and Stoikov S. — [The price impact of order book events](https://arxiv.org/pdf/1011.6402.pdf)
4. Cartea A., Jaimungal S. and Wang Y. — [Spoofing and Price Manipulation in Order Driven Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3431139)
5. Silyantev E. — [Order flow analysis of cryptocurrency markets](https://link.springer.com/article/10.1007/s42521-019-00007-w)
6. Perez I.E. — [A Study of CUSUM Statistics on Bitcoin Transactions](https://academicworks.cuny.edu/cgi/viewcontent.cgi?article=1682&context=hc_sas_etds)

<!-- MARKDOWN LINKS -->
[contributors-shield]: https://img.shields.io/github/contributors/orderbooktools/crobat.svg?style=flat-square
[contributors-url]: https://github.com/orderbooktools/crobat/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/orderbooktools/crobat.svg?style=flat-square
[forks-url]: https://github.com/orderbooktools/crobat/network/members
[stars-shield]: https://img.shields.io/github/stars/orderbooktools/crobat.svg?style=flat-square
[stars-url]: https://github.com/orderbooktools/crobat/stargazers
[issues-shield]: https://img.shields.io/github/issues/orderbooktools/crobat.svg?style=flat-square
[issues-url]: https://github.com/orderbooktools/crobat/issues
[license-shield]: https://img.shields.io/github/license/orderbooktools/crobat.svg?style=flat-square
[license-url]: https://github.com/orderbooktools/crobat/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/ieperez
