## this is an object checking script
import crobat 

### build out the list of objects and their functions
#print(dir(crobat))

misc_module_objects = [    
    '__builtins__', '__cached__', '__doc__', '__file__',
    '__loader__', '__name__', '__package__', '__path__', '__spec__', 
    ] 

crobat_imports  = [
    'L2_Update', 'UpdateSnapshot_ask_Seq', 'UpdateSnapshot_bid_Seq',
     'check_order', 'convert_array_to_list_dict',
    'convert_array_to_list_dict_sob',
    'filesave', 'filesaver', 'get_min_dec', 'get_tick_distance',
    'history', 'main', 'orderbook', 'orderbook_helpers',
    'pd_csv_save', 'pd_excel_save', 'pd_pkl_save', 'price_match',
    'recorder', 'set_sign', 'set_signed_position'
]

standard_library_and_reqs = [
 'asyncio','bisect', 'Channel', 'Client', 'copra', 'copy', 'datetime', 'gc', 'np', 'pd', 'time'
]


misc_class_objects = [
'__add__', '__class__', '__contains__', '__delattr__',
'__dir__', '__doc__', '__eq__', '__format__', '__ge__',
'__getattribute__', '__getitem__', '__getnewargs__',
'__gt__', '__hash__', '__init__', '__init_subclass__',
'__iter__', '__le__', '__len__', '__lt__', '__mod__',
'__mul__', '__ne__', '__new__', '__reduce__', '__reduce_ex__',
'__repr__', '__rmod__', '__rmul__', '__setattr__', '__sizeof__',
'__str__', '__subclasshook__', 'capitalize', 'casefold',
'center', 'count', 'encode', 'endswith', 'expandtabs',
'find', 'format', 'format_map', 'index', 'isalnum', 'isalpha',
'isascii', 'isdecimal', 'isdigit', 'isidentifier', 'islower',
'isnumeric', 'isprintable', 'isspace', 'istitle', 'isupper',
'join', 'ljust', 'lower', 'lstrip', 'maketrans', 'partition',
'replace', 'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit',
'rstrip', 'split', 'splitlines', 'startswith', 'strip', 'swapcase',
'title', 'translate', 'upper', 'zfill']
 
for module in crobat_imports[:3]:
    directory = dir(module)
    for item in misc_class_objects:
        if item in directory:
            directory.remove(item)
    print(module, directory)
# im not sure what 
#from crobat import orderbook
#print(dir(orderbook))

#history_object = orderbook.history()
#print(dir(history_object))

