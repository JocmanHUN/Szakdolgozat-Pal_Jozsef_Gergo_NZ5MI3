import unittest
from unittest.mock import patch

from src.Backend.probability_models.form_multiplicative_model import (
    calculate_weighted_form_multiplicative,
    predict_with_form_multiplicative_model
)


class TestBayesPredictionModels(unittest.TestCase):

    def setUp(self):
        """Prepare sample match data for testing."""
        self.mock_matches = [
            # Simulated matches with various outcomes
            {
                'home_team_id': 1,
                'away_team_id': 2,
                'score_home': 2,
                'score_away': 1
            },
            {
                'home_team_id': 1,
                'away_team_id': 2,
                'score_home': 1,
                'score_away': 1
            },
            {
                'home_team_id': 1,
                'away_team_id': 2,
                'score_home': 0,
                'score_away': 2
            },
            # Additional matches to test decay
            {
                'home_team_id': 1,
                'away_team_id': 2,
                'score_home': 3,
                'score_away': 0
            },
            {
                'home_team_id': 1,
                'away_team_id': 2,
                'score_home': 1,
                'score_away': 3
            }
        ]

    @patch('src.Backend.DB.fixtures.get_last_matches')
    def test_calculate_weighted_bayes_probabilities_basic(self, mock_get_last_matches):
        """
        Test the weighted Bayes probabilities calculation.
        """
        mock_get_last_matches.return_value = self.mock_matches

        # Test home team probabilities
        probs = calculate_weighted_form_multiplicative(1, num_matches=5, decay_factor=0.9)

        self.assertIsNotNone(probs, "Probabilities should not be None")

        # Check that probabilities are present
        self.assertTrue(all(key in probs for key in ["win", "draw", "loss"]),
                        "All probability keys should be present")

        # Check probabilities sum to 1
        total_prob = probs["win"] + probs["draw"] + probs["loss"]
        self.assertAlmostEqual(total_prob, 1.0, msg="Probabilities should sum to 1")

    def test_calculate_weighted_bayes_probabilities_no_matches(self):
        """
        Test scenario with no matches or invalid matches.
        """
        with patch('src.Backend.DB.fixtures.get_last_matches', return_value=[]):
            # No matches
            probs = calculate_weighted_form_multiplicative(1)
            self.assertIsNotNone(probs, "Probabilities should not be None for empty matches")

            # Check default probabilities
            self.assertTrue(all(key in probs for key in ["win", "draw", "loss"]))
            total_prob = probs["win"] + probs["draw"] + probs["loss"]
            self.assertAlmostEqual(total_prob, 1.0)

        with patch('src.Backend.DB.fixtures.get_last_matches', return_value=[
            {'score_home': None, 'score_away': None}
        ]):
            # Matches with no valid scores
            probs = calculate_weighted_form_multiplicative(1)
            self.assertIsNotNone(probs, "Probabilities should not be None for invalid matches")

            # Check default probabilities
            self.assertTrue(all(key in probs for key in ["win", "draw", "loss"]))
            total_prob = probs["win"] + probs["draw"] + probs["loss"]
            self.assertAlmostEqual(total_prob, 1.0)

    @patch('src.Backend.DB.fixtures.get_last_matches')
    def test_bayes_empirical_predict(self, mock_get_last_matches):
        """
        Test the Bayes empirical prediction function.
        """
        mock_get_last_matches.return_value = self.mock_matches

        # Predict match outcome
        prediction = predict_with_form_multiplicative_model(1, 2, num_matches=5, decay_factor=0.9)

        self.assertIsNotNone(prediction, "Prediction should not be None")

        # Verify keys
        self.assertEqual(set(prediction.keys()), {"1", "X", "2"},
                         "Prediction should have 1, X, 2 keys")

        # Check probabilities sum to 100
        total_prob = prediction["1"] + prediction["X"] + prediction["2"]
        self.assertAlmostEqual(total_prob, 100.0, msg="Probabilities should sum to 100")

        # Check individual probabilities are between 0 and 100
        for key, prob in prediction.items():
            self.assertTrue(0 <= prob <= 100,
                            f"Probability for {key} should be between 0 and 100")

    def test_bayes_empirical_predict_insufficient_data(self):
        """
        Test prediction with insufficient match data.
        """
        with patch('src.Backend.DB.fixtures.get_last_matches', return_value=[]):
            # No matches for either team
            prediction = predict_with_form_multiplicative_model(1, 2)

            # Instead of checking for None, check for default 50-50 prediction
            self.assertIsNotNone(prediction, "Prediction should have default values")
            self.assertEqual(prediction["1"], 50.0)
            self.assertEqual(prediction["X"], 0.0)
            self.assertEqual(prediction["2"], 50.0)

    @patch('src.Backend.DB.fixtures.get_last_matches')
    def test_decay_factor_variations(self, mock_get_last_matches):
        """
        Test different decay factor values.
        """
        mock_get_last_matches.return_value = self.mock_matches

        # Test various decay factors
        for decay_factor in [0.5, 0.7, 0.9, 1.0]:
            with self.subTest(decay_factor=decay_factor):
                # Calculate probabilities and predict
                probs = calculate_weighted_form_multiplicative(1, num_matches=5, decay_factor=decay_factor)
                prediction = predict_with_form_multiplicative_model(1, 2, num_matches=5, decay_factor=decay_factor)

                self.assertIsNotNone(probs,
                                     f"Probabilities should not be None for decay factor {decay_factor}")
                self.assertIsNotNone(prediction,
                                     f"Prediction should not be None for decay factor {decay_factor}")

                # Verify probabilities sum to 1 and predictions sum to 100
                self.assertAlmostEqual(probs["win"] + probs["draw"] + probs["loss"], 1.0)
                self.assertAlmostEqual(prediction["1"] + prediction["X"] + prediction["2"], 100.0)


if __name__ == '__main__':
    unittest.main()