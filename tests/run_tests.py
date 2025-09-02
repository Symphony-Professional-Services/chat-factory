import unittest
import sys
import os
from unittest.mock import patch

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_tests():
    # Patch logging.basicConfig to prevent file permission errors
    with patch('logging.basicConfig'):
        # Discover and run all tests
        test_loader = unittest.TestLoader()
        test_suite = test_loader.discover(os.path.dirname(os.path.abspath(__file__)), pattern='test_*.py')
        test_runner = unittest.TextTestRunner(verbosity=2)
        test_runner.run(test_suite)

if __name__ == "__main__":
    run_tests()
