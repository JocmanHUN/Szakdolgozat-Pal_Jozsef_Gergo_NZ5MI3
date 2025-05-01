import pandas as pd
from src.Backend.DB.connection import get_db_connection

def fetch_random_nonoverlapping_fixtures(model_id: int, odds_min: float = 1.01, odds_max: float = 1000.0, target_count: int = 25):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT DISTINCT
        f.id AS fixture_id,
        f.date AS match_date,
        ht.name AS home_team,
        at.name AS away_team,
        mp.predicted_outcome,
        mp.was_correct,
        mp.probability AS model_probability,  -- <<< EZ a fontos sor
        CASE 
            WHEN mp.predicted_outcome = '1' THEN (
                SELECT MAX(o.home_odds) 
                FROM odds o 
                WHERE o.fixture_id = f.id AND o.home_odds BETWEEN %s AND %s
            )
            WHEN mp.predicted_outcome = 'X' THEN (
                SELECT MAX(o.draw_odds) 
                FROM odds o 
                WHERE o.fixture_id = f.id AND o.draw_odds BETWEEN %s AND %s
            )
            WHEN mp.predicted_outcome = '2' THEN (
                SELECT MAX(o.away_odds) 
                FROM odds o 
                WHERE o.fixture_id = f.id AND o.away_odds BETWEEN %s AND %s
            )
            ELSE NULL
        END AS odds
    FROM fixtures f
    JOIN model_predictions mp ON mp.fixture_id = f.id AND mp.model_id = %s
    JOIN teams ht ON ht.id = f.home_team_id
    JOIN teams at ON at.id = f.away_team_id
    WHERE f.status IN ('FT', 'AET', 'PEN')
      AND (
          (mp.predicted_outcome = '1' AND EXISTS (SELECT 1 FROM odds o WHERE o.fixture_id = f.id AND o.home_odds BETWEEN %s AND %s))
          OR (mp.predicted_outcome = 'X' AND EXISTS (SELECT 1 FROM odds o WHERE o.fixture_id = f.id AND o.draw_odds BETWEEN %s AND %s))
          OR (mp.predicted_outcome = '2' AND EXISTS (SELECT 1 FROM odds o WHERE o.fixture_id = f.id AND o.away_odds BETWEEN %s AND %s))
      )
    """

    params = (
        odds_min, odds_max,
        odds_min, odds_max,
        odds_min, odds_max,
        model_id,
        odds_min, odds_max,
        odds_min, odds_max,
        odds_min, odds_max
    )

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    df = pd.DataFrame(rows)
    df['match_date'] = pd.to_datetime(df['match_date'])
    df = df.sort_values('match_date').reset_index(drop=True)

    selected = []
    available = df.copy()

    while not available.empty and len(selected) < target_count:
        chosen = available.sample(1).iloc[0]
        selected.append(chosen)
        chosen_time = chosen['match_date']

        available = available[
            ~(
                (available['match_date'] >= chosen_time - pd.Timedelta(hours=2)) &
                (available['match_date'] <= chosen_time + pd.Timedelta(hours=2))
            )
        ]

    if len(selected) < target_count:
        print(f"⚠️ Csak {len(selected)} meccset tudtunk kiválasztani a megadott feltételekkel.")
        return pd.DataFrame(selected).sort_values('match_date').reset_index(drop=True)

    return pd.DataFrame(selected).sort_values('match_date').reset_index(drop=True)

def fetch_matches_for_all_models(odds_min: float = 1.01, odds_max: float = 1000.0, target_count: int = 25):
    """
    Visszaad egy DataFrame-et, amelyben minden kiválasztott mérkőzéshez
    minden modell predikciója szerepel (predicted_outcome, was_correct, odds, probability).
    Konzolra is kiírja az eredményt (részben).
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Modell ID-k és nevek
    all_model_ids = [1, 2, 3, 4, 5, 6]
    model_names = ["Bayes_Classic", "Monte_Carlo", "Poisson", "Bayes_Empirical", "Logistic_Regression", "Elo"]

    # --- 1. Válasszunk mérkőzéseket ---
    base_query = """
    SELECT DISTINCT
        f.id AS fixture_id,
        f.date AS match_date,
        ht.name AS home_team,
        at.name AS away_team
    FROM fixtures f
    JOIN model_predictions mp ON mp.fixture_id = f.id
    JOIN teams ht ON ht.id = f.home_team_id
    JOIN teams at ON at.id = f.away_team_id
    WHERE f.status IN ('FT', 'AET', 'PEN')
      AND EXISTS (
          SELECT 1 FROM odds o 
          WHERE o.fixture_id = f.id 
            AND (o.home_odds BETWEEN %s AND %s OR o.draw_odds BETWEEN %s AND %s OR o.away_odds BETWEEN %s AND %s)
      )
    """

    cursor.execute(base_query, (odds_min, odds_max, odds_min, odds_max, odds_min, odds_max))
    all_fixtures = cursor.fetchall()

    if not all_fixtures:
        conn.close()
        print("⚠️ Nem találtunk megfelelő mérkőzéseket.")
        return pd.DataFrame()

    df_fixtures = pd.DataFrame(all_fixtures)
    df_fixtures['match_date'] = pd.to_datetime(df_fixtures['match_date'])
    df_fixtures = df_fixtures.sort_values('match_date').reset_index(drop=True)

    # Nem átfedő meccsek kiválasztása
    selected_fixtures = []
    available = df_fixtures.copy()

    while not available.empty and len(selected_fixtures) < target_count:
        chosen = available.sample(1).iloc[0]
        selected_fixtures.append(chosen)
        chosen_time = chosen['match_date']

        available = available[
            ~(
                (available['match_date'] >= chosen_time - pd.Timedelta(hours=2)) &
                (available['match_date'] <= chosen_time + pd.Timedelta(hours=2))
            )
        ]

    if len(selected_fixtures) < target_count:
        print(f"⚠️ Csak {len(selected_fixtures)} mérkőzést tudtunk kiválasztani: {len(selected_fixtures)} db.")

    selected_df = pd.DataFrame(selected_fixtures).sort_values('match_date').reset_index(drop=True)

    # --- 2. Lekérjük az összes modell predikcióját minden kiválasztott meccsre ---
    combined_results = []

    for fixture_row in selected_df.itertuples():
        fixture_id = fixture_row.fixture_id

        # Lekérjük az összes modell predikcióját egy adott meccsre
        prediction_query = """
        SELECT 
            mp.model_id,
            mp.predicted_outcome,
            mp.was_correct,
            mp.probability,
            CASE 
                WHEN mp.predicted_outcome = '1' THEN (
                    SELECT MAX(o.home_odds) FROM odds o WHERE o.fixture_id = %s AND o.home_odds BETWEEN %s AND %s
                )
                WHEN mp.predicted_outcome = 'X' THEN (
                    SELECT MAX(o.draw_odds) FROM odds o WHERE o.fixture_id = %s AND o.draw_odds BETWEEN %s AND %s
                )
                WHEN mp.predicted_outcome = '2' THEN (
                    SELECT MAX(o.away_odds) FROM odds o WHERE o.fixture_id = %s AND o.away_odds BETWEEN %s AND %s
                )
                ELSE NULL
            END AS odds
        FROM model_predictions mp
        WHERE mp.fixture_id = %s
        ORDER BY mp.model_id
        """

        cursor.execute(prediction_query, (
            fixture_id, odds_min, odds_max,
            fixture_id, odds_min, odds_max,
            fixture_id, odds_min, odds_max,
            fixture_id
        ))

        predictions = cursor.fetchall()

        if not predictions:
            continue  # Ha nincs predikció, kihagyjuk ezt a meccset

        prediction_dict = {p['model_id']: p for p in predictions}

        # Új rekord létrehozása
        record = {
            "fixture_id": fixture_row.fixture_id,
            "match_date": fixture_row.match_date,
            "home_team": fixture_row.home_team,
            "away_team": fixture_row.away_team
        }

        # Minden modellhez hozzáadjuk a predikciókat
        for model_id, model_name in zip(all_model_ids, model_names):
            if model_id in prediction_dict:
                pred = prediction_dict[model_id]
                record[f"{model_name}_predicted_outcome"] = pred['predicted_outcome']
                record[f"{model_name}_was_correct"] = pred['was_correct']
                record[f"{model_name}_odds"] = pred['odds']
                record[f"{model_name}_model_probability"] = pred['probability']
            else:
                record[f"{model_name}_predicted_outcome"] = None
                record[f"{model_name}_was_correct"] = None
                record[f"{model_name}_odds"] = None
                record[f"{model_name}_model_probability"] = None

        combined_results.append(record)

    conn.close()

    # --- DataFrame létrehozása ---
    if combined_results:
        df_result = pd.DataFrame(combined_results)
        return df_result
    else:
        print("⚠️ Nem sikerült mérkőzéseket találni.")
        return pd.DataFrame()


