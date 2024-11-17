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


def write_to_cards(data, team_id):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO cards (
            team_id, yellow_cards, red_cards,
            yellow_cards_0_15, yellow_cards_16_30, yellow_cards_31_45, yellow_cards_46_60, yellow_cards_61_75, yellow_cards_76_90, yellow_cards_91_105, yellow_cards_106_120,
            red_cards_0_15, red_cards_16_30, red_cards_31_45, red_cards_46_60, red_cards_61_75, red_cards_76_90, red_cards_91_105, red_cards_106_120
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        for card in data:
            cursor.execute(query, (
                team_id,
                card['yellow_cards'], card['red_cards'],
                card['yellow_cards_0_15'], card['yellow_cards_16_30'], card['yellow_cards_31_45'], card['yellow_cards_46_60'], card['yellow_cards_61_75'],
                card['yellow_cards_76_90'], card['yellow_cards_91_105'], card['yellow_cards_106_120'],
                card['red_cards_0_15'], card['red_cards_16_30'], card['red_cards_31_45'], card['red_cards_46_60'], card['red_cards_61_75'],
                card['red_cards_76_90'], card['red_cards_91_105'], card['red_cards_106_120']
            ))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database write error for cards: {err}")
    finally:
        cursor.close()
        connection.close()


def read_from_cards(team_id):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT * FROM cards WHERE team_id = %s"
        cursor.execute(query, (team_id,))
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
