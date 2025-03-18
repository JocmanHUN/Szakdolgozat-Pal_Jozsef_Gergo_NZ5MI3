import numpy as np
from scipy.stats import poisson
from src.Backend.helpersAPI import get_last_matches


def calculate_weighted_goal_expectancy(team_id):
    """
    Kiszámítja egy csapat súlyozott várható gólmennyiségét az utolsó 10 mérkőzése alapján.
    A frissebb meccsek nagyobb súllyal számítanak.
    """
    matches = get_last_matches(team_id)
    if not matches:
        return 0.0, 0.0  # Ne térjen vissza None értékkel, mert az később hibát okozhat

    total_weights = 0
    weighted_goals_for = 0
    weighted_goals_against = 0
    num_matches = len(matches)

    # Súlyok beállítása: legfrissebb meccs súlya 1, a régebbieké exponenciálisan csökken
    decay_factor = 0.8  # Minden meccs 20%-kal kisebb súlyt kap

    for i, match in enumerate(matches):
        weight = decay_factor ** (num_matches - i - 1)
        total_weights += weight

        if match['home_team_id'] == team_id:
            weighted_goals_for += (match['score_home'] or 0) * weight
            weighted_goals_against += (match['score_away'] or 0) * weight
        else:
            weighted_goals_for += (match['score_away'] or 0) * weight
            weighted_goals_against += (match['score_home'] or 0) * weight

    # Ha total_weights 0 lenne, akkor kerüljük a hibát
    if total_weights == 0:
        return 0.0, 0.0

    avg_goals_for = weighted_goals_for / total_weights
    avg_goals_against = weighted_goals_against / total_weights

    return float(avg_goals_for), float(avg_goals_against)



def monte_carlo_predict(home_team_id, away_team_id, num_simulations=10000):
    """
    Monte Carlo szimuláció segítségével kiszámítja a mérkőzés 1X2 valószínűségeit,
    a frissebb mérkőzések nagyobb súlyozásával.
    """
    home_avg_goals, home_avg_conceded = calculate_weighted_goal_expectancy(home_team_id)
    away_avg_goals, away_avg_conceded = calculate_weighted_goal_expectancy(away_team_id)

    if home_avg_goals is None or away_avg_goals is None:
        return None  # Ha nincs elég adat, nem tudunk becslést adni

    # Várható gólok számítása a súlyozott statisztikák alapján
    home_expected_goals = (home_avg_goals + away_avg_conceded) / 2
    away_expected_goals = (away_avg_goals + home_avg_conceded) / 2

    # Monte Carlo szimuláció futtatása
    home_wins, draws, away_wins = 0, 0, 0

    for _ in range(num_simulations):
        home_goals = poisson.rvs(home_expected_goals)  # Hazai csapat véletlenszerű góljai
        away_goals = poisson.rvs(away_expected_goals)  # Vendég csapat véletlenszerű góljai

        if home_goals > away_goals:
            home_wins += 1
        elif home_goals < away_goals:
            away_wins += 1
        else:
            draws += 1

    # Százalékos eredmények kiszámítása
    home_win_prob = (home_wins / num_simulations) * 100
    draw_prob = (draws / num_simulations) * 100
    away_win_prob = (away_wins / num_simulations) * 100

    return {
        "1": round(home_win_prob, 2),
        "X": round(draw_prob, 2),
        "2": round(away_win_prob, 2)
    }
