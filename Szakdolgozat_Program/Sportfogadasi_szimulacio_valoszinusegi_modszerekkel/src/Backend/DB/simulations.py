from tkinter import messagebox

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
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (create_simulation).")
        return None

    cursor = connection.cursor()
    try:
        # 🔍 Ellenőrizzük, hogy már létezik-e ilyen szimuláció
        cursor.execute("""
            SELECT id FROM simulations WHERE match_group_id = %s AND strategy_id = %s
        """, (match_group_id, strategy_id))
        existing_simulation = cursor.fetchone()

        if existing_simulation:
            return existing_simulation[0]

        # ➕ Új szimuláció beszúrása
        cursor.execute("""
            INSERT INTO simulations (
                match_group_id, strategy_id, total_profit_loss, simulation_date,
                bayes_classic_profit, monte_carlo_profit, poisson_profit,
                bayes_empirical_profit, log_reg_profit, elo_profit,
                bayes_classic_stake, monte_carlo_stake, poisson_stake,
                bayes_empirical_stake, log_reg_stake, elo_stake
            )
            VALUES (%s, %s, 0, NOW(), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        """, (match_group_id, strategy_id))

        simulation_id = cursor.lastrowid
        connection.commit()
        return simulation_id

    except Exception as e:
        print(f"❌ Hiba történt a create_simulation során: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def load_aggregated_simulations():
    """
    Lekérdezi a befejezett mérkőzéscsoportokhoz tartozó szimulációk összesített adatait,
    beleértve az egyes valószínűségi modellekhez tartozó profitokat is.
    """
    connection = get_db_connection()
    if not connection:
        print("❌ Nincs adatbáziskapcsolat!")
        return []

    cursor = connection.cursor(dictionary=True)
    results = []

    try:
        sql = """
       SELECT s.id AS id,
           mg.name AS sim_name,
           s.strategy_id,
           s.total_profit_loss,
           s.simulation_date,
           s.bayes_classic_profit,
           s.monte_carlo_profit,
           s.poisson_profit,
           s.bayes_empirical_profit,
           s.log_reg_profit,
           s.elo_profit,
           s.bayes_classic_stake,
           s.monte_carlo_stake,
           s.poisson_stake,
           s.bayes_empirical_stake,
           s.log_reg_stake,
           s.elo_stake
        FROM simulations s
        JOIN match_groups mg ON s.match_group_id = mg.id
        WHERE NOT EXISTS (
            SELECT 1
            FROM match_group_fixtures mgf
            JOIN fixtures f ON mgf.fixture_id = f.id
            WHERE mgf.match_group_id = mg.id
              AND f.status NOT IN ('FT','AET','PEN')
        )
        ORDER BY s.simulation_date DESC
        """
        cursor.execute(sql)
        results = cursor.fetchall()

    except Exception as e:
        print(f"❌ Hiba a load_aggregated_simulations lekérdezésekor: {e}")

    finally:
        cursor.close()
        connection.close()

    return results

def load_simulation_profits_data(strategy_id=None):
    """
    Betölti a szimulációs profit és stake adatokat az adatbázisból,
    csak a lezárult fogadásokra (total_profit_loss != 0).
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        if strategy_id is not None:
            cursor.execute("""
                SELECT 
                    s.id, s.strategy_id, 
                    s.bayes_classic_profit, s.monte_carlo_profit, s.poisson_profit,
                    s.bayes_empirical_profit, s.log_reg_profit, s.elo_profit,
                    s.bayes_classic_stake, s.monte_carlo_stake, s.poisson_stake,
                    s.bayes_empirical_stake, s.log_reg_stake, s.elo_stake,
                    st.strategy_name
                FROM simulations s
                JOIN strategies st ON s.strategy_id = st.id
                WHERE s.strategy_id = %s AND s.total_profit_loss != 0
            """, (strategy_id,))
        else:
            cursor.execute("""
                SELECT 
                    s.id, s.strategy_id, 
                    s.bayes_classic_profit, s.monte_carlo_profit, s.poisson_profit,
                    s.bayes_empirical_profit, s.log_reg_profit, s.elo_profit,
                    s.bayes_classic_stake, s.monte_carlo_stake, s.poisson_stake,
                    s.bayes_empirical_stake, s.log_reg_stake, s.elo_stake,
                    st.strategy_name
                FROM simulations s
                JOIN strategies st ON s.strategy_id = st.id
                WHERE s.total_profit_loss != 0
            """)

        rows = cursor.fetchall()

        simulation_data = []
        for row in rows:
            simulation_data.append({
                'id': row[0],
                'strategy_id': row[1],
                'bayes_classic_profit': row[2],
                'monte_carlo_profit': row[3],
                'poisson_profit': row[4],
                'bayes_empirical_profit': row[5],
                'log_reg_profit': row[6],
                'elo_profit': row[7],
                'bayes_classic_stake': row[8],
                'monte_carlo_stake': row[9],
                'poisson_stake': row[10],
                'bayes_empirical_stake': row[11],
                'log_reg_stake': row[12],
                'elo_stake': row[13],
                'strategy_name': row[14]
            })

        return simulation_data

    except Exception as e:
        print(f"Hiba történt a szimulációs adatok betöltésekor: {e}")
        return []
    finally:
        cursor.close()
        connection.close()




