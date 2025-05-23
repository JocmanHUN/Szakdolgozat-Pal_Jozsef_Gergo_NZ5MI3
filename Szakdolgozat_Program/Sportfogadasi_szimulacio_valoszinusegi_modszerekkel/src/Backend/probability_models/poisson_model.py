import numpy as np
import scipy.stats as stats

from src.Backend.DB.fixtures import get_last_matches


def calculate_weighted_goal_expectancy(team_id, num_matches=10, decay_factor=0.9):
    """
    Kiszámítja a várható gólmennyiséget súlyozottan az utolsó `num_matches` mérkőzés alapján.
    Frissebb meccsek nagyobb súlyt kapnak (decay_factor értékkel súlyozva).
    """
    matches = get_last_matches(team_id, num_matches)
    if not matches:
        return None, None

    valid_matches = [
        match for match in matches
        if match['score_home'] is not None and match['score_away'] is not None
    ]

    if not valid_matches:
        return None, None

    total_weights = 0
    weighted_goals_for = 0
    weighted_goals_against = 0

    num_valid_matches = len(valid_matches)

    for i, match in enumerate(valid_matches):
        weight = decay_factor ** (num_valid_matches - i - 1)  # Újabb meccsek nagyobb súlyt kapnak
        total_weights += weight

        goals_for = match['score_home'] if match['home_team_id'] == team_id else match['score_away']
        goals_against = match['score_away'] if match['home_team_id'] == team_id else match['score_home']

        weighted_goals_for += goals_for * weight
        weighted_goals_against += goals_against * weight

    avg_goals_for = weighted_goals_for / total_weights
    avg_goals_against = weighted_goals_against / total_weights

    return avg_goals_for, avg_goals_against


def poisson_probability(expected_goals, actual_goals):
    """
    Poisson valószínűség kiszámítása egy adott gólmennyiségre.
    """
    return stats.poisson.pmf(actual_goals, expected_goals)


def poisson_predict(home_team_id, away_team_id, num_matches=10, decay_factor=0.9):
    """
    A Poisson-eloszlás segítségével kiszámítja a mérkőzés 1X2 valószínűségeit, százalékban kifejezve.
    Az eredményeket normalizálja, hogy pontosan 100%-ot adjanak ki.
    """
    home_avg_goals, home_avg_conceded = calculate_weighted_goal_expectancy(home_team_id, num_matches, decay_factor)
    away_avg_goals, away_avg_conceded = calculate_weighted_goal_expectancy(away_team_id, num_matches, decay_factor)

    if home_avg_goals is None or away_avg_goals is None:
        return None  # Ha nincs elég adat, nem tudunk becslést adni

    home_expected_goals = (home_avg_goals + away_avg_conceded) / 2
    away_expected_goals = (away_avg_goals + home_avg_conceded) / 2

    max_goals = 5  # Itt fix 0-5 gólig számolunk (tehát 6x6 mátrix)

    result_matrix = np.zeros((max_goals + 1, max_goals + 1))

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            prob = poisson_probability(home_expected_goals, home_goals) * \
                   poisson_probability(away_expected_goals, away_goals)
            result_matrix[home_goals, away_goals] = prob

    # Nyers valószínűségek
    home_raw = np.sum(np.tril(result_matrix, -1))
    draw_raw = np.sum(np.diag(result_matrix))
    away_raw = np.sum(np.triu(result_matrix, 1))
    total_raw = home_raw + draw_raw + away_raw

    # Normalizált értékek
    home_win_prob = (home_raw / total_raw) * 100
    draw_prob = (draw_raw / total_raw) * 100
    away_win_prob = (away_raw / total_raw) * 100

    return {
        "1": float(round(home_win_prob, 2)),
        "X": float(round(draw_prob, 2)),
        "2": float(round(away_win_prob, 2))
    }




