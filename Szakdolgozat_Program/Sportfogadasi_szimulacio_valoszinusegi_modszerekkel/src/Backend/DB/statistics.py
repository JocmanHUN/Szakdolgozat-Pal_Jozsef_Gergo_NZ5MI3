import mysql.connector

from src.Backend.DB.connection import get_db_connection


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
        #AAdatok beszúrása vagy frissítése az adatbázisba
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