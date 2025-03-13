from src.Backend.helpersAPI import get_last_10_matches


def calculate_bayes_probabilities(team_id):
    """
    Kiszámítja egy csapat múltbeli győzelem, döntetlen és vereség arányait.
    """
    matches = get_last_10_matches(team_id)
    if not matches:
        return None

    total_matches = len(matches)
    wins = sum(
        1 for match in matches if (match['home_team_id'] == team_id and match['score_home'] > match['score_away']) or
        (match['away_team_id'] == team_id and match['score_away'] > match['score_home']))
    draws = sum(1 for match in matches if match['score_home'] == match['score_away'])
    losses = total_matches - wins - draws

    return {
        "win": wins / total_matches,
        "draw": draws / total_matches,
        "loss": losses / total_matches
    }


def bayes_outcome_probabilities(home_team_id, away_team_id):
    """
    Bayes-tétel segítségével kiszámítja a mérkőzés 1X2 valószínűségeit, biztosítva, hogy az összeg 100% legyen.
    """
    home_probs = calculate_bayes_probabilities(home_team_id)
    away_probs = calculate_bayes_probabilities(away_team_id)

    if home_probs is None or away_probs is None:
        return None  # Ha nincs elég adat, nem tudunk becslést adni

    # Feltételes valószínűségek számítása Bayes-tétel alapján
    home_win_prob = (home_probs["win"] + (1 - away_probs["win"])) / 2 * 100
    draw_prob = (home_probs["draw"] + away_probs["draw"]) / 2 * 100
    away_win_prob = (away_probs["win"] + (1 - home_probs["win"])) / 2 * 100

    # **Normalizálás**: biztosítjuk, hogy az összeg pontosan 100% legyen
    total = home_win_prob + draw_prob + away_win_prob
    home_win_prob = (home_win_prob / total) * 100
    draw_prob = (draw_prob / total) * 100
    away_win_prob = (away_win_prob / total) * 100

    return {
        "home_win": round(home_win_prob, 2),
        "draw": round(draw_prob, 2),
        "away_win": round(away_win_prob, 2)
    }
