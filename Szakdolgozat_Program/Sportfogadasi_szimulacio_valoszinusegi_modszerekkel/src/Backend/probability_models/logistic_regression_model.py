import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import cross_val_score

from src.Backend.api_requests import get_match_statistics
from src.Backend.helpersAPI import get_last_matches


def extract_features(match_stats):
    features = np.array([
        safe_float(match_stats.get('shots_on_goal')),
        safe_float(match_stats.get('shots_off_goal')),
        safe_float(match_stats.get('total_shots')),
        safe_float(match_stats.get('blocked_shots')),
        safe_float(match_stats.get('shots_insidebox')),
        safe_float(match_stats.get('shots_outsidebox')),
        safe_float(match_stats.get('fouls')),
        safe_float(match_stats.get('corner_kicks')),
        safe_float(match_stats.get('offsides')),
        safe_float(match_stats.get('ball_possession'), default=50.0),
        safe_float(match_stats.get('yellow_cards')),
        safe_float(match_stats.get('red_cards')),
        safe_float(match_stats.get('goalkeeper_saves')),
        safe_float(match_stats.get('total_passes')),
        safe_float(match_stats.get('passes_accurate')),
        safe_float(match_stats.get('passes_percentage'), default=80.0)
    ], dtype=np.float64)

    print(f"📌 Extracted features: {features}")
    return features

def prepare_training_data(team_id, num_matches=30):
    print(f"🔍 Preparing training data for team ID: {team_id}")
    matches = get_last_matches(team_id, num_matches)
    print(f"✅ {len(matches)} matches retrieved for team ID: {team_id}")

    X, y = [], []

    for match in matches:
        match_stats_list = get_match_statistics(match['id'])
        print(f"⚽ Match ID: {match['id']} - Stats retrieved: {len(match_stats_list) if match_stats_list else 'None'}")

        if not match_stats_list or len(match_stats_list) != 2:
            print("⚠️ Skipped match due to incomplete statistics.")
            continue
        print(match_stats_list)
        # Ellenőrizzük, hogy API vagy adatbázisos struktúra
        if 'team' in match_stats_list[0]:
            home_stats = next((s for s in match_stats_list if s.get('team', {}).get('id') == match['home_team_id']),
                              None)
            away_stats = next((s for s in match_stats_list if s.get('team', {}).get('id') == match['away_team_id']),
                              None)
        else:
            home_stats = next((s for s in match_stats_list if s.get('team_id') == match['home_team_id']), None)
            away_stats = next((s for s in match_stats_list if s.get('team_id') == match['away_team_id']), None)

        if not home_stats or not away_stats:
            print("⚠️ Skipped match due to missing home or away stats.")
            continue

        home_features = extract_features(home_stats)
        away_features = extract_features(away_stats)

        if match['score_home'] is None or match['score_away'] is None:
            print("⚠️ Skipped match due to missing score.")
            continue

        if match['home_team_id'] == team_id:
            indicators = [1, 0]
            result = 2 if match['score_home'] > match['score_away'] else 0 if match['score_home'] < match[
                'score_away'] else 1
            match_features = np.concatenate((home_features, away_features, indicators))
        else:
            indicators = [0, 1]
            result = 2 if match['score_away'] > match['score_home'] else 0 if match['score_away'] < match[
                'score_home'] else 1
            match_features = np.concatenate((away_features, home_features, indicators))

        print(f"🔸 Match features: {match_features} - Result label: {result}")

        X.append(match_features)
        y.append(result)

    print(f"🟢 Training dataset prepared with {len(X)} samples.")
    return np.array(X), np.array(y)


def train_logistic_regression(home_team_id, away_team_id):
    home_X, home_y = prepare_training_data(home_team_id)
    away_X, away_y = prepare_training_data(away_team_id)

    X = np.concatenate((home_X, away_X))
    y = np.concatenate((home_y, away_y))

    imputer = SimpleImputer(strategy="mean")
    scaler = StandardScaler()

    X = imputer.fit_transform(X)
    X = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=1000, class_weight='balanced')

    cv = min(5, len(y))
    scores = cross_val_score(model, X, y, cv=cv)
    print(f"📈 Cross-validation scores: {scores}")
    print(f"📊 Average CV accuracy: {scores.mean():.2%}")

    model.fit(X, y)
    print(f"🎯 Model trained successfully.")

    return model, imputer, scaler

def logistic_regression_predict(home_team_id, away_team_id):
    print(f"🔮 Predicting outcome for Home: {home_team_id} vs Away: {away_team_id}")
    model, imputer, scaler = train_logistic_regression(home_team_id, away_team_id)

    home_stats = get_average_team_statistics(home_team_id)
    away_stats = get_average_team_statistics(away_team_id)

    match_features = np.concatenate((home_stats, away_stats, [1, 0])).reshape(1, -1)  # [1,0]: Hazai indikátor
    match_features = imputer.transform(match_features)
    match_features = scaler.transform(match_features)

    probs = model.predict_proba(match_features)[0]

    # probs[0]: vereség (away win), probs[1]: döntetlen, probs[2]: győzelem (home win)
    print(f"🔖 Predicted probabilities: Home Win: {probs[2]}, Draw: {probs[1]}, Away Win: {probs[0]}")

    return {
        "1": float(round(probs[2] * 100, 2)),
        "X": float(round(probs[1] * 100, 2)),
        "2": float(round(probs[0] * 100, 2))
    }



def get_average_team_statistics(team_id, num_matches=10):
    print(f"📊 Calculating average statistics for team ID: {team_id}")
    matches = get_last_matches(team_id, num_matches)
    total_stats = np.zeros(16, dtype=np.float64)
    count = 0

    for match in matches:
        match_stats_list = get_match_statistics(match['id'])
        if not match_stats_list:
            continue

        match_stats = next((stats for stats in match_stats_list if stats['team_id'] == team_id), None)
        if not match_stats:
            continue

        total_stats += extract_features(match_stats)
        count += 1

    if count == 0:
        print(f"⚠️ Nincs elegendő adat a csapat {team_id} statisztikáihoz!")
        return np.full(16, 0.0)

    avg_stats = total_stats / count
    print(f"📌 Average stats for team ID {team_id}: {avg_stats}")
    return avg_stats

def safe_float(val, default=0.0):
    try:
        if isinstance(val, str):
            val = val.replace('%', '')
        return float(val)
    except (ValueError, TypeError):
        return default