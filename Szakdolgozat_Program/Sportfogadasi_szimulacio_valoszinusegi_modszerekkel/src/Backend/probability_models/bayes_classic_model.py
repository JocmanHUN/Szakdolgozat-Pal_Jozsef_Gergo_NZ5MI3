from src.Backend.DB.fixtures import get_last_matches


def calculate_prior_probabilities(team_id, num_matches=10, decay_factor=0.9):
    """
    Súlyozottan számítja ki a múltbeli győzelem, döntetlen, vereség arányokat.
    """
    matches = get_last_matches(team_id, num_matches)
    if not matches:
        return None, 0

    valid_matches = [m for m in matches if m['score_home'] is not None and m['score_away'] is not None]
    if not valid_matches:
        return None, 0

    total_weights = 0
    weighted_wins, weighted_draws, weighted_losses = 0, 0, 0
    num_valid_matches = len(valid_matches)

    for i, match in enumerate(valid_matches):
        weight = decay_factor ** (num_valid_matches - i - 1)
        total_weights += weight

        if match['score_home'] == match['score_away']:
            weighted_draws += weight
        elif (match['home_team_id'] == team_id and match['score_home'] > match['score_away']) or \
             (match['away_team_id'] == team_id and match['score_away'] > match['score_home']):
            weighted_wins += weight
        else:
            weighted_losses += weight

    if total_weights == 0:
        return None, 0

    priors = {
        "win": weighted_wins / total_weights,
        "draw": weighted_draws / total_weights,
        "loss": weighted_losses / total_weights
    }

    return priors, num_valid_matches


def bayes_classic_predict(home_team_id, away_team_id, num_matches=10, decay_factor=0.9):
    home_priors, total_matches_home = calculate_prior_probabilities(home_team_id, num_matches, decay_factor)
    away_priors, total_matches_away = calculate_prior_probabilities(away_team_id, num_matches, decay_factor)

    if home_priors is None or away_priors is None or total_matches_home == 0 or total_matches_away == 0:
        return None

    P_draw_given_played = ((home_priors["draw"] * total_matches_home) +
                           (away_priors["draw"] * total_matches_away)) / (total_matches_home + total_matches_away)

    P_home_win = home_priors["win"] * (1 - away_priors["win"])
    P_away_win = away_priors["win"] * (1 - home_priors["win"])
    P_draw = P_draw_given_played

    total = P_home_win + P_away_win + P_draw
    P_home_win = (P_home_win / total) * 100
    P_draw = (P_draw / total) * 100
    P_away_win = (P_away_win / total) * 100

    return {
        "1": round(P_home_win, 2),
        "X": round(P_draw, 2),
        "2": round(P_away_win, 2)
    }
