import mysql.connector

from src.Backend.DB.connection import get_db_connection


def write_to_odds(odds_data):
    """
    Elmenti az oddsokat az adatbázisba.
    """
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO odds (fixture_id, bookmaker_id, home_odds, draw_odds, away_odds, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            home_odds = VALUES(home_odds),
            draw_odds = VALUES(draw_odds),
            away_odds = VALUES(away_odds),
            updated_at = VALUES(updated_at)
    """
    try:
        for odd in odds_data:
            cursor.execute(query, (
                odd["fixture_id"],
                odd["bookmaker_id"],
                odd["home_odds"],
                odd["draw_odds"],
                odd["away_odds"],
                odd["updated_at"]
            ))
        connection.commit()
        print(f"{len(odds_data)} odds mentve.")
    except mysql.connector.Error as err:
        print(f"Database write error for odds: {err}")
    finally:
        cursor.close()
        connection.close()

def read_odds_by_fixture(fixture_id):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM odds WHERE fixture_id = %s"
    try:
        cursor.execute(query, (fixture_id,))
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database read error for odds: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def get_pre_match_fixtures_with_odds():
    """
    Lekérdezi az adatbázisból a pre-match mérkőzéseket és a hozzájuk tartozó oddsokat.
    :return: Lista a mérkőzésekről és oddsokról.
    """
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT 
            f.id AS fixture_id,
            t1.name AS home_team,
            t2.name AS away_team,
            f.date AS match_date,
            o.home_odds,
            o.draw_odds,
            o.away_odds
        FROM fixtures f
        JOIN teams t1 ON f.home_team_id = t1.id
        JOIN teams t2 ON f.away_team_id = t2.id
        LEFT JOIN odds o ON f.id = o.fixture_id
        WHERE f.status = 'NS'
    """
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error fetching fixtures with odds: {err}")
        return []
    finally:
        cursor.close()
        connection.close()
def get_odds_by_fixture_id(fixture_id):
    """
    Lekérdezi az oddsokat egy adott mérkőzéshez az adatbázisból.
    """
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT b.name AS bookmaker, o.home_odds, o.draw_odds, o.away_odds
        FROM odds o
        JOIN bookmakers b ON o.bookmaker_id = b.id
        WHERE o.fixture_id = %s
    """
    try:
        cursor.execute(query, (fixture_id,))
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database read error for odds: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def odds_already_saved(fixture_id):
    """
    Ellenőrzi, hogy az adott mérkőzéshez (fixture_id) már el vannak-e mentve az oddsok az adatbázisban.

    :param fixture_id: A mérkőzés azonosítója.
    :return: True, ha már van mentett odds, False egyébként.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return False

    cursor = connection.cursor()

    try:
        query = "SELECT COUNT(*) FROM odds WHERE fixture_id = %s"
        cursor.execute(query, (fixture_id,))
        result = cursor.fetchone()  # Egyetlen sor eredmény
        return result[0] > 0  # Ha az első elem nagyobb, mint 0, akkor már van elmentett odds
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba: {err}")
        return False
    finally:
        cursor.close()
        connection.close()

def get_best_odds_for_fixture(fixture_id, predicted_outcome):
    """
    Lekérdezi az adott mérkőzéshez tartozó legjobb oddsot és a megfelelő fogadóirodát.

    :param fixture_id: A mérkőzés azonosítója.
    :param predicted_outcome: A modell által előrejelzett eredmény ("Home", "Draw" vagy "Away").
    :return: (legjobb_odds, bookmaker_id) ha találunk, különben (None, None)
    """
    connection = get_db_connection()
    if connection is None:
        return None, None

    cursor = connection.cursor(dictionary=True)

    # Kiválasztjuk a megfelelő oszlopot az eredmény alapján
    column_name = {
        "1": "home_odds",
        "X": "draw_odds",
        "2": "away_odds"
    }.get(predicted_outcome, None)
    if column_name is None:
        return None, None  # Ha a modell érvénytelen eredményt adott vissza

    query = f"""
        SELECT bookmaker_id, {column_name} AS selected_odds
        FROM odds
        WHERE fixture_id = %s
        ORDER BY selected_odds DESC
        LIMIT 1
    """

    try:
        cursor.execute(query, (fixture_id,))
        result = cursor.fetchone()
        if result:
            return result
        return None, None

    except Exception as e:
        print(f"❌ Hiba az odds lekérdezésekor: {e}")
        return None, None

    finally:
        cursor.close()
        connection.close()

