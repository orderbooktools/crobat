import sys
print(sys.path)

import lobster 
import asyncio, time
import inspect


print(dir(lobster))
misc = ['__builtins__', '__cached__', '__doc__', '__file__', '__loader__',
        '__name__', '__package__', '__path__', '__spec__']

from_imports = ['bisect', 'copy', 'np', 'pd']


class_default_dir = ['__class__', '__delattr__', '__dict__', '__dir__',
 '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', 
 '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__',
 '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', 
 '__sizeof__', '__str__', '__subclasshook__', '__weakref__']

func_default_dir =  ['__annotations__', '__call__', '__class__', '__closure__',
 '__code__', '__defaults__', '__delattr__', '__dict__', 
 '__dir__', '__doc__', '__eq__', '__format__', '__ge__', 
 '__get__', '__getattribute__', '__globals__', '__gt__',
 '__hash__', '__init__', '__init_subclass__', '__kwdefaults__',
 '__le__', '__lt__', '__module__', '__name__', '__ne__', '__new__', 
 '__qualname__', '__reduce__', '__reduce_ex__', '__repr__',
'__setattr__', '__sizeof__', '__str__', '__subclasshook__']

class dummy_class():
    pass

def dummy_function():
    pass


for sub_module in dir(lobster):
    if sub_module in (misc+from_imports):
        print(sub_module, "we dont need it")
    else:
        print(type(getattr(lobster, sub_module)))
        if type(getattr(lobster, sub_module)) == type(dummy_function):  #
            for attribute in dir(getattr(lobster, sub_module)):
                if attribute not in func_default_dir:
                    print(attribute)
                else:
                    pass
        elif type(getattr(lobster, sub_module)) == type(dummy_class):
            for attribute in dir(getattr(lobster, sub_module)):
                if attribute not in class_default_dir:
                    print(attribute)
                else:
                    pass
                    
           #if type(getattr(lobster, sub_module))
        #print(sub_module, dir(getattr(lobster, sub_module)))

print("using inpsect")
        

for name, data in inspect.getmembers(lobster):
    if name in (misc+from_imports):
        print(sub_module, "we dont need it")
    else:
        print('{} : {!r}'.format(name, data))

## how do i want ths i testing suite to work 

# test py
# import lobster or some package

# test A. types of module

# for each sub module list objects

# for each object list params and attr

# now that i have a map






#for submodule in dir(lobster)

#from test import test_connection

#test_connection.main()


# #from datetime import datetime
# import copra.rest
# from copra.websocket import Channel, Client
# #import pandas as pd

# # how do i want this shit to work

# # 1. you import the program
# # 2. you intialize the args, with the option to start recording
# # 3a. if you choose to start recording
# #     i. you can call the class.get_item to see what the last order was
# #     ii. you can call a function to get the current picture of the orderbook
# #     iii.  you can call a function to  get the running order book images  as dirty or pandas'd
# #     iv.  you can call a function to get the last_orders disrt or as pandas
# # 3b. if not you have the option of calling the class indiviudually within your own asyncio loop
# # 4. error handling ? 

# def main():
#     settings = rec.input_args()
#     loop = asyncio.get_event_loop()
#     channel = Channel('level2', settings.currency_pair) 
#     channel2 =Channel('ticker', settings.currency_pair)
#     ws = rec.L2_Update(loop, channel, settings)
#     ws.subscribe(channel2)
#     try:
#         loop.run_forever()
#     except KeyboardInterrupt:
#         loop.run_until_complete(ws.close())
#         loop.close()

# if __name__ == '__main__':
#     main()