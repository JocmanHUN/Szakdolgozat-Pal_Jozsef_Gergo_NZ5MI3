from src.Backend.helpersAPI import get_db_connection, get_best_odds_for_fixture


def create_simulation(match_group_id, strategy_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id FROM simulations WHERE match_group_id = %s AND strategy_id = %s
    """, (match_group_id, strategy_id))
    existing_simulation = cursor.fetchone()

    if existing_simulation:
        cursor.close()
        connection.close()
        return existing_simulation[0]

    cursor.execute("""
        INSERT INTO simulations (match_group_id, strategy_id, total_profit_loss, simulation_date) 
        VALUES (%s, %s, 0, NOW())
    """, (match_group_id, strategy_id))

    simulation_id = cursor.lastrowid
    connection.commit()
    cursor.close()
    connection.close()

    return simulation_id


def fill_simulation_predictions(simulation_id, predictions):
    connection = get_db_connection()
    cursor = connection.cursor()

    total_profit = 0
    all_predictions_completed = True
    stake = 10  # fix tét

    for pred in predictions:
        fixture_result = get_fixture_result(pred["fixture_id"])

        if fixture_result:
            was_correct = int(pred["predicted_outcome"] == fixture_result["actual_result"])

            odds_mapping = {'1': fixture_result['odds_home'],
                            'X': fixture_result['odds_draw'],
                            '2': fixture_result['odds_away']}
            odds = odds_mapping[pred["predicted_outcome"]]

            profit = stake * (odds - 1) if was_correct else -stake
            total_profit += profit

            cursor.execute("""
                UPDATE model_predictions 
                SET was_correct = %s
                WHERE fixture_id = %s AND model_id = %s
            """, (was_correct, pred["fixture_id"], pred["model_id"]))

        else:
            all_predictions_completed = False

    cursor.execute("""
        UPDATE simulations SET total_profit_loss = %s WHERE id = %s
    """, (total_profit, simulation_id))

    connection.commit()
    cursor.close()
    connection.close()

    return all_predictions_completed


def update_simulation_profit(match_group_id):
    connection = get_db_connection()
    if connection is None:
        return

    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT 
            mp.id,
            mp.fixture_id,
            mp.was_correct, 
            mp.predicted_outcome
        FROM model_predictions mp
        WHERE mp.match_group_id = %s;
    """

    try:
        cursor.execute(query, (match_group_id,))
        predictions = cursor.fetchall()

        total_profit = 0.0
        stake = 10.0  # fix tét

        for pred in predictions:
            fixture_id = pred["fixture_id"]
            was_correct = pred["was_correct"]
            predicted_outcome = pred["predicted_outcome"]

            if was_correct:
                best_odds = get_best_odds_for_fixture(fixture_id, predicted_outcome)
                if best_odds:
                    profit = stake * (best_odds[0] - 1)
                    total_profit += profit
                else:
                    print(f"⚠️ Hiányzó odds (fixture: {fixture_id})")
            else:
                total_profit -= stake  # vesztes tippnél a tét elveszik

        cursor.execute("""
            UPDATE simulations
            SET total_profit_loss = %s
            WHERE match_group_id = %s
        """, (total_profit, match_group_id))
        connection.commit()

    except Exception as e:
        print(f"❌ Hiba a profit frissítésekor: {e}")

    finally:
        cursor.close()
        connection.close()


def get_fixture_result(fixture_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT actual_result, odds_home, odds_draw, odds_away FROM fixtures WHERE id = %s AND status = 'FT'
    """, (fixture_id,))

    result = cursor.fetchone()
    cursor.close()
    connection.close()

    return result

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


def get_all_strategies():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, strategy_name FROM strategies")
    strategies = cursor.fetchall()

    cursor.close()
    connection.close()

    return strategies

def evaluate_predictions(fixture_id, home_score, away_score):
    """Frissíti a model_predictions táblában a was_correct mezőt, de csak ha még nincs beállítva."""
    connection = get_db_connection()
    cursor = connection.cursor()

    # 🔥 Meghatározzuk a mérkőzés valódi eredményét
    if home_score > away_score:
        actual_outcome = "1"  # Hazai győzelem
    elif home_score < away_score:
        actual_outcome = "2"  # Vendég győzelem
    else:
        actual_outcome = "X"  # Döntetlen
    print(actual_outcome)
    # 🔍 Lekérjük azokat a predikciókat, amelyekhez a was_correct még nincs beállítva
    query = """
        SELECT id, predicted_outcome FROM model_predictions 
        WHERE fixture_id = %s AND was_correct IS NULL
    """
    cursor.execute(query, (fixture_id,))
    predictions = cursor.fetchall()
    if not predictions:
        print(f"✅ Minden predikció már ki van értékelve a mérkőzéshez: {fixture_id}")
        cursor.close()
        connection.close()
        return  # Ha nincs mit frissíteni, kilépünk

    print(f"🔄 {len(predictions)} predikció frissítése...")

    # 🔄 Frissítjük a was_correct mezőt csak azoknál, ahol még NULL az érték
    update_query = """
        UPDATE model_predictions 
        SET was_correct = %s
        WHERE id = %s
    """
    updates = [(int(predicted_outcome == actual_outcome), pred_id) for pred_id, predicted_outcome in predictions]

    cursor.executemany(update_query, updates)  # Egyszerre több rekord frissítése

    connection.commit()
    cursor.close()
    connection.close()

    print(f"✅ Mérkőzés (ID: {fixture_id}) kiértékelve. {len(updates)} új predikció frissítve.")



