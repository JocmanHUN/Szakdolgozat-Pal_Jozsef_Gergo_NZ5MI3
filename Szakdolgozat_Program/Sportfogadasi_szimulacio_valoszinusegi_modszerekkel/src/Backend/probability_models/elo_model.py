import math
from src.Backend.api_requests import get_team_statistics

ELO_START_VALUES = {
    "top_5": 1700,
    "top_20": 1550,
    "other": 1400
}

K_FACTOR = 32

def get_initial_elo(team_id, league_id, season="2024"):
    TOP_5_LEAGUES = {39, 140, 78, 135, 61}
    TOP_20_LEAGUES = {71, 128, 94, 88, 253, 144, 203, 235, 307, 210, 179, 262, 180, 278}

    if league_id in TOP_5_LEAGUES:
        base_elo = ELO_START_VALUES["top_5"]
    elif league_id in TOP_20_LEAGUES:
        base_elo = ELO_START_VALUES["top_20"]
    else:
        base_elo = ELO_START_VALUES["other"]

    prev_season = str(int(season) - 1)
    team_stats_current = get_team_statistics(league_id, season, team_id)
    team_stats_previous = get_team_statistics(league_id, prev_season, team_id)

    if not team_stats_current or not team_stats_previous:
        print(f"⚠️ Hiányzó statisztikák a csapathoz (ID: {team_id}).")
        return base_elo

    prev_league_id = team_stats_previous.get("league", {}).get("id", None)
    if prev_league_id is None or prev_league_id != league_id:
        print(f"⚠ FIGYELMEZTETÉS: A csapat (ID: {team_id}) más ligában játszott tavaly!")

    total_wins = team_stats_previous.get("fixtures", {}).get("wins", {}).get("total", 0) + \
                 team_stats_current.get("fixtures", {}).get("wins", {}).get("total", 0)
    total_draws = team_stats_previous.get("fixtures", {}).get("draws", {}).get("total", 0) + \
                  team_stats_current.get("fixtures", {}).get("draws", {}).get("total", 0)
    total_losses = team_stats_previous.get("fixtures", {}).get("loses", {}).get("total", 0) + \
                   team_stats_current.get("fixtures", {}).get("loses", {}).get("total", 0)

    elo_adjustment = (total_wins * 5) + (total_draws * 2) - (total_losses * 3)
    base_elo += elo_adjustment

    print(f"Csapat ID: {team_id}, Liga ID: {league_id}, Kezdő ELO: {base_elo}")
    return base_elo


def elo_predict(home_team_id, away_team_id, league_id, season="2024"):
    home_elo = get_initial_elo(home_team_id, league_id, season)
    away_elo = get_initial_elo(away_team_id, league_id, season)

    elo_diff = home_elo - away_elo

    P_home_win = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
    P_away_win = 1 / (1 + 10 ** ((home_elo - away_elo) / 400))

    P_draw = 1 / (1 + 10 ** (abs(elo_diff) / 800))

    total = P_home_win + P_away_win + P_draw
    P_home_win /= total
    P_away_win /= total
    P_draw /= total

    print(f"ELO különbség: {elo_diff}")
    print(f"Esélyek: Hazai - {P_home_win:.4f}, Döntetlen - {P_draw:.4f}, Vendég - {P_away_win:.4f}")

    return {
        "1": round(P_home_win * 100, 2),
        "X": round(P_draw * 100, 2),
        "2": round(P_away_win * 100, 2)
    }
