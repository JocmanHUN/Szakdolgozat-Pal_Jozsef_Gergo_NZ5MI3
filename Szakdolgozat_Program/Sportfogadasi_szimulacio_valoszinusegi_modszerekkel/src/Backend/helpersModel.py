from datetime import datetime

from dateutil import parser

from src.Backend.api_requests import get_league_id_by_fixture, get_match_statistics, get_fixtures_for_team, \
    get_head_to_head_stats, fetch_odds_for_fixture, get_fixture_by_id, get_team_country_by_id
from src.Backend.helpersAPI import get_league_by_team, save_model_prediction, write_league_id_to_team, get_last_matches, \
    write_to_match_statistics, write_to_fixtures, read_odds_by_fixture, write_to_odds, read_from_match_statistics, \
    read_head_to_head_stats, delete_fixture_by_id
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
    valid_fixtures = []
    for home_team_id, away_team_id, fixture_id in fixture_list:
        print(f"\n🔎 **Adatok biztosítása a mérkőzéshez: {home_team_id} vs {away_team_id}** (Fixture ID: {fixture_id})")
        for team_id in [home_team_id, away_team_id]:
            matches = get_last_matches(team_id, away_team_id, num_matches)

            # Ha nincs elég meccs, próbáljuk pótolni
            if not matches or len(matches) < num_matches:
                print(
                    f"⚠️ Nem elegendő meccs található az adatbázisban (Csapat ID: {team_id}), API lekérés szükséges...")

                api_matches = get_fixtures_for_team(team_id, num_matches+10)
                if api_matches:
                    write_to_fixtures(api_matches)
                    print(f"✅ {len(api_matches)} mérkőzés elmentve (Csapat ID: {team_id}).")
                else:
                    print(f"❌ Nem sikerült meccseket lekérni az API-ból (Csapat ID: {team_id})")

                # Újra lekérjük az adatbázisból
                matches = get_last_matches(team_id, away_team_id, 30)

            # 🔽 Statisztikával rendelkező meccsek szűrése
            valid_matches = []
            consecutive_failures = 0

            for match in matches:
                stats = read_from_match_statistics(match["id"])
                if stats:
                    valid_matches.append(match)
                    consecutive_failures = 0
                else:
                    stats_from_api = get_match_statistics(match["id"])
                    if stats_from_api:
                        print(f"✅ Stat lekérve és elmentve: {match['id']}")
                        valid_matches.append(match)
                        consecutive_failures = 0
                    else:
                        print(f"❌ Nincs stat az API-ban sem, törlés: {match['id']}")
                        delete_fixture_by_id(match["id"])  # Csak ha tényleg volt mentve
                        consecutive_failures += 1

                        if consecutive_failures >= 30:
                            print(f"🛑 3 egymást követő stat hiány, megszakítva (Csapat ID: {team_id})")
                            break

                if len(valid_matches) >= num_matches:
                    break

            print(f"📊 {len(valid_matches)} statisztikával rendelkező meccs (Csapat ID: {team_id})")

            if len(valid_matches) < 10:
                print(
                    f"⛔ Nem elég statisztikás meccs (min. 10 kellene), ezért a mérkőzés kihagyva (Csapat ID: {team_id})")
                break  # már az egyik csapatnál sem elég, nem kell nézni tovább

        h2h_matches = read_head_to_head_stats(home_team_id, away_team_id)

        if len(h2h_matches) < 10:
            print(
                f"⚠️ Nem elegendő H2H meccs az adatbázisban ({len(h2h_matches)} db), API lekérés szükséges: ({home_team_id} vs {away_team_id})")
            h2h_stats = get_head_to_head_stats(home_team_id, away_team_id)
        else:
            print(f"✅ Megfelelő számú H2H meccs található az adatbázisban ({len(h2h_matches)} db)")
            h2h_stats = h2h_matches

        valid_matches = []

        for match in h2h_stats:
            match_date = parser.isoparse(match["date"]) if isinstance(match["date"], str) else match["date"]
            match_date = match_date.replace(tzinfo=None)

            if match.get("status") in ("NS", "TBD", "POSTP"):
                continue

            stats = read_from_match_statistics(match["id"])
            if stats:
                valid_matches.append(match)
                continue

            stats = get_match_statistics(match["id"])
            if not stats or not any(
                    any(item.get("value") not in [None, 0, ""] for item in team["statistics"]) for team in stats):
                print(f"❌ Nincs használható stat ehhez a H2H meccshez: {match['id']}")
                continue

            fixture = get_fixture_by_id(match["id"])
            if not fixture:
                continue

            match["home_team_id"] = fixture["teams"]["home"]["id"]
            match["home_team_name"] = fixture["teams"]["home"]["name"]
            match["home_team_logo"] = fixture["teams"]["home"]["logo"]
            match["home_team_country"] = get_team_country_by_id(match["home_team_id"]) or None

            match["away_team_id"] = fixture["teams"]["away"]["id"]
            match["away_team_name"] = fixture["teams"]["away"]["name"]
            match["away_team_logo"] = fixture["teams"]["away"]["logo"]
            match["away_team_country"] = get_team_country_by_id(match["away_team_id"]) or None

            match["date"] = parser.isoparse(fixture["fixture"]["date"])
            match["status"] = fixture["fixture"]["status"]
            match["score_home"] = fixture["goals"]["home"]
            match["score_away"] = fixture["goals"]["away"]

            write_to_fixtures([match])
            for team_stats in stats:
                team_id = team_stats["team"]["id"]
                write_to_match_statistics(match["id"], team_id, team_stats["statistics"])

            print(f"✅ Fixture és stat mentve: {match['id']}")
            valid_matches.append(match)

        # ✅ Végső ellenőrzés
        if len(valid_matches) < 5:
            print(f"⛔ Nem elég H2H meccs statisztikával (csak {len(valid_matches)}), mérkőzés kihagyva.")
            continue
        else:
            print(f"📊 Összesen {len(valid_matches)} H2H meccshez van statisztika.")

        # Újra lekérjük az összes H2H meccset a végső ellenőrzéshez
        valid_final_h2h = []
        all_h2h_matches = read_head_to_head_stats(home_team_id, away_team_id)
        for match in all_h2h_matches:
            stats = read_from_match_statistics(match["id"])
            print(f"📂 Fixture ID: {match['id']} → {len(stats)} stat sor található.")
            if stats:
                valid_final_h2h.append(match)

        print(f"📊 Összesen {len(valid_final_h2h)} H2H meccshez van statisztika elmentve.")

        if len(valid_final_h2h) < 5:
            print(f"⛔ Nem elég H2H adat (min. 5 statisztikás meccs kellene), ezért a mérkőzés kihagyva.")
            continue

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
                    continue
            else:
                print(f"❌ Nem sikerült lekérni az oddsokat: {fixture_id}")
                continue
        valid_fixtures.append(fixture_id)
    if valid_fixtures:
        print("\n✅ **Minden szükséges adat elérhető! A szimuláció futtatható.** 🚀")
    return valid_fixtures


