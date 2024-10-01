import mysql.connector
from src.config import DB_CONFIG

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

            # Lekérjük a hazai és vendég csapat adatait
            get_or_create_team(home_team_id, fixture['home_team_name'], fixture['home_team_country'], fixture['home_team_logo'])
            get_or_create_team(away_team_id, fixture['away_team_name'], fixture['away_team_country'], fixture['away_team_logo'])

            # Ha a csapatok már léteznek az adatbázisban, beszúrjuk a mérkőzést
            cursor.execute(query, (
                fixture['id'],
                fixture['date'],
                fixture['home_team_id'],
                fixture['away_team_id'],
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
def write_to_match_statistics(data):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO match_statistics (id, fixture_id, team_id, type, value) 
        VALUES (%s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE type=VALUES(type), value=VALUES(value)
    """
    try:
        for stat in data:
            # Ellenőrizzük, hogy a 'stat' tartalmazza-e az 'id' mezőt
            stat_id = stat.get('id')
            if not stat_id:
                print(f"Hiányzó 'id' mező a statisztikában: {stat}")
                continue  # Ha nincs 'id', akkor kihagyjuk ezt a statisztikát

            cursor.execute(query, (
                stat_id,
                stat['fixture_id'],
                stat['team_id'],
                stat['type'],
                stat['value']
            ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database write error for match statistics: {err}")
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

# Cards handling
def write_to_cards(data):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO cards (id, fixture_id, team_id, yellow_cards, red_cards) 
        VALUES (%s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE yellow_cards=VALUES(yellow_cards), red_cards=VALUES(red_cards)
    """
    try:
        for card in data:
            cursor.execute(query, (
                card['id'],
                card['fixture_id'],
                card['team_id'],
                card['yellow_cards'],
                card['red_cards']
            ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database write error for cards: {err}")
    finally:
        cursor.close()
        connection.close()

def read_from_cards(fixture_id):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT * FROM cards WHERE fixture_id = %s"
        cursor.execute(query, (fixture_id,))
        cards = cursor.fetchall()
        return cards
    except mysql.connector.Error as err:
        print(f"Database read error for cards: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

# Goals handling
def write_to_goals(data):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO goals (id, fixture_id, team_id, goals_for, goals_against) 
        VALUES (%s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE goals_for=VALUES(goals_for), goals_against=VALUES(goals_against)
    """
    try:
        for goal in data:
            cursor.execute(query, (
                goal['id'],
                goal['fixture_id'],
                goal['team_id'],
                goal['goals_for'],
                goal['goals_against']
            ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database write error for goals: {err}")
    finally:
        cursor.close()
        connection.close()

def read_from_goals(fixture_id):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT * FROM goals WHERE fixture_id = %s"
        cursor.execute(query, (fixture_id,))
        goals = cursor.fetchall()
        return goals
    except mysql.connector.Error as err:
        print(f"Database read error for goals: {err}")
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

