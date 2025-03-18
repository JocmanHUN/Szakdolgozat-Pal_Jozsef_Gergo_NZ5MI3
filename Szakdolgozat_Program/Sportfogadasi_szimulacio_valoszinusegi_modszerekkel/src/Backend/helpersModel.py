from datetime import datetime

from src.Backend.helpersAPI import get_league_by_team, save_model_prediction
from src.Backend.probability_models.bayes_classic_model import bayes_classic_predict
from src.Backend.probability_models.bayes_empirical_model import bayes_empirical_predict
from src.Backend.probability_models.elo_model import elo_predict
from src.Backend.probability_models.logistic_regression_model import logistic_regression_predict
from src.Backend.probability_models.monte_carlo_model import monte_carlo_predict
from src.Backend.probability_models.poisson_model import poisson_predict


def save_all_predictions(fixture_id, home_team_id, away_team_id, match_group_id):
    """
    Elmenti az összes modell előrejelzését egy adott mérkőzésre.
    """
    # 🏆 Liga lekérése csapat alapján
    league_id = get_league_by_team(home_team_id)
    # 📆 Helyes szezon megállapítása
    season = get_current_season()

    if league_id is None:
        print(f"⚠️ Nem sikerült lekérni a liga azonosítót a {home_team_id} csapathoz. Elo-modell kihagyva!")
        return

    models = {
        1: bayes_classic_predict,
        2: monte_carlo_predict,
        3: poisson_predict,
        4: bayes_empirical_predict,
        5: logistic_regression_predict,
        6: lambda h, a: elo_predict(h, a, league_id, season)  # Elo-modell csapat alapján szerzett ligával
    }

    for model_id, model_function in models.items():
        prediction = model_function(home_team_id, away_team_id)

        if prediction:
            best_outcome = max(prediction, key=prediction.get)
            best_probability = prediction[best_outcome]
            print(best_outcome, best_probability)
            save_model_prediction(fixture_id, model_id, best_outcome, best_probability, match_group_id)

    print(f"📊 Minden modell előrejelzése mentve a {fixture_id} mérkőzéshez!")


def get_current_season():
    """
    Megállapítja az aktuális szezon évszámát a futó szezon alapján.
    Példa: Ha 2024 március van → 2023/24 szezon → 2023 a helyes szezonkezdés.
           Ha 2024 szeptember van → 2024/25 szezon → 2024 a helyes szezonkezdés.
    """
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Ha az év első felében vagyunk (január - június), akkor az előző év a szezon kezdete
    if current_month < 7:
        return current_year - 1  # Pl. 2024 március → 2023/24 szezon
    else:
        return current_year  # Pl. 2024 szeptember → 2024/25 szezon
