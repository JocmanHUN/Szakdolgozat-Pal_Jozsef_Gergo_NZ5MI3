import unittest
from src.Backend.strategies.martingale import martingale


class TestMartingaleStrategy(unittest.TestCase):

    def setUp(self):
        self.base_stake = 10
        self.starting_bankroll = 1000

    def test_martingale_all_wins(self):
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 1.5},
            {'won': True, 'odds': 3.0}
        ]

        bankroll, stakes = martingale(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll[0], 1000)
        self.assertEqual(stakes, [10, 10, 10])
        self.assertEqual(bankroll[1], 1010)
        self.assertEqual(bankroll[2], 1015)
        self.assertEqual(bankroll[3], 1035)

    def test_martingale_all_losses(self):
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 1.5},
            {'won': False, 'odds': 3.0}
        ]
        base_stake = 20

        bankroll, stakes = martingale(bets, base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [20, 40, 80])
        self.assertEqual(bankroll[1], 980)
        self.assertEqual(bankroll[2], 940)
        self.assertEqual(bankroll[3], 860)

    def test_martingale_mixed_results(self):
        bets = [
            {'won': False, 'odds': 2.0},  # -10 -> 990
            {'won': False, 'odds': 1.5},  # -20 -> 970
            {'won': True,  'odds': 2.0},  # +40 -> 1010
            {'won': False, 'odds': 3.0},  # -10 -> 1000
            {'won': True,  'odds': 1.5}   # +10 -> 1010
        ]

        bankroll, stakes = martingale(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [10, 20, 40, 10, 20])
        self.assertEqual(bankroll[1], 990)
        self.assertEqual(bankroll[2], 970)
        self.assertEqual(bankroll[3], 1010)
        self.assertEqual(bankroll[4], 1000)
        self.assertEqual(bankroll[5], 1010)

    def test_martingale_long_losing_streak(self):
        bets = [{'won': False, 'odds': 2.0} for _ in range(6)]
        base_stake = 10

        bankroll, stakes = martingale(bets, base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [10, 20, 40, 80, 160, 320])
        expected_final = 1000 - sum(stakes)
        self.assertEqual(bankroll[-1], expected_final)
        self.assertEqual(bankroll[-1], 370)

    def test_martingale_win_after_losing_streak(self):
        bets = [
            {'won': False, 'odds': 2.0},  # -10
            {'won': False, 'odds': 2.0},  # -20
            {'won': False, 'odds': 2.0},  # -40
            {'won': True,  'odds': 2.0}   # +80
        ]

        bankroll, stakes = martingale(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(stakes, [10, 20, 40, 80])
        self.assertEqual(bankroll[-1], 1010)  # 1000 - 70 + 80

        # Check win recovery logic
        total_lost = sum(stakes[:-1])
        win_profit = stakes[-1] * (bets[-1]['odds'] - 1)
        self.assertEqual(win_profit, total_lost + self.base_stake)

    def test_martingale_empty_bets(self):
        bets = []

        bankroll, stakes = martingale(bets, self.base_stake, bankroll_start=self.starting_bankroll)

        self.assertEqual(bankroll, [1000])
        self.assertEqual(stakes, [])


if __name__ == '__main__':
    unittest.main()
