from src.Backend.DB.connection import get_db_connection
from src.Backend.DB.fixtures import get_fixture_result
from src.Backend.DB.odds import get_best_odds_for_fixture


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
            UPDATE strategies
            SET total_profit_loss = %s
            WHERE match_group_id = %s
        """, (total_profit, match_group_id))
        connection.commit()

    except Exception as e:
        print(f"❌ Hiba a profit frissítésekor: {e}")

    finally:
        cursor.close()
        connection.close()

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