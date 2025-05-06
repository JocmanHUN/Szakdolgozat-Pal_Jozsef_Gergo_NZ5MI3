from src.Backend.DB.fixtures import get_last_matches


def calculate_weighted_form_multiplicative(team_id, num_matches=10, decay_factor=0.9):
    """
    Súlyozottan számítja ki a múltbeli győzelem, döntetlen, vereség arányokat.
    """
    matches = get_last_matches(team_id, num_matches)
    if not matches:
        return None

    valid_matches = [
        match for match in matches
        if match['score_home'] is not None and match['score_away'] is not None
    ]

    if not valid_matches:
        return None

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
        return None

    priors = {
        "win": weighted_wins / total_weights,
        "draw": weighted_draws / total_weights,
        "loss": weighted_losses / total_weights
    }

    return priors


def predict_with_balance_model(home_team_id, away_team_id, num_matches=10, decay_factor=0.9):
    home_probs = calculate_weighted_form_multiplicative(home_team_id, num_matches, decay_factor)
    away_probs = calculate_weighted_form_multiplicative(away_team_id, num_matches, decay_factor)

    if home_probs is None or away_probs is None:
        return None  # Ha nincs elég adat, nem tudunk becslést adni

    # Feltételes valószínűségek számítása Bayes-tétel alapján
    home_win_prob = (home_probs["win"] + (1 - away_probs["win"])) / 2 * 100
    draw_prob = (home_probs["draw"] + away_probs["draw"]) / 2 * 100
    away_win_prob = (away_probs["win"] + (1 - home_probs["win"])) / 2 * 100

    # Normalizálás: biztosítjuk, hogy az összeg pontosan 100% legyen
    total = home_win_prob + draw_prob + away_win_prob
    home_win_prob = (home_win_prob / total) * 100
    draw_prob = (draw_prob / total) * 100
    away_win_prob = (away_win_prob / total) * 100

    return {
        "1": round(home_win_prob, 2),
        "X": round(draw_prob, 2),
        "2": round(away_win_prob, 2)
    }
