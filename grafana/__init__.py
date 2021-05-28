## this is the init of crobat 

"""
crobat is organized into a few subsections
the first is
1. stream settings
2. prebuilt standalone solutions 
3. all the postgresshit
4. grafana support
5. what else

"""

## this is thge grafana ini

import sys
import warnings 

import configparser
#import psutil 
## 
## these are the requirements that you need to run grafana
requirements = [
    'psycopg2', 'config', 'configparser'
]

for modulename in requirements:
    if modulename not in sys.modules:
        message = 'You have not imported the {} module'.format(modulename)
        warnings.warn(message, category=None, stacklevel=1, source=None)

# if "grafana-server" in (p.name() for p in psutil.process_iter()):
#     print("Grafana-server is running")
# else:
#     message = "please start your gra"


