from src.Backend.helpersAPI import get_last_matches


def calculate_prior_probabilities(team_id):
    """
    Kiszámítja egy csapat múltbeli győzelem, döntetlen és vereség priorként használt arányait.
    """
    matches = get_last_matches(team_id)
    if not matches:
        return None

    total_matches = len(matches)
    wins = sum(1 for match in matches if
               (match['home_team_id'] == team_id and match['score_home'] > match['score_away']) or
               (match['away_team_id'] == team_id and match['score_away'] > match['score_home'])
               )
    draws = sum(1 for match in matches if match['score_home'] == match['score_away'])
    losses = total_matches - wins - draws

    return {
        "win": wins / total_matches,  # Győzelmi arány
        "draw": draws / total_matches,  # Döntetlen arány
        "loss": losses / total_matches  # Vereség arány
    }


def bayes_classic_predict(home_team_id, away_team_id):
    home_priors = calculate_prior_probabilities(home_team_id)
    away_priors = calculate_prior_probabilities(away_team_id)

    if home_priors is None or away_priors is None:
        return None  # Ha nincs elég adat, nem tudunk becslést adni

    total_matches_home = len(get_last_matches(home_team_id))
    total_matches_away = len(get_last_matches(away_team_id))

    if total_matches_home == 0 or total_matches_away == 0:
        return None

    # Súlyozott döntetlen számítás
    P_draw_given_played = ((home_priors["draw"] * total_matches_home) + (away_priors["draw"] * total_matches_away)) / (total_matches_home + total_matches_away)

    # Bayes-tétel alkalmazása helyes normalizálással
    P_home_win = home_priors["win"] * (1 - away_priors["win"])
    P_away_win = away_priors["win"] * (1 - home_priors["win"])
    P_draw = P_draw_given_played  # Már súlyozott döntetlen valószínűség

    # Normalizálás, hogy az összeg pontosan 100% legyen
    total = P_home_win + P_away_win + P_draw
    P_home_win = (P_home_win / total) * 100
    P_draw = (P_draw / total) * 100
    P_away_win = (P_away_win / total) * 100

    return {
        "1": round(P_home_win, 2),
        "X": round(P_draw, 2),
        "2": round(P_away_win, 2)
    }
