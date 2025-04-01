import mysql.connector
import requests

from src.Backend.DB.connection import get_db_connection
from src.Backend.DB.statistics import read_from_match_statistics
from src.Backend.DB.teams import get_or_create_team
from src.Backend.DB.utils import normalize_date
from src.config import BASE_URL, API_KEY, HOST


def write_to_fixtures(data):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO fixtures (id, date, home_team_id, away_team_id, score_home, score_away, status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE date=VALUES(date), home_team_id=VALUES(home_team_id), 
        away_team_id=VALUES(away_team_id), score_home=VALUES(score_home), 
        score_away=VALUES(score_away), status=VALUES(status)
    """
    try:
        for fixture in data:
            home_team_id = fixture['home_team_id']
            away_team_id = fixture['away_team_id']

                # Csapatok létezésének ellenőrzése vagy létrehozása
            get_or_create_team(home_team_id, fixture['home_team_name'], fixture['home_team_country'], fixture['home_team_logo'])
            get_or_create_team(away_team_id, fixture['away_team_name'], fixture['away_team_country'], fixture['away_team_logo'])

            status = fixture['status']['short'] if isinstance(fixture['status'], dict) else fixture['status']
            # Mérkőzés beszúrása
            cursor.execute(query, (
                    fixture['id'],
                    fixture['date'],
                    home_team_id,
                    away_team_id,
                    fixture['score_home'],
                    fixture['score_away'],
                    status
                ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Adatbázis írási hiba mérkőzések esetén: {err}")
    finally:
        cursor.close()
        connection.close()


def read_from_fixtures(league_id, season, from_date=None, to_date=None):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT * FROM fixtures 
            WHERE home_team_id IN (SELECT id FROM teams WHERE league_id = %s) 
              AND away_team_id IN (SELECT id FROM teams WHERE league_id = %s)
        """
        params = (league_id, league_id)
        if from_date:
            query += " AND date >= %s"
            params += (from_date,)
        if to_date:
            query += " AND date <= %s"
            params += (to_date,)
        cursor.execute(query, params)
        fixtures = cursor.fetchall()
        return fixtures
    except mysql.connector.Error as err:
        print(f"Database read error for fixtures: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def update_fixture_status(updates):
    """
    Tömbösített adatbázis frissítés.
    :param updates: Lista tuple-ökből, melyek a következőt tartalmazzák:
                    (new_status, new_date, home_score, away_score, fixture_id)
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz.")
        return

    cursor = connection.cursor()

    try:
        update_query = """
            UPDATE fixtures
            SET 
                status = %s,
                date = %s,
                score_home = %s,
                score_away = %s
            WHERE id = %s
        """
        cursor.executemany(update_query, updates)
        connection.commit()
        print(f"✅ {cursor.rowcount} mérkőzés frissítve az adatbázisban.")
    except Exception as e:
        print(f"❌ Hiba történt az adatbázis frissítésekor: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

def get_fixtures_with_updatable_status():
    """
    Lekéri azokat a meccseket, amelyek frissíthetők:
    - Nem végződtek még (`FT`),
    - És/vagy NS státuszúak, de már legalább 2 órája kezdődniük kellett volna.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz.")
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT id, status, date, score_home, score_away
            FROM fixtures
            WHERE 
                status IN ('NS', '1H', 'HT', '2H', 'ET', 'BT', 'P', 'SUSP', 'INT')
                AND (
                status != 'NS'
                OR (status = 'NS' AND TIMESTAMPDIFF(MINUTE, date, NOW()) >= 120)
                )
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_last_matches(team_id, opponent_id=None, num_matches=10):
    """
    Lekéri egy csapat utolsó X mérkőzését az adatbázisból, kizárva azokat, ahol az ellenfél az opponent_id.

    :param team_id: A csapat azonosítója.
    :param opponent_id: Ha meg van adva, kizárja az ellene játszott mérkőzéseket.
    :param num_matches: Hány mérkőzést kérjünk le (alapértelmezett: 10).
    :return: Lista a csapat legutóbbi X mérkőzéséről.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz.")
        return []

    cursor = connection.cursor(dictionary=True)

    try:
        query = """
                SELECT f.id, f.date, 
                       f.home_team_id, ht.name AS home_team_name, 
                       f.away_team_id, at.name AS away_team_name, 
                       f.score_home, f.score_away, f.status
                FROM fixtures f
                JOIN teams ht ON f.home_team_id = ht.id
                JOIN teams at ON f.away_team_id = at.id
                WHERE (f.home_team_id = %s OR f.away_team_id = %s)
                AND f.date < NOW()
        """

        # Ha van megadott ellenfél (opponent_id), kizárjuk azokat a mérkőzéseket
        params = [team_id, team_id]
        if opponent_id:
            query += " AND NOT (f.home_team_id = %s AND f.away_team_id = %s) AND NOT (f.home_team_id = %s AND f.away_team_id = %s)"
            params.extend([opponent_id, team_id, team_id, opponent_id])

        query += " ORDER BY f.date DESC LIMIT %s"
        params.append(num_matches)

        cursor.execute(query, tuple(params))
        matches = cursor.fetchall()

        if not matches:
            print(f"⚠️ Nincs elég múltbeli mérkőzés az adatbázisban (Csapat ID: {team_id}).")
        else:
            print(f"✅ {len(matches)} mérkőzés található az adatbázisban (Csapat ID: {team_id}).")

        return matches

    except mysql.connector.Error as err:
        print(f"❌ Adatbázis hiba a mérkőzések lekérdezésekor: {err}")
        return []

    finally:
        cursor.close()
        connection.close()

def fetch_fixtures_for_simulation(simulation_id):
    """Lekéri az adott szimulációhoz tartozó mérkőzéseket, beleértve az aktuális állapotot és végeredményt is."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT f.id AS fixture_id, 
                   f.status,  -- Mérkőzés státusza (NS, FT, stb.)
                   f.score_home,  -- Hazai csapat pontszáma
                   f.score_away,  -- Vendég csapat pontszáma
                   t1.name AS home_team, 
                   t2.name AS away_team, 
                   f.date AS match_date
            FROM match_group_fixtures mgf
            JOIN fixtures f ON mgf.fixture_id = f.id
            JOIN teams t1 ON f.home_team_id = t1.id
            JOIN teams t2 ON f.away_team_id = t2.id
            WHERE mgf.match_group_id = %s
        """
        cursor.execute(query, (simulation_id,))
        results = cursor.fetchall()  # Több mérkőzés lehet egy szimulációhoz

        print("🔍 DEBUG: Lekért mérkőzések adatai:", results)  # Debug célokra

        return results

    except mysql.connector.Error as err:
        print(f"❌ Adatbázis hiba mérkőzések lekérdezésekor: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def read_head_to_head_stats(home_team_id, away_team_id):
    """
    Lekérdezi az utolsó 5 egymás elleni mérkőzést a fixtures táblából, kizárólag azokat,
    amelyekhez van elmentett statisztika. Ha nincs, törli a mérkőzést az adatbázisból.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz.")
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT f.id, f.date, 
                   f.home_team_id, ht.name AS home_team_name, 
                   f.away_team_id, at.name AS away_team_name, 
                   f.score_home, f.score_away, f.status
            FROM fixtures f
            JOIN teams ht ON f.home_team_id = ht.id
            JOIN teams at ON f.away_team_id = at.id
            WHERE ((f.home_team_id = %s AND f.away_team_id = %s) 
                OR (f.home_team_id = %s AND f.away_team_id = %s))
                AND f.date < NOW()
            ORDER BY f.date DESC
        """
        cursor.execute(query, (home_team_id, away_team_id, away_team_id, home_team_id))
        matches = cursor.fetchall()

        valid_matches = []
        for match in matches:
            stats = read_from_match_statistics(match["id"])
            if stats:
                valid_matches.append(match)
            else:
                print(f"❌ Nincs stat az API-ban sem, törlés: {match['id']}")
                delete_fixture_by_id(match["id"])

        if valid_matches:
            print(f"📊 Összesen {len(valid_matches)} H2H meccshez van statisztika ({home_team_id} vs {away_team_id}).")
        else:
            print(f"⚠️ Nincs statisztikával rendelkező H2H meccs az adatbázisban ({home_team_id} vs {away_team_id}).")

        return valid_matches  # max 5 visszaadva

    except mysql.connector.Error as err:
        print(f"❌ Adatbázis hiba H2H statisztikák lekérdezésekor: {err}")
        return []

    finally:
        cursor.close()
        connection.close()

def check_h2h_match_exists(match_id):
    """
    Ellenőrzi, hogy egy adott H2H mérkőzés már létezik-e az adatbázisban és befejeződött-e.
    :param match_id: A mérkőzés egyedi azonosítója (API-ból kapott ID).
    :return: True, ha már létezik és nem pre-match, False, ha nem.
    """
    connection = get_db_connection()
    if connection is None:
        return False

    cursor = connection.cursor()
    query = """
        SELECT id FROM fixtures 
        WHERE id = %s AND status NOT IN ('NS', 'TBD', 'POSTP')
    """
    cursor.execute(query, (match_id,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    return result is not None

def get_pre_match_fixtures():
    """
    Lekérdezi az adatbázisból az összes pre-match (NS státuszú) mérkőzést.
    :return: A mérkőzések listája.
    """
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT 
            fixtures.id AS fixture_id,
            fixtures.date AS match_date,
            home_team.name AS home_team,
            away_team.name AS away_team
            FROM fixtures
            LEFT JOIN teams AS home_team ON fixtures.home_team_id = home_team.id
            LEFT JOIN teams AS away_team ON fixtures.away_team_id = away_team.id
            WHERE fixtures.status = 'NS' 
            AND fixtures.date >= NOW()
            ORDER BY fixtures.date ASC;
        """
        cursor.execute(query)
        fixtures = cursor.fetchall()
        return fixtures
    except mysql.connector.Error as err:
        print(f"Database read error for fixtures: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def delete_fixture_by_id(fixture_id):
    """
    Törli az adott ID-jű mérkőzést a 'fixtures' táblából, ha létezik.

    :param fixture_id: A törlendő mérkőzés azonosítója.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz a törléshez.")
        return

    cursor = connection.cursor()

    try:
        # Először ellenőrizzük, hogy létezik-e a meccs
        cursor.execute("SELECT id FROM fixtures WHERE id = %s", (fixture_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("DELETE FROM fixtures WHERE id = %s", (fixture_id,))
            connection.commit()
            print(f"🗑️ Mérkőzés törölve az adatbázisból (Fixture ID: {fixture_id})")
        else:
            print(f"ℹ️ A mérkőzés nem található az adatbázisban (Fixture ID: {fixture_id})")

    except Exception as e:
        print(f"❌ Hiba történt a mérkőzés törlése közben: {e}")

    finally:
        cursor.close()
        connection.close()

def get_fixture_result(fixture_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT actual_result, odds_home, odds_draw, odds_away FROM fixtures WHERE id = %s AND status = 'FT'
    """, (fixture_id,))

    result = cursor.fetchone()
    cursor.close()
    connection.close()

    return result