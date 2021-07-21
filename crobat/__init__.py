## this is the crobat init 
## very straight forward import everything so that we can run crobat



# # filesave shit 
# from .filesave import *
# from .orderbook import *
# from .orderbook_helpers import * 
# from .recorder import *

# ## i think everything is okay???
#
import sys, os
# i need to add each wd to the syspath
# 1 get the relative path
#os.chdir('..')
sys.path.append(os.getcwd())

# # 2 i need to import everything independently
# #import filesave
# import orderbook
# import orderbook_helpers
# import recorder
