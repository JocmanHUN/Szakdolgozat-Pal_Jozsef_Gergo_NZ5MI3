from datetime import datetime

from dateutil import parser

from src.Backend.api_requests import get_league_id_by_fixture, get_match_statistics, get_fixtures_for_team, \
    get_head_to_head_stats, fetch_odds_for_fixture
from src.Backend.helpersAPI import get_league_by_team, save_model_prediction, write_league_id_to_team, get_last_matches, \
    write_to_match_statistics, write_to_fixtures, read_odds_by_fixture, write_to_odds, read_from_match_statistics, \
    read_head_to_head_stats
from src.Backend.probability_models.bayes_classic_model import bayes_classic_predict
from src.Backend.probability_models.bayes_empirical_model import bayes_empirical_predict
from src.Backend.probability_models.elo_model import elo_predict
from src.Backend.probability_models.logistic_regression_model import logistic_regression_predict
from src.Backend.probability_models.monte_carlo_model import monte_carlo_predict
from src.Backend.probability_models.poisson_model import poisson_predict


def save_all_predictions(fixture_id, home_team_id, away_team_id, match_group_id):
    """
    Elmenti az összes modell előrejelzését egy adott mérkőzésre.
    """
    # 🏆 Liga lekérése csapat alapján
    league_id = get_league_by_team(home_team_id)

    # 📆 Helyes szezon megállapítása
    season = get_current_season()

    if league_id is None:
        print(
            f"⚠️ Nem sikerült lekérni a liga azonosítót a {home_team_id} csapathoz. Próbálkozás fixture_id alapján...")
        league_id = get_league_id_by_fixture(fixture_id)

        if league_id:
            write_league_id_to_team(home_team_id, league_id)
        else:
            print("❌ Elo-modell kihagyva, liga ID továbbra sincs.")
            return

    models = {
        1: bayes_classic_predict,
        2: monte_carlo_predict,
        3: poisson_predict,
        4: bayes_empirical_predict,
        5: logistic_regression_predict,
        6: lambda h, a: elo_predict(h, a, league_id, season)  # Elo-modell csapat alapján szerzett ligával
    }

    for model_id, model_function in models.items():
        prediction = model_function(home_team_id, away_team_id)

        if prediction:
            best_outcome = max(prediction, key=prediction.get)
            best_probability = prediction[best_outcome]
            print(best_outcome, best_probability)
            save_model_prediction(fixture_id, model_id, best_outcome, best_probability, match_group_id)

    print(f"📊 Minden modell előrejelzése mentve a {fixture_id} mérkőzéshez!")


def get_current_season():
    """
    Megállapítja az aktuális szezon évszámát a futó szezon alapján.
    Példa: Ha 2024 március van → 2023/24 szezon → 2023 a helyes szezonkezdés.
           Ha 2024 szeptember van → 2024/25 szezon → 2024 a helyes szezonkezdés.
    """
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Ha az év első felében vagyunk (január - június), akkor az előző év a szezon kezdete
    if current_month < 7:
        return current_year - 1  # Pl. 2024 március → 2023/24 szezon
    else:
        return current_year  # Pl. 2024 szeptember → 2024/25 szezon


def ensure_simulation_data_available(fixture_list, num_matches=15):
    """
    Biztosítja, hogy a modellekhez szükséges adatok rendelkezésre álljanak az adatbázisban.
    Ha hiányoznak, az API-ból lekérdezi és elmenti azokat.

    :param fixture_list: Mérkőzések listája ([(home_team_id, away_team_id, fixture_id), ...]).
    :param league_id: A liga azonosítója.
    :param season: Az aktuális szezon.
    """
    for home_team_id, away_team_id, fixture_id in fixture_list:
        print(f"\n🔎 **Adatok biztosítása a mérkőzéshez: {home_team_id} vs {away_team_id}** (Fixture ID: {fixture_id})")

        for team_id in [home_team_id, away_team_id]:
            matches = get_last_matches(team_id,away_team_id, num_matches)
            if len(matches) < 15:
                print(f"⚠️ Nincs elég múltbeli meccs (Csapat ID: {team_id}), API lekérés...")
                api_matches = get_fixtures_for_team(team_id,num_matches)
                if api_matches:
                    write_to_fixtures(api_matches)
                    print(f"✅ {len(api_matches)} mérkőzés elmentve (Csapat ID: {team_id}).")

                    # **Mérkőzés statisztikák biztosítása**
                    for match in api_matches:
                        if not read_from_match_statistics(match["id"]):
                            print(f"⚠️ Hiányzó statisztikák mérkőzéshez: {match['id']}, API lekérés...")
                            stats = get_match_statistics(match["id"])
                            if stats:
                                print(f"✅ Statisztikák elmentve mérkőzéshez: {match['id']}")
                            else:
                                print(f"❌ Nem sikerült lekérni a statisztikákat: {match['id']}")
                else:
                    print(f"❌ API-ból sem sikerült lekérni az adatokat a csapathoz: {team_id}")

        # **Head-to-head statisztikák biztosítása**
        h2h_matches = read_head_to_head_stats(home_team_id, away_team_id)
        if h2h_matches:
            latest_h2h_date = max(match["date"] for match in h2h_matches)  # Legfrissebb H2H meccs dátuma
            print(f"🔎 Utolsó H2H mérkőzés dátuma az adatbázisban: {latest_h2h_date}")
        else:
            latest_h2h_date = None

        # **Lekérjük az API-ból az utolsó 5 H2H mérkőzést**
        h2h_stats = get_head_to_head_stats(home_team_id, away_team_id)
        if h2h_stats:
            new_h2h_matches = [
                match for match in h2h_stats
                if latest_h2h_date is None or (
                        (parser.isoparse(match["date"]) if isinstance(match["date"], str) else match["date"]).replace(
                            tzinfo=None)
                        > latest_h2h_date.replace(tzinfo=None)
                )
            ]
            if new_h2h_matches:
                print(f"✅ {len(new_h2h_matches)} új H2H mérkőzés elmentése ({home_team_id} vs {away_team_id})")
                write_to_fixtures(new_h2h_matches)

                # **H2H mérkőzések statisztikáinak biztosítása**
                for match in new_h2h_matches:
                    if not read_from_match_statistics(match["id"]):
                        print(f"⚠️ Hiányzó statisztikák H2H mérkőzéshez: {match['id']}, API lekérés...")
                        stats = get_match_statistics(match["id"])
                        if stats:
                            print(f"✅ Statisztikák elmentve H2H mérkőzéshez: {match['id']}")
                        else:
                            print(f"❌ Nem sikerült lekérni a statisztikákat: {match['id']}")
            else:
                print(f"🔵 Nincsenek újabb H2H mérkőzések az adatbázishoz képest.")
        else:
            print(f"❌ Nem sikerült lekérni a H2H statisztikákat: {home_team_id} vs {away_team_id}")

        if not read_odds_by_fixture(fixture_id):
            print(f"⚠️ Hiányzó oddsok: {fixture_id}, API lekérés...")
            odds = fetch_odds_for_fixture(fixture_id)
            if odds:
                processed_odds = []
                for bookmaker in odds:  # A fogadóirodákat tartalmazó lista
                    for bet in bookmaker.get("bookmakers", []):
                        for bet_option in bet.get("bets", []):
                            if bet_option.get("name") == "Match Winner":
                                processed_odds.append({
                                    "fixture_id": fixture_id,
                                    "bookmaker_id": bet["id"],
                                    "home_odds": bet_option["values"][0]["odd"],
                                    "draw_odds": bet_option["values"][1]["odd"],
                                    "away_odds": bet_option["values"][2]["odd"],
                                    "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                })

                if processed_odds:
                    write_to_odds(processed_odds)  # Oddsok mentése
                    print(f"✅ Oddsok elmentve a mérkőzéshez: {fixture_id}")
                else:
                    print(f"❌ Nem sikerült oddsokat feldolgozni: {fixture_id}")
            else:
                print(f"❌ Nem sikerült lekérni az oddsokat: {fixture_id}")

    print("\n✅ **Minden szükséges adat elérhető! A szimuláció futtatható.** 🚀")

