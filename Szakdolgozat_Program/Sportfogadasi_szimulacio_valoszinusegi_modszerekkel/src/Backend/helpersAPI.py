import mysql.connector
import requests

from src.config import DB_CONFIG, BASE_URL, API_KEY, HOST
from dateutil import parser
import pytz

def get_db_connection():
    """Establishes the database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return None

# Leagues handling
def write_to_leagues(data):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = "INSERT INTO leagues (id, name, country) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE name=VALUES(name), country=VALUES(country)"
    try:
        for league in data:
            cursor.execute(query, (league['id'], league['name'], league['country']))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database write error for leagues: {err}")
    finally:
        cursor.close()
        connection.close()

def read_from_leagues():
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM leagues")
        leagues = cursor.fetchall()
        return leagues
    except mysql.connector.Error as err:
        print(f"Database read error for leagues: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

# Teams handling
def write_to_teams(data, league_id):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO teams (id, name, country, logo, league_id) 
        VALUES (%s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE name=VALUES(name), country=VALUES(country), logo=VALUES(logo), league_id=VALUES(league_id)
    """
    try:
        for team in data:
            cursor.execute(query, (team['id'], team['name'], team['country'], team['logo'], league_id))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database write error for teams: {err}")
    finally:
        cursor.close()
        connection.close()

def read_from_teams(league_id, season):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT * FROM teams WHERE league_id = %s"
        cursor.execute(query, (league_id,))
        teams = cursor.fetchall()
        return teams
    except mysql.connector.Error as err:
        print(f"Database read error for teams: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

# Fixtures handling
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

            # Mérkőzés beszúrása
            cursor.execute(query, (
                fixture['id'],
                fixture['date'],
                home_team_id,
                away_team_id,
                fixture['score_home'],
                fixture['score_away'],
                fixture['status']
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

# Match statistics handling
def write_to_match_statistics(fixture_id, team_id, statistics):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()

    # SQL query az adatok beszúrásához vagy frissítéséhez
    query = """
        INSERT INTO match_statistics (
            fixture_id, team_id, shots_on_goal, shots_off_goal, total_shots, 
            blocked_shots, shots_insidebox, shots_outsidebox, fouls, corner_kicks, 
            offsides, ball_possession, yellow_cards, red_cards, goalkeeper_saves, 
            total_passes, passes_accurate, passes_percentage
        ) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            shots_on_goal=VALUES(shots_on_goal), 
            shots_off_goal=VALUES(shots_off_goal), 
            total_shots=VALUES(total_shots), 
            blocked_shots=VALUES(blocked_shots), 
            shots_insidebox=VALUES(shots_insidebox), 
            shots_outsidebox=VALUES(shots_outsidebox), 
            fouls=VALUES(fouls), 
            corner_kicks=VALUES(corner_kicks), 
            offsides=VALUES(offsides), 
            ball_possession=VALUES(ball_possession), 
            yellow_cards=VALUES(yellow_cards), 
            red_cards=VALUES(red_cards), 
            goalkeeper_saves=VALUES(goalkeeper_saves), 
            total_passes=VALUES(total_passes), 
            passes_accurate=VALUES(passes_accurate), 
            passes_percentage=VALUES(passes_percentage)
    """

    # Az API válasz alapján a megfelelő értékek kinyerése
    data = {
        'shots_on_goal': None,
        'shots_off_goal': None,
        'total_shots': None,
        'blocked_shots': None,
        'shots_insidebox': None,
        'shots_outsidebox': None,
        'fouls': None,
        'corner_kicks': None,
        'offsides': None,
        'ball_possession': None,
        'yellow_cards': None,
        'red_cards': None,
        'goalkeeper_saves': None,
        'total_passes': None,
        'passes_accurate': None,
        'passes_percentage': None
    }

    # Adatok kitöltése a statisztikai típusok alapján
    for stat in statistics:
        stat_type = stat['type']
        stat_value = stat['value']

        if stat_type == 'Shots on Goal':
            data['shots_on_goal'] = stat_value
        elif stat_type == 'Shots off Goal':
            data['shots_off_goal'] = stat_value
        elif stat_type == 'Total Shots':
            data['total_shots'] = stat_value
        elif stat_type == 'Blocked Shots':
            data['blocked_shots'] = stat_value
        elif stat_type == 'Shots insidebox':
            data['shots_insidebox'] = stat_value
        elif stat_type == 'Shots outsidebox':
            data['shots_outsidebox'] = stat_value
        elif stat_type == 'Fouls':
            data['fouls'] = stat_value
        elif stat_type == 'Corner Kicks':
            data['corner_kicks'] = stat_value
        elif stat_type == 'Offsides':
            data['offsides'] = stat_value
        elif stat_type == 'Ball Possession':
            data['ball_possession'] = stat_value
        elif stat_type == 'Yellow Cards':
            data['yellow_cards'] = stat_value
        elif stat_type == 'Red Cards':
            data['red_cards'] = stat_value
        elif stat_type == 'Goalkeeper Saves':
            data['goalkeeper_saves'] = stat_value
        elif stat_type == 'Total passes':
            data['total_passes'] = stat_value
        elif stat_type == 'Passes accurate':
            data['passes_accurate'] = stat_value
        elif stat_type == 'Passes %':
            data['passes_percentage'] = stat_value

    try:
        # Adatok beszúrása vagy frissítése az adatbázisba
        cursor.execute(query, (
            fixture_id, team_id,
            data['shots_on_goal'], data['shots_off_goal'], data['total_shots'],
            data['blocked_shots'], data['shots_insidebox'], data['shots_outsidebox'],
            data['fouls'], data['corner_kicks'], data['offsides'],
            data['ball_possession'], data['yellow_cards'], data['red_cards'],
            data['goalkeeper_saves'], data['total_passes'], data['passes_accurate'],
            data['passes_percentage']
        ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Adatbázis írási hiba: {err}")
    finally:
        cursor.close()
        connection.close()


def read_from_match_statistics(fixture_id):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT * FROM match_statistics WHERE fixture_id = %s"
        cursor.execute(query, (fixture_id,))
        stats = cursor.fetchall()
        return stats
    except mysql.connector.Error as err:
        print(f"Database read error for match statistics: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


def write_to_cards(data, team_id, season):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO cards (
            team_id, season, yellow_cards, red_cards,
            yellow_cards_0_15, yellow_cards_16_30, yellow_cards_31_45, yellow_cards_46_60, yellow_cards_61_75, yellow_cards_76_90, yellow_cards_91_105, yellow_cards_106_120,
            red_cards_0_15, red_cards_16_30, red_cards_31_45, red_cards_46_60, red_cards_61_75, red_cards_76_90, red_cards_91_105, red_cards_106_120
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            yellow_cards=VALUES(yellow_cards), red_cards=VALUES(red_cards),
            yellow_cards_0_15=VALUES(yellow_cards_0_15), yellow_cards_16_30=VALUES(yellow_cards_16_30), yellow_cards_31_45=VALUES(yellow_cards_31_45), 
            yellow_cards_46_60=VALUES(yellow_cards_46_60), yellow_cards_61_75=VALUES(yellow_cards_61_75), yellow_cards_76_90=VALUES(yellow_cards_76_90), 
            yellow_cards_91_105=VALUES(yellow_cards_91_105), yellow_cards_106_120=VALUES(yellow_cards_106_120),
            red_cards_0_15=VALUES(red_cards_0_15), red_cards_16_30=VALUES(red_cards_16_30), red_cards_31_45=VALUES(red_cards_31_45), 
            red_cards_46_60=VALUES(red_cards_46_60), red_cards_61_75=VALUES(red_cards_61_75), red_cards_76_90=VALUES(red_cards_76_90), 
            red_cards_91_105=VALUES(red_cards_91_105), red_cards_106_120=VALUES(red_cards_106_120)
    """
    try:
        cursor.execute(query, (
            team_id, season,
            data['yellow_cards'], data['red_cards'],
            data['yellow_cards_0_15'], data['yellow_cards_16_30'], data['yellow_cards_31_45'],
            data['yellow_cards_46_60'], data['yellow_cards_61_75'],
            data['yellow_cards_76_90'], data['yellow_cards_91_105'], data['yellow_cards_106_120'],
            data['red_cards_0_15'], data['red_cards_16_30'], data['red_cards_31_45'], data['red_cards_46_60'],
            data['red_cards_61_75'],
            data['red_cards_76_90'], data['red_cards_91_105'], data['red_cards_106_120']
        ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Adatbázis írási hiba: {err}")
        print(f"Adatok: {data}, Csapat ID: {team_id}, Szezon: {season}")
    finally:
        cursor.close()
        connection.close()


def read_from_cards(team_id, season):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT * FROM cards WHERE team_id = %s AND season = %s"
        cursor.execute(query, (team_id, season))
        cards = cursor.fetchall()
        return cards
    except mysql.connector.Error as err:
        print(f"Database read error for cards: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def get_or_create_team(team_id, team_name, country, logo):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor(dictionary=True)

    # Ellenőrizzük, hogy a csapat létezik-e
    cursor.execute("SELECT id FROM teams WHERE id = %s", (team_id,))
    team = cursor.fetchone()

    if not team:
        # Ha a csapat nem létezik, beszúrjuk az adatbázisba
        try:
            query = """
                INSERT INTO teams (id, name, country, logo) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (team_id, team_name, country, logo))
            connection.commit()
            print(f"Új csapat beszúrva: {team_name}")
        except mysql.connector.Error as err:
            print(f"Adatbázis írási hiba csapat esetén: {err}")
        finally:
            cursor.close()
            connection.close()
    else:
        print(f"Csapat már létezik: {team_name}")


def get_team_id_by_name(team_name):
    """Lekéri a csapat azonosítóját a neve alapján az adatbázisból."""
    connection = get_db_connection()
    if connection is None:
        return None

    cursor = connection.cursor()
    try:
        query = "SELECT id FROM teams WHERE name = %s LIMIT 1"
        cursor.execute(query, (team_name,))
        result = cursor.fetchone()

        if result:
            return result[0]  # A csapat azonosítója
        else:
            return None  # Ha a csapat nem található
    except mysql.connector.Error as err:
        print(f"Database read error for team: {err}")
        return None
    finally:
        if cursor:
            cursor.close()  # Bezárjuk a kurzort
        if connection:
            connection.close()  # Bezárjuk az adatbázis kapcsolatot


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

def save_bookmakers(bookmakers):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO bookmakers (id, name)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name)
    """
    try:
        for bookmaker_id, bookmaker_name in bookmakers.items():
            cursor.execute(query, (bookmaker_id, bookmaker_name))
        connection.commit()
        print(f"{len(bookmakers)} fogadóiroda mentve az adatbázisba.")
    except mysql.connector.Error as err:
        print(f"Database write error for bookmakers: {err}")
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

def read_from_bookmakers():
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name FROM bookmakers")
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database read error for bookmakers: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


def normalize_date(date_str):
    """
    Normalizálja az API-ból kapott dátumot. Ha már UTC-ben van, nem módosít rajta.
    """
    if not date_str:
        return None

    parsed_date = parser.isoparse(date_str)

    # Ha már UTC-ben van (tartalmaz "Z"-t vagy időzónát), akkor csak a formátumot egységesítjük
    if parsed_date.tzinfo is not None:
        return parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Ha nincs időzóna információ, feltételezzük, hogy helyi idő és UTC-re konvertáljuk
    return parsed_date.replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

def check_group_name_exists(simulation_name):
    """
    Ellenőrzi, hogy létezik-e már egy adott nevű szimuláció a match_groups táblában.

    :param simulation_name: A keresett szimuláció neve.
    :return: True, ha a szimuláció már létezik, különben False.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return False

    cursor = connection.cursor()
    try:
        query = "SELECT id FROM match_groups WHERE name = %s"  # ✅ A helyes oszlopnév: name
        cursor.execute(query, (simulation_name,))
        result = cursor.fetchone()
        return result is not None  # True, ha van ilyen név, különben False
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba a szimuláció ellenőrzése közben: {err}")
        return False
    finally:
        cursor.close()
        connection.close()

def save_match_to_group(match_group_id, fixture_id):
    """
    Kapcsolótáblába szúrja a mérkőzéseket a megadott mérkőzéscsoport ID-hoz.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return

    cursor = connection.cursor()
    try:
        # Ellenőrizzük, hogy a mérkőzés már hozzá van-e rendelve a csoporthoz
        cursor.execute("""
            SELECT 1 FROM match_group_fixtures WHERE match_group_id = %s AND fixture_id = %s
        """, (match_group_id, fixture_id))
        result = cursor.fetchone()

        if not result:
            # Ha még nincs benne, akkor beszúrjuk
            cursor.execute("""
                INSERT INTO match_group_fixtures (match_group_id, fixture_id) VALUES (%s, %s)
            """, (match_group_id, fixture_id))
            connection.commit()
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba mérkőzés-csoport mentésénél: {err}")
    finally:
        cursor.close()
        connection.close()


def save_match_group(match_group_name):
    """
    Ha még nincs ilyen mérkőzéscsoport, létrehozza, majd visszaadja annak ID-ját.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return None

    cursor = connection.cursor()
    try:
        # Ellenőrizzük, hogy létezik-e már ilyen nevű mérkőzéscsoport
        cursor.execute("SELECT id FROM match_groups WHERE name = %s", (match_group_name,))
        result = cursor.fetchone()

        if result:
            match_group_id = result[0]  # Ha létezik, visszaadjuk az ID-t
        else:
            # Ha nem létezik, létrehozzuk
            cursor.execute("INSERT INTO match_groups (name) VALUES (%s)", (match_group_name,))
            connection.commit()
            match_group_id = cursor.lastrowid  # Az újonnan létrehozott ID

        return match_group_id
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba mérkőzéscsoport mentésénél: {err}")
        return None
    finally:
        cursor.close()
        connection.close()

def load_simulations_from_db():
    """Lekérdezi az adatbázisból az összes szimulációt."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, name, created_at FROM match_groups ORDER BY created_at DESC")
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba szimulációk lekérdezésekor: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def fetch_fixtures_for_simulation(simulation_id):
    """Lekéri az adott szimulációhoz tartozó mérkőzéseket az adatbázisból."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT f.id AS fixture_id, 
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
        return cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Adatbázis hiba mérkőzések lekérdezésekor: {err}")
        return []
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



def read_head_to_head_stats(home_team_id, away_team_id):
    """
    Lekérdezi az utolsó 5 egymás elleni mérkőzést a fixtures táblából.

    :param home_team_id: Hazai csapat ID.
    :param away_team_id: Vendég csapat ID.
    :return: Lista az utolsó 5 mérkőzésről, ahol a két csapat játszott egymás ellen.
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
            LIMIT 5
        """
        cursor.execute(query, (home_team_id, away_team_id, away_team_id, home_team_id))
        h2h_matches = cursor.fetchall()

        if not h2h_matches:
            print(f"⚠️ Nincs elérhető H2H mérkőzés az adatbázisban ({home_team_id} vs {away_team_id}).")
        else:
            print(f"✅ {len(h2h_matches)} H2H mérkőzés található az adatbázisban ({home_team_id} vs {away_team_id}).")

        return h2h_matches

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

def get_existing_h2h_matches(home_team_id, away_team_id):
    """
    Lekérdezi az adatbázisból a már létező H2H mérkőzéseket, kizárva a pre-match státuszúakat.
    """
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT * FROM fixtures 
    WHERE 
    ((home_team_id = %s AND away_team_id = %s) 
    OR (home_team_id = %s AND away_team_id = %s))
    AND status NOT IN ('NS', 'TBD', 'POSTP')
    ORDER BY date DESC
    LIMIT 5;
    """
    cursor.execute(query, (home_team_id, away_team_id, away_team_id, home_team_id))
    matches = cursor.fetchall()
    cursor.close()
    connection.close()

    return matches

def save_model_prediction(fixture_id, model_id, predicted_outcome, probability, match_group_id):
    """
    Elmenti a modellek predikcióit az adatbázisba.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO model_predictions (fixture_id, model_id, predicted_outcome, probability, match_group_id)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (fixture_id, model_id, predicted_outcome, probability, match_group_id))
        connection.commit()

        print(
            f"✅ Predikció mentve: Fixture ID: {fixture_id}, Model ID: {model_id}, Outcome: {predicted_outcome}, Probability: {probability}%")

    except Exception as e:
        print(f"❌ Hiba történt a predikció mentése közben: {e}")

    finally:
        cursor.close()
        connection.close()


def get_league_by_team(team_id):
    """
    Lekéri az adott csapat aktuális ligáját az adatbázisból.
    Az utolsó bejegyzett mérkőzés alapján határozza meg a ligát.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT league_id 
            FROM teams 
            WHERE id = %s
        """
        cursor.execute(query, (team_id,))  # 🔹 Itt csak egy paraméter kell, ezért a vesszőt meg kell tartani!

        result = cursor.fetchone()
        print(f"Ita: {result}")
        if result:
            return result["league_id"]
        else:
            print(f"⚠️ Nincs találat az adatbázisban erre a team_id-re: {team_id}")
            return None

    except Exception as e:
        print(f"❌ Hiba történt a liga lekérdezésekor csapat alapján: {e}")
        return None

    finally:
        cursor.close()
        connection.close()

def get_predictions_for_fixture(fixture_id):
    """
    Lekérdezi egy adott mérkőzéshez tartozó modellek előrejelzéseit az adatbázisból.
    """
    connection = get_db_connection()
    if connection is None:
        return {}

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT model_id, predicted_outcome, probability
    FROM model_predictions
    WHERE fixture_id = %s
    """

    cursor.execute(query, (fixture_id,))
    predictions = cursor.fetchall()
    cursor.close()
    connection.close()

    # Modell ID-k leképezése a megfelelő nevekre
    model_map = {
        1: "bayes_classic",
        2: "monte_carlo",
        3: "poisson",
        4: "bayes_empirical",
        5: "log_reg",
        6: "elo"
    }

    model_predictions = {name: "-" for name in model_map.values()}  # Alapértelmezett érték '-'

    for pred in predictions:
        model_name = model_map.get(pred["model_id"])
        if model_name:
            model_predictions[model_name] = f"{pred['predicted_outcome']} ({pred['probability']}%)"

    return model_predictions

