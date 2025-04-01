import time
from asyncio import timeout

from src.Backend.DB.connection import get_db_connection
from src.Backend.DB.fixtures import get_fixture_result, fetch_fixtures_for_simulation
from src.Backend.DB.odds import get_best_odds_for_fixture
from src.Backend.strategies.fibonacci import fibonacci
from src.Backend.strategies.flatBetting import flat_betting
from src.Backend.strategies.kellyCriterion import kelly_criterion
from src.Backend.strategies.martingale import martingale
from src.Backend.strategies.valueBetting import value_betting

strategy_model_map = {
    1: [1, 2, 3, 4, 5, 6],  # Flat
    2: [1, 2, 3, 4, 5, 6],  # Value
    3: [1, 2, 3, 4, 5, 6],  # Martingale
    4: [1, 2, 3, 4, 5, 6],  # Fibonacci
    5: [1, 2, 3, 4, 5, 6],  # Kelly
}

strategy_funcs = {
    1: flat_betting,
    2: value_betting,
    3: martingale,
    4: fibonacci,
    5: kelly_criterion
}

def save_model_prediction(fixture_id, model_id, predicted_outcome, probability, match_group_id):
    """
    Elmenti a modellek predikcióit az adatbázisba.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO model_predictions (fixture_id, model_id, predicted_outcome, probability, match_group_id)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (fixture_id, model_id, predicted_outcome, probability, match_group_id))
        connection.commit()

        print(
            f"✅ Predikció mentve: Fixture ID: {fixture_id}, Model ID: {model_id}, Outcome: {predicted_outcome}, Probability: {probability}%")

    except Exception as e:
        print(f"❌ Hiba történt a predikció mentése közben: {e}")

    finally:
        cursor.close()
        connection.close()


def get_predictions_for_fixture(fixture_id):
    """
    Lekérdezi egy adott mérkőzéshez tartozó modellek előrejelzéseit az adatbázisból.
    """
    connection = get_db_connection()
    if connection is None:
        return {}

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT model_id, predicted_outcome, probability
    FROM model_predictions
    WHERE fixture_id = %s
    """

    cursor.execute(query, (fixture_id,))
    predictions = cursor.fetchall()
    cursor.close()
    connection.close()

    # Modell ID-k leképezése a megfelelő nevekre
    model_map = {
        1: "bayes_classic",
        2: "monte_carlo",
        3: "poisson",
        4: "bayes_empirical",
        5: "log_reg",
        6: "elo"
    }

    model_predictions = {name: "-" for name in model_map.values()}  # Alapértelmezett érték '-'

    for pred in predictions:
        model_name = model_map.get(pred["model_id"])
        if model_name:
            model_predictions[model_name] = f"{pred['predicted_outcome']} ({pred['probability']}%)"

    return model_predictions

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
        UPDATE strategies SET total_profit_loss = %s WHERE id = %s
    """, (total_profit, simulation_id))

    connection.commit()
    cursor.close()
    connection.close()

    return all_predictions_completed


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


def update_strategy_profit(sim_id, completed_fixtures):
    connection = get_db_connection()
    if connection is None:
        return
    cursor = connection.cursor(dictionary=True)
    completed_fixtures.sort(key=lambda x: x.get("match_date"))
    strategies = ["1", "2", "3", "4", "5"]
    base_stake = 10.0  # Alap tét minden stratégiához

    for strategy_id in strategies:
        strategy_profit = 0.0

        for model_id in range(1, 7):  # 6 modell
            model_profit = 0.0
            stake = base_stake
            fib_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34]
            fib_index = 0  # csak Fibonaccihoz használjuk

            for fixture in completed_fixtures:
                fixture_id = fixture["fixture_id"]
                home_score = fixture.get("score_home")
                away_score = fixture.get("score_away")
                if home_score is None or away_score is None:
                    continue

                # Predikció lekérdezése
                cursor.execute("""
                    SELECT was_correct, predicted_outcome
                    FROM model_predictions
                    WHERE fixture_id = %s AND match_group_id = %s AND model_id = %s
                """, (fixture_id, sim_id, model_id))
                prediction = cursor.fetchone()

                if not prediction:
                    continue

                was_correct = prediction["was_correct"]
                predicted_outcome = prediction["predicted_outcome"]

                # Odds lekérdezése
                best_odds = get_best_odds_for_fixture(fixture_id, predicted_outcome)
                odds = best_odds.get("selected_odds") if best_odds else None

                if not odds or odds <= 1.01:
                    continue

                result = "✅ Győztes tipp" if was_correct else "❌ Vesztes tipp"

                if strategy_id == "1":  # Flat Betting
                    if was_correct:
                        match_profit = stake * (odds - 1)
                        model_profit += match_profit
                        result_str = "✅ Győztes tipp"
                    else:
                        match_profit = -stake
                        model_profit += match_profit
                        result_str = "❌ Vesztes tipp"

                    print(
                        f"[Flat] Modell {model_id}, Meccs {fixture_id} - {result_str}, Odds: {odds}, Meccs profit: {match_profit:.2f}, Összesített: {model_profit:.2f}")

                elif strategy_id == "2":  # Value Betting
                    model_prob = 0.5
                    if (model_prob * odds) > 1:
                        if was_correct:
                            profit = stake * (odds - 1)
                            model_profit += profit
                        else:
                            model_profit -= stake
                        print(f"[Value] Modell {model_id}, Meccs {fixture_id} - {result}, Odds: {odds}, Profit: {model_profit:.2f}")
                    else:
                        print(f"[Value] Modell {model_id}, Meccs {fixture_id} - Tipp nem érte meg (value alacsony)")

                elif strategy_id == "3":  # Martingale
                    if was_correct:
                        profit = stake * (odds - 1)
                        model_profit += profit
                        stake = base_stake
                    else:
                        model_profit -= stake
                        stake *= 2
                    print(f"[Martingale] Modell {model_id}, Meccs {fixture_id} - {result}, Tét: {stake}, Profit: {model_profit:.2f}")

                elif strategy_id == "4":  # Fibonacci
                    current_stake = base_stake * fib_seq[fib_index]
                    if was_correct:
                        profit = current_stake * (odds - 1)
                        model_profit += profit
                        fib_index = max(0, fib_index - 2)
                    else:
                        model_profit -= current_stake
                        fib_index = min(len(fib_seq)-1, fib_index + 1)
                    stake = base_stake * fib_seq[fib_index]
                    print(f"[Fibonacci] Modell {model_id}, Meccs {fixture_id} - {result}, Tét: {current_stake}, Profit: {model_profit:.2f}")

                elif strategy_id == "5":  # Kelly Criterion
                    model_prob = 0.5
                    kelly_fraction = (model_prob * (odds - 1)) / odds
                    current_stake = stake * kelly_fraction
                    if was_correct:
                        profit = current_stake * (odds - 1)
                        model_profit += profit
                    else:
                        model_profit -= current_stake
                    print(f"[Kelly] Modell {model_id}, Meccs {fixture_id} - {result}, Tét: {current_stake:.2f}, Profit: {model_profit:.2f}")

            strategy_profit += model_profit
            print(f"📈 Stratégia {strategy_id}, Modell {model_id} végső profit: {model_profit:.2f}")

        # Adatbázis frissítés
        cursor.execute("""
            UPDATE simulations
            SET total_profit_loss = %s
            WHERE match_group_id = %s AND strategy_id = %s
        """, (strategy_profit, sim_id, strategy_id))
        connection.commit()

        print(f"✅ Stratégia ID {strategy_id} összesített profitja (match_group_id={sim_id}): {strategy_profit:.2f}")

    cursor.close()
    connection.close()


def get_prediction_from_db(fixture_id, model_name, match_group_id):
    model_map = {
        "bayes_classic": 1,
        "monte_carlo": 2,
        "poisson": 3,
        "bayes_empirical": 4,
        "log_reg": 5,
        "elo": 6
    }
    model_id = model_map.get(model_name)
    if model_id is None:
        return None

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT predicted_outcome, was_correct, probability
        FROM model_predictions
        WHERE fixture_id = %s AND model_id = %s AND match_group_id = %s
    """
    cursor.execute(query, (fixture_id, model_id, match_group_id))
    result = cursor.fetchone()

    cursor.close()
    connection.close()
    return result






