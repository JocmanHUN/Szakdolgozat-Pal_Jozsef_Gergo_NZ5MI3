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