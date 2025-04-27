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


def get_odds_stats_by_strategy_and_model():
    """
    Lekérdezi az odds statisztikákat stratégia és modell szerint bontva.
    Visszatér egy szótárral, ahol a kulcsok a stratégia azonosítók, az értékek pedig
    modell azonosítókat és odds statisztikákat tartalmazó szótárak.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_odds_stats_by_strategy_and_model).")
        return {}

    cursor = connection.cursor(dictionary=True)
    try:
        # Győztes tippek átlagos odds értékei modellenként és stratégiánként
        win_query = """
            SELECT 
                s.strategy_id,
                mp.model_id,
                AVG(CASE 
                    WHEN mp.predicted_outcome = '1' THEN o.home_odds
                    WHEN mp.predicted_outcome = 'X' THEN o.draw_odds
                    WHEN mp.predicted_outcome = '2' THEN o.away_odds
                    ELSE NULL
                END) AS average_odds
            FROM model_predictions mp
            JOIN fixtures f ON mp.fixture_id = f.id
            JOIN odds o ON f.id = o.fixture_id
            JOIN simulations s ON mp.match_group_id = s.match_group_id
            WHERE mp.was_correct = 1
            GROUP BY s.strategy_id, mp.model_id
        """
        cursor.execute(win_query)
        win_results = cursor.fetchall()

        # Vesztes tippek átlagos odds értékei modellenként és stratégiánként
        loss_query = """
            SELECT 
                s.strategy_id,
                mp.model_id,
                AVG(CASE 
                    WHEN mp.predicted_outcome = '1' THEN o.home_odds
                    WHEN mp.predicted_outcome = 'X' THEN o.draw_odds
                    WHEN mp.predicted_outcome = '2' THEN o.away_odds
                    ELSE NULL
                END) AS average_odds
            FROM model_predictions mp
            JOIN fixtures f ON mp.fixture_id = f.id
            JOIN odds o ON f.id = o.fixture_id
            JOIN simulations s ON mp.match_group_id = s.match_group_id
            WHERE mp.was_correct = 0
            GROUP BY s.strategy_id, mp.model_id
        """
        cursor.execute(loss_query)
        loss_results = cursor.fetchall()

        # Összes tipp átlagos odds értékei modellenként és stratégiánként
        total_query = """
            SELECT 
                s.strategy_id,
                mp.model_id,
                AVG(CASE 
                    WHEN mp.predicted_outcome = '1' THEN o.home_odds
                    WHEN mp.predicted_outcome = 'X' THEN o.draw_odds
                    WHEN mp.predicted_outcome = '2' THEN o.away_odds
                    ELSE NULL
                END) AS average_odds
            FROM model_predictions mp
            JOIN fixtures f ON mp.fixture_id = f.id
            JOIN odds o ON f.id = o.fixture_id
            JOIN simulations s ON mp.match_group_id = s.match_group_id
            GROUP BY s.strategy_id, mp.model_id
        """
        cursor.execute(total_query)
        total_results = cursor.fetchall()

        # Rendezzük át az eredményt használhatóbb formátumba
        odds_stats = {}

        # Inicializáljuk a stratégia-modell struktúrát
        for win_item in win_results:
            strategy_id = win_item['strategy_id']
            model_id = win_item['model_id']
            if strategy_id not in odds_stats:
                odds_stats[strategy_id] = {}
            if model_id not in odds_stats[strategy_id]:
                odds_stats[strategy_id][model_id] = {
                    'win_odds_avg': 0.0,
                    'loss_odds_avg': 0.0,
                    'total_odds_avg': 0.0
                }
            odds_stats[strategy_id][model_id]['win_odds_avg'] = round(float(win_item['average_odds']), 2)

        # Hozzáadjuk a vesztes tippek átlagos odds értékeit
        for loss_item in loss_results:
            strategy_id = loss_item['strategy_id']
            model_id = loss_item['model_id']
            if strategy_id not in odds_stats:
                odds_stats[strategy_id] = {}
            if model_id not in odds_stats[strategy_id]:
                odds_stats[strategy_id][model_id] = {
                    'win_odds_avg': 0.0,
                    'loss_odds_avg': 0.0,
                    'total_odds_avg': 0.0
                }
            odds_stats[strategy_id][model_id]['loss_odds_avg'] = round(float(loss_item['average_odds']), 2)

        # Hozzáadjuk az összes tipp átlagos odds értékeit
        for total_item in total_results:
            strategy_id = total_item['strategy_id']
            model_id = total_item['model_id']
            if strategy_id not in odds_stats:
                odds_stats[strategy_id] = {}
            if model_id not in odds_stats[strategy_id]:
                odds_stats[strategy_id][model_id] = {
                    'win_odds_avg': 0.0,
                    'loss_odds_avg': 0.0,
                    'total_odds_avg': 0.0
                }
            odds_stats[strategy_id][model_id]['total_odds_avg'] = round(float(total_item['average_odds']), 2)

        return odds_stats

    except Exception as e:
        print(f"❌ Hiba történt a get_odds_stats_by_strategy_and_model során: {e}")
        return {}

    finally:
        cursor.close()
        connection.close()
