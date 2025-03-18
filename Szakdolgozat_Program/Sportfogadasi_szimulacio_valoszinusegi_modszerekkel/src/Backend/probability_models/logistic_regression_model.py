import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from src.Backend.api_requests import get_match_statistics
from src.Backend.helpersAPI import get_last_matches


def prepare_training_data(team_id, num_matches=10):
    """
    Előkészíti az adathalmazt a logisztikus regresszióhoz a múltbéli mérkőzések statisztikái alapján.
    """
    matches = get_last_matches(team_id, num_matches)

    if not matches:
        print(f"⚠️ Nincs elég adat a regresszióhoz ({team_id}).")
        return None, None

    X = []
    y = []

    for match in matches:
        match_stats_list = get_match_statistics(match['id'])

        if not match_stats_list:
            print(f"⚠️ Hiányzó statisztikák mérkőzéshez: {match['id']}. Kihagyva.")
            continue

        match_stats = next((stats for stats in match_stats_list if stats['team_id'] == team_id), None)

        if not match_stats:
            print(f"⚠️ Nincsenek statisztikai adatok erre a csapatra: {team_id}. Kihagyva.")
            continue

        for key in match_stats.keys():
            if match_stats[key] is None:
                match_stats[key] = 0

        ball_possession = float(str(match_stats.get('ball_possession', '50')).replace('%', ''))
        passes_percentage = float(str(match_stats.get('passes_percentage', '80')).replace('%', ''))

        features = [
            match_stats.get('shots_on_goal', 0),
            match_stats.get('shots_off_goal', 0),
            match_stats.get('total_shots', 0),
            match_stats.get('blocked_shots', 0),
            match_stats.get('shots_insidebox', 0),
            match_stats.get('shots_outsidebox', 0),
            match_stats.get('fouls', 0),
            match_stats.get('corner_kicks', 0),
            match_stats.get('offsides', 0),
            ball_possession,
            match_stats.get('yellow_cards', 0),
            match_stats.get('red_cards', 0),
            match_stats.get('goalkeeper_saves', 0),
            match_stats.get('total_passes', 0),
            match_stats.get('passes_accurate', 0),
            passes_percentage
        ]

        if match['home_team_id'] == team_id:
            team_goals = match['score_home'] or 0
            opponent_goals = match['score_away'] or 0
        else:
            team_goals = match['score_away'] or 0
            opponent_goals = match['score_home'] or 0

        X.append(features)
        y.append(2 if team_goals > opponent_goals else 0 if team_goals < opponent_goals else 1)

    if not X:
        print("⚠️ Nincs elég adat a tanuláshoz.")
        return None, None

    print("\n🔹 Tanítási adatok:")
    for i, row in enumerate(X):
        print(f"📊 Mérkőzés {i + 1}: {row}")

    print(f"📊 Célváltozó (y): {y}")
    print(f"📈 Feature mátrix mérete: {np.array(X).shape}")

    imputer = SimpleImputer(strategy="mean")
    X = imputer.fit_transform(X)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    return np.array(X), np.array(y)


def train_logistic_regression(team_id):
    """
    Logisztikus regresszió betanítása a statisztikai adatok alapján.
    """
    X, y = prepare_training_data(team_id)
    print(f"📊 Egyedi osztályok a célváltozóban és azok előfordulásai: {np.unique(y, return_counts=True)}")

    if X is None or y is None:
        return None

    model = LogisticRegression(solver='lbfgs', class_weight='balanced')
    model.fit(X, y)
    return model


def get_average_team_statistics(team_id, num_matches=10):
    """
    Egy csapat utolsó `num_matches` mérkőzésének statisztikai átlaga.
    Ha nincs adat, akkor alapértékeket használunk.
    """
    matches = get_last_matches(team_id, num_matches)

    if not matches:
        print(f"⚠️ Nincs elérhető múltbeli statisztika a csapathoz: {team_id}")
        return np.zeros(16)

    total_stats = np.zeros(16, dtype=float)
    count = 0

    for match in matches:
        match_stats_list = get_match_statistics(match['id'])

        if not match_stats_list:
            continue

        match_stats = next((stats for stats in match_stats_list if stats['team_id'] == team_id), None)

        if not match_stats:
            continue

        features = [
            match_stats.get('shots_on_goal', 0),
            match_stats.get('shots_off_goal', 0),
            match_stats.get('total_shots', 0),
            match_stats.get('blocked_shots', 0),
            match_stats.get('shots_insidebox', 0),
            match_stats.get('shots_outsidebox', 0),
            match_stats.get('fouls', 0),
            match_stats.get('corner_kicks', 0),
            match_stats.get('offsides', 0),
            match_stats.get('ball_possession', '50'),
            match_stats.get('yellow_cards', 0),
            match_stats.get('red_cards', 0),
            match_stats.get('goalkeeper_saves', 0),
            match_stats.get('total_passes', 0),
            match_stats.get('passes_accurate', 0),
            match_stats.get('passes_percentage', '80')
        ]

        try:
            features = [float(str(x).replace('%', '').strip()) if x is not None else 0.0 for x in features]
            total_stats += np.array(features, dtype=float)
            count += 1
        except ValueError as e:
            print(f"⚠️ Hiba történt a konverzió során: {e}. Mérkőzés kihagyva.")

    return total_stats / count if count > 0 else np.zeros(16)


def logistic_regression_predict(home_team_id, away_team_id):
    """
    Logisztikus regressziós modell előrejelzése egy mérkőzés kimenetelére.
    """
    home_model = train_logistic_regression(home_team_id)
    away_model = train_logistic_regression(away_team_id)

    if home_model is None or away_model is None:
        return None

    home_stats = get_average_team_statistics(home_team_id)
    away_stats = get_average_team_statistics(away_team_id)

    if home_stats is None or away_stats is None:
        return None

    match_features = (home_stats + away_stats) / 2
    match_features = np.array([match_features])

    print("\n🔹 Előrejelzéshez használt feature-ek:")
    print(f"📊 {match_features}")

    home_probs = home_model.predict_proba(match_features)[0]
    away_probs = away_model.predict_proba(match_features)[0]

    home_win_prob = home_probs[2] * 100
    draw_prob = (home_probs[1] + away_probs[1]) / 2 * 100
    away_win_prob = away_probs[0] * 100

    print(f"\n📊 **Végső előrejelzés**: 🏠 {home_win_prob:.2f}% ⚖️ {draw_prob:.2f}% 🚀 {away_win_prob:.2f}%")

    return {
        "1": round(home_win_prob, 2),
        "X": round(draw_prob, 2),
        "2": round(away_win_prob, 2)
    }
