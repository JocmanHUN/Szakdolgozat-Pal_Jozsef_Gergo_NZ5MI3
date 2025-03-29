import mysql.connector

from src.Backend.DB.connection import get_db_connection


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