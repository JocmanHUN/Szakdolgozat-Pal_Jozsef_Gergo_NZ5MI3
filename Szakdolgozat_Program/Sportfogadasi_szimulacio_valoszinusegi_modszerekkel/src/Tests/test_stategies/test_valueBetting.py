import unittest

from src.Backend.strategies.valueBetting import value_betting


class TestValueBettingStrategy(unittest.TestCase):

    def test_value_betting_all_positive_ev(self):
        """Test value betting strategy with all positive expected value bets"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.6},  # Model: 60%, Bookmaker: 50%
            {'won': False, 'odds': 3.0, 'model_probability': 0.4}  # Model: 40%, Bookmaker: 33.3%
        ]
        stake = 100

        bankroll, stakes = value_betting(bets, stake)

        # Check initial bankroll
        self.assertEqual(bankroll[0], 1000)

        # Both bets have positive EV, so should bet the full stake
        self.assertEqual(stakes, [100, 100])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: +100 * (2.0-1) = +100 -> 1100
        # Bet 2: -100 -> 1000
        self.assertEqual(bankroll[1], 1100)
        self.assertEqual(bankroll[2], 1000)

    def test_value_betting_all_negative_ev(self):
        """Test value betting strategy with all negative expected value bets"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.4},  # Model: 40%, Bookmaker: 50%
            {'won': False, 'odds': 1.5, 'model_probability': 0.6}  # Model: 60%, Bookmaker: 66.7%
        ]
        stake = 50

        bankroll, stakes = value_betting(bets, stake)

        # Should not bet on negative EV bets
        self.assertEqual(stakes, [0, 0])

        # Bankroll should remain unchanged
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_value_betting_mixed_ev(self):
        """Test value betting strategy with mixed EV bets"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.6},  # Positive EV
            {'won': False, 'odds': 1.5, 'model_probability': 0.5},  # Negative EV
            {'won': True, 'odds': 3.0, 'model_probability': 0.4}  # Positive EV
        ]
        stake = 200

        bankroll, stakes = value_betting(bets, stake)

        # Should only bet on positive EV opportunities
        self.assertEqual(stakes, [200, 0, 200])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: +200 * (2.0-1) = +200 -> 1200
        # Bet 2: No bet -> 1200
        # Bet 3: +200 * (3.0-1) = +400 -> 1600
        self.assertEqual(bankroll[1], 1200)
        self.assertEqual(bankroll[2], 1200)
        self.assertEqual(bankroll[3], 1600)

    def test_value_betting_borderline_cases(self):
        """Test value betting strategy with borderline EV cases"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.5},  # EV = 0 (exactly equal probabilities)
            {'won': False, 'odds': 2.0, 'model_probability': 0.501},  # Barely positive EV
            {'won': True, 'odds': 2.0, 'model_probability': 0.499}  # Barely negative EV
        ]
        stake = 75

        bankroll, stakes = value_betting(bets, stake)

        # Should only bet on the positive EV bet (second one)
        self.assertEqual(stakes, [0, 75, 0])

        # Check bankroll calculations
        self.assertEqual(bankroll[1], 1000)  # No bet
        self.assertEqual(bankroll[2], 1000 - 75)  # Loss
        self.assertEqual(bankroll[3], 925)  # No bet

    def test_value_betting_high_odds(self):
        """Test value betting strategy with high odds but low probability"""
        bets = [
            {'won': False, 'odds': 10.0, 'model_probability': 0.15},  # Model: 15%, Bookmaker: 10%
            {'won': True, 'odds': 7.0, 'model_probability': 0.1}  # Model: 10%, Bookmaker: 14.3%
        ]
        stake = 50

        bankroll, stakes = value_betting(bets, stake)

        # First bet has positive EV, second has negative
        self.assertEqual(stakes, [50, 0])

        # Check bankroll after loss on high odds bet
        self.assertEqual(bankroll[1], 950)
        self.assertEqual(bankroll[2], 950)  # No change on second bet

    def test_value_betting_equal_probabilities(self):
        """Test value betting strategy when model and bookmaker probabilities are equal"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.5},  # Model = Bookmaker = 50%
            {'won': False, 'odds': 4.0, 'model_probability': 0.25}  # Model = Bookmaker = 25%
        ]
        stake = 100

        bankroll, stakes = value_betting(bets, stake)

        # No value in either bet (equal probabilities)
        self.assertEqual(stakes, [0, 0])

        # Bankroll should remain unchanged
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_value_betting_empty_bets(self):
        """Test value betting strategy with no bets"""
        bets = []
        stake = 50

        bankroll, stakes = value_betting(bets, stake)

        # Only initial bankroll should be present
        self.assertEqual(bankroll, [1000])

        # No stakes should be used
        self.assertEqual(stakes, [])


if __name__ == '__main__':
    unittest.main()