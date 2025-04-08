import unittest
from unittest.mock import patch, MagicMock

from src.Backend.probability_models.monte_carlo_model import (
    calculate_weighted_goal_expectancy,
    monte_carlo_predict
)


class TestMonteCarloModel(unittest.TestCase):

    @patch('src.Backend.probability_models.monte_carlo_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_no_matches(self, mock_get_last_matches):
        """Test goal expectancy calculation when no matches are available"""
        mock_get_last_matches.return_value = []

        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5)

        # Should return zeros when no matches
        self.assertEqual(avg_goals_for, 0.0)
        self.assertEqual(avg_goals_against, 0.0)
        mock_get_last_matches.assert_called_once_with(1, 5)

    @patch('src.Backend.probability_models.monte_carlo_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_no_valid_matches(self, mock_get_last_matches):
        """Test goal expectancy calculation when matches have no scores"""
        mock_get_last_matches.return_value = [
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': None, 'score_away': None},
            {'home_team_id': 3, 'away_team_id': 1, 'score_home': None, 'score_away': None}
        ]

        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5)

        # Should return zeros when no valid matches
        self.assertEqual(avg_goals_for, 0.0)
        self.assertEqual(avg_goals_against, 0.0)

    @patch('src.Backend.probability_models.monte_carlo_model.get_last_matches')
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

    @patch('src.Backend.probability_models.monte_carlo_model.get_last_matches')
    def test_calculate_weighted_goal_expectancy_with_decay(self, mock_get_last_matches):
        """Test goal expectancy calculation with decay factor"""
        mock_get_last_matches.return_value = [
            # Older match (weighted less)
            {'home_team_id': 1, 'away_team_id': 2, 'score_home': 1, 'score_away': 1},
            # Recent match (weighted more)
            {'home_team_id': 1, 'away_team_id': 3, 'score_home': 3, 'score_away': 0}
        ]

        # With decay_factor=0.5, the older match has weight 0.5, newer match has weight 1.0
        avg_goals_for, avg_goals_against = calculate_weighted_goal_expectancy(1, num_matches=5, decay_factor=0.5)

        # Weighted goals scored: (1*0.5 + 3*1.0)/(0.5+1.0) = 2.33
        # Weighted goals conceded: (1*0.5 + 0*1.0)/(0.5+1.0) = 0.33
        self.assertAlmostEqual(avg_goals_for, 2.33, places=2)
        self.assertAlmostEqual(avg_goals_against, 0.33, places=2)

    @patch('src.Backend.probability_models.monte_carlo_model.calculate_weighted_goal_expectancy')
    @patch('src.Backend.probability_models.monte_carlo_model.poisson.rvs')
    def test_monte_carlo_predict_no_data(self, mock_poisson_rvs, mock_calculate_goal_expectancy):
        """Test Monte Carlo prediction when no data is available"""
        mock_calculate_goal_expectancy.side_effect = [
            (0.0, 1.5),  # Home team has no goal data
            (2.0, 1.0)  # Away team has data
        ]

        result = monte_carlo_predict(1, 2, num_simulations=100)

        # Should return None when no sufficient data
        self.assertIsNone(result)
        mock_poisson_rvs.assert_not_called()  # Should not attempt simulation

    @patch('src.Backend.probability_models.monte_carlo_model.calculate_weighted_goal_expectancy')
    @patch('src.Backend.probability_models.monte_carlo_model.poisson.rvs')
    def test_monte_carlo_predict_with_fixed_outcomes(self, mock_poisson_rvs, mock_calculate_goal_expectancy):
        """Test Monte Carlo prediction with controlled simulation outcomes"""
        mock_calculate_goal_expectancy.side_effect = [
            (2.0, 1.0),  # Home team
            (1.5, 1.5)  # Away team
        ]

        # Simulate: 6 home wins, 3 draws, 1 away win
        mock_poisson_rvs.side_effect = [
            2, 1,  # Home team scores 2, away scores 1 (home win)
            3, 0,  # Home team scores 3, away scores 0 (home win)
            1, 1,  # Draw
            0, 0,  # Draw
            2, 0,  # Home win
            1, 0,  # Home win
            0, 1,  # Away win
            1, 0,  # Home win
            1, 1,  # Draw
            2, 1,  # Home win
        ]

        result = monte_carlo_predict(1, 2, num_simulations=10)

        # Expected probabilities based on our fixed simulation outcomes
        self.assertEqual(result["1"], 60.0)  # 6/10 home wins
        self.assertEqual(result["X"], 30.0)  # 3/10 draws
        self.assertEqual(result["2"], 10.0)  # 1/10 away wins

        # Check that all simulations were run
        self.assertEqual(mock_poisson_rvs.call_count, 20)  # 10 simulations, 2 calls per simulation

    @patch('src.Backend.probability_models.monte_carlo_model.calculate_weighted_goal_expectancy')
    def test_monte_carlo_predict_integration(self, mock_calculate_goal_expectancy):
        """Test full Monte Carlo prediction with more realistic data"""
        mock_calculate_goal_expectancy.side_effect = [
            (1.8, 0.9),  # Home team averages 1.8 goals scored, 0.9 conceded
            (1.5, 1.2)  # Away team averages 1.5 goals scored, 1.2 conceded
        ]

        # Use a small number of simulations for testing speed
        # We'll set a seed for reproducibility in real tests
        result = monte_carlo_predict(1, 2, num_simulations=1000)

        # Not testing exact values because Monte Carlo is probabilistic
        # Just ensure output is in correct format and reasonable range
        self.assertIn("1", result)
        self.assertIn("X", result)
        self.assertIn("2", result)

        # Probabilities should sum to 100%
        self.assertAlmostEqual(result["1"] + result["X"] + result["2"], 100.0, places=1)

        # Probabilities should be between 0 and 100
        for key in ["1", "X", "2"]:
            self.assertTrue(0 <= result[key] <= 100)

    @patch('src.Backend.probability_models.monte_carlo_model.calculate_weighted_goal_expectancy')
    def test_monte_carlo_probabilities_distribution(self, mock_calculate_goal_expectancy):
        """Test that Monte Carlo probabilities are in expected ranges for different scenarios"""
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

                result = monte_carlo_predict(1, 2, num_simulations=2000)

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


if __name__ == '__main__':
    unittest.main()