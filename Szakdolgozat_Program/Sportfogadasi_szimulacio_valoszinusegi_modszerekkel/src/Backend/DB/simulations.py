import mysql.connector

from src.Backend.DB.connection import get_db_connection


def check_group_name_exists(simulation_name):
    """
    Ellenőrzi, hogy létezik-e már egy adott nevű szimuláció a match_groups táblában.

    :param simulation_name: A keresett szimuláció neve.
    :return: True, ha a szimuláció már létezik, különben False.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return False

    cursor = connection.cursor()
    try:
        query = "SELECT id FROM match_groups WHERE name = %s"  # ✅ A helyes oszlopnév: name
        cursor.execute(query, (simulation_name,))
        result = cursor.fetchone()
        return result is not None  # True, ha van ilyen név, különben False
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba a szimuláció ellenőrzése közben: {err}")
        return False
    finally:
        cursor.close()
        connection.close()

def save_match_to_group(match_group_id, fixture_id):
    """
    Kapcsolótáblába szúrja a mérkőzéseket a megadott mérkőzéscsoport ID-hoz.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return

    cursor = connection.cursor()
    try:
        # Ellenőrizzük, hogy a mérkőzés már hozzá van-e rendelve a csoporthoz
        cursor.execute("""
            SELECT 1 FROM match_group_fixtures WHERE match_group_id = %s AND fixture_id = %s
        """, (match_group_id, fixture_id))
        result = cursor.fetchone()

        if not result:
            # Ha még nincs benne, akkor beszúrjuk
            cursor.execute("""
                INSERT INTO match_group_fixtures (match_group_id, fixture_id) VALUES (%s, %s)
            """, (match_group_id, fixture_id))
            connection.commit()
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba mérkőzés-csoport mentésénél: {err}")
    finally:
        cursor.close()
        connection.close()


def save_match_group(match_group_name):
    """
    Ha még nincs ilyen mérkőzéscsoport, létrehozza, majd visszaadja annak ID-ját.
    """
    connection = get_db_connection()
    if connection is None:
        print("Nem sikerült csatlakozni az adatbázishoz.")
        return None

    cursor = connection.cursor()
    try:
        # Ellenőrizzük, hogy létezik-e már ilyen nevű mérkőzéscsoport
        cursor.execute("SELECT id FROM match_groups WHERE name = %s", (match_group_name,))
        result = cursor.fetchone()

        if result:
            match_group_id = result[0]  # Ha létezik, visszaadjuk az ID-t
        else:
            # Ha nem létezik, létrehozzuk
            cursor.execute("INSERT INTO match_groups (name) VALUES (%s)", (match_group_name,))
            connection.commit()
            match_group_id = cursor.lastrowid  # Az újonnan létrehozott ID

        return match_group_id
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba mérkőzéscsoport mentésénél: {err}")
        return None
    finally:
        cursor.close()
        connection.close()

def load_simulations_from_db():
    """Lekérdezi az adatbázisból az összes szimulációt."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, name, created_at FROM match_groups ORDER BY created_at DESC")
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Adatbázis hiba szimulációk lekérdezésekor: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

def create_simulation(match_group_id, strategy_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # 🔍 Ellenőrizzük, hogy már létezik-e ilyen szimuláció
    cursor.execute("""
        SELECT id FROM simulations WHERE match_group_id = %s AND strategy_id = %s
    """, (match_group_id, strategy_id))
    existing_simulation = cursor.fetchone()

    if existing_simulation:
        cursor.close()
        connection.close()
        return existing_simulation[0]

    # ➕ Új szimuláció beszúrása
    cursor.execute("""
        INSERT INTO simulations (match_group_id, strategy_id, total_profit_loss, simulation_date) 
        VALUES (%s, %s, 0, NOW())
    """, (match_group_id, strategy_id))

    simulation_id = cursor.lastrowid
    connection.commit()
    cursor.close()
    connection.close()

    return simulation_id


def is_simulation_completed(simulation_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM simulation_predictions WHERE simulation_id = %s AND was_correct IS NULL
    """, (simulation_id,))

    incomplete = cursor.fetchone()[0]
    cursor.close()
    connection.close()

    return incomplete == 0  # Ha 0, akkor minden mérkőzés kész.