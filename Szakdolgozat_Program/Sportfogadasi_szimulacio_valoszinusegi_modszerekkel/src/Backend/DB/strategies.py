from src.Backend.DB.connection import get_db_connection
from src.Backend.DB.odds import get_best_odds_for_fixture


def get_all_strategies():
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (get_all_strategies).")
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, strategy_name FROM strategies")
        strategies = cursor.fetchall()
        return strategies

    except Exception as e:
        print(f"❌ Hiba történt a get_all_strategies során: {e}")
        return []

    finally:
        cursor.close()
        connection.close()


def load_model_strategy_comparison(sim_id):
    """
    Az egyes modellek teljesítményét összehasonlítja az egyes stratégiákon.

    Args:
        sim_id: A szimuláció azonosítója (match_group_id)

    Returns:
        Dictionary, amely tartalmazza az összes modell és stratégia kombinációhoz
        tartozó teljesítmény statisztikákat.
    """
    connection = get_db_connection()
    if connection is None:
        print("❌ Nem sikerült csatlakozni az adatbázishoz (load_model_strategy_comparison).")
        return None

    cursor = connection.cursor(dictionary=True)
    results = {}

    try:
        # Lekérjük az összes befejezett meccset a szimulációból
        cursor.execute("""
            SELECT f.fixture_id, f.date, f.score_home, f.score_away
            FROM fixtures f
            JOIN match_group_fixtures mgf ON f.fixture_id = mgf.fixture_id
            WHERE mgf.match_group_id = %s 
            AND f.score_home IS NOT NULL 
            AND f.score_away IS NOT NULL
        """, (sim_id,))

        completed_fixtures = cursor.fetchall()
        if not completed_fixtures:
            print(f"⚠️ Nincs befejezett meccs a match_group_id={sim_id} szimulációban.")
            return None

        completed_fixtures.sort(key=lambda x: x["date"])
        strategies = ["1", "2", "3", "4", "5"]
        base_stake = 10.0
        initial_bankroll = 10  # Kezdeti bankroll

        # Inicializáljuk az eredmény dict-et
        for strategy_id in strategies:
            results[strategy_id] = {}
            for model_id in range(1, 7):
                results[strategy_id][model_id] = {
                    "total_profit": 0.0,
                    "wins": 0,
                    "losses": 0,
                    "total_bets": 0,
                    "win_amounts": [],  # Győztes fogadások profitja
                    "loss_amounts": [],  # Vesztes fogadások vesztesége
                    "all_profits": [],  # Minden fogadás profit/veszteség értéke
                    "max_profit": 0.0,
                    "max_loss": 0.0,
                    "current_bankroll": initial_bankroll,
                    "final_bankroll": initial_bankroll
                }

        # Végigmegyünk az összes stratégián és modellen
        for strategy_id in strategies:
            for model_id in range(1, 7):
                stake = base_stake
                fib_seq = [1, 1, 2, 3, 5, 8, 13, 21, 34]
                fib_index = 0
                bankroll = initial_bankroll

                for fixture in completed_fixtures:
                    fixture_id = fixture["fixture_id"]

                    # Lekérjük a modell előrejelzését erre a meccsre
                    cursor.execute("""
                        SELECT was_correct, predicted_outcome, probability
                        FROM model_predictions
                        WHERE fixture_id = %s AND match_group_id = %s AND model_id = %s
                    """, (fixture_id, sim_id, model_id))
                    prediction = cursor.fetchone()

                    if not prediction:
                        continue

                    was_correct = prediction["was_correct"]
                    predicted_outcome = prediction["predicted_outcome"]
                    model_prob = float(str(prediction["probability"]).replace(",", ".")) / 100

                    # Lekérjük a legjobb oddsot az előrejelzett kimenetelre
                    best_odds = get_best_odds_for_fixture(fixture_id, predicted_outcome)
                    odds = best_odds.get("selected_odds") if best_odds else None

                    if not odds or odds <= 1.01:
                        continue

                    match_profit = 0.0
                    current_stake = stake

                    # Stratégia-specifikus logika
                    if strategy_id == "1":  # Flat Betting
                        match_profit = stake * (odds - 1) if was_correct else -stake

                    elif strategy_id == "2":  # Value Betting
                        if (model_prob * odds) > 1:
                            match_profit = stake * (odds - 1) if was_correct else -stake
                        else:
                            continue  # Nem fogadtunk erre a meccsre

                    elif strategy_id == "3":  # Martingale
                        if was_correct:
                            match_profit = current_stake * (odds - 1)
                            stake = base_stake  # Visszaállítjuk az alap tétet
                        else:
                            match_profit = -current_stake
                            stake *= 2  # Duplázzuk a tétet

                    elif strategy_id == "4":  # Fibonacci
                        current_stake = base_stake * fib_seq[fib_index]
                        if was_correct:
                            match_profit = current_stake * (odds - 1)
                            fib_index = max(0, fib_index - 2)
                        else:
                            match_profit = -current_stake
                            fib_index = min(len(fib_seq) - 1, fib_index + 1)
                        stake = base_stake * fib_seq[fib_index]

                    elif strategy_id == "5":  # Kelly Criterion
                        b = odds - 1
                        kelly_fraction = (model_prob * b - (1 - model_prob)) / b

                        if kelly_fraction <= 0:
                            continue  # Nem fogadtunk erre a meccsre

                        current_stake = bankroll * kelly_fraction

                        if was_correct:
                            match_profit = current_stake * b
                        else:
                            match_profit = -current_stake

                        bankroll += match_profit

                    # Statisztikák frissítése
                    model_data = results[strategy_id][model_id]
                    model_data["total_profit"] += match_profit
                    model_data["all_profits"].append(match_profit)
                    model_data["total_bets"] += 1

                    if was_correct:
                        model_data["wins"] += 1
                        model_data["win_amounts"].append(match_profit)
                        model_data["max_profit"] = max(model_data["max_profit"], match_profit)
                    else:
                        model_data["losses"] += 1
                        model_data["loss_amounts"].append(match_profit)
                        model_data["max_loss"] = min(model_data["max_loss"], match_profit)

                # Végső számítások a modellhez
                model_data = results[strategy_id][model_id]
                if strategy_id == "5":  # Kelly esetén
                    model_data["final_bankroll"] = bankroll
                else:
                    model_data["final_bankroll"] = initial_bankroll + model_data["total_profit"]

                # Statisztikai számítások
                if model_data["total_bets"] > 0:
                    model_data["win_rate"] = model_data["wins"] / model_data["total_bets"]
                    model_data["avg_profit"] = model_data["total_profit"] / model_data["total_bets"]

                    if model_data["wins"] > 0:
                        model_data["avg_win"] = sum(model_data["win_amounts"]) / model_data["wins"]
                    else:
                        model_data["avg_win"] = 0

                    if model_data["losses"] > 0:
                        model_data["avg_loss"] = sum(model_data["loss_amounts"]) / model_data["losses"]
                    else:
                        model_data["avg_loss"] = 0

                    # Profit/veszteség arány
                    if model_data["losses"] > 0 and model_data["avg_loss"] != 0:
                        model_data["profit_loss_ratio"] = abs(model_data["avg_win"] / model_data["avg_loss"])
                    else:
                        model_data["profit_loss_ratio"] = float('inf')

                    # Medián és szórás számítás
                    if model_data["all_profits"]:
                        all_profits = sorted(model_data["all_profits"])
                        n = len(all_profits)
                        if n % 2 == 0:
                            model_data["median_profit"] = (all_profits[n // 2 - 1] + all_profits[n // 2]) / 2
                        else:
                            model_data["median_profit"] = all_profits[n // 2]

                        # Szórás számítás
                        mean = model_data["avg_profit"]
                        variance = sum((x - mean) ** 2 for x in all_profits) / n
                        model_data["std_deviation"] = variance ** 0.5
                else:
                    model_data["win_rate"] = 0
                    model_data["avg_profit"] = 0
                    model_data["avg_win"] = 0
                    model_data["avg_loss"] = 0
                    model_data["profit_loss_ratio"] = 0
                    model_data["median_profit"] = 0
                    model_data["std_deviation"] = 0

                # Tisztítás: eltávolítjuk a részletes listákat az eredményből
                # (csak a számított értékeket adjuk vissza)
                model_data.pop("win_amounts", None)
                model_data.pop("loss_amounts", None)
                model_data.pop("all_profits", None)

        print(
            f"✅ A modell-stratégia összehasonlítási adatok sikeresen betöltve a match_group_id={sim_id} szimulációhoz.")
        return results

    except Exception as e:
        print(f"❌ Hiba történt a load_model_strategy_comparison során: {e}")
        return None

    finally:
        cursor.close()
        connection.close()