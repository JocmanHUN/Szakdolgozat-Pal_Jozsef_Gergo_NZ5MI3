import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from src.Backend.probability_models.logistic_regression_model import (
    extract_features,
    prepare_training_data,
    train_logistic_regression,
    logistic_regression_predict,
    get_average_team_statistics,
    safe_float
)


class TestLogisticRegressionModel(unittest.TestCase):

    def test_safe_float_valid_values(self):
        """Test the safe_float function with valid inputs"""
        test_cases = [
            (10, 10.0),
            ("15", 15.0),
            ("20.5", 20.5),
            ("30%", 30.0),
            (5.5, 5.5)
        ]

        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = safe_float(input_val)
                self.assertEqual(result, expected)

    def test_safe_float_invalid_values(self):
        """Test the safe_float function with invalid inputs"""
        test_cases = [
            (None, 0.0),
            ("", 0.0),
            ("invalid", 0.0),
            ({}, 0.0)
        ]

        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = safe_float(input_val)
                self.assertEqual(result, expected)

    def test_safe_float_custom_default(self):
        """Test the safe_float function with custom default value"""
        test_cases = [
            (None, 99.0),
            ("invalid", 99.0)
        ]

        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = safe_float(input_val, default=99.0)
                self.assertEqual(result, expected)

    def test_extract_features(self):
        """Test feature extraction from match statistics"""
        # Test with complete statistics
        complete_stats = {
            'shots_on_goal': 5,
            'shots_off_goal': 8,
            'total_shots': 15,
            'blocked_shots': 2,
            'shots_insidebox': 10,
            'shots_outsidebox': 5,
            'fouls': 12,
            'corner_kicks': 6,
            'offsides': 3,
            'ball_possession': 60,
            'yellow_cards': 2,
            'red_cards': 0,
            'goalkeeper_saves': 4,
            'total_passes': 450,
            'passes_accurate': 380,
            'passes_percentage': 84
        }

        with patch('builtins.print'):  # Suppress print statements
            features = extract_features(complete_stats)

            # Check shape and type
            self.assertEqual(features.shape, (16,))
            self.assertEqual(features.dtype, np.float64)

            # Check specific values
            self.assertEqual(features[0], 5.0)  # shots_on_goal
            self.assertEqual(features[9], 60.0)  # ball_possession
            self.assertEqual(features[15], 84.0)  # passes_percentage

    def test_extract_features_missing_values(self):
        """Test feature extraction with missing statistics"""
        incomplete_stats = {
            'shots_on_goal': 5,
            'shots_off_goal': 8,
            # missing total_shots
            'blocked_shots': 2,
            # missing shots_insidebox
            'shots_outsidebox': 5,
            'fouls': 12,
            'corner_kicks': 6,
            # missing offsides
            # missing ball_possession (should use default)
            'yellow_cards': 2,
            'red_cards': 0,
            # missing goalkeeper_saves
        }

        with patch('builtins.print'):  # Suppress print statements
            features = extract_features(incomplete_stats)

            # Check specific values with defaults
            self.assertEqual(features[2], 0.0)  # missing total_shots
            self.assertEqual(features[4], 0.0)  # missing shots_insidebox
            self.assertEqual(features[8], 0.0)  # missing offsides
            self.assertEqual(features[9], 50.0)  # ball_possession default
            self.assertEqual(features[12], 0.0)  # missing goalkeeper_saves

    @patch('src.Backend.probability_models.logistic_regression_model.get_last_matches')
    @patch('src.Backend.probability_models.logistic_regression_model.get_match_statistics')
    def test_prepare_training_data_no_matches(self, mock_get_stats, mock_get_matches):
        """Test preparing training data when no matches are available"""
        mock_get_matches.return_value = []

        with patch('builtins.print'):  # Suppress print statements
            X, y = prepare_training_data(1, num_matches=5)

            # Should return empty arrays
            self.assertEqual(X.shape, (0,))
            self.assertEqual(y.shape, (0,))

            mock_get_matches.assert_called_once_with(1, 5)
            mock_get_stats.assert_not_called()

    @patch('src.Backend.probability_models.logistic_regression_model.get_last_matches')
    @patch('src.Backend.probability_models.logistic_regression_model.get_match_statistics')
    @patch('src.Backend.probability_models.logistic_regression_model.extract_features')
    def test_prepare_training_data_home_team(self, mock_extract_features, mock_get_stats, mock_get_matches):
        """Test preparing training data for home team matches"""
        # Mock matches data
        mock_get_matches.return_value = [
            {'id': 1, 'home_team_id': 1, 'away_team_id': 2, 'score_home': 2, 'score_away': 1}
        ]

        # Mock match statistics
        mock_get_stats.return_value = [
            {'team_id': 1, 'shots_on_goal': 5},  # Home team stats
            {'team_id': 2, 'shots_on_goal': 3}  # Away team stats
        ]

        # Mock extracted features
        mock_extract_features.side_effect = [
            np.array([5.0, 8.0, 15.0, 2.0, 10.0, 5.0, 12.0, 6.0, 3.0, 60.0, 2.0, 0.0, 4.0, 450.0, 380.0, 84.0]),
            np.array([3.0, 5.0, 10.0, 1.0, 7.0, 3.0, 10.0, 4.0, 2.0, 40.0, 1.0, 0.0, 6.0, 350.0, 280.0, 80.0])
        ]

        with patch('builtins.print'):  # Suppress print statements
            X, y = prepare_training_data(1, num_matches=5)

            # Check shapes
            self.assertEqual(X.shape, (1, 34))  # 16 features per team + 2 indicators
            self.assertEqual(y.shape, (1,))

            # Check result - home team won (2-1), so result should be 2 (win)
            self.assertEqual(y[0], 2)

            # Check indicators - should be [1, 0] for home team
            self.assertEqual(X[0, 32], 1)
            self.assertEqual(X[0, 33], 0)

    @patch('src.Backend.probability_models.logistic_regression_model.get_last_matches')
    @patch('src.Backend.probability_models.logistic_regression_model.get_match_statistics')
    @patch('src.Backend.probability_models.logistic_regression_model.extract_features')
    def test_prepare_training_data_away_team(self, mock_extract_features, mock_get_stats, mock_get_matches):
        """Test preparing training data for away team matches"""
        # Mock matches data
        mock_get_matches.return_value = [
            {'id': 1, 'home_team_id': 2, 'away_team_id': 1, 'score_home': 1, 'score_away': 1}
        ]

        # Mock match statistics
        mock_get_stats.return_value = [
            {'team_id': 2, 'shots_on_goal': 4},  # Home team stats
            {'team_id': 1, 'shots_on_goal': 4}  # Away team stats
        ]

        # Mock extracted features
        mock_extract_features.side_effect = [
            np.array([4.0, 6.0, 12.0, 2.0, 8.0, 4.0, 10.0, 5.0, 2.0, 55.0, 1.0, 0.0, 3.0, 400.0, 320.0, 80.0]),
            np.array([4.0, 7.0, 13.0, 2.0, 9.0, 4.0, 8.0, 6.0, 1.0, 45.0, 2.0, 0.0, 3.0, 380.0, 310.0, 82.0])
        ]

        with patch('builtins.print'):  # Suppress print statements
            X, y = prepare_training_data(1, num_matches=5)

            # Check shapes
            self.assertEqual(X.shape, (1, 34))
            self.assertEqual(y.shape, (1,))

            # Check result - match was a draw (1-1), so result should be 1 (draw)
            self.assertEqual(y[0], 1)

            # Check indicators - should be [0, 1] for away team
            self.assertEqual(X[0, 32], 0)
            self.assertEqual(X[0, 33], 1)

    @patch('src.Backend.probability_models.logistic_regression_model.prepare_training_data')
    @patch('src.Backend.probability_models.logistic_regression_model.LogisticRegression')
    def test_train_logistic_regression(self, mock_logreg, mock_prepare_data):
        """Test logistic regression model training"""
        # Mock training data
        mock_prepare_data.side_effect = [
            (np.array([[1, 2, 3, 4, 5]]), np.array([2, 0, 1])),  # home team data
            (np.array([[6, 7, 8, 9, 10]]), np.array([1, 2, 0]))  # away team data
        ]

        # Mock logistic regression model
        mock_model = MagicMock()
        mock_logreg.return_value = mock_model
        mock_model.fit.return_value = mock_model

        with patch('builtins.print'):  # Suppress print statements
            with patch('src.Backend.probability_models.logistic_regression_model.cross_val_score',
                       return_value=np.array([0.7, 0.8, 0.75])):
                model, imputer, scaler = train_logistic_regression(1, 2)

                # Check that model was called and fit
                mock_logreg.assert_called_once()
                mock_model.fit.assert_called_once()

                # Check that data was combined correctly
                mock_prepare_data.assert_called()

                # Verify returned objects
                self.assertEqual(model, mock_model)
                self.assertIsNotNone(imputer)
                self.assertIsNotNone(scaler)

    @patch('src.Backend.probability_models.logistic_regression_model.train_logistic_regression')
    @patch('src.Backend.probability_models.logistic_regression_model.get_average_team_statistics')
    def test_logistic_regression_predict(self, mock_get_avg_stats, mock_train):
        """Test logistic regression prediction"""
        # Mock model and preprocessors
        mock_model = MagicMock()
        mock_imputer = MagicMock()
        mock_scaler = MagicMock()

        mock_train.return_value = (mock_model, mock_imputer, mock_scaler)

        # Mock average statistics
        mock_get_avg_stats.side_effect = [
            np.array([5.0, 8.0, 15.0, 2.0, 10.0, 5.0, 12.0, 6.0, 3.0, 60.0, 2.0, 0.0, 4.0, 450.0, 380.0, 84.0]),  # home
            np.array([3.0, 5.0, 10.0, 1.0, 7.0, 3.0, 10.0, 4.0, 2.0, 40.0, 1.0, 0.0, 6.0, 350.0, 280.0, 80.0])  # away
        ]

        # Mock transformed data
        mock_imputer.transform.return_value = np.array([[1, 2, 3]])
        mock_scaler.transform.return_value = np.array([[0.1, 0.2, 0.3]])

        # Mock model prediction
        mock_model.predict_proba.return_value = np.array([[0.2, 0.3, 0.5]])
        mock_model.classes_ = np.array([0, 1, 2])  # away win, draw, home win

        with patch('builtins.print'):  # Suppress print statements
            result = logistic_regression_predict(1, 2)

            # Check that model was called with preprocessed data
            mock_train.assert_called_once_with(1, 2)
            mock_model.predict_proba.assert_called_once()

            # Check result format and values
            self.assertIn("1", result)
            self.assertIn("X", result)
            self.assertIn("2", result)

            # Check probabilities based on mocked predict_proba
            # class 2 (home win) -> "1"
            # class 1 (draw) -> "X"
            # class 0 (away win) -> "2"
            self.assertEqual(result["1"], 50.0)  # class 2 probability
            self.assertEqual(result["X"], 30.0)  # class 1 probability
            self.assertEqual(result["2"], 20.0)  # class 0 probability

    @patch('src.Backend.probability_models.logistic_regression_model.get_last_matches')
    @patch('src.Backend.probability_models.logistic_regression_model.get_match_statistics')
    @patch('src.Backend.probability_models.logistic_regression_model.extract_features')
    def test_get_average_team_statistics(self, mock_extract_features, mock_get_stats, mock_get_matches):
        """Test calculating average team statistics"""
        # Mock matches data
        mock_get_matches.return_value = [
            {'id': 1, 'home_team_id': 1, 'away_team_id': 2},
            {'id': 2, 'home_team_id': 3, 'away_team_id': 1}
        ]

        # Mock match statistics
        mock_get_stats.side_effect = [
            [
                {'team_id': 1, 'shots_on_goal': 4},
                {'team_id': 2, 'shots_on_goal': 3}
            ],
            [
                {'team_id': 3, 'shots_on_goal': 2},
                {'team_id': 1, 'shots_on_goal': 5}
            ]
        ]

        # Előre definiáljuk a mock értékeket, amiket ellenőrzünk később
        feature_set_1 = np.array(
            [4.0, 6.0, 12.0, 2.0, 8.0, 4.0, 10.0, 5.0, 2.0, 55.0, 1.0, 0.0, 3.0, 400.0, 320.0, 80.0])
        feature_set_2 = np.array(
            [5.0, 7.0, 13.0, 3.0, 9.0, 4.0, 8.0, 6.0, 1.0, 45.0, 2.0, 0.0, 2.0, 380.0, 310.0, 82.0])
        expected_avg = (feature_set_1 + feature_set_2) / 2

        # Mock extracted features for team 1 in both matches
        mock_extract_features.side_effect = [feature_set_1, feature_set_2]

        with patch('builtins.print'):  # Suppress print statements
            avg_stats = get_average_team_statistics(1, num_matches=5)

            # Check that stats were averaged correctly
            np.testing.assert_array_almost_equal(avg_stats, expected_avg)

            # Check function calls
            mock_get_matches.assert_called_once_with(1, 5)
            self.assertEqual(mock_get_stats.call_count, 2)
            self.assertEqual(mock_extract_features.call_count, 2)


if __name__ == '__main__':
    unittest.main()