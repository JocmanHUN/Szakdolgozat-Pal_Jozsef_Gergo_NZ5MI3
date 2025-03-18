from src.Backend.helpersAPI import get_db_connection


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


def fill_simulation_predictions(simulation_id, predictions, stake=10):
    connection = get_db_connection()
    cursor = connection.cursor()

    total_profit = 0
    all_predictions_completed = True

    for pred in predictions:
        fixture_result = get_fixture_result(pred["fixture_id"])

        # Ellenőrizzük, hogy ismert-e már a végeredmény
        if fixture_result:
            was_correct = int(pred["predicted_outcome"] == fixture_result["actual_result"])

            odds_mapping = {'1': fixture_result['odds_home'],
                            'X': fixture_result['odds_draw'],
                            '2': fixture_result['odds_away']}
            odds = odds_mapping[pred["predicted_outcome"]]

            # Profit számítás
            if was_correct:
                profit = stake * (odds - 1)
            else:
                profit = -stake

            total_profit += profit
        else:
            was_correct = None
            all_predictions_completed = False

        cursor.execute("""
            INSERT INTO simulation_predictions (simulation_id, fixture_id, prediction_id, was_correct) 
            VALUES (%s, %s, %s, %s)
        """, (simulation_id, pred["fixture_id"], pred["model_id"], was_correct))

    # Frissítjük a teljes profitot
    cursor.execute("""
        UPDATE simulations SET total_profit_loss = %s WHERE id = %s
    """, (total_profit, simulation_id))

    connection.commit()
    cursor.close()
    connection.close()

    return all_predictions_completed  # Ez jelzi, hogy minden mérkőzés eredménye ismert-e.

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
