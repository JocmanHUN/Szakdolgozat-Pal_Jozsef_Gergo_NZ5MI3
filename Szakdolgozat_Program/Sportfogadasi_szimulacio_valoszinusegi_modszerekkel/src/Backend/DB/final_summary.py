from src.Backend.DB.connection import get_db_connection


def fetch_completed_summary():
    """
    Lekérdezi:
      - completed_groups: Befejezett meccscsoportok száma
      - total_simulations: Összes szimuláció (befejezett csoportokhoz)
      - total_fixtures: Összes résztvevő mérkőzés (befejezett csoportokban)
    Visszatér egy dict-tel, pl.
      {"completed_groups": X, "total_simulations": Y, "total_fixtures": Z}
    """
    connection = get_db_connection()
    if not connection:
        print("❌ Nincs adatbáziskapcsolat!")
        return None

    results = {
        "completed_groups": 0,
        "total_simulations": 0,
        "total_fixtures": 0
    }

    try:
        cursor = connection.cursor(dictionary=True)

        # 1) Befejezett meccscsoportok száma
        cursor.execute("""
            SELECT COUNT(*) AS completed_groups
            FROM match_groups mg
            WHERE NOT EXISTS (
                SELECT 1
                FROM match_group_fixtures mgf
                JOIN fixtures f ON mgf.fixture_id = f.id
                WHERE mgf.match_group_id = mg.id
                  AND f.status NOT IN ('FT','AET','PEN')
            )
        """)
        row = cursor.fetchone()
        results["completed_groups"] = row["completed_groups"] if row else 0

        # 2) Összes szimuláció
        cursor.execute("""
            SELECT COUNT(*) AS total_simulations
            FROM simulations s
            JOIN match_groups mg ON s.match_group_id = mg.id
            WHERE NOT EXISTS (
                SELECT 1
                FROM match_group_fixtures mgf
                JOIN fixtures f ON mgf.fixture_id = f.id
                WHERE mgf.match_group_id = mg.id
                  AND f.status NOT IN ('FT','AET','PEN')
            )
        """)
        row = cursor.fetchone()
        results["total_simulations"] = row["total_simulations"] if row else 0

        # 3) Összes résztvevő mérkőzés
        cursor.execute("""
            SELECT COUNT(DISTINCT mgf.fixture_id) AS total_fixtures
            FROM match_group_fixtures mgf
            JOIN match_groups mg ON mgf.match_group_id = mg.id
            JOIN fixtures f ON mgf.fixture_id = f.id
            WHERE NOT EXISTS (
                SELECT 1
                FROM match_group_fixtures sub_mgf
                JOIN fixtures sub_f ON sub_mgf.fixture_id = sub_f.id
                WHERE sub_mgf.match_group_id = mg.id
                  AND sub_f.status NOT IN ('FT','AET','PEN')
            )
        """)
        row = cursor.fetchone()
        results["total_fixtures"] = row["total_fixtures"] if row else 0

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"❌ Hiba a fetch_completed_summary közben: {e}")
        connection.close()
        return None

    return results


