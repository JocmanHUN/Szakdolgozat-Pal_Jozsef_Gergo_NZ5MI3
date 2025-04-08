import unittest

from src.Backend.strategies.kellyCriterion import kelly_criterion


class TestKellyCriterionStrategy(unittest.TestCase):

    def test_kelly_criterion_favorable_bets(self):
        """Test Kelly criterion with favorable bets (positive expected value)"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.6},  # EV positive, should bet
            {'won': False, 'odds': 3.0, 'model_probability': 0.5}  # EV positive, should bet
        ]

        bankroll, stakes = kelly_criterion(bets)

        # Check initial bankroll
        self.assertEqual(bankroll[0], 1000)

        # Calculate expected stake fractions
        # Bet 1: (2.0-1)*0.6 - (1-0.6))/1.0 = 0.6-0.4/1.0 = 0.2
        # Bet 2: (3.0-1)*0.5 - (1-0.5))/2.0 = 1.0-0.5/2.0 = 0.25
        expected_stake1 = 1000 * 0.2
        expected_stake2 = (1000 + expected_stake1 * 1.0) * 0.25  # Updated bankroll after first bet

        # Allow small float differences
        self.assertAlmostEqual(stakes[0], expected_stake1, delta=0.01)
        self.assertAlmostEqual(stakes[1], expected_stake2, delta=0.01)

        # Check bankroll progression
        # After bet 1: 1000 + 200*1.0 = 1200
        # After bet 2: 1200 - 300 = 900 (assuming stake2 is around 300)
        self.assertAlmostEqual(bankroll[1], 1000 + expected_stake1 * 1.0, delta=0.01)
        self.assertAlmostEqual(bankroll[2], bankroll[1] - expected_stake2, delta=0.01)

    def test_kelly_criterion_unfavorable_bets(self):
        """Test Kelly criterion with unfavorable bets (negative expected value)"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.4},  # EV negative, shouldn't bet
            {'won': False, 'odds': 1.5, 'model_probability': 0.5}  # EV negative, shouldn't bet
        ]

        bankroll, stakes = kelly_criterion(bets)

        # Stakes should be zero for unfavorable bets
        self.assertEqual(stakes, [0, 0])

        # Bankroll should remain unchanged
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_kelly_criterion_zero_odds(self):
        """Test Kelly criterion with zero or negative odds"""
        bets = [
            {'won': True, 'odds': 0, 'model_probability': 0.5},  # Invalid odds
            {'won': True, 'odds': -1.0, 'model_probability': 0.5}  # Invalid odds
        ]

        bankroll, stakes = kelly_criterion(bets)

        # Stakes should be zero for invalid odds
        self.assertEqual(stakes, [0, 0])

        # Bankroll should remain unchanged
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_kelly_criterion_mixed_bets(self):
        """Test Kelly criterion with mixed favorable and unfavorable bets"""
        bets = [
            {'won': True, 'odds': 2.5, 'model_probability': 0.6},  # Favorable (bet)
            {'won': False, 'odds': 2.0, 'model_probability': 0.3},  # Unfavorable (don't bet)
            {'won': True, 'odds': 1.8, 'model_probability': 0.7}  # Favorable (bet)
        ]

        bankroll, stakes = kelly_criterion(bets)

        # Should only bet on the favorable bets (first and third)
        self.assertGreater(stakes[0], 0)
        self.assertEqual(stakes[1], 0)
        self.assertGreater(stakes[2], 0)

        # Verify bankroll progression
        # After bet 1: increase due to win
        # After bet 2: unchanged (no bet)
        # After bet 3: increase due to win
        self.assertGreater(bankroll[1], bankroll[0])
        self.assertEqual(bankroll[2], bankroll[1])
        self.assertGreater(bankroll[3], bankroll[2])

    def test_kelly_criterion_custom_bankroll(self):
        """Test Kelly criterion with custom initial bankroll"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 0.6}
        ]
        initial_bankroll = 5000

        bankroll, stakes = kelly_criterion(bets, initial_bankroll)

        # Initial bankroll should be the custom value
        self.assertEqual(bankroll[0], 5000)

        # Stake should be proportional to initial bankroll
        expected_stake = 5000 * 0.2  # (2.0-1)*0.6 - (1-0.6))/1.0 = 0.2
        self.assertAlmostEqual(stakes[0], expected_stake, delta=0.01)

    def test_kelly_criterion_empty_bets(self):
        """Test Kelly criterion with no bets"""
        bets = []

        bankroll, stakes = kelly_criterion(bets)

        # Only initial bankroll should be present
        self.assertEqual(bankroll, [1000])

        # No stakes should be used
        self.assertEqual(stakes, [])

    def test_kelly_criterion_extreme_probabilities(self):
        """Test Kelly criterion with extreme probabilities"""
        bets = [
            {'won': True, 'odds': 2.0, 'model_probability': 1.0},  # 100% chance to win
            {'won': False, 'odds': 5.0, 'model_probability': 0.0}  # 0% chance to win
        ]

        bankroll, stakes = kelly_criterion(bets)

        # For 100% win chance, Kelly suggests betting 100% of bankroll
        self.assertAlmostEqual(stakes[0], 1000, delta=0.01)

        # For 0% win chance, should bet nothing
        self.assertEqual(stakes[1], 0)


if __name__ == '__main__':
    unittest.main()