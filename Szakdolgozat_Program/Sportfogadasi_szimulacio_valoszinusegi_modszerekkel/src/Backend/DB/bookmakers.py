import mysql.connector

from src.Backend.DB.connection import get_db_connection


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