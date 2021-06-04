## this file tests old crobat scripts

# imports okay
import crobat_old.main_script
import unittest
# lets try running the script

print(dir(crobat_old))

print(crobat_old.__spec__)

# testing the main script 



class MainScriptTest(unittest.TestCase):
    def setUp(self):
        pass
        
    def test_script(self):
        crobat_old.main_script.main()
        self.assertIsNotNone(crobat_old.main_script.ws.hist)

    def tearDown(self):
        pass