
from scipy.stats import poisson

from src.Backend.DB.fixtures import get_last_matches


def calculate_weighted_goal_expectancy(team_id, num_matches=10, decay_factor=0.8):
    """
    Kiszámítja egy csapat súlyozott várható gólmennyiségét az utolsó `num_matches` mérkőzése alapján.
    A frissebb meccsek nagyobb súlyt kapnak.
    """
    matches = get_last_matches(team_id, num_matches)
    if not matches:
        return 0.0, 0.0

    valid_matches = [
        match for match in matches
        if match['score_home'] is not None and match['score_away'] is not None
    ]

    if not valid_matches:
        return 0.0, 0.0

    total_weights = 0
    weighted_goals_for = 0
    weighted_goals_against = 0
    num_valid_matches = len(valid_matches)

    for i, match in enumerate(valid_matches):
        weight = decay_factor ** (num_valid_matches - i - 1)
        total_weights += weight

        goals_for = match['score_home'] if match['home_team_id'] == team_id else match['score_away']
        goals_against = match['score_away'] if match['home_team_id'] == team_id else match['score_home']

        weighted_goals_for += goals_for * weight
        weighted_goals_against += goals_against * weight

    if total_weights == 0:
        return 0.0, 0.0

    avg_goals_for = weighted_goals_for / total_weights
    avg_goals_against = weighted_goals_against / total_weights

    return float(avg_goals_for), float(avg_goals_against)


def monte_carlo_predict(home_team_id, away_team_id, num_simulations=10000, num_matches=10, decay_factor=0.8):
    """
    Monte Carlo szimulációval számolja ki a mérkőzés 1X2 valószínűségeit.
    """
    home_avg_goals, home_avg_conceded = calculate_weighted_goal_expectancy(home_team_id, num_matches, decay_factor)
    away_avg_goals, away_avg_conceded = calculate_weighted_goal_expectancy(away_team_id, num_matches, decay_factor)

    if home_avg_goals == 0 or away_avg_goals == 0:
        return None  # Nem áll rendelkezésre megfelelő adat a pontos előrejelzéshez

    home_expected_goals = (home_avg_goals + away_avg_conceded) / 2
    away_expected_goals = (away_avg_goals + home_avg_conceded) / 2

    home_wins, draws, away_wins = 0, 0, 0

    for _ in range(num_simulations):
        home_goals = poisson.rvs(home_expected_goals)
        away_goals = poisson.rvs(away_expected_goals)

        if home_goals > away_goals:
            home_wins += 1
        elif home_goals < away_goals:
            away_wins += 1
        else:
            draws += 1

    home_win_prob = (home_wins / num_simulations) * 100
    draw_prob = (draws / num_simulations) * 100
    away_win_prob = (away_wins / num_simulations) * 100

    return {
        "1": round(home_win_prob, 2),
        "X": round(draw_prob, 2),
        "2": round(away_win_prob, 2)
    }
