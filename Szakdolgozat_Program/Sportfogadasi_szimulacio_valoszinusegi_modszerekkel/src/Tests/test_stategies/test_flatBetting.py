import unittest
from src.Backend.strategies.flatBetting import flat_betting


class TestFlatBettingStrategy(unittest.TestCase):

    def setUp(self):
        self.default_bankroll = 1000

    def test_flat_betting_all_wins(self):
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': True, 'odds': 1.5},
            {'won': True, 'odds': 3.0}
        ]
        stake = 50

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=self.default_bankroll)

        self.assertEqual(bankroll[0], 1000)
        self.assertEqual(stakes, [50, 50, 50])
        self.assertEqual(bankroll[1], 1050)   # +50
        self.assertEqual(bankroll[2], 1075)   # +25
        self.assertEqual(bankroll[3], 1175)   # +100

    def test_flat_betting_all_losses(self):
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 1.5},
            {'won': False, 'odds': 3.0}
        ]
        stake = 25

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=self.default_bankroll)

        self.assertEqual(stakes, [25, 25, 25])
        self.assertEqual(bankroll[1], 975)
        self.assertEqual(bankroll[2], 950)
        self.assertEqual(bankroll[3], 925)

    def test_flat_betting_mixed_results(self):
        bets = [
            {'won': False, 'odds': 2.0},  # -100 -> 900
            {'won': True, 'odds': 2.5},   # +150 -> 1050
            {'won': False, 'odds': 1.8},  # -100 -> 950
            {'won': True, 'odds': 3.0}    # +200 -> 1150
        ]
        stake = 100

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=self.default_bankroll)

        self.assertEqual(stakes, [100, 100, 100, 100])
        self.assertEqual(bankroll[1], 900)
        self.assertEqual(bankroll[2], 1050)
        self.assertEqual(bankroll[3], 950)
        self.assertEqual(bankroll[4], 1150)

    def test_flat_betting_custom_initial_bankroll(self):
        bets = [
            {'won': True, 'odds': 2.0},   # +200 -> 2200
            {'won': False, 'odds': 2.0}   # -200 -> 2000
        ]
        stake = 200
        initial_bankroll = 2000

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=initial_bankroll)

        self.assertEqual(bankroll[0], 2000)
        self.assertEqual(stakes, [200, 200])
        self.assertEqual(bankroll[1], 2200)
        self.assertEqual(bankroll[2], 2000)

    def test_flat_betting_empty_bets(self):
        bets = []
        stake = 50

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=self.default_bankroll)

        self.assertEqual(bankroll, [1000])
        self.assertEqual(stakes, [])

    def test_flat_betting_zero_stake(self):
        bets = [
            {'won': True, 'odds': 2.0},
            {'won': False, 'odds': 1.5}
        ]
        stake = 0

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=self.default_bankroll)

        self.assertEqual(stakes, [0, 0])
        self.assertEqual(bankroll, [1000, 1000, 1000])

    def test_flat_betting_low_bankroll_reduction(self):
        """Test when bankroll is not enough to cover the stake"""
        bets = [
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0},
            {'won': False, 'odds': 2.0}
        ]
        stake = 400
        initial_bankroll = 1000

        bankroll, stakes = flat_betting(bets, stake, bankroll_start=initial_bankroll)

        # Stake may drop on last bet if bankroll insufficient
        self.assertEqual(bankroll[0], 1000)
        self.assertEqual(stakes[0], 400)  # 600
        self.assertEqual(stakes[1], 400)  # 200
        self.assertEqual(stakes[2], 200)  # 0
        self.assertEqual(stakes[3], 0)    # 0
        self.assertEqual(bankroll[-1], 0)


if __name__ == '__main__':
    unittest.main()
