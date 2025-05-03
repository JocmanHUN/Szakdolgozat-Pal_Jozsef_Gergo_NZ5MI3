import unittest
from unittest.mock import patch

from src.Backend.probability_models.form_average_model import calculate_weighted_form_probabilities, predict_with_form_average_model


class TestProbabilityModels(unittest.TestCase):

    @patch('src.Backend.probability_models.bayes_classic_model.get_last_matches')
    def test_calculate_prior_probabilities_no_matches(self, mock_get_last_matches):
        """Test when no matches are returned"""
        mock_get_last_matches.return_value = []
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)

        self.assertIsNone(priors)
        self.assertEqual(num_matches, 0)
        mock_get_last_matches.assert_called_once_with(1, 10)

    @patch('src.Backend.probability_models.bayes_classic_model.get_last_matches')
    def test_calculate_prior_probabilities_no_valid_matches(self, mock_get_last_matches):
        """Test when matches exist but none have valid scores"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': None, 'score_away': None},
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': None, 'score_away': None}
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)

        self.assertIsNone(priors)
        self.assertEqual(num_matches, 0)

    @patch('src.Backend.probability_models.bayes_classic_model.get_last_matches')
    def test_calculate_prior_probabilities_all_wins(self, mock_get_last_matches):
        """Test when team won all matches"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 0},
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 1, 'score_away': 0}
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)

        self.assertEqual(num_matches, 2)
        self.assertAlmostEqual(priors['win'], 1.0)
        self.assertAlmostEqual(priors['draw'], 0.0)
        self.assertAlmostEqual(priors['loss'], 0.0)

    @patch('src.Backend.probability_models.bayes_classic_model.get_last_matches')
    def test_calculate_prior_probabilities_all_losses(self, mock_get_last_matches):
        """Test when team lost all matches"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 0, 'score_away': 2},
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': 3, 'score_away': 1}
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10)

        self.assertEqual(num_matches, 2)
        self.assertAlmostEqual(priors['win'], 0.0)
        self.assertAlmostEqual(priors['draw'], 0.0)
        self.assertAlmostEqual(priors['loss'], 1.0)

    @patch('src.Backend.probability_models.bayes_classic_model.get_last_matches')
    def test_calculate_prior_probabilities_mixed_results(self, mock_get_last_matches):
        """Test with a mix of wins, draws, and losses"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 0},  # win
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': 1, 'score_away': 1},  # draw
            {'home_team_id': 1, 'away_team_id': 4, 'score_home': 0, 'score_away': 3}  # loss
        ]
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10, decay_factor=1.0)

        self.assertEqual(num_matches, 3)
        self.assertAlmostEqual(priors['win'], 1 / 3)
        self.assertAlmostEqual(priors['draw'], 1 / 3)
        self.assertAlmostEqual(priors['loss'], 1 / 3)

    @patch('src.Backend.probability_models.bayes_classic_model.get_last_matches')
    def test_calculate_prior_probabilities_with_decay(self, mock_get_last_matches):
        """Test decay factor with ordered matches (newer matches should have more weight)"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 0, 'score_away': 1},  # loss (oldest)
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 1, 'score_away': 1},  # draw
            {'home_team_id': 1, 'away_team_id': 4, 'score_home': 2, 'score_away': 0}  # win (newest)
        ]
        decay_factor = 0.5
        priors, num_matches = calculate_weighted_form_probabilities(team_id=1, num_matches=10, decay_factor=decay_factor)

        # Calculate expected weights: oldest to newest: 0.25, 0.5, 1.0
        # Total weight: 1.75
        # win: 1.0/1.75 = 0.571, draw: 0.5/1.75 = 0.286, loss: 0.25/1.75 = 0.143
        self.assertEqual(num_matches, 3)
        self.assertAlmostEqual(priors['win'], 0.571, places=3)
        self.assertAlmostEqual(priors['draw'], 0.286, places=3)
        self.assertAlmostEqual(priors['loss'], 0.143, places=3)

    @patch('src.Backend.probability_models.bayes_classic_model.calculate_prior_probabilities')
    def test_bayes_classic_predict_no_data(self, mock_calculate_priors):
        """Test when there's no data for one or both teams"""
        mock_calculate_priors.side_effect = [(None, 0), (None, 0)]
        result = predict_with_form_average_model(home_team_id=1, away_team_id=2)
        self.assertIsNone(result)

        # Test when home team has no matches
        mock_calculate_priors.side_effect = [(None, 0), ({"win": 0.5, "draw": 0.3, "loss": 0.2}, 5)]
        result = predict_with_form_average_model(home_team_id=1, away_team_id=2)
        self.assertIsNone(result)

        # Test when away team has no matches
        mock_calculate_priors.side_effect = [({"win": 0.6, "draw": 0.2, "loss": 0.2}, 10), (None, 0)]
        result = predict_with_form_average_model(home_team_id=1, away_team_id=2)
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.bayes_classic_model.calculate_prior_probabilities')
    def test_bayes_classic_predict_calculation(self, mock_calculate_priors):
        """Test the calculation with known values"""
        home_priors = {"win": 0.6, "draw": 0.2, "loss": 0.2}
        away_priors = {"win": 0.5, "draw": 0.3, "loss": 0.2}

        mock_calculate_priors.side_effect = [(home_priors, 10), (away_priors, 10)]

        result = predict_with_form_average_model(home_team_id=1, away_team_id=2)

        # Expected calculations:
        # P_draw_given_played = (0.2*10 + 0.3*10) / 20 = 0.25
        # P_home_win = 0.6 * (1-0.5) = 0.3
        # P_away_win = 0.5 * (1-0.6) = 0.2
        # P_draw = 0.25
        # total = 0.3 + 0.2 + 0.25 = 0.75
        # normalized: home_win = 0.3/0.75 = 0.4 (40%),
        # draw = 0.25/0.75 = 0.333 (33.33%),
        # away_win = 0.2/0.75 = 0.266 (26.67%)

        self.assertEqual(result["1"], 40.0)
        self.assertEqual(result["X"], 33.33)
        self.assertEqual(result["2"], 26.67)

    @patch('src.Backend.probability_models.bayes_classic_model.calculate_prior_probabilities')
    def test_bayes_classic_predict_with_different_match_counts(self, mock_calculate_priors):
        """Test when teams have different number of matches"""
        home_priors = {"win": 0.7, "draw": 0.2, "loss": 0.1}
        away_priors = {"win": 0.4, "draw": 0.4, "loss": 0.2}

        mock_calculate_priors.side_effect = [(home_priors, 15), (away_priors, 5)]

        result = predict_with_form_average_model(home_team_id=1, away_team_id=2)

        # Expected calculations:
        # P_draw_given_played = (0.2*15 + 0.4*5) / 20 = 0.25
        # P_home_win = 0.7 * (1-0.4) = 0.42
        # P_away_win = 0.4 * (1-0.7) = 0.12
        # P_draw = 0.25
        # total = 0.42 + 0.12 + 0.25 = 0.79
        # normalized: home_win = 0.42/0.79 = 0.5316 (53.16%),
        # draw = 0.25/0.79 = 0.3165 (31.65%),
        # away_win = 0.12/0.79 = 0.1519 (15.19%)

        self.assertEqual(result["1"], 53.16)
        self.assertEqual(result["X"], 31.65)
        self.assertEqual(result["2"], 15.19)


if __name__ == '__main__':
    unittest.main()