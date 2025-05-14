import unittest
from src.Backend.strategies.fibonacci import fibonacci


class TestBettingStrategies(unittest.TestCase):

    def setUp(self):
        self.base_stake = 10
        self.starting_bankroll = 1000

    def test_fibonacci_all_wins(self):
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 1.5},
            {'won': True, 'odds': 3.0}
        ]

        bankroll, stakes = fibonacci(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll[0], 1000)
        self.assertEqual(stakes, [10, 10, 10])
        self.assertEqual(bankroll[1], 1010)  # +10
        self.assertEqual(bankroll[2], 1015)  # +5
        self.assertEqual(bankroll[3], 1035)  # +20

    def test_fibonacci_all_losses(self):
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 1.5},
            {'won': False, 'odds': 3.0},
            {'won': False, 'odds': 2.5}
        ]

        bankroll, stakes = fibonacci(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [10, 10, 20, 30])
        self.assertEqual(bankroll[1], 990)
        self.assertEqual(bankroll[2], 980)
        self.assertEqual(bankroll[3], 960)
        self.assertEqual(bankroll[4], 930)

    def test_fibonacci_mixed_results(self):
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': True, 'odds': 2.5},
            {'won': False, 'odds': 1.8},
            {'won': True, 'odds': 3.0}
        ]

        bankroll, stakes = fibonacci(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [10, 10, 20, 10, 10])
        self.assertEqual(bankroll[1], 990)
        self.assertEqual(bankroll[2], 980)
        self.assertEqual(bankroll[3], 1010)
        self.assertEqual(bankroll[4], 1000)
        self.assertEqual(bankroll[5], 1020)

    def test_fibonacci_index_reset_to_zero(self):
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 2.0}
        ]

        bankroll, stakes = fibonacci(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [10, 10])
        self.assertEqual(bankroll[1], 1010)
        self.assertEqual(bankroll[2], 1020)

    def test_fibonacci_extended_sequence(self):
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': True, 'odds': 2.0}
        ]

        bankroll, stakes = fibonacci(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        expected_stakes = [10, 10, 20, 30, 50, 80]
        self.assertEqual(stakes, expected_stakes)

        final_expected_bankroll = 1000 - 10 - 10 - 20 - 30 - 50 + 80
        self.assertEqual(bankroll[-1], final_expected_bankroll)

    def test_fibonacci_custom_base_stake(self):
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': True, 'odds': 2.0}
        ]

        base_stake = 25
        bankroll, stakes = fibonacci(bets, base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [25, 25, 50])
        final_expected_bankroll = 1000 - 25 - 25 + 50
        self.assertEqual(bankroll[-1], final_expected_bankroll)

    def test_fibonacci_empty_bets(self):
        bets = []

        bankroll, stakes = fibonacci(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll, [1000])
        self.assertEqual(stakes, [])


if __name__ == '__main__':
    unittest.main()
