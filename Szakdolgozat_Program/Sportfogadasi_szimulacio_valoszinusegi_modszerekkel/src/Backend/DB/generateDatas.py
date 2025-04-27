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
