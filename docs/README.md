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

4. [Cartea. A, Jaimungal S. and Wang Y. - Spoofing and Price Manipulation in Order Driven Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3431139) 

5. [Silyantev, E. - Order flow analysis of cryptocurrency markets  ](https://link.springer.com/article/10.1007/s42521-019-00007-w#article-info)

The last paper, 5, shows a working model implementing Order Flow Imbalance (OFI) and Trade Flow Imbalance to BTC-USD trades was done by [Ed Silyantev](https://medium.com/@eliquinox/order-flow-analysis-of-cryptocurrency-markets-b479a0216ad8). He developed a tool to assess OFI and TFI of XBT-USD pair. 

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites
You can use  ```requirements.txt``` to see what is necessary but they are also listed below:

**from standard python library:** asyncio, time, datetime, sys, bisect 

**requisite modules:** [copra](https://www.neuraldump.net/2018/07/copra-an-asyncronous-python-websocket-client-for-coinbase-pro/),  pandas, numpy

### Installation
Given that this is still very much a work in progress, it may make more sense to fork the project, or download the project as a compressed folder, and build ```CSV_out_test.py``` with your preferred settings.

 *Note*: depending on the popularity of the asset and the computational power of your PC, you may run into errors arising from the computer not being able to keep up with the market (especially BTC-USD). I would suggest experimenting with an unpopular pair, (e.g.,  XRP-USD), or a crypto-crypto pair (e.g., XRP-BTC), and timing your queries outside of NYSE, and London Stock Exchange trading hours as they tend to have less activity.

however if you want an easy installation: 

 ```pip3 install crobat``` 
 
<!-- USAGE EXAMPLES -->
## Usage

Since this is an orderbook <u>recorder</u> my use until now has been to record the orderbook. However there are accessors in the ```LOB_funcs.py``` file, under in the *history* class. In the /test folder there is a small usecase if you would like to see it but documentation is pending.

1. For now we only have the full orderbook, with no regard for ticksize, and we call that ```recorder_full.py```. 

2. We change the ```settings``` variable in the ```CSV_out_test.py``` file that has arguments for:

    | Parameter                | Function Arg  | Type |  Description | 
    |-------------------------|-------------------|------| -------|
    | Recording Duration | duration      | int  | recording time in seconds | 
    | Position Range     | position_range| int  | ordinal distance from the best bid(ask) |
    | Currency Pair      | currency_pair | str  | [List of currency pairs supported by Coinbase](https://help.coinbase.com/en/pro/trading-and-funding/cryptocurrency-trading-pairs/locations-and-trading-pairs) |

3. When you are ready, you can start the build. When it finishes you should get a message ```Connection Closed``` from ```CoPrA```. And the files for the limit orderbook for each side should be created with a timestamp:

    |Filename|side|description|
    |----|----|----|
    |L2_orderbook_events_askYYYY-MM-DDTHH:MM:SS.ffffff| ask|Time series of order book events on the ask side|
    |L2_orderbook_events_bidYYYY-MM-DDTHH:MM:SS.ffffff| bid| Time series of order book events on the bid side |
    |L2_orderbook_events_signedYYYY-MM-DDTHH:MM:SS.ffffff| both | Time series of order book events on both sides, - sign for bid, +sign for ask|
    |L2_orderbook_ask_volmYYYY-MM-DDTHH:MM:SS.ffffff| ask |Time series of the volume snapshots of order book on the ask side |
    |L2_orderbook_bid_volmYYYY-MM-DDTHH:MM:SS.ffffff| bid |Time series of the volume snapshots of order book on the bid side |
    |L2_orderbook_signed_volmYYYY-MM-DDTHH:MM:SS.ffffff | both |Time series of the volume  snapshots of the signed order book, - for bid, + for ask|
    |L2_orderbook_ask_volmYYYY-MM-DDTHH:MM:SS.ffffff| ask |Time series of the price snapshots of order book on the ask side |
    |L2_orderbook_bid_volmYYYY-MM-DDTHH:MM:SS.ffffff| bid |Time series of the price snapshots of order book on the bid side |
    |L2_orderbook_signed_volmYYYY-MM-DDTHH:MM:SS.ffffff | both |Time series of the price snapshots of the signed order book, - for bid, + for ask|

#### Understanding The Raw Order Book Data

The coinbase exchange operates using the double auction model, the [Coinbase Pro API](https://docs.pro.coinbase.com/), and by extension the [CoPrA API](https://copra.readthedocs.io/en/latest/) makes it realitively easy to get still images of an instance of the orderbook as [```snapshots```](https://docs.pro.coinbase.com/#the-level2-channel) and it sends updates in real time of the volume at a particular price level as [```l2_update```](https://docs.pro.coinbase.com/#the-level2-channel) messages. If you would like to know more, the cited papers do a great job introducing the double auction model for the purposes of defining the types of orders, and how they record events and make sense of them. 

#### Orderbook Snapshots

Below there is a graph of the snapshot where bids (green) show open limit orders to buy the 1 unit of the cryptocurrency below $7085.930, and asks (red) show open limit orders to buy 1 unit above $7085.930. The x-axis shows the price points, and the y-axis is the aggregate size at the price level. Note that  the signed orderbook calls volume on the bid side negative. 

<img src="https://raw.githubusercontent.com/orderbooktools/crobat/master/images/figure_1.png" >

Early and current works relied on exchanges and private data providers (e.g., [NASDAQ - BookViewer](https://data.nasdaq.com/BookViewer.aspx), [LOBSTER](https://lobsterdata.com/)) to provide reconstructions of orderbooks. Earlier works were limited to taking snapshots and inferring the possible sequence of orderbook events between states. Coinbase and by extension crobat update the levels on the instance of a update message from the exchange so there is no guess as to what happened between states of the order book. The current format of the orderbook snapshot is not aggregated. The format of the orderbook snapshot for a single side is shown below

| Timestamp | 1 | 2| 3| ...| position range |
|--------------------------------------|------------------------------|-----------------------------|-------------------------------|----| -------------------|
|YYYY-MM-DDTHH:MM:SS.ffffff| total BTC at position 1 |total BTC at position 2| total BTC at position 3 | ... |  total BTC at position range |

The associated price quote (price quote (USD per XTC))snapshot is also generated, to make generation of market depth feasible. 

| Timestamp | 1 | 2| 3| ...| position range |
|--------------------------------------|------------------------------|-----------------------------|-------------------------------|----| -------------------|
|YYYY-MM-DDTHH:MM:SS.ffffff| price quote  at position 1 |price quote at position 2| price quote at position 3 | ... |  price quote at  position range |

The signed orderbook takes a different approach to position labelling so please keep that in mind. (note: I should  shift the position index to start at 1, for singe side order book snapshot time series). The signed orderbook snapshot is generated in a similar fashion with a volume, and price at each position. However, it uses the convention established in [3] for the signed order book. where positions on the bid are negative, with negative volume (XTC). I'll show the default setting that displays the 5 best bids and asks on each side.

| Timestamp | -5 | -4| -3| -2| -1 | 1| 2|3|4|5|
|-----------------------------|---------------------------|-----------------------------|-------------------------------|----| -------------------|----| -----|------|------|-----|
|YYYY-MM-DDTHH:MM:SS.ffffff| total XTC at the 5<sup>th </sup> best bid |total XTC at the 4<sup>th</sup> best bid| total XTC at the 3<sup>rd</sup> best bid | total XTC at the 2<sup>nd</sup> best bid |  total XTC at the best bid| total XTC at the best ask|total XTC at the best 2<sup>nd</sup> ask|total XTC at the 3<sup>rd</sup>  best ask|total XTC at the 4<sup>th</sup> best ask|total XTC at the 5<sup>th</sup> best ask|

Similar to the single side implementation, there is an associated price quote  (e.g., USD per XTC) snapshot generated at each timepoint. The default format is given below:

| Timestamp | -5 | -4| -3| -2| -1 | 1| 2|3|4|5|
|-----------------------------|---------------------------|-----------------------------|-------------------------------|----| -------------------|----| -----|------|------|-----|
|YYYY-MM-DDTHH:MM:SS.ffffff| price quote at the 5<sup>th </sup> best bid | price quote  at the 4<sup>th</sup> best bid| price quote at the 3<sup>rd</sup> best bid | price quote at the 2<sup>nd</sup> best bid |  price quote at the best bid| price quote at the best ask| price quote at the best 2<sup>nd</sup> ask|price quote at the 3<sup>rd</sup>  best ask|price quote at the 4<sup>th</sup> best ask|price quote at the 5<sup>th</sup> best ask|


#### Event Recordings
 Event recording are a timeseries of MO, LO, CO's as afforded from the ```l2_update``` messages which are used to update the price, volume pair size at each price level. The format of the Event recorder is as follows:
 
 | Timestamp | order type | price level | event size | position | mid price| bid-ask spread|
 |--------------------------------------|----------------------------|---------------|--------------|-------------|-------------|--------------------|
|YYYY-MM-DDTHH:MM:SS.ffffff| MO, LO, CO | price level in quote currency| event size in base currency |position | (best-ask + best-bid)/2 |  best-ask - best-bid range|

Signed event recordings follow the convention from [The Price impact of Orderbook events](https://arxiv.org/pdf/1011.6402.pdf), where positive order flow is due to MO's on the buy side, CO on the sell side, and LO on the buy side. Conversely,  negative order flow is due to MO's on the sell side, CO on the buy side, and LO on the buy side. The format is similar to the single side order book events timeseries, but the order volume is signed based on the aforementioned construction. 

 | Timestamp | order type | price level | event size | position |side| mid price| bid-ask spread|
 |--------------------------------------|----------------------------|---------------|-------|-------|-------------|-------------|--------------------|
|YYYY-MM-DDTHH:MM:SS.ffffff| MO, LO, CO | price level in quote currency| event size in base currency |signed position(- for bids, + for asks) |buy/sell | (best-ask + best-bid)/2 |  best-ask - best-bid range|

<!-- ROADMAP -->
## Roadmap
####Features that need to be developed in order of priority:

1. fixed tick orderbook snapshots and event recording 
2. ~~market depth recording in both base and quote currencies.~~
3. ~~Acessor functions~~(*documentation pending*)
4. ~~modernizing/optimizing iteration and classes~~(replaced sort instances with insert, and a little bit of logic)
5. **Finding a way to call the classes outside of the AsyncIO or WebSocket Loop (help me figure this one out!)**

 
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
