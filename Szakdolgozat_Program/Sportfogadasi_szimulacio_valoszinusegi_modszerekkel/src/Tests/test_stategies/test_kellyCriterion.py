import unittest
from src.Backend.strategies.kellyCriterion import kelly_criterion


class TestKellyCriterionStrategy(unittest.TestCase):

    def setUp(self):
        self.starting_bankroll = 1000
        self.fractional = 0.25

    def test_kelly_criterion_favorable_bets(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 60},
            {'won': False, 'odds': 3.0, 'model_probability': 50}
        ]

        bankroll, stakes = kelly_criterion(bets, bankroll_start=self.starting_bankroll, fractional=self.fractional)

        self.assertEqual(bankroll[0], 1000)

        # Bet 1:
        # b = 1.0, p = 0.6, q = 0.4
        # raw_fraction = (1.0*0.6 - 0.4)/1.0 = 0.2
        # stake = 1000 * 0.2 * 0.25 = 50
        expected_stake1 = 1000 * 0.2 * 0.25
        self.assertAlmostEqual(stakes[0], expected_stake1, delta=0.01)
        self.assertAlmostEqual(bankroll[1], 1000 - expected_stake1 + expected_stake1 * 2.0, delta=0.01)

        # Bet 2:
        # b = 2.0, p = 0.5, q = 0.5
        # raw_fraction = (2.0*0.5 - 0.5)/2.0 = 0.25
        # stake = bankroll[1] * 0.25 * 0.25
        expected_stake2 = bankroll[1] * 0.25 * 0.25
        self.assertAlmostEqual(stakes[1], expected_stake2, delta=0.01)
        self.assertAlmostEqual(bankroll[2], bankroll[1] - expected_stake2, delta=0.01)

    def test_kelly_criterion_unfavorable_bets(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 40},
            {'won': False, 'odds': 1.5, 'model_probability': 50}
        ]

        bankroll, stakes = kelly_criterion(bets, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [0, 0])
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_kelly_criterion_zero_odds(self):
        bets = [
            {'won': True, 'odds': 0, 'model_probability': 50},
            {'won': True, 'odds': -1.0, 'model_probability': 50}
        ]

        bankroll, stakes = kelly_criterion(bets, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [0, 0])
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_kelly_criterion_mixed_bets(self):
        bets = [
            {'won': True, 'odds': 2.5, 'model_probability': 60},
            {'won': False, 'odds': 2.0, 'model_probability': 30},
            {'won': True, 'odds': 1.8, 'model_probability': 70}
        ]

        bankroll, stakes = kelly_criterion(bets, bankroll_start=self.starting_bankroll)

        self.assertGreater(stakes[0], 0)
        self.assertEqual(stakes[1], 0)
        self.assertGreater(stakes[2], 0)

        self.assertGreater(bankroll[1], bankroll[0])
        self.assertEqual(bankroll[2], bankroll[1])
        self.assertGreater(bankroll[3], bankroll[2])

    def test_kelly_criterion_custom_bankroll(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 60}
        ]
        initial_bankroll = 5000

        bankroll, stakes = kelly_criterion(bets, bankroll_start=initial_bankroll)

        self.assertEqual(bankroll[0], 5000)
        expected_stake = 5000 * 0.2 * 0.25
        self.assertAlmostEqual(stakes[0], expected_stake, delta=0.01)

    def test_kelly_criterion_empty_bets(self):
        bets = []

        bankroll, stakes = kelly_criterion(bets, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll, [1000])
        self.assertEqual(stakes, [])

    def test_kelly_criterion_extreme_probabilities(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 100},
            {'won': False, 'odds': 5.0, 'model_probability': 0}
        ]

        bankroll, stakes = kelly_criterion(bets, bankroll_start=self.starting_bankroll)

        self.assertAlmostEqual(stakes[0], 1000 * 1.0 * 0.25, delta=0.01)
        self.assertEqual(stakes[1], 0)


if __name__ == '__main__':
    unittest.main()
