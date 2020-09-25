<!--
*** Thanks for checking out this README Template. If you have a suggestion that would
*** make this better, please fork the repo and create a pull request or simply open
*** an issue with the tag "enhancement".
*** Thanks again! Now go create something AMAZING! :D
***
***
***
*** To avoid retyping too much info. Do a search and replace for the following:
*** github_username, repo_name, twitter_handle, email
-->





<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![GNU GPLv3][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<p align="center">
    <img src="https://raw.githubusercontent.com/orderbooktools/crobat/master/images/crobat.png" alt="Logo" width="120" height="80">

  <h3 align="center">crobat</h3>

  <p align="center">
    Crypocurrency Order Book Analysis Tool  
    <br />
    <a href="https://github.com/orderbooktools/crobat"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/orderbooktools/crobat">View Demo</a>
    ·
    <a href="https://github.com/orderbooktools/crobat">Report Bug</a>
    ·
    <a href="https://github.com/orderbooktools/crobat/issues">Request Feature</a>
  </p>
</p>


<!-- TABLE OF CONTENTS -->
## Table of Contents

* [About the Project](#about-the-project)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)
* [Acknowledgements](#acknowledgements)



<!-- ABOUT THE PROJECT -->
## About The Project

<!--[![Product Name Screen Shot][product-screenshot]](https://example.com) -->

This project is an extension of my thesis, <a href="https://academicworks.cuny.edu/cgi/viewcontent.cgi?article=1682&context=hc_sas_etds"> A Study of CUSUM Statistics on Bitcoin Transactions </a>, where I was tasked with implementing CUSUM statistic processes to identify price actions periods in bitcoin markets. After developing a tool for market orders, the natural extension was to find relationships from activities in the limit order book. I started developing this tool to record instances of the limit order book in order to record Limit Order insertions (LO), cancellations (CO), and Market Orders (MO).

As the project grew I wanted to make a tool that could be used by academics looking to apply and develop market microstructure models in live markets. As a result, the styles in which the limit orderbook and orderbook events are recorded are being developed in accordance to the conventions presented in recent market microstructure papers correspond to the following papers:

1. [Huang W., Lehalle C.A. and Rosenbaum M. - Simulating and analyzing order book data:The queue-reactive model](https://arxiv.org/pdf/1312.0563.pdf)

2. [Cont R., Stoikov S. and Talreja R. - A stochastic model for order book dynamics](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.139.1085&rep=rep1&type=pdf)

3. [Cont R., Kukanov A. and Stoikov S. - The price impact of order book events](https://arxiv.org/pdf/1011.6402.pdf) 


<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites
You can use  ```requirements.txt``` to see what is necessary but they are also listed below:

**from standard python library:** asyncio, time, datetime, sys, bisect 

**requisite modules:** [copra](https://www.neuraldump.net/2018/07/copra-an-asyncronous-python-websocket-client-for-coinbase-pro/),  pandas, numpy

### Installation

```sh
pip3 install crobat
```

<!-- USAGE EXAMPLES -->
## Usage

Since this is an orderbook <u>recorder</u> my use until now has been to record the orderbook. I should write acessors to get the latest event or orderbook snapshot in realtime.

1. For now we only have the full orderbook, with no regard for ticksize, and we call that ```recorder_full.py``` (I'm still working on fixed tick).

2. We change the ```settings``` variable in the ```input_args.py``` file that has arguments for:

    | Parameter                | Function Arg  | Type |  Description | 
|---------------------------|-------------------|------| -----|
| Recording Duration | duration      | int  | recording time in seconds | 
| Position Range     | position_range| int  | ordinal distance from the best bid(ask) |
| Currency Pair      | currency_pair | str  | [List of currency pairs supported by Coinbase](https://help.coinbase.com/en/pro/trading-and-funding/cryptocurrency-trading-pairs/locations-and-trading-pairs)|

3. When you are ready, you can start the build. When it finishes you should get a message ```Connection Closed``` from ```CoPrA```. And the files for the limit orderbook for each side should be created with a timestamp:

    |Filename|side|description|
|----|----|----|
|L2_orderbook_events_askYYYY-MM-DDTHH:MM:SS.ffffff| ask| Order book events on the ask side|
|L2_orderbook_events_bidYYYY-MM-DDTHH:MM:SS.ffffff| bid| Order book events on the bid side |
|L2_orderbook_askYYYY-MM-DDTHH:MM:SS.ffffff| ask |Images of orderbook on the ask side |
|L2_orderbook_bidYYYY-MM-DDTHH:MM:SS.ffffff| bid |Images of orderbook on the bid side |

#### Understanding The Raw Order Book Data

The coinbase exchange operates using the double auction model, the [Coinbase Pro API](https://docs.pro.coinbase.com/), and by extension the [CoPrA API](https://copra.readthedocs.io/en/latest/) makes it realitively easy to get still images of an instance of the orderbook as [```snapshots```](https://docs.pro.coinbase.com/#the-level2-channel) and it sends updates in real time of the volume at a particular price level as [```l2_update```](https://docs.pro.coinbase.com/#the-level2-channel) messages. If you would like to know more, the cited papers do a great job introducing the double auction model for the purposes of defining the types of orders, and how they record events and make sense of them. 

#### Orderbook Snapshots

Below there is a graph of the snapshot where bids (green) show open limit orders to buy the 1 unit of the cryptocurrency below $7085.930, and asks (red) show open limit orders to buy 1 unit above $7085.930. The x-axis shows the price points, and the y-axis is the aggregate size at the price level.

<img src="https://raw.githubusercontent.com/orderbooktools/crobat/master/images/figure_1.png" >

Early and current works relied on exchanges and private data providers (e.g., [NASDAQ - BookViewer](https://data.nasdaq.com/BookViewer.aspx), [LOBSTER](https://lobsterdata.com/)) to provide reconstructions of orderbooks. Earlier works were limited to taking snapshots and inferring the possible sequence of orderbook events between states. Coinbase and by extension crobat update the levels on the instance of a update message from the exchange so there is no guess as to what happened between states of the order book. The current format of the orderbook snapshot is not aggregated. The format of the orderbook snapshot is shown below

| Timestamp | 0 | 1| 2| ...| position range -1|
|--------------------------------------|------------------------------|-----------------------------|-------------------------------|----| -------------------|
|YYYY-MM-DDTHH:MM:SS.ffffff| total BTC at position 0 |total BTC at position 1| total BTC at position 2 | ... |  total BTC at position range -1|

This has some limitations as you cannot get market depth in the quote currency. These snapshots in the future will include the price at each position for studies involving market depth. The Event Recorder does retain price point information.

#### Event Recordings
 Event recording are a timeseries of MO, LO, CO's as afforded from the ```l2_update``` messages which are used to update the price, volume pair size at each price level. The format of the Event recorder is as follows:
 
 | Timestamp | order type | price level | event size | position | mid price| bid-ask spread|
 |--------------------------------------|----------------------------|---------------|--------------|-------------|-------------|--------------------|
|YYYY-MM-DDTHH:MM:SS.ffffff| MO, LO, CO | price level in quote currency| event size in base currency |position | (best-ask + best-bid)/2 |  best-ask - best-bid range|

<!-- ROADMAP -->
## Roadmap
####Features that need to be developed in order of priority:

1. fixed tick orderbook snapshots and event recording
2. market depth recording in both base and quote currencies.
3. Acessor functions
4. modernizing/optimizing iteration and classes

See the [open issues](https://github.com/orderbooktools/crobat/issues) for a list of proposed features (and known issues).

<!-- CONTRIBUTING -->
## Contributing

Any contributions you make are greatly appreciated. I am not much of a computer scientist so suggestions and feedback will improve this project for everyone and make me a more capable developer for future projects.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- LICENSE -->
## License

Distributed under the GNU GPLv3 License. See `LICENSE` for more information.

<!-- CONTACT -->
## Contact

Ivan E. Perez - [@IvanEPerez](https://twitter.com/IvanEPerez) - perez.ivan.e@gmail.com

Project Link: [https://github.com/orderbooktools/crobat](https://github.com/orderbooktools/crobat)

<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements

* [Tony Podlaski](https://www.neuraldump.net)
* [Olympia Hadjilidis]( http://math.hunter.cuny.edu/~olympia)
<!--* [William Hilska](https://www.twitter.com/swillmatic)-->


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/orderbooktools/crobat.svg?style=flat-square
[contributors-url]: https://github.com/orderbooktools/crobat/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/orderbooktools/crobat.svg?style=flat-square
[forks-url]: https://github.com/orderbooktools/crobat/network/members
[stars-shield]: https://img.shields.io/github/stars/orderbooktools/crobat.svg?style=flat-square
[stars-url]: https://github.com/orderbooktools/crobat/stargazers
[issues-shield]: https://img.shields.io/github/issues/orderbooktools/crobat.svg?style=flat-square
[issues-url]: https://github.com/orderbooktools/crobat/issues
[license-shield]: https://img.shields.io/github/license/orderbooktools/crobat.svg?style=flat-square
[license-url]: https://github.com/orderbooktools/crobat/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/ieperez
[product-screenshot]: images/screenshot.png
