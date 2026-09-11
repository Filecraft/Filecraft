import unittest
from package_portable import validate_portable

class BudgetChecks(unittest.TestCase):
    def test_exact_limits_rejected(self):
        for expanded,archive in [(200_000,1),(1,100_000),(0,1),(1,-1)]:
            with self.assertRaises(ValueError):validate_portable(expanded,archive)
    def test_tiny_allowed(self):validate_portable(199_999,99_999)

if __name__=='__main__':unittest.main()
