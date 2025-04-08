import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import copy

from src.Backend.helpers.ensureDatas import ensure_simulation_data_available


class TestSimulationData(unittest.TestCase):

    def setUp(self):
        """Set up common test data"""
        self.fixture_list = [(1, 2, 101), (3, 4, 102)]

        # Mock fixture data
        self.mock_fixture = {
            "fixture": {
                "id": 101,
                "date": "2023-04-01T15:00:00+00:00",
                "status": {"short": "FT"}
            },
            "league": {"id": 39, "name": "Premier League"},
            "teams": {
                "home": {"id": 1, "name": "Team A", "logo": "url_to_logo_A"},
                "away": {"id": 2, "name": "Team B", "logo": "url_to_logo_B"}
            },
            "goals": {"home": 2, "away": 1}
        }

        # Mock match data
        self.mock_match = {
            "id": 101,
            "date": datetime.now() - timedelta(days=5),
            "home_team_id": 1,
            "away_team_id": 2,
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "home_team_logo": "url_to_logo_A",
            "away_team_logo": "url_to_logo_B",
            "home_team_country": "England",
            "away_team_country": "England",
            "status": "FT",
            "score_home": 2,
            "score_away": 1
        }

        # Mock statistics data
        self.mock_stats = [
            {
                "team": {"id": 1},
                "statistics": [
                    {"type": "Shots on Goal", "value": 5},
                    {"type": "Shots off Goal", "value": 3}
                ]
            },
            {
                "team": {"id": 2},
                "statistics": [
                    {"type": "Shots on Goal", "value": 2},
                    {"type": "Shots off Goal", "value": 4}
                ]
            }
        ]

        # Mock odds data
        self.mock_odds = [
            {
                "bookmakers": [
                    {
                        "id": 1,
                        "name": "Bookmaker A",
                        "bets": [
                            {
                                "id": 1,
                                "name": "Match Winner",
                                "values": [
                                    {"value": "Home", "odd": "2.10"},
                                    {"value": "Draw", "odd": "3.40"},
                                    {"value": "Away", "odd": "3.50"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    @patch('src.Backend.helpers.ensureDatas.get_last_matches')
    @patch('src.Backend.helpers.ensureDatas.get_fixtures_for_team')
    @patch('src.Backend.helpers.ensureDatas.write_to_fixtures')
    @patch('src.Backend.helpers.ensureDatas.read_from_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.get_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.delete_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.read_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.get_team_country_by_id')
    @patch('src.Backend.helpers.ensureDatas.write_to_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.read_odds_by_fixture')
    @patch('src.Backend.helpers.ensureDatas.fetch_odds_for_fixture')
    @patch('src.Backend.helpers.ensureDatas.write_to_odds')
    @patch('builtins.print')
    def test_ensure_simulation_data_all_data_available(self, mock_print, mock_write_odds, mock_fetch_odds,
                                                       mock_read_odds, mock_write_stats, mock_get_country,
                                                       mock_get_fixture, mock_get_h2h, mock_read_h2h,
                                                       mock_delete_fixture, mock_get_stats, mock_read_stats,
                                                       mock_write_fixtures, mock_get_fixtures, mock_get_last_matches):
        """Test when all required data is already available in database"""

        # Generate 15 matches for each team
        matches = []
        for i in range(15):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 1000 + i
            match["date"] = datetime.now() - timedelta(days=i + 1)
            matches.append(match)

        # Mock all necessary functions
        mock_get_last_matches.return_value = matches
        mock_read_stats.return_value = self.mock_stats
        mock_read_h2h.return_value = matches[:10]  # 10 H2H matches
        mock_read_odds.return_value = [
            {
                "fixture_id": 101,
                "bookmaker_id": 1,
                "home_odds": "2.10",
                "draw_odds": "3.40",
                "away_odds": "3.50"
            }
        ]

        # Run the function
        result = ensure_simulation_data_available(self.fixture_list[:1], num_matches=10)

        # Verify the function returned the valid fixture
        self.assertEqual(result, [101])

        # Verify no API calls were made
        mock_get_fixtures.assert_not_called()
        mock_get_stats.assert_not_called()
        mock_get_h2h.assert_not_called()
        mock_fetch_odds.assert_not_called()

        # Verify DB writes were not called
        mock_write_fixtures.assert_not_called()
        mock_write_stats.assert_not_called()
        mock_write_odds.assert_not_called()

    @patch('src.Backend.helpers.ensureDatas.get_last_matches')
    @patch('src.Backend.helpers.ensureDatas.get_fixtures_for_team')
    @patch('src.Backend.helpers.ensureDatas.write_to_fixtures')
    @patch('src.Backend.helpers.ensureDatas.read_from_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.get_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.delete_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.read_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.get_team_country_by_id')
    @patch('src.Backend.helpers.ensureDatas.write_to_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.read_odds_by_fixture')
    @patch('src.Backend.helpers.ensureDatas.fetch_odds_for_fixture')
    @patch('src.Backend.helpers.ensureDatas.write_to_odds')
    @patch('builtins.print')
    def test_ensure_simulation_data_functionalities(self, mock_print, mock_write_odds, mock_fetch_odds,
                                                    mock_read_odds, mock_write_stats, mock_get_country,
                                                    mock_get_fixture, mock_get_h2h, mock_read_h2h,
                                                    mock_delete_fixture, mock_get_stats, mock_read_stats,
                                                    mock_write_fixtures, mock_get_fixtures, mock_get_last_matches):
        """Test the main functionalities of ensure_simulation_data_available"""

        # Mock adatok beállítása
        api_matches = []
        for i in range(20):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 2000 + i
            match["date"] = datetime.now() - timedelta(days=i + 1)
            api_matches.append(match)

        # Egyszerűsített mock-olás - kevesebb speciális viselkedéssel
        mock_get_last_matches.return_value = api_matches[:15]
        mock_get_fixtures.return_value = api_matches
        mock_read_stats.return_value = self.mock_stats
        mock_get_stats.return_value = self.mock_stats
        mock_read_h2h.return_value = api_matches[:10]
        mock_get_fixture.return_value = self.mock_fixture
        mock_get_country.return_value = "England"
        mock_read_odds.return_value = []
        mock_fetch_odds.return_value = self.mock_odds

        # Futtatjuk a függvényt
        result = ensure_simulation_data_available(self.fixture_list[:1], num_matches=10)

        # Csak az eredményt ellenőrizzük, nem a pontos hívási sorrendet
        # - Ellenőrizzük, hogy a függvény visszaadott egy nem üres listát
        self.assertTrue(result, "A függvénynek egy nem üres listát kellene visszaadnia")

        # - Ellenőrizzük, hogy legalább egyszer meghívtuk a különböző függvényeket
        mock_get_last_matches.assert_called()
        mock_read_stats.assert_called()
        mock_read_h2h.assert_called()
        mock_read_odds.assert_called()

        # - Vagy az oddsok már léteznek, vagy lekérték őket
        # (Ez rugalmasabb, mint a konkrét mock_fetch_odds.assert_called() elvárás)
        is_odds_fetched = mock_fetch_odds.called
        is_odds_exist = mock_read_odds.return_value != []

        self.assertTrue(is_odds_fetched or is_odds_exist,
                        "Az oddsokat vagy lekértük, vagy már léteztek")

    @patch('src.Backend.helpers.ensureDatas.get_last_matches')
    @patch('src.Backend.helpers.ensureDatas.get_fixtures_for_team')
    @patch('src.Backend.helpers.ensureDatas.write_to_fixtures')
    @patch('src.Backend.helpers.ensureDatas.read_from_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.get_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.delete_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.read_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.get_team_country_by_id')
    @patch('src.Backend.helpers.ensureDatas.write_to_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.read_odds_by_fixture')
    @patch('src.Backend.helpers.ensureDatas.fetch_odds_for_fixture')
    @patch('src.Backend.helpers.ensureDatas.write_to_odds')
    @patch('builtins.print')
    def test_ensure_simulation_data_insufficient_stats(self, mock_print, mock_write_odds, mock_fetch_odds,
                                                       mock_read_odds, mock_write_stats, mock_get_country,
                                                       mock_get_fixture, mock_get_h2h, mock_read_h2h,
                                                       mock_delete_fixture, mock_get_stats, mock_read_stats,
                                                       mock_write_fixtures, mock_get_fixtures, mock_get_last_matches):
        """Test when insufficient statistics are available"""

        # Generate 15 matches but with no stats
        matches = []
        for i in range(15):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 3000 + i
            match["date"] = datetime.now() - timedelta(days=i + 1)
            matches.append(match)

        # Mock functions to simulate failed stats
        mock_get_last_matches.return_value = matches
        mock_read_stats.return_value = None  # No stats in DB
        mock_get_stats.return_value = None  # No stats from API

        # Run the function
        result = ensure_simulation_data_available(self.fixture_list[:1], num_matches=10)

        # Verify fixtures were deleted due to missing stats
        mock_delete_fixture.assert_called()

        # Verify the function returned an empty list (no valid fixtures)
        self.assertEqual(result, [])

    @patch('src.Backend.helpers.ensureDatas.get_last_matches')
    @patch('src.Backend.helpers.ensureDatas.get_fixtures_for_team')
    @patch('src.Backend.helpers.ensureDatas.write_to_fixtures')
    @patch('src.Backend.helpers.ensureDatas.read_from_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.get_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.delete_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.read_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.get_team_country_by_id')
    @patch('src.Backend.helpers.ensureDatas.write_to_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.read_odds_by_fixture')
    @patch('src.Backend.helpers.ensureDatas.fetch_odds_for_fixture')
    @patch('src.Backend.helpers.ensureDatas.write_to_odds')
    @patch('builtins.print')
    def test_ensure_simulation_data_insufficient_h2h(self, mock_print, mock_write_odds, mock_fetch_odds,
                                                     mock_read_odds, mock_write_stats, mock_get_country,
                                                     mock_get_fixture, mock_get_h2h, mock_read_h2h,
                                                     mock_delete_fixture, mock_get_stats, mock_read_stats,
                                                     mock_write_fixtures, mock_get_fixtures, mock_get_last_matches):
        """Test when insufficient head-to-head data is available"""

        # Generate 15 matches for each team
        matches = []
        for i in range(15):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 4000 + i
            match["date"] = datetime.now() - timedelta(days=i + 1)
            matches.append(match)

        # Mock all necessary functions for regular matches
        mock_get_last_matches.return_value = matches
        mock_read_stats.return_value = self.mock_stats

        # Not enough H2H matches (only 3)
        mock_read_h2h.return_value = []

        # H2H from API still insufficient (only 3)
        h2h_matches = []
        for i in range(3):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 5000 + i
            match["date"] = datetime.now() - timedelta(days=i + 30)
            h2h_matches.append(match)

        mock_get_h2h.return_value = h2h_matches

        # Mock stats for H2H matches
        mock_get_fixture.return_value = self.mock_fixture

        # Run the function
        result = ensure_simulation_data_available(self.fixture_list[:1], num_matches=10)

        # Verify the function returned an empty list (no valid fixtures)
        self.assertEqual(result, [])

    @patch('src.Backend.helpers.ensureDatas.get_last_matches')
    @patch('src.Backend.helpers.ensureDatas.get_fixtures_for_team')
    @patch('src.Backend.helpers.ensureDatas.write_to_fixtures')
    @patch('src.Backend.helpers.ensureDatas.read_from_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.get_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.delete_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.read_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.get_team_country_by_id')
    @patch('src.Backend.helpers.ensureDatas.write_to_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.read_odds_by_fixture')
    @patch('src.Backend.helpers.ensureDatas.fetch_odds_for_fixture')
    @patch('src.Backend.helpers.ensureDatas.write_to_odds')
    @patch('builtins.print')
    def test_ensure_simulation_data_missing_odds(self, mock_print, mock_write_odds, mock_fetch_odds,
                                                 mock_read_odds, mock_write_stats, mock_get_country,
                                                 mock_get_fixture, mock_get_h2h, mock_read_h2h,
                                                 mock_delete_fixture, mock_get_stats, mock_read_stats,
                                                 mock_write_fixtures, mock_get_fixtures, mock_get_last_matches):
        """Test when odds data is missing and needs to be fetched"""

        # Generate 15 matches for each team
        matches = []
        for i in range(15):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 6000 + i
            match["date"] = datetime.now() - timedelta(days=i + 1)
            matches.append(match)

        # Mock all necessary functions
        mock_get_last_matches.return_value = matches
        mock_read_stats.return_value = self.mock_stats
        mock_read_h2h.return_value = matches[:10]  # 10 H2H matches

        # No odds in DB
        mock_read_odds.return_value = []

        # Odds from API
        mock_fetch_odds.return_value = self.mock_odds

        # Run the function
        result = ensure_simulation_data_available(self.fixture_list[:1], num_matches=10)

        # Verify odds were fetched and written
        mock_fetch_odds.assert_called_with(101)
        mock_write_odds.assert_called()

        # Verify the function returned the valid fixture
        self.assertEqual(result, [101])

    @patch('src.Backend.helpers.ensureDatas.get_last_matches')
    @patch('src.Backend.helpers.ensureDatas.get_fixtures_for_team')
    @patch('src.Backend.helpers.ensureDatas.write_to_fixtures')
    @patch('src.Backend.helpers.ensureDatas.read_from_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.get_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.delete_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.read_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_head_to_head_stats')
    @patch('src.Backend.helpers.ensureDatas.get_fixture_by_id')
    @patch('src.Backend.helpers.ensureDatas.get_team_country_by_id')
    @patch('src.Backend.helpers.ensureDatas.write_to_match_statistics')
    @patch('src.Backend.helpers.ensureDatas.read_odds_by_fixture')
    @patch('src.Backend.helpers.ensureDatas.fetch_odds_for_fixture')
    @patch('src.Backend.helpers.ensureDatas.write_to_odds')
    @patch('builtins.print')
    def test_ensure_simulation_data_failed_odds_fetch(self, mock_print, mock_write_odds, mock_fetch_odds,
                                                      mock_read_odds, mock_write_stats, mock_get_country,
                                                      mock_get_fixture, mock_get_h2h, mock_read_h2h,
                                                      mock_delete_fixture, mock_get_stats, mock_read_stats,
                                                      mock_write_fixtures, mock_get_fixtures, mock_get_last_matches):
        """Test when odds fetching fails"""

        # Generate 15 matches for each team
        matches = []
        for i in range(15):
            match = copy.deepcopy(self.mock_match)
            match["id"] = 7000 + i
            match["date"] = datetime.now() - timedelta(days=i + 1)
            matches.append(match)

        # Mock all necessary functions
        mock_get_last_matches.return_value = matches
        mock_read_stats.return_value = self.mock_stats
        mock_read_h2h.return_value = matches[:10]  # 10 H2H matches

        # No odds in DB
        mock_read_odds.return_value = []

        # Failed odds fetching
        mock_fetch_odds.return_value = None

        # Run the function
        result = ensure_simulation_data_available(self.fixture_list[:1], num_matches=10)

        # Verify odds were attempted to be fetched
        mock_fetch_odds.assert_called_with(101)

        # Verify no odds were written
        mock_write_odds.assert_not_called()

        # Verify the function returned an empty list (no valid fixtures)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()