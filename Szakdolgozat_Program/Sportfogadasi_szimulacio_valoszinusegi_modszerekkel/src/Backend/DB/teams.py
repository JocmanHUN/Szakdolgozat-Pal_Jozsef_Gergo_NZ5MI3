import mysql.connector
from src.Backend.DB.connection import get_db_connection


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

def read_from_teams(league_id):
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

def write_league_id_to_team(team_id, league_id):
    """
    Frissíti a megadott csapat league_id értékét az adatbázisban.

    :param team_id: A frissítendő csapat azonosítója.
    :param league_id: A liga azonosító, amit be kell állítani.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        update_query = """
            UPDATE teams
            SET league_id = %s
            WHERE id = %s
        """

        cursor.execute(update_query, (league_id, team_id))
        connection.commit()

        if cursor.rowcount > 0:
            print(f"✅ Liga azonosító sikeresen frissítve: team_id={team_id}, league_id={league_id}")
        else:
            print(f"⚠️ Nem található csapat ezzel a team_id-vel: {team_id}")

    except Exception as e:
        print(f"❌ Hiba történt a liga frissítésekor az adatbázisban: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
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
        print(team_id)
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

def get_team_name_from_db(team_id):
    """
    Lekéri a csapat nevét az adatbázisból a megadott csapat ID alapján.
    """
    connection = get_db_connection()  # Az adatbázis kapcsolat itt jön létre
    if connection is None:
        return 'Unknown'

    cursor = connection.cursor(dictionary=True)
    query = "SELECT name FROM teams WHERE id = %s"
    cursor.execute(query, (team_id,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    return result['name'] if result else 'Unknown'