import unittest

from src.Backend.strategies.flatBetting import flat_betting


class TestFlatBettingStrategy(unittest.TestCase):

    def test_flat_betting_all_wins(self):
        """Test flat betting strategy with all winning bets"""
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 1.5},
            {'won': True, 'odds': 3.0}
        ]
        stake = 50

        bankroll, stakes = flat_betting(bets, stake)

        # Check initial bankroll
        self.assertEqual(bankroll[0], 1000)

        # Check stakes used - should be constant
        self.assertEqual(stakes, [50, 50, 50])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: +50 (2.0-1) = +50 -> 1050
        # Bet 2: +50 (1.5-1) = +25 -> 1075
        # Bet 3: +50 (3.0-1) = +100 -> 1175
        self.assertEqual(bankroll[1], 1050)
        self.assertEqual(bankroll[2], 1075)
        self.assertEqual(bankroll[3], 1175)

    def test_flat_betting_all_losses(self):
        """Test flat betting strategy with all losing bets"""
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 1.5},
            {'won': False, 'odds': 3.0}
        ]
        stake = 25

        bankroll, stakes = flat_betting(bets, stake)

        # Check stakes - should all be the same
        self.assertEqual(stakes, [25, 25, 25])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: -25 -> 975
        # Bet 2: -25 -> 950
        # Bet 3: -25 -> 925
        self.assertEqual(bankroll[1], 975)
        self.assertEqual(bankroll[2], 950)
        self.assertEqual(bankroll[3], 925)

    def test_flat_betting_mixed_results(self):
        """Test flat betting strategy with mixed winning and losing bets"""
        bets = [
            {'won': False, 'odds': 2.0},  # Lose
            {'won': True, 'odds': 2.5},  # Win
            {'won': False, 'odds': 1.8},  # Lose
            {'won': True, 'odds': 3.0}  # Win
        ]
        stake = 100

        bankroll, stakes = flat_betting(bets, stake)

        # Check stakes - should all be the same
        self.assertEqual(stakes, [100, 100, 100, 100])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: -100 -> 900
        # Bet 2: +100 * (2.5-1) = +150 -> 1050
        # Bet 3: -100 -> 950
        # Bet 4: +100 * (3.0-1) = +200 -> 1150
        self.assertEqual(bankroll[1], 900)
        self.assertEqual(bankroll[2], 1050)
        self.assertEqual(bankroll[3], 950)
        self.assertEqual(bankroll[4], 1150)

    def test_flat_betting_custom_initial_bankroll(self):
        """Test flat betting with a custom initial bankroll"""
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': False, 'odds': 2.0}
        ]
        stake = 200
        initial_bankroll = 2000

        bankroll, stakes = flat_betting(bets, stake, initial_bankroll)

        # Check initial bankroll is custom value
        self.assertEqual(bankroll[0], 2000)

        # Check bankroll calculations with custom initial value
        # Initial: 2000
        # Bet 1: +200 * (2.0-1) = +200 -> 2200
        # Bet 2: -200 -> 2000
        self.assertEqual(bankroll[1], 2200)
        self.assertEqual(bankroll[2], 2000)

    def test_flat_betting_empty_bets(self):
        """Test flat betting strategy with no bets"""
        bets = []
        stake = 50

        bankroll, stakes = flat_betting(bets, stake)

        # Only initial bankroll should be present
        self.assertEqual(bankroll, [1000])

        # No stakes should be used
        self.assertEqual(stakes, [])

    def test_flat_betting_zero_stake(self):
        """Test flat betting with zero stake"""
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': False, 'odds': 1.5}
        ]
        stake = 0

        bankroll, stakes = flat_betting(bets, stake)

        # Stakes should all be zero
        self.assertEqual(stakes, [0, 0])

        # Bankroll should not change
        self.assertEqual(bankroll, [1000, 1000, 1000])


if __name__ == '__main__':
    unittest.main()