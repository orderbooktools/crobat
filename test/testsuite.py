# tests/runner.py
import unittest

# import your test modules
import crobat_old_test

# initialize the test suite
loader = unittest.TestLoader()
suite  = unittest.TestSuite()

# add tests to the test suite
suite.addTests(loader.loadTestsFromModule(crobat_old_test))
#suite.addTests(loader.loadTestsFromModule(scenario))
#suite.addTests(loader.loadTestsFromModule(thing))

# initialize a runner, pass it your suite and run it
runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(suite)