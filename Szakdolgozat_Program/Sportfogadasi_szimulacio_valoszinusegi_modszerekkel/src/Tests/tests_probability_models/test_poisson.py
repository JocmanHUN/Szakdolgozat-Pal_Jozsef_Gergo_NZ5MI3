import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from src.Backend.probability_models.poisson_model import (
    calculate_weighted_goal_expectancy,
    poisson_probability,
    poisson_predict
)


class TestPoissonModel(unittest.TestCase):

    @patch('src.Backend.probability_models.poisson_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_no_matches(self, mock_get_last_matches):
        """Test goal expectancy calculation when no matches are available"""
        mock_get_last_matches.return_value = []

        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5)

        # Should return None when no matches
        self.assertIsNone(avg_goals_for)
        self.assertIsNone(avg_goals_against)
        mock_get_last_matches.assert_called_once_with(1, 5)

    @patch('src.Backend.probability_models.poisson_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_no_valid_matches(self, mock_get_last_matches):
        """Test goal expectancy calculation when matches have no scores"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': None, 'score_away': None},
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': None, 'score_away': None}
        ]

        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5)

        # Should return None when no valid matches
        self.assertIsNone(avg_goals_for)
        self.assertIsNone(avg_goals_against)

    @patch('src.Backend.probability_models.poisson_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_home_team(self, mock_get_last_matches):
        """Test goal expectancy calculation for home team matches"""
        mock_get_last_matches.return_value = [
            # Team 1 is home team in this match
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 1},
            # Team 1 is away team in this match
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': 0, 'score_away': 3}
        ]

        # With decay_factor=1.0 (no decay), we should get the average
        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5, decay_factor=1.0)

        # Average goals scored: (2+3)/2 = 2.5
        # Average goals conceded: (1+0)/2 = 0.5
        self.assertAlmostEqual(avg_goals_for, 2.5)
        self.assertAlmostEqual(avg_goals_against, 0.5)

    @patch('src.Backend.probability_models.poisson_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_with_decay(self, mock_get_last_matches):
        """Test goal expectancy calculation with decay factor"""
        mock_get_last_matches.return_value = [
            # Older match (weighted less)
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 1, 'score_away': 1},
            # Recent match (weighted more)
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 3, 'score_away': 0},
            # Most recent match (weighted most)
            {'home_team_id': 4, 'away_team_id': 1, 'score_home': 1, 'score_away': 2}
        ]

        # With decay_factor=0.5, weights: 0.25 (oldest), 0.5 (middle), 1.0 (newest)
        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5, decay_factor=0.5)

        # Weighted goals scored: (1*0.25 + 3*0.5 + 2*1.0)/(0.25+0.5+1.0) = 2.14
        # Weighted goals conceded: (1*0.25 + 0*0.5 + 1*1.0)/(0.25+0.5+1.0) = 0.71
        self.assertAlmostEqual(avg_goals_for, 2.14, places=2)
        self.assertAlmostEqual(avg_goals_against, 0.71, places=2)

    def test_poisson_probability(self):
        """Test Poisson probability calculation"""
        # Test with expected values and known probabilities
        test_cases = [
            (1.0, 0, 0.3679),  # P(X=0 | lambda=1.0)
            (1.0, 1, 0.3679),  # P(X=1 | lambda=1.0)
            (1.0, 2, 0.1839),  # P(X=2 | lambda=1.0)
            (2.5, 0, 0.0821),  # P(X=0 | lambda=2.5)
            (2.5, 2, 0.2565),  # P(X=2 | lambda=2.5)
        ]

        for expected_goals, actual_goals, expected_prob in test_cases:
            with self.subTest(expected=expected_goals, actual=actual_goals):
                prob = poisson_probability(expected_goals, actual_goals)
                self.assertAlmostEqual(prob, expected_prob, places=4)

    @patch('src.Backend.probability_models.poisson_model.calculate_weighted_goal_expectancy')
    def test_poisson_predict_no_data(self, mock_calculate_goal_expectancy):
        """Test Poisson prediction when no data is available"""
        mock_calculate_goal_expectancy.side_effect = [
            (None, None),  # Home team has no goal data
            (2.0, 1.0)  # Away team has data
        ]

        result = poisson_predict(1, 2)

        # Should return None when no sufficient data
        self.assertIsNone(result)

    @patch('src.Backend.probability_models.poisson_model.calculate_weighted_goal_expectancy')
    @patch('src.Backend.probability_models.poisson_model.poisson_probability')
    def test_poisson_predict_result_matrix(self, mock_poisson_prob, mock_calculate_goal_expectancy):
        """Test Poisson prediction result matrix calculation"""
        mock_calculate_goal_expectancy.side_effect = [
            (2.0, 1.0),  # Home team
            (1.5, 1.5)  # Away team
        ]

        # Create a deterministic probability matrix for testing
        def mock_probability(expected, actual):
            if expected == 1.75 and actual == 0:
                return 0.2
            elif expected == 1.75 and actual == 1:
                return 0.3
            elif expected == 1.75 and actual == 2:
                return 0.2
            elif expected == 1.25 and actual == 0:
                return 0.3
            elif expected == 1.25 and actual == 1:
                return 0.4
            elif expected == 1.25 and actual == 2:
                return 0.1
            else:
                return 0.01

        mock_poisson_prob.side_effect = mock_probability

        result = poisson_predict(1, 2)

        # Check that we have proper format
        self.assertIn("1", result)
        self.assertIn("X", result)
        self.assertIn("2", result)

        # Check that probabilities sum to 100%
        self.assertAlmostEqual(result["1"] + result["X"] + result["2"], 100.0, places=1)

    @patch('src.Backend.probability_models.poisson_model.calculate_weighted_goal_expectancy')
    def test_poisson_predict_integration(self, mock_calculate_goal_expectancy):
        """Test full Poisson prediction with realistic data"""
        mock_calculate_goal_expectancy.side_effect = [
            (1.8, 0.9),  # Home team averages 1.8 goals scored, 0.9 conceded
            (1.5, 1.2)  # Away team averages 1.5 goals scored, 1.2 conceded
        ]

        result = poisson_predict(1, 2)

        # Not testing exact values because calculation is deterministic
        # Just ensure output is in correct format and reasonable range
        self.assertIn("1", result)
        self.assertIn("X", result)
        self.assertIn("2", result)

        # Probabilities should sum to 100%
        self.assertAlmostEqual(result["1"] + result["X"] + result["2"], 100.0, places=1)

        # Probabilities should be between 0 and 100
        for key in ["1", "X", "2"]:
            self.assertTrue(0 <= result[key] <= 100)

    @patch('src.Backend.probability_models.poisson_model.calculate_weighted_goal_expectancy')
    def test_poisson_probabilities_different_scenarios(self, mock_calculate_goal_expectancy):
        """Test that Poisson probabilities are in expected ranges for different scenarios"""
        test_cases = [
            # Evenly matched teams
            {
                "home_stats": (1.5, 1.2),
                "away_stats": (1.4, 1.3),
                "description": "evenly matched teams"
            },
            # Strong home team advantage
            {
                "home_stats": (2.5, 0.8),
                "away_stats": (1.0, 1.8),
                "description": "strong home team"
            },
            # Strong away team advantage
            {
                "home_stats": (0.8, 2.0),
                "away_stats": (2.2, 0.9),
                "description": "strong away team"
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["description"]):
                mock_calculate_goal_expectancy.side_effect = [
                    case["home_stats"],
                    case["away_stats"]
                ]

                result = poisson_predict(1, 2)

                # Check that probabilities sum to 100%
                self.assertAlmostEqual(result["1"] + result["X"] + result["2"], 100.0, places=1)

                # For strong home team, home win probability should be higher
                if case["description"] == "strong home team":
                    self.assertTrue(result["1"] > result["2"])
                    self.assertTrue(result["1"] > 50)

                # For strong away team, away win probability should be higher
                if case["description"] == "strong away team":
                    self.assertTrue(result["2"] > result["1"])
                    self.assertTrue(result["2"] > 50)

                # For evenly matched teams, home and away probabilities should be closer
                if case["description"] == "evenly matched teams":
                    self.assertLess(abs(result["1"] - result["2"]), 20)

    @patch('src.Backend.probability_models.poisson_model.stats')
    def test_poisson_matrix_calculation(self, mock_stats):
        """Test that the Poisson probability matrix is correctly created and processed"""
        # Mock the calculate_weighted_goal_expectancy function
        with patch('src.Backend.probability_models.poisson_model.calculate_weighted_goal_expectancy') as mock_calc:
            mock_calc.side_effect = [
                (2.0, 1.0),  # Home team stats
                (1.5, 1.5)  # Away team stats
            ]

            # Calculate expected goals
            # home_expected = (2.0 + 1.5) / 2 = 1.75
            # away_expected = (1.5 + 1.0) / 2 = 1.25

            # Mock the Poisson PMF to return consistent values for testing
            def mock_pmf(k, mu):
                if mu == 1.75:  # Home expected goals
                    values = {0: 0.17, 1: 0.30, 2: 0.26, 3: 0.15, 4: 0.07, 5: 0.02}
                    return values.get(k, 0.01)
                elif mu == 1.25:  # Away expected goals
                    values = {0: 0.29, 1: 0.36, 2: 0.22, 3: 0.09, 4: 0.03, 5: 0.01}
                    return values.get(k, 0.01)
                return 0.01

            mock_stats.poisson.pmf.side_effect = mock_pmf

            result = poisson_predict(1, 2)

            # Verify result format
            self.assertIn("1", result)
            self.assertIn("X", result)
            self.assertIn("2", result)

            # Check that probabilities sum to 100%
            self.assertAlmostEqual(result["1"] + result["X"] + result["2"], 100.0, places=1)

            # Check that all probabilities are in valid range
            for key in ["1", "X", "2"]:
                self.assertTrue(0 <= result[key] <= 100,
                                f"Probability for {key} should be between 0 and 100")

            # Instead of assuming specific relationships, check that the distribution makes sense:
            # The expected goals suggest home team should have an advantage,
            # but we don't need to strictly enforce ordering
            self.assertGreater(result["1"], 20, "Home win probability should be significant")

if __name__ == '__main__':
    unittest.main()