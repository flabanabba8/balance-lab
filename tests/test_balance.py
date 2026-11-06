import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('balance_core', Path(__file__).parents[1] / 'core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

class BalanceTests(unittest.TestCase):
    def setUp(self):
        self.unit = {'hp': 10, 'damage': 5, 'hit': 0.5, 'crit': 0.2, 'crit_multiplier': 2}

    def test_identical_candidates_are_paired_and_repeatable(self):
        first = core.compare_duel(self.unit, self.unit, self.unit, 50, 20, 123)
        self.assertEqual(first, core.compare_duel(self.unit, self.unit, self.unit, 50, 20, 123))
        self.assertEqual(first['win_rate_difference'], 0)
        self.assertEqual(first['paired_standard_error'], 0)

    def test_guaranteed_win_and_timeout(self):
        player = dict(self.unit, hit=1, damage=10, crit=0)
        enemy = dict(self.unit, hit=0)
        result = core.compare_duel(player, self.unit, enemy, 10, 1, 5)
        self.assertEqual(result['baseline']['win'], 10)
        timeout = core.compare_duel(enemy, enemy, enemy, 10, 3, 5)
        self.assertEqual(timeout['baseline']['timeout'], 10)

    def test_bad_numbers(self):
        with self.assertRaises(ValueError):
            core.compare_duel(dict(self.unit, hp=float('nan')), self.unit, self.unit, 10, 2, 0)

if __name__ == '__main__':
    unittest.main()
