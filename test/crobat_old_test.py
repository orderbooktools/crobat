## this file tests old crobat scripts

# imports okay
import crobat_old
import unittest
#import crobat_old.main_script
#print(dir(crobat_old))
#print(crobat_old.__doc__)
# lets try running the script

# print(dir(crobat_old))

# print(crobat_old.__spec__)

#testing the main script 

#crobat_old.main_script.main()

# modules are 
#LOB_funcs.py
#recorder_full.py

from crobat_old.LOB_funcs import *
from crobat_old.recorder_full import *
from crobat_old.main_script import *

#print(dir(crobat_old.LOB_funcs))

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

# directory = dir(crobat_old.LOB_funcs).copy()
# print(directory[2])
# found_list = []
# for attribute in directory:
#     print(attribute)
#     if not (attribute.startswith('__') or attribute.endswith('__')):
#         if attribute not in standard_library_and_reqs:
#             found_list.append(attribute)



#     # if attribute.endswith('__'):
#     #     print "alt found", attribute
#     #     directory.remove(attribute)
# print(found_list)

# for item in found_list:
#     try:
#         print(item, len(getattr(crobat_old.LOB_funcs, item).__doc__))
#     except:
#         print(item, "No docstring found")

        
    # if (directory[i] in misc_module_objects) or (directory[i] in standard_library_and_reqs):
    #     del directory[i] 
    #if i in standard_library_and_reqs:
    #    directory.remove(i)
    
#print(directory)
        

class ModuleTest(unittest.TestCase):
    """
    Moduletest class run tests on modules
    to check if they have appropriate documentation, are can be called safely?
    
    Attributes
    ----------
    None

    Methods
    -------
    setUp
        empty method
    
    test_docstrings_LOBfuncs
        tests the docstrings of the module LOB_funcs.py
    
    
    
    """

    def setUp(self):
        pass

    # def test_add(self):
    #     actual = 2 + 1 
    #     expected = 4
    #     self.assertEqual(actual, expected)        

    def test_docstrings_LOBfuncs(self):
        directory = dir(crobat_old.LOB_funcs).copy()
        found_list = []
        for attribute in directory:
            if not (attribute.startswith('__') or attribute.endswith('__')):
                if attribute not in standard_library_and_reqs:
                    found_list.append(attribute)
        for item in found_list:
            docstring = getattr(crobat_old.LOB_funcs, item).__doc__
            self.assertIsNotNone(docstring)
    
    def test_docstrings_recorder_full(self):
        directory = dir(crobat_old.recorder_full).copy()
        found_list = []
        for attribute in directory:
            if not (attribute.startswith('__') or attribute.endswith('__')):
                if attribute not in standard_library_and_reqs:
                    attr_type = str(type(getattr(crobat_old.recorder_full, attribute)))
                    if not (attr_type.endswith("module'>") or attr_type.endswith("'type'>")):
                        found_list.append(attribute)
        for item in found_list:
            for item in found_list:
                try:
                    docstring = getattr(crobat_old.recorder_full, item).__doc__
                    self.assertIsNotNone(docstring)
                except:
                    print("docstring not found ", item)
    
    def test_docstrings_main_script(self):
        directory = dir(crobat_old.main_script).copy()
        found_list = []
        for attribute in directory:
            if not (attribute.startswith('__') or attribute.endswith('__')):
                if attribute not in standard_library_and_reqs:
                    found_list.append(attribute)
        for item in found_list:
            item_type = str(type(getattr(crobat_old.main_script, item)))
            if item_type.endswith("module'>") or item_type.endswith("'type'>"):
                found_list.remove(item)
            else:
                print(item, item_type)
        for item in found_list:
            try:
                docstring = getattr(crobat_old.main_script, item).__doc__
                self.assertIsNotNone(docstring)
            except:
                print("docstring not found ", item)

    def tearDown(self):
        pass