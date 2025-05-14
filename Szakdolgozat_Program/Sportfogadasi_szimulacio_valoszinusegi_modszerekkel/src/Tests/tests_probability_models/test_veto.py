import unittest
from unittest.mock import patch

from src.Backend.probability_models.veto_model import calculate_weighted_form_probabilities, predict_with_veto_model


class TestProbabilityModels(unittest.TestCase):

    @patch('src.Backend.probability_models.veto_model.get_last_matches')
    def test_calculate_prior_probabilities_no_matches(self, mock_get_last_matches):
        mock_get_last_matches.return_value = []
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)
        self.assertIsNone(priors)
        self.assertEqual(num_matches, 0)
        mock_get_last_matches.assert_called_once_with(1, 10)

    @patch('src.Backend.probability_models.veto_model.get_last_matches')
    def test_calculate_prior_probabilities_no_valid_matches(self, mock_get_last_matches):
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': None, 'score_away': None},
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': None, 'score_away': None}
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)
        self.assertIsNone(priors)
        self.assertEqual(num_matches, 0)

    @patch('src.Backend.probability_models.veto_model.get_last_matches')
    def test_calculate_prior_probabilities_all_wins(self, mock_get_last_matches):
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 0},
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 1, 'score_away': 0}
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)
        self.assertEqual(num_matches, 2)
        self.assertAlmostEqual(priors['win'], 1.0)
        self.assertAlmostEqual(priors['draw'], 0.0)
        self.assertAlmostEqual(priors['loss'], 0.0)

    @patch('src.Backend.probability_models.veto_model.get_last_matches')
    def test_calculate_prior_probabilities_all_losses(self, mock_get_last_matches):
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 0, 'score_away': 2},
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': 3, 'score_away': 1}
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)
        self.assertEqual(num_matches, 2)
        self.assertAlmostEqual(priors['win'], 0.0)
        self.assertAlmostEqual(priors['draw'], 0.0)
        self.assertAlmostEqual(priors['loss'], 1.0)

    @patch('src.Backend.probability_models.veto_model.get_last_matches')
    def test_calculate_prior_probabilities_mixed_results(self, mock_get_last_matches):
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 0},  # win
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': 1, 'score_away': 1},  # draw
            {'home_team_id': 1, 'away_team_id': 4, 'score_home': 0, 'score_away': 3}   # loss
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10, decay_factor=1.0)
        self.assertEqual(num_matches, 3)
        self.assertAlmostEqual(priors['win'], 1 / 3)
        self.assertAlmostEqual(priors['draw'], 1 / 3)
        self.assertAlmostEqual(priors['loss'], 1 / 3)

    @patch('src.Backend.probability_models.veto_model.get_last_matches')
    def test_calculate_prior_probabilities_with_decay(self, mock_get_last_matches):
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 0, 'score_away': 1},  # loss (oldest)
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 1, 'score_away': 1},  # draw
            {'home_team_id': 1, 'away_team_id': 4, 'score_home': 2, 'score_away': 0}   # win (newest)
        ]
        decay_factor = 0.5
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10, decay_factor=decay_factor)
        self.assertEqual(num_matches, 3)
        self.assertAlmostEqual(priors['win'], 0.571, places=3)
        self.assertAlmostEqual(priors['draw'], 0.286, places=3)
        self.assertAlmostEqual(priors['loss'], 0.143, places=3)

    @patch('src.Backend.probability_models.veto_model.calculate_weighted_form_probabilities')
    def test_predict_with_veto_model_no_data(self, mock_calc_priors):
        mock_calc_priors.side_effect = [(None, 0), (None, 0)]
        result = predict_with_veto_model(1, 2)
        self.assertIsNone(result)

        mock_calc_priors.side_effect = [(None, 0), ({"win": 0.5, "draw": 0.3, "loss": 0.2}, 5)]
        result = predict_with_veto_model(1, 2)
        self.assertIsNone(result)

        mock_calc_priors.side_effect = [({"win": 0.6, "draw": 0.2, "loss": 0.2}, 10), (None, 0)]
        result = predict_with_veto_model(1, 2)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.veto_model.calculate_weighted_form_probabilities')
    def test_predict_with_veto_model_calculation(self, mock_calc_priors):
        home_priors = {"win": 0.6, "draw": 0.2, "loss": 0.2}
        away_priors = {"win": 0.5, "draw": 0.3, "loss": 0.2}
        mock_calc_priors.side_effect = [(home_priors, 10), (away_priors, 10)]
        result = predict_with_veto_model(1, 2)

        self.assertEqual(result["1"], 40.0)
        self.assertEqual(result["X"], 33.33)
        self.assertEqual(result["2"], 26.67)

    @patch('src.Backend.probability_models.veto_model.calculate_weighted_form_probabilities')
    def test_predict_with_veto_model_different_match_counts(self, mock_calc_priors):
        home_priors = {"win": 0.7, "draw": 0.2, "loss": 0.1}
        away_priors = {"win": 0.4, "draw": 0.4, "loss": 0.2}
        mock_calc_priors.side_effect = [(home_priors, 15), (away_priors, 5)]
        result = predict_with_veto_model(1, 2)

        self.assertEqual(result["1"], 53.16)
        self.assertEqual(result["X"], 31.65)
        self.assertEqual(result["2"], 15.19)


if __name__ == '__main__':
    unittest.main()
