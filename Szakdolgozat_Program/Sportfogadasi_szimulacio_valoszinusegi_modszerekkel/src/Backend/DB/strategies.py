from src.Backend.DB.connection import get_db_connection
from src.Backend.DB.odds import get_best_odds_for_fixture


def get_all_strategies():
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_all_strategies).")
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, strategy_name FROM strategies")
        strategies = cursor.fetchall()
        return strategies

    except Exception as e:
        print(f"❌ Hiba történt a get_all_strategies során: {e}")
        return []

    finally:
        cursor.close()
        connection.close()
