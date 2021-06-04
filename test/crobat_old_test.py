## this file tests old crobat scripts

# imports okay
#import crobat_old.main_script
import unittest
import crobat_old 


# lets try running the script

# print(dir(crobat_old))

# print(crobat_old.__spec__)

# testing the main script 

#crobat_old.main_script.main()


class ModuleTest(unittest.TestCase):
    def setUp(self):
        pass

    # def test_add(self):
    #     actual = 2 + 1 
    #     expected = 4
    #     self.assertEqual(actual, expected)

    def test_import(self):
        pass

    def test_docstrings(self):
        
        self.assertIsNotNone(crobat_old.main_script.ws.hist)

    def tearDown(self):
        pass