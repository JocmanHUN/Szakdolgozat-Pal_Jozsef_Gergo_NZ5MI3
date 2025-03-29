from src.Backend.DB.connection import get_db_connection


def get_all_strategies():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, strategy_name FROM strategies")
    strategies = cursor.fetchall()

    cursor.close()
    connection.close()

    return strategies