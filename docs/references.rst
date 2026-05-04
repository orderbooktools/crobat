References
==========

crobat's event recording conventions follow the market microstructure
literature. The output formats for order book snapshots, event time
series, and signed order flow are designed to be compatible with the
models described in the papers below.

Order book dynamics and queue-reactive models
---------------------------------------------

Huang W., Lehalle C.A. and Rosenbaum M. (2015).
*Simulating and analyzing order book data: The queue-reactive model.*
Journal of the American Statistical Association.
https://arxiv.org/pdf/1312.0563.pdf

Stochastic order book models
-----------------------------

Cont R., Stoikov S. and Talreja R. (2010).
*A stochastic model for order book dynamics.*
Operations Research.
https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.139.1085&rep=rep1&type=pdf

Signed order flow and price impact
-----------------------------------

Cont R., Kukanov A. and Stoikov S. (2011).
*The price impact of order book events.*
Journal of Financial Econometrics.
https://arxiv.org/pdf/1011.6402.pdf

This paper defines the signed order book convention used in crobat:
positive order flow from buy MOs, sell COs, and buy LOs; negative from
sell MOs, buy COs, and sell LOs.

Spoofing and manipulation
--------------------------

Cartea A., Jaimungal S. and Wang Y. (2020).
*Spoofing and Price Manipulation in Order Driven Markets.*
Applied Mathematical Finance.
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3431139

Cryptocurrency order flow analysis
------------------------------------

Silyantev E. (2019).
*Order flow analysis of cryptocurrency markets.*
Digital Finance.
https://link.springer.com/article/10.1007/s42521-019-00007-w

This paper demonstrates Order Flow Imbalance (OFI) and Trade Flow
Imbalance applied to BTC-USD, providing a working model for the type
of analysis crobat's output is designed to support.

Related work
------------

This library grew out of research presented in:

Perez I.E. (2021).
*A Study of CUSUM Statistics on Bitcoin Transactions.*
CUNY Academic Works.
https://academicworks.cuny.edu/cgi/viewcontent.cgi?article=1682&context=hc_sas_etds
