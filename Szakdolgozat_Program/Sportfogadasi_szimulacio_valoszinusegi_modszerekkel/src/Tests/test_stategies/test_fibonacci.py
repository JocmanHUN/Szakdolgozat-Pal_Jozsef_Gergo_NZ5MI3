import unittest

from src.Backend.strategies.fibonacci import fibonacci


class TestBettingStrategies(unittest.TestCase):

    def test_fibonacci_all_wins(self):
        """Test Fibonacci strategy with all winning bets"""
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 1.5},
            {'won': True, 'odds': 3.0}
        ]
        base_stake = 10

        bankroll, stakes = fibonacci(bets, base_stake)

        # Check initial bankroll
        self.assertEqual(bankroll[0], 1000)

        # Check stakes used - should reset after each win
        self.assertEqual(stakes, [10, 10, 10])

        # Check final bankroll calculations
        # Initial: 1000
        # Bet 1: +10 (2.0-1) = +10 -> 1010
        # Bet 2: +10 (1.5-1) = +5 -> 1015
        # Bet 3: +10 (3.0-1) = +20 -> 1035
        self.assertEqual(bankroll[1], 1010)
        self.assertEqual(bankroll[2], 1015)
        self.assertEqual(bankroll[3], 1035)

    def test_fibonacci_all_losses(self):
        """Test Fibonacci strategy with all losing bets"""
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 1.5},
            {'won': False, 'odds': 3.0},
            {'won': False, 'odds': 2.5}
        ]
        base_stake = 10

        bankroll, stakes = fibonacci(bets, base_stake)

        # Check stakes progression follows Fibonacci sequence
        # Starting with [10, 10], then adding next Fibonacci numbers
        self.assertEqual(stakes, [10, 10, 20, 30])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: -10 -> 990
        # Bet 2: -10 -> 980
        # Bet 3: -20 -> 960
        # Bet 4: -30 -> 930
        self.assertEqual(bankroll[1], 990)
        self.assertEqual(bankroll[2], 980)
        self.assertEqual(bankroll[3], 960)
        self.assertEqual(bankroll[4], 930)

    def test_fibonacci_mixed_results(self):
        """Test Fibonacci strategy with mixed winning and losing bets"""
        bets = [
            {'won': False, 'odds': 2.0},  # Lose - progress to next Fibonacci
            {'won': False, 'odds': 2.0},  # Lose - progress to next Fibonacci
            {'won': True, 'odds': 2.5},  # Win - go back 2 steps
            {'won': False, 'odds': 1.8},  # Lose - progress to next Fibonacci
            {'won': True, 'odds': 3.0}  # Win - go back 2 steps
        ]
        base_stake = 10

        bankroll, stakes = fibonacci(bets, base_stake)

        # Check stakes progression
        # First bet: 10 (base)
        # Second bet: 10 (next in sequence after loss)
        # Third bet: 20 (next in sequence after loss)
        # Fourth bet: 10 (reset 2 steps after win)
        # Fifth bet: 10 (reset 2 steps after win)
        self.assertEqual(stakes, [10, 10, 20, 10, 10])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: -10 -> 990
        # Bet 2: -10 -> 980
        # Bet 3: +20 * (2.5-1) = +30 -> 1010
        # Bet 4: -10 -> 1000
        # Bet 5: +10 * (3.0-1) = +20 -> 1020
        self.assertEqual(bankroll[1], 990)
        self.assertEqual(bankroll[2], 980)
        self.assertEqual(bankroll[3], 1010)
        self.assertEqual(bankroll[4], 1000)
        self.assertEqual(bankroll[5], 1020)

    def test_fibonacci_index_reset_to_zero(self):
        """Test Fibonacci strategy when index would reset below 0"""
        bets = [
            {'won': True, 'odds': 2.0},  # Win - try to go back 2 steps (which would be -1)
            {'won': True, 'odds': 2.0}  # Win - try to go back 2 steps (which would be -1)
        ]
        base_stake = 10

        bankroll, stakes = fibonacci(bets, base_stake)

        # Check that stakes don't go below the base value
        self.assertEqual(stakes, [10, 10])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: +10 * (2.0-1) = +10 -> 1010
        # Bet 2: +10 * (2.0-1) = +10 -> 1020
        self.assertEqual(bankroll[1], 1010)
        self.assertEqual(bankroll[2], 1020)

    def test_fibonacci_extended_sequence(self):
        """Test Fibonacci strategy with enough losses to extend the sequence"""
        bets = [
            {'won': False, 'odds': 2.0},  # Lose - progress to next (index 1)
            {'won': False, 'odds': 2.0},  # Lose - progress to next (index 2)
            {'won': False, 'odds': 2.0},  # Lose - progress to next (index 3)
            {'won': False, 'odds': 2.0},  # Lose - progress to next (index 4)
            {'won': False, 'odds': 2.0},  # Lose - progress to next (index 5)
            {'won': True, 'odds': 2.0}  # Win - go back 2 steps (index 3)
        ]
        base_stake = 10

        bankroll, stakes = fibonacci(bets, base_stake)

        # Expected Fibonacci sequence: [10, 10, 20, 30, 50, 80]
        expected_stakes = [10, 10, 20, 30, 50, 80]

        # Check that stakes follow the expected sequence
        self.assertEqual(stakes, expected_stakes)

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1-5: Losses
        # Bet 6: +80 * (2.0-1) = +80
        final_expected_bankroll = 1000 - 10 - 10 - 20 - 30 - 50 + 80
        self.assertEqual(bankroll[-1], final_expected_bankroll)

    def test_fibonacci_custom_base_stake(self):
        """Test Fibonacci strategy with custom base stake"""
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': True, 'odds': 2.0}
        ]
        base_stake = 25

        bankroll, stakes = fibonacci(bets, base_stake)

        # Expected stakes with base_stake = 25
        expected_stakes = [25, 25, 50]

        # Check that stakes use the custom base value
        self.assertEqual(stakes, expected_stakes)

        # Final bankroll should reflect the custom stake
        final_expected_bankroll = 1000 - 25 - 25 + 50
        self.assertEqual(bankroll[-1], final_expected_bankroll)

    def test_fibonacci_empty_bets(self):
        """Test Fibonacci strategy with no bets"""
        bets = []
        base_stake = 10

        bankroll, stakes = fibonacci(bets, base_stake)

        # Only initial bankroll should be present
        self.assertEqual(bankroll, [1000])

        # No stakes should be used
        self.assertEqual(stakes, [])


if __name__ == '__main__':
    unittest.main()