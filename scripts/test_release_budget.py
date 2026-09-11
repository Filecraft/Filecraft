"""Release byte budgets; no dependencies or large fixture allocation."""
import unittest
from release_budget import validate_sizes


class BudgetChecks(unittest.TestCase):
    def test_small_build(self):
        validate_sizes(binary=700_000, app=1_400_000, archive=700_000)

    def test_each_boundary_rejected(self):
        for field, limit in [('binary', 2_000_000), ('app', 3_000_000), ('archive', 1_500_000)]:
            sizes = dict(binary=1, app=1, archive=1)
            sizes[field] = limit
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_sizes(**sizes)

    def test_empty_sizes_rejected(self):
        with self.assertRaises(ValueError):
            validate_sizes(binary=0, app=10, archive=5)


if __name__ == '__main__':
    unittest.main()
