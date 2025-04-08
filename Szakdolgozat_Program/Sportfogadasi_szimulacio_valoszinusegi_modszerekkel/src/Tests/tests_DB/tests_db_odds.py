import unittest
from unittest.mock import patch, MagicMock
import mysql.connector
from datetime import datetime

from src.Backend.DB.odds import write_to_odds, read_odds_by_fixture, get_pre_match_fixtures_with_odds, \
    get_odds_by_fixture_id, odds_already_saved, get_best_odds_for_fixture


class TestOddsDB(unittest.TestCase):

    def setUp(self):
        # Mock cursor és connection objektumok létrehozása minden teszthez
        self.mock_cursor = MagicMock()
        self.mock_connection = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_write_to_odds_success(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection

        # Teszt adatok
        test_odds_data = [
            {
                "fixture_id": 1,
                "bookmaker_id": 1,
                "home_odds": 2.5,
                "draw_odds": 3.0,
                "away_odds": 2.8,
                "updated_at": datetime.now()
            },
            {
                "fixture_id": 2,
                "bookmaker_id": 1,
                "home_odds": 1.8,
                "draw_odds": 3.2,
                "away_odds": 4.5,
                "updated_at": datetime.now()
            }
        ]

        # Függvény hívása
        write_to_odds(test_odds_data)

        # Ellenőrzések
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        self.mock_connection.commit.assert_called_once()
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_write_to_odds_db_error(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.execute.side_effect = mysql.connector.Error("Test DB error")

        # Teszt adatok
        test_odds_data = [
            {
                "fixture_id": 1,
                "bookmaker_id": 1,
                "home_odds": 2.5,
                "draw_odds": 3.0,
                "away_odds": 2.8,
                "updated_at": datetime.now()
            }
        ]

        # Függvény hívása
        write_to_odds(test_odds_data)

        # Ellenőrzések
        self.mock_connection.commit.assert_not_called()
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_write_to_odds_no_connection(self, mock_get_db):
        # Mock beállítása: nincs adatbázis kapcsolat
        mock_get_db.return_value = None

        # Teszt adatok
        test_odds_data = [
            {
                "fixture_id": 1,
                "bookmaker_id": 1,
                "home_odds": 2.5,
                "draw_odds": 3.0,
                "away_odds": 2.8,
                "updated_at": datetime.now()
            }
        ]

        # Függvény hívása
        result = write_to_odds(test_odds_data)

        # Ellenőrzések: ha nincs kapcsolat, a függvény nem dob hibát, csak visszatér
        self.assertIsNone(result)

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_read_odds_by_fixture_success(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        expected_results = [
            {
                "fixture_id": 1,
                "bookmaker_id": 1,
                "home_odds": 2.5,
                "draw_odds": 3.0,
                "away_odds": 2.8
            }
        ]
        self.mock_cursor.fetchall.return_value = expected_results

        # Függvény hívása
        result = read_odds_by_fixture(1)

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, expected_results)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_read_odds_by_fixture_db_error(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.execute.side_effect = mysql.connector.Error("Test DB error")

        # Függvény hívása
        result = read_odds_by_fixture(1)

        # Ellenőrzések
        self.assertEqual(result, [])
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_read_odds_by_fixture_no_connection(self, mock_get_db):
        # Mock beállítása: nincs adatbázis kapcsolat
        mock_get_db.return_value = None

        # Függvény hívása
        result = read_odds_by_fixture(1)

        # Ellenőrzések
        self.assertEqual(result, [])

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_pre_match_fixtures_with_odds_success(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        expected_results = [
            {
                "fixture_id": 1,
                "home_team": "Team A",
                "away_team": "Team B",
                "match_date": datetime.now(),
                "home_odds": 2.0,
                "draw_odds": 3.0,
                "away_odds": 4.0
            }
        ]
        self.mock_cursor.fetchall.return_value = expected_results

        # Függvény hívása
        result = get_pre_match_fixtures_with_odds()

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, expected_results)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_pre_match_fixtures_with_odds_db_error(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.execute.side_effect = mysql.connector.Error("Test DB error")

        # Függvény hívása
        result = get_pre_match_fixtures_with_odds()

        # Ellenőrzések
        self.assertEqual(result, [])
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_pre_match_fixtures_with_odds_no_connection(self, mock_get_db):
        # Mock beállítása: nincs adatbázis kapcsolat
        mock_get_db.return_value = None

        # Függvény hívása
        result = get_pre_match_fixtures_with_odds()

        # Ellenőrzések
        self.assertEqual(result, [])

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_odds_by_fixture_id_success(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        expected_results = [
            {
                "bookmaker": "Bookmaker A",
                "home_odds": 2.0,
                "draw_odds": 3.0,
                "away_odds": 4.0
            }
        ]
        self.mock_cursor.fetchall.return_value = expected_results

        # Függvény hívása
        result = get_odds_by_fixture_id(1)

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, expected_results)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_odds_by_fixture_id_db_error(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.execute.side_effect = mysql.connector.Error("Test DB error")

        # Függvény hívása
        result = get_odds_by_fixture_id(1)

        # Ellenőrzések
        self.assertEqual(result, [])
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_odds_by_fixture_id_no_connection(self, mock_get_db):
        # Mock beállítása: nincs adatbázis kapcsolat
        mock_get_db.return_value = None

        # Függvény hívása
        result = get_odds_by_fixture_id(1)

        # Ellenőrzések
        self.assertEqual(result, [])

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_odds_already_saved_true(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.fetchone.return_value = (1,)  # Count > 0, tehát van már mentve

        # Függvény hívása
        result = odds_already_saved(1)

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertTrue(result)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_odds_already_saved_false(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.fetchone.return_value = (0,)  # Count = 0, tehát nincs mentve

        # Függvény hívása
        result = odds_already_saved(1)

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertFalse(result)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_odds_already_saved_db_error(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.execute.side_effect = mysql.connector.Error("Test DB error")

        # Függvény hívása
        result = odds_already_saved(1)

        # Ellenőrzések
        self.assertFalse(result)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_odds_already_saved_no_connection(self, mock_get_db):
        # Mock beállítása: nincs adatbázis kapcsolat
        mock_get_db.return_value = None

        # Függvény hívása
        result = odds_already_saved(1)

        # Ellenőrzések
        self.assertFalse(result)

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_best_odds_for_fixture_home_win(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        expected_result = {
            "bookmaker_id": 1,
            "selected_odds": 2.5
        }
        self.mock_cursor.fetchone.return_value = expected_result

        # Függvény hívása
        result = get_best_odds_for_fixture(1, "1")  # 1 = Home Win

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, expected_result)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_best_odds_for_fixture_draw(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        expected_result = {
            "bookmaker_id": 2,
            "selected_odds": 3.2
        }
        self.mock_cursor.fetchone.return_value = expected_result

        # Függvény hívása
        result = get_best_odds_for_fixture(1, "X")  # X = Draw

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, expected_result)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_best_odds_for_fixture_away_win(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        expected_result = {
            "bookmaker_id": 3,
            "selected_odds": 4.0
        }
        self.mock_cursor.fetchone.return_value = expected_result

        # Függvény hívása
        result = get_best_odds_for_fixture(1, "2")  # 2 = Away Win

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, expected_result)
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()

    @patch('src.Backend.DB.odds.get_db_connection')
    def test_get_best_odds_for_fixture_no_result(self, mock_get_db):
        # Mock beállítása
        mock_get_db.return_value = self.mock_connection
        self.mock_cursor.fetchone.return_value = None  # Nincs találat

        # Függvény hívása
        result = get_best_odds_for_fixture(1, "1")

        # Ellenőrzések
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, (None, None))
        self.mock_cursor.close.assert_called_once()
        self.mock_connection.close.assert_called_once()


        @patch('src.Backend.DB.odds.get_db_connection')
        def test_get_best_odds_for_fixture_no_result(self, mock_get_db):
            # Mock beállítása
            mock_get_db.return_value = self.mock_connection
            self.mock_cursor.fetchone.return_value = None  # Nincs találat

            # Függvény hívása
            result = get_best_odds_for_fixture(1, "1")

            # Ellenőrzések
            self.mock_cursor.execute.assert_called_once()
            self.assertEqual(result, (None, None))
            self.mock_cursor.close.assert_called_once()
            self.mock_connection.close.assert_called_once()

        @patch('src.Backend.DB.odds.get_db_connection')
        def test_get_best_odds_for_fixture_db_error(self, mock_get_db):
            # Mock beállítása
            mock_get_db.return_value = self.mock_connection
            self.mock_cursor.execute.side_effect = Exception("Test error")

            # Függvény hívása
            result = get_best_odds_for_fixture(1, "1")

            # Ellenőrzések
            self.assertEqual(result, (None, None))
            self.mock_cursor.close.assert_called_once()
            self.mock_connection.close.assert_called_once()

        @patch('src.Backend.DB.odds.get_db_connection')
        def test_get_best_odds_for_fixture_no_connection(self, mock_get_db):
            # Mock beállítása: nincs adatbázis kapcsolat
            mock_get_db.return_value = None

            # Függvény hívása
            result = get_best_odds_for_fixture(1, "1")

            # Ellenőrzések
            self.assertEqual(result, (None, None))


if __name__ == '__main__':
    unittest.main()