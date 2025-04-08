import unittest

from src.Backend.strategies.martingale import martingale


class TestMartingaleStrategy(unittest.TestCase):

    def test_martingale_all_wins(self):
        """Test martingale strategy with all winning bets"""
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 1.5},
            {'won': True, 'odds': 3.0}
        ]
        base_stake = 10

        bankroll, stakes = martingale(bets, base_stake)

        # Check initial bankroll
        self.assertEqual(bankroll[0], 1000)

        # Check stakes - should always be base_stake after a win
        self.assertEqual(stakes, [10, 10, 10])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: +10 (2.0-1) = +10 -> 1010
        # Bet 2: +10 (1.5-1) = +5 -> 1015
        # Bet 3: +10 (3.0-1) = +20 -> 1035
        self.assertEqual(bankroll[1], 1010)
        self.assertEqual(bankroll[2], 1015)
        self.assertEqual(bankroll[3], 1035)

    def test_martingale_all_losses(self):
        """Test martingale strategy with all losing bets"""
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 1.5},
            {'won': False, 'odds': 3.0}
        ]
        base_stake = 20

        bankroll, stakes = martingale(bets, base_stake)

        # Check stakes - should double after each loss
        self.assertEqual(stakes, [20, 40, 80])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: -20 -> 980
        # Bet 2: -40 -> 940
        # Bet 3: -80 -> 860
        self.assertEqual(bankroll[1], 980)
        self.assertEqual(bankroll[2], 940)
        self.assertEqual(bankroll[3], 860)

    def test_martingale_mixed_results(self):
        """Test martingale strategy with mixed winning and losing bets"""
        bets = [
            {'won': False, 'odds': 2.0},  # Lose - double stake
            {'won': False, 'odds': 1.5},  # Lose - double stake again
            {'won': True, 'odds': 2.0},  # Win - reset to base stake
            {'won': False, 'odds': 3.0},  # Lose - double stake
            {'won': True, 'odds': 1.5}  # Win - reset to base stake
        ]
        base_stake = 10

        bankroll, stakes = martingale(bets, base_stake)

        # Check stakes progression
        # First bet: 10 (base)
        # Second bet: 20 (double after loss)
        # Third bet: 40 (double after loss)
        # Fourth bet: 10 (reset after win)
        # Fifth bet: 20 (double after loss)
        self.assertEqual(stakes, [10, 20, 40, 10, 20])

        # Check bankroll calculations
        # Initial: 1000
        # Bet 1: -10 -> 990
        # Bet 2: -20 -> 970
        # Bet 3: +40 * (2.0-1) = +40 -> 1010
        # Bet 4: -10 -> 1000
        # Bet 5: +20 * (1.5-1) = +10 -> 1010
        self.assertEqual(bankroll[1], 990)
        self.assertEqual(bankroll[2], 970)
        self.assertEqual(bankroll[3], 1010)
        self.assertEqual(bankroll[4], 1000)
        self.assertEqual(bankroll[5], 1010)

    def test_martingale_long_losing_streak(self):
        """Test martingale strategy with a long losing streak"""
        bets = [{'won': False, 'odds': 2.0} for _ in range(6)]
        base_stake = 10

        bankroll, stakes = martingale(bets, base_stake)

        # Check stakes progression - doubles each time
        # 10, 20, 40, 80, 160, 320
        self.assertEqual(stakes, [10, 20, 40, 80, 160, 320])

        # Check final bankroll
        # Initial: 1000
        # Losses: -10 -20 -40 -80 -160 -320 = -630
        # Final: 1000 - 630 = 370
        self.assertEqual(bankroll[-1], 370)

    def test_martingale_win_after_losing_streak(self):
        """Test martingale recovery after a losing streak"""
        bets = [
            {'won': False, 'odds': 2.0},  # Lose
            {'won': False, 'odds': 2.0},  # Lose
            {'won': False, 'odds': 2.0},  # Lose
            {'won': True, 'odds': 2.0}  # Win
        ]
        base_stake = 10

        bankroll, stakes = martingale(bets, base_stake)

        # Check stakes progression
        # 10, 20, 40, 80
        self.assertEqual(stakes, [10, 20, 40, 80])

        # Check bankroll
        # Initial: 1000
        # Losses: -10 -20 -40 = -70
        # Win: +80 * (2.0-1) = +80
        # Final: 1000 - 70 + 80 = 1010
        self.assertEqual(bankroll[-1], 1010)

        # Verify that a single win recovers all previous losses plus one base stake profit
        total_lost = sum(stakes[:-1])
        win_amount = stakes[-1] * (bets[-1]['odds'] - 1)
        self.assertEqual(win_amount, total_lost + base_stake)

    def test_martingale_empty_bets(self):
        """Test martingale strategy with no bets"""
        bets = []
        base_stake = 10

        bankroll, stakes = martingale(bets, base_stake)

        # Only initial bankroll should be present
        self.assertEqual(bankroll, [1000])

        # No stakes should be used
        self.assertEqual(stakes, [])


if __name__ == '__main__':
    unittest.main()