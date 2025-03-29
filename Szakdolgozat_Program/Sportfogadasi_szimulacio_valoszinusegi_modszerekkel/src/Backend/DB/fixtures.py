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

def update_fixtures_status():
    """
    Csak azokat az `NS` státuszú mérkőzéseket frissíti, amelyek már lejártak vagy ma játszódnak.
    """

    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return

    cursor = connection.cursor(dictionary=True)

    try:
        # **1. Lekérdezzük azokat az `NS` státuszú mérkőzéseket, amelyek már lejártak vagy ma vannak.**
        query = """
            SELECT id, status, DATE_FORMAT(date, '%Y-%m-%dT%H:%i:%sZ') as date, score_home, score_away 
            FROM fixtures 
            WHERE status = 'NS' AND date <= NOW()
        """
        cursor.execute(query)
        fixtures = cursor.fetchall()

        if not fixtures:
            print("Nincs frissítendő mérkőzés.")
            return

        updates = []

        # **2. Egyenként kérjük le az API-ból az adatokat**
        for fixture in fixtures:
            fixture_id = str(fixture["id"])
            url = f"{BASE_URL}fixtures"
            headers = {
                'x-apisports-key': API_KEY,
                'x-rapidapi-host': HOST
            }
            params = {'id': fixture_id, 'timezone': 'Europe/Budapest'}

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            api_data = response.json().get("response", [])
            print(api_data)
            if not api_data:
                continue  # Ha az API nem adott vissza adatot, lépjünk tovább

            api_fixture = api_data[0]

            # Új adatok
            new_status = api_fixture["fixture"]["status"]["short"]
            new_date = normalize_date(api_fixture["fixture"]["date"])

            # **Ellenőrizzük, hogy az eredmény nem None**
            home_score = api_fixture["score"]["fulltime"].get("home")
            away_score = api_fixture["score"]["fulltime"].get("away")

            # Ha nincs eredmény, állítsuk NULL-ra
            home_score = home_score if home_score is not None else None
            away_score = away_score if away_score is not None else None

            # **Ellenőrizzük, hogy minden szükséges adat megvan-e**
            if not all([new_status, new_date, fixture_id]):
                print(f"HIBA: Hiányzó adatok a mérkőzés frissítéséhez: {fixture_id}")
                continue

            updates.append((new_status, new_date, home_score, away_score, fixture_id))

        # **3. Debug: Ellenőrizzük az updates listát**
        print(f"Frissítendő mérkőzések száma: {len(updates)}")
        for update in updates:
            if len(update) != 5:
                print(f"HIBA: Hibás tuple méret az updates listában: {update}")

        # **4. Tömbösített adatbázis frissítés, ha van változás**
        if updates:
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
            print(f"{len(updates)} mérkőzés frissítve.")
            print(updates)

        else:
            print("Nincs változás az adatbázisban.")

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