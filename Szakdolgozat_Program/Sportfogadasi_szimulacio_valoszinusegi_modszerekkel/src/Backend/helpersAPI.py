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
        query = "SELECT id FROM teams WHERE name = %s"
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
        cursor.close()
        connection.close()

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
    Frissíti az adatbázisban lévő mérkőzések státuszát és egyéb mezőit az API válaszai alapján,
    csak ha valóban változás történt.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return

    cursor = connection.cursor(dictionary=True)
    try:
        # Lekérdezzük az adatbázisból az összes `NS` státuszú mérkőzést
        query = "SELECT id, status, DATE_FORMAT(date, '%Y-%m-%dT%H:%i:%sZ') as date, score_home, score_away FROM fixtures WHERE status = 'NS'"
        cursor.execute(query)
        fixtures = cursor.fetchall()

        for fixture in fixtures:
            fixture_id = fixture["id"]

            # API lekérdezés a mérkőzés adataiért
            url = f"{BASE_URL}fixtures"
            headers = {
                'x-apisports-key': API_KEY,
                'x-rapidapi-host': HOST
            }
            params = {'id': fixture_id}

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json().get("response", [{}])[0]

                # Kinyerjük az adatokat az API válaszból
                new_status = data["fixture"]["status"]["short"]
                new_date = normalize_date(data["fixture"]["date"])
                home_score = data["score"]["fulltime"].get("home")
                away_score = data["score"]["fulltime"].get("away")

                # Normalize értékek összehasonlítás előtt
                db_status = fixture["status"].strip().upper()
                api_status = new_status.strip().upper()
                db_date = normalize_date(fixture["date"])

                db_home_score = fixture["score_home"] if fixture["score_home"] is not None else 0
                db_away_score = fixture["score_away"] if fixture["score_away"] is not None else 0
                api_home_score = home_score if home_score is not None else 0
                api_away_score = away_score if away_score is not None else 0

                # Ellenőrizzük a változásokat
                changes = []
                if db_status != api_status:
                    changes.append(f"status: {db_status} -> {api_status}")
                if db_date != new_date:
                    changes.append(f"date: {db_date} -> {new_date}")
                if db_home_score != api_home_score:
                    changes.append(f"score_home: {db_home_score} -> {api_home_score}")
                if db_away_score != api_away_score:
                    changes.append(f"score_away: {db_away_score} -> {api_away_score}")

                # Csak akkor frissítünk, ha történt változás
                if changes:
                    update_query = """
                        UPDATE fixtures
                        SET 
                            status = %s,
                            date = %s,
                            score_home = %s,
                            score_away = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (
                        new_status,
                        new_date,
                        home_score,
                        away_score,
                        fixture_id
                    ))
                    connection.commit()
                    print(f"Mérkőzés frissítve: {fixture_id}, változások: {', '.join(changes)}")
                else:
                    print(f"Mérkőzés változatlan: {fixture_id}, státusz: {db_status}")

            except requests.exceptions.RequestException as e:
                print(f"API hiba a mérkőzés frissítésekor ({fixture_id}): {e}")

    except mysql.connector.Error as err:
        print(f"Adatbázis hiba a mérkőzések frissítésekor: {err}")
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
    Normalizálja a dátum formátumát UTC-re (ISO 8601), hogy az összehasonlítás biztosan helyes legyen.
    :param date_str: A dátum sztring formátumban.
    :return: ISO 8601 formátumú UTC dátum (pl. 2025-01-12T18:15:00Z).
    """
    if not date_str:
        return None
    # Parse és UTC-re konvertálás
    parsed_date = parser.isoparse(date_str).astimezone(pytz.utc)
    return parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")  # UTC idő formátuma

