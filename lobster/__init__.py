## this is the __init__.py for the lobster ubs module of crobat
## decisions will it run like base crobat? NO 
## will it use elements from base crobat ? maybe
## whats different about this vs crobat? 
	# 1. the file output format is different so filesave needs its own functions
	# 2. the postgres realization is also different from base crobat so it needs its own postgres setup
	# 3. the grafana integration is finished but documentation will need to be included
	# 4. 
from .LOB_funcs import *
