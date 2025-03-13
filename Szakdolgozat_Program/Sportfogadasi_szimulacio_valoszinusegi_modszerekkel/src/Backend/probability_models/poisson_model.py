import numpy as np
import scipy.stats as stats
from src.Backend.helpersAPI import get_last_10_matches


def calculate_goal_expectancy(team_id):
    """
    Kiszámítja a hazai és vendégcsapat várható gólmennyiségét az utolsó 10 mérkőzés alapján.
    """
    matches = get_last_10_matches(team_id)
    if not matches:
        return None, None

    total_goals_for = sum(
        match['score_home'] if match['home_team_id'] == team_id else match['score_away'] for match in matches)
    total_goals_against = sum(
        match['score_away'] if match['home_team_id'] == team_id else match['score_home'] for match in matches)
    avg_goals_for = total_goals_for / len(matches)
    avg_goals_against = total_goals_against / len(matches)

    return avg_goals_for, avg_goals_against


def poisson_probability(expected_goals, actual_goals):
    """
    Poisson valószínűség kiszámítása egy adott gólmennyiségre.
    """
    return stats.poisson.pmf(actual_goals, expected_goals)


def poisson_outcome_probabilities(home_team_id, away_team_id):
    """
    A Poisson-eloszlás segítségével kiszámítja a mérkőzés 1X2 valószínűségeit, százalékban kifejezve.
    """
    home_avg_goals, home_avg_conceded = calculate_goal_expectancy(home_team_id)
    away_avg_goals, away_avg_conceded = calculate_goal_expectancy(away_team_id)

    if home_avg_goals is None or away_avg_goals is None:
        return None  # Ha nincs elég adat, nem tudunk becslést adni

    home_expected_goals = (home_avg_goals + away_avg_conceded) / 2
    away_expected_goals = (away_avg_goals + home_avg_conceded) / 2

    max_goals = 5  # Maximum gólhatár a valószínűségszámításhoz
    result_matrix = np.zeros((max_goals + 1, max_goals + 1))

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            result_matrix[home_goals, away_goals] = poisson_probability(home_expected_goals,
                                                                        home_goals) * poisson_probability(
                away_expected_goals, away_goals)

    home_win_prob = np.sum(np.tril(result_matrix, -1)) * 100  # Hazai győzelem
    draw_prob = np.sum(np.diag(result_matrix)) * 100  # Döntetlen
    away_win_prob = np.sum(np.triu(result_matrix, 1)) * 100  # Vendég győzelem

    return {
        "home_win": round(home_win_prob, 2),  # Két tizedesjegyre kerekítve
        "draw": round(draw_prob, 2),
        "away_win": round(away_win_prob, 2)
    }

