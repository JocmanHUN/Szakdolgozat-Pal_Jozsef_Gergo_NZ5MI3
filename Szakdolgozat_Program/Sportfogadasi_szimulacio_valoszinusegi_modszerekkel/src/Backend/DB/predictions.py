from src.Backend.DB.connection import get_db_connection
from src.Backend.DB.fixtures import get_fixture_result
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
    connection = get_db_connection()
    cursor = connection.cursor()
    try:


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
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_predictions_for_fixture).")
        return {}

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT model_id, predicted_outcome, probability
            FROM model_predictions
            WHERE fixture_id = %s
        """
        cursor.execute(query, (fixture_id,))
        predictions = cursor.fetchall()

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

    except Exception as e:
        print(f"❌ Hiba történt a get_predictions_for_fixture során: {e}")
        return {}

    finally:
        cursor.close()
        connection.close()

def evaluate_predictions(fixture_id, home_score, away_score):
    """Frissíti a model_predictions táblában a was_correct mezőt, de csak ha még nincs beállítva."""
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (evaluate_predictions).")
        return

    cursor = connection.cursor()
    try:
        # 🔥 Meghatározzuk a mérkőzés valódi eredményét
        if home_score > away_score:
            actual_outcome = "1"
        elif home_score < away_score:
            actual_outcome = "2"
        else:
            actual_outcome = "X"
        print(f"Actual outcome: {actual_outcome}")

        # 🔍 Lekérjük azokat a predikciókat, amelyekhez a was_correct még nincs beállítva
        query = """
            SELECT id, predicted_outcome FROM model_predictions 
            WHERE fixture_id = %s AND was_correct IS NULL
        """
        cursor.execute(query, (fixture_id,))
        predictions = cursor.fetchall()
        if not predictions:
            print(f"✅ Minden predikció már ki van értékelve a mérkőzéshez: {fixture_id}")
            return

        print(f"🔄 {len(predictions)} predikció frissítése...")

        # 🔄 Frissítjük a was_correct mezőt
        update_query = """
            UPDATE model_predictions 
            SET was_correct = %s
            WHERE id = %s
        """
        updates = [(int(predicted_outcome == actual_outcome), pred_id) for pred_id, predicted_outcome in predictions]
        cursor.executemany(update_query, updates)

        connection.commit()
        print(f"✅ Mérkőzés (ID: {fixture_id}) kiértékelve. {len(updates)} új predikció frissítve.")

    except Exception as e:
        print(f"❌ Hiba történt az evaluate_predictions során: {e}")

    finally:
        cursor.close()
        connection.close()


def update_strategy_profit(sim_id, completed_fixtures):
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (update_strategy_profit).")
        return

    cursor = connection.cursor(dictionary=True)
    try:
        completed_fixtures.sort(key=lambda x: x.get("match_date"))
        strategies = ["1", "2", "3", "4", "5"]
        base_stake = 10.0
        initial_bankroll = 10  # Kezdeti bankroll

        for strategy_id in strategies:
            strategy_profit = 0.0
            model_profits = [0.0] * 6  # Lista az egyes modellek profitjának tárolására

            for model_id in range(1, 7):
                model_profit = 0.0
                stake = base_stake
                fib_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34]
                fib_index = 0
                bankroll = initial_bankroll

                for fixture in completed_fixtures:
                    fixture_id = fixture["fixture_id"]
                    home_score = fixture.get("score_home")
                    away_score = fixture.get("score_away")
                    if home_score is None or away_score is None:
                        continue

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
                    best_odds = get_best_odds_for_fixture(fixture_id, predicted_outcome)
                    odds = best_odds.get("selected_odds") if best_odds else None
                    if not odds or odds <= 1.01:
                        continue

                    result = "✅ Győztes tipp" if was_correct else "❌ Vesztes tipp"

                    if strategy_id == "1":  # Flat
                        match_profit = stake * (odds - 1) if was_correct else -stake
                        model_profit += match_profit

                    elif strategy_id == "2":  # Value
                        db_prediction = get_prediction_by_model_id(fixture_id, model_id, sim_id)
                        model_prob = float(str(db_prediction["probability"]).replace(",", ".")) / 100
                        if (model_prob * odds) > 1:
                            match_profit = stake * (odds - 1) if was_correct else -stake
                            model_profit += match_profit

                    elif strategy_id == "3":  # Martingale
                        if was_correct:
                            model_profit += stake * (odds - 1)
                            stake = base_stake
                        else:
                            model_profit -= stake
                            stake *= 2

                    elif strategy_id == "4":  # Fibonacci
                        current_stake = base_stake * fib_seq[fib_index]
                        if was_correct:
                            model_profit += current_stake * (odds - 1)
                            fib_index = max(0, fib_index - 2)
                        else:
                            model_profit -= current_stake
                            fib_index = min(len(fib_seq) - 1, fib_index + 1)
                        stake = base_stake * fib_seq[fib_index]

                    elif strategy_id == "5":  # Kelly
                        db_prediction = get_prediction_by_model_id(fixture_id, model_id, sim_id)
                        if not db_prediction:
                            continue
                        model_prob = float(str(db_prediction["probability"]).replace(",", ".")) / 100
                        b = odds - 1
                        kelly_fraction = (model_prob * b - (1 - model_prob)) / b
                        if kelly_fraction <= 0:
                            continue
                        current_stake = bankroll * kelly_fraction
                        if was_correct:
                            bankroll += current_stake * b
                        else:
                            bankroll -= current_stake
                        model_profit = bankroll - initial_bankroll

                strategy_profit += model_profit
                model_profits[model_id - 1] = model_profit  # mentés a listába

            # Frissítés az adatbázisban
            cursor.execute("""
                UPDATE simulations
                SET total_profit_loss = %s,
                    bayes_classic_profit = %s,
                    monte_carlo_profit = %s,
                    poisson_profit = %s,
                    bayes_empirical_profit = %s,
                    log_reg_profit = %s,
                    elo_profit = %s
                WHERE match_group_id = %s AND strategy_id = %s
            """, (
                strategy_profit,
                model_profits[0],
                model_profits[1],
                model_profits[2],
                model_profits[3],
                model_profits[4],
                model_profits[5],
                sim_id,
                strategy_id
            ))
            connection.commit()
            print(f"✅ Stratégia {strategy_id} profitjai elmentve.")

    except Exception as e:
        print(f"❌ Hiba történt az update_strategy_profit során: {e}")

    finally:
        cursor.close()
        connection.close()

def get_prediction_from_db(fixture_id: object, model_name: object, match_group_id: object) -> None:
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
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_prediction_from_db).")
        return None

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT predicted_outcome, was_correct, probability
            FROM model_predictions
            WHERE fixture_id = %s AND model_id = %s AND match_group_id = %s
        """
        cursor.execute(query, (fixture_id, model_id, match_group_id))
        result = cursor.fetchone()
        return result

    except Exception as e:
        print(f"❌ Hiba történt a get_prediction_from_db során: {e}")
        return None

    finally:
        cursor.close()
        connection.close()

def get_all_predictions():
    """
    Lekéri az összes predikciót a model_predictions táblából, amelyeknél a was_correct NEM NULL.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_all_predictions).")
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT id, fixture_id, model_id, predicted_outcome, probability, match_group_id, was_correct
            FROM model_predictions
            WHERE was_correct IS NOT NULL
        """
        cursor.execute(query)
        results = cursor.fetchall()
        return results

    except Exception as e:
        print(f"❌ Hiba történt a get_all_predictions során: {e}")
        return []

    finally:
        cursor.close()
        connection.close()


def get_all_models():
    """
    Lekéri az összes modellt a models táblából: id, name mezők.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_all_models).")
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = "SELECT model_id, model_name FROM models ORDER BY model_id"
        cursor.execute(query)
        results = cursor.fetchall()
        return results

    except Exception as e:
        print(f"❌ Hiba történt a get_all_models során: {e}")
        return []

    finally:
        cursor.close()
        connection.close()

def get_prediction_by_model_id(fixture_id: int, model_id: int, match_group_id: int) -> dict:
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_prediction_by_model_id).")
        return None

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT predicted_outcome, was_correct, probability
            FROM model_predictions
            WHERE fixture_id = %s AND model_id = %s AND match_group_id = %s
        """
        cursor.execute(query, (fixture_id, model_id, match_group_id))
        return cursor.fetchone()

    except Exception as e:
        print(f"❌ Hiba történt a get_prediction_by_model_id során: {e}")
        return None

    finally:
        cursor.close()
        connection.close()




