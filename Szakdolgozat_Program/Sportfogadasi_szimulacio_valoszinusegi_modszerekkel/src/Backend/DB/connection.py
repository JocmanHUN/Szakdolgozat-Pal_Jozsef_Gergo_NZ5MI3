import mysql.connector
import time
from src.config import DB_CONFIG

def get_db_connection(retries=10, delay=5):
    """
    Megpróbál csatlakozni az adatbázishoz, legfeljebb `retries` alkalommal.
    Ha nem sikerül, None-t ad vissza.
    """
    for attempt in range(1, retries+1):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            return connection
        except mysql.connector.Error as err:
            print(f"Adatbázis hiba: {err} (próba: {attempt}/{retries})")
            if attempt < retries:
                time.sleep(delay)
    # Ha idáig eljutunk, nem sikerült a csatlakozás
    return None
