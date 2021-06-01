import unittest 
import os

path =  '/home/ivan/Documents/github/crobat/'
os.chdir(path)
print(os.getcwd())

from lobster import LOB_funcs

class test_output_format(unittest.TestCase):
    def setUp(self):
        """ Call before every testcase"""
        self.foo = 