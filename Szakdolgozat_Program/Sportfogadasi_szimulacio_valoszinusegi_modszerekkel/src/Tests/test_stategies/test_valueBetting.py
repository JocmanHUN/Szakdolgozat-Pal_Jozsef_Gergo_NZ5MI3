import unittest
from src.Backend.strategies.valueBetting import value_betting


class TestValueBettingStrategy(unittest.TestCase):

    def setUp(self):
        self.starting_bankroll = 1000

    def test_value_betting_all_positive_ev(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 60},
            {'won': False, 'odds': 3.0, 'model_probability': 40}
        ]
        stake = 100

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll[0], 1000)
        self.assertEqual(stakes, [100, 100])
        self.assertEqual(bankroll[1], 1100)
        self.assertEqual(bankroll[2], 1000)

    def test_value_betting_all_negative_ev(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 40},
            {'won': False, 'odds': 1.5, 'model_probability': 60}
        ]
        stake = 50

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [0, 0])
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_value_betting_mixed_ev(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 60},   # value: 1.2 > 1
            {'won': False, 'odds': 1.5, 'model_probability': 50},  # value: 0.75
            {'won': True, 'odds': 3.0, 'model_probability': 40}    # value: 1.2 > 1
        ]
        stake = 200

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [200, 0, 200])
        self.assertEqual(bankroll[1], 1200)
        self.assertEqual(bankroll[2], 1200)
        self.assertEqual(bankroll[3], 1600)

    def test_value_betting_borderline_cases(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 50},    # EV = 1.0 (edge)
            {'won': False, 'odds': 2.0, 'model_probability': 50.1}, # EV = 1.002 > 1
            {'won': True, 'odds': 2.0, 'model_probability': 49.9}   # EV = 0.998 < 1
        ]
        stake = 75

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [0, 75, 0])
        self.assertEqual(bankroll[1], 1000)
        self.assertEqual(bankroll[2], 925)
        self.assertEqual(bankroll[3], 925)

    def test_value_betting_high_odds(self):
        bets = [
            {'won': False, 'odds': 10.0, 'model_probability': 15},  # EV = 1.5
            {'won': True, 'odds': 7.0, 'model_probability': 10}     # EV = 0.7
        ]
        stake = 50

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [50, 0])
        self.assertEqual(bankroll[1], 950)
        self.assertEqual(bankroll[2], 950)

    def test_value_betting_equal_probabilities(self):
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 50},
            {'won': False, 'odds': 4.0, 'model_probability': 25}
        ]
        stake = 100

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [0, 0])
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_value_betting_empty_bets(self):
        bets = []
        stake = 50

        bankroll, stakes = value_betting(bets, stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll, [1000])
        self.assertEqual(stakes, [])


if __name__ == '__main__':
    unittest.main()
