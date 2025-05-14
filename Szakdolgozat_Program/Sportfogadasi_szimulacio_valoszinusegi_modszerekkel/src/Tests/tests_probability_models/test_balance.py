import unittest
from unittest.mock import patch
from src.Backend.probability_models.balance_model import (
    calculate_weighted_form_multiplicative,
    predict_with_balance_model
)


class TestBalanceModel(unittest.TestCase):

    def setUp(self):
        self.valid_matches = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 0},  # win
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 1, 'score_away': 1},  # draw
            {'home_team_id': 4, 'away_team_id': 1, 'score_home': 3, 'score_away': 1},  # loss
        ]
        self.invalid_matches = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': None, 'score_away': None}
        ]

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_calculate_weighted_form_multiplicative_valid(self, mock_get_last_matches):
        mock_get_last_matches.return_value = self.valid_matches
        probs = calculate_weighted_form_multiplicative(1, num_matches=3, decay_factor=1.0)
        self.assertIsNotNone(probs)
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=5)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_calculate_weighted_form_multiplicative_empty(self, mock_get_last_matches):
        mock_get_last_matches.return_value = []
        result = calculate_weighted_form_multiplicative(1)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_calculate_weighted_form_multiplicative_invalid_scores(self, mock_get_last_matches):
        mock_get_last_matches.return_value = self.invalid_matches
        result = calculate_weighted_form_multiplicative(1)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_predict_with_balance_model_valid(self, mock_get_last_matches):
        mock_get_last_matches.return_value = self.valid_matches
        result = predict_with_balance_model(1, 2, num_matches=3, decay_factor=1.0)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(sum(result.values()), 100.0, places=2)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_predict_with_balance_model_missing_data(self, mock_get_last_matches):
        mock_get_last_matches.return_value = []
        result = predict_with_balance_model(1, 2)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_predict_with_balance_model_only_home_data(self, mock_get_last_matches):
        def side_effect(team_id, *_):
            return self.valid_matches if team_id == 1 else []

        mock_get_last_matches.side_effect = side_effect
        result = predict_with_balance_model(1, 2)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_predict_with_balance_model_only_away_data(self, mock_get_last_matches):
        def side_effect(team_id, *_):
            return self.valid_matches if team_id == 2 else []

        mock_get_last_matches.side_effect = side_effect
        result = predict_with_balance_model(1, 2)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.balance_model.get_last_matches')
    def test_predict_with_decay_effect(self, mock_get_last_matches):
        mock_get_last_matches.return_value = self.valid_matches
        for decay in [0.5, 0.8, 0.9, 1.0]:
            with self.subTest(decay=decay):
                result = predict_with_balance_model(1, 2, decay_factor=decay)
                self.assertIsNotNone(result)
                self.assertAlmostEqual(sum(result.values()), 100.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
