# api_requests.py
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import requests
from src.config import API_KEY, BASE_URL, HOST
from src.Backend.helpersAPI import (
    write_to_leagues, read_from_leagues,
    write_to_teams, read_from_teams,
    write_to_fixtures, read_from_fixtures,
    write_to_match_statistics, read_from_match_statistics, write_to_odds, get_odds_by_fixture_id, save_bookmakers,
    odds_already_saved, read_from_bookmakers, get_last_10_matches, read_odds_by_fixture, get_or_create_team,
    read_head_to_head_stats
)

def get_leagues():
    """
    Ligák lekérése az API-ról és adatbázisba mentése.
    :return: A ligák listája.
    """
    leagues = read_from_leagues()
    if leagues:  # Ha az adatbázisban már vannak ligák, akkor azokat használjuk
        return leagues

    url = f"{BASE_URL}leagues"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Hibakezelés HTTP hibákra
        data = response.json()
        leagues = [
            {
                "id": league['league']['id'],
                "name": league['league']['name'],
                "country": league['country']['name']
            }
            for league in data.get('response', []) if league['league'].get('id')
        ]
        write_to_leagues(leagues)  # Mentés az adatbázisba
        return leagues
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []


def get_teams(league_id, season):
    """
    Csapatok lekérése az API-ról és adatbázisba mentése.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve.
    :return: A csapatok listája.
    """
    teams = read_from_teams(league_id, season)
    if teams:  # Ha az adatbázisban már vannak csapatok, akkor azokat használjuk
        return teams

    url = f"{BASE_URL}teams"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,
        'season': season
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Hibakezelés HTTP hibákra
        data = response.json()
        teams = [
            {
                "id": team['team']['id'],
                "name": team['team']['name'],
                "country": team['team']['country'],
                "logo": team['team']['logo'],
                "league_id": league_id  # Liga azonosító hozzáadása
            }
            for team in data.get('response', [])
        ]
        if teams:
            write_to_teams(teams, league_id)  # Csapatok mentése az adatbázisba
        else:
            print("Nincsenek csapatok a megadott liga és szezon alapján.")
        return teams
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []


def get_fixtures(league_id, season, from_date=None, to_date=None, team_id=None, status=None,
                 timezone="Europe/Budapest"):
    """
    Mérkőzések lekérése az API-ról és adatbázisba mentése.
    """
    fixtures = read_from_fixtures(league_id, season, from_date, to_date)
    if fixtures:
        return fixtures

    url = f"{BASE_URL}fixtures"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,
        'season': season,
        'timezone': timezone
    }

    # Opcionális paraméterek hozzáadása
    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    if team_id:
        params['team'] = team_id
    if status:
        params['status'] = status

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Hibakezelés HTTP hibákra
        data = response.json()

        if 'response' in data and data['response']:
            fixtures = [
                {
                    "id": fixture['fixture']['id'],
                    "date": fixture['fixture']['date'],
                    "home_team_id": fixture['teams']['home']['id'],
                    "home_team_name": fixture['teams']['home']['name'],
                    "home_team_country": fixture['league'].get('country', 'Unknown'),  # Ország kezelése
                    "home_team_logo": fixture['teams']['home']['logo'],
                    "away_team_id": fixture['teams']['away']['id'],
                    "away_team_name": fixture['teams']['away']['name'],
                    "away_team_country": fixture['league'].get('country', 'Unknown'),  # Ország kezelése
                    "away_team_logo": fixture['teams']['away']['logo'],
                    "score_home": fixture['score']['fulltime']['home'] if fixture['score']['fulltime'][
                                                                              'home'] is not None else 0,
                    "score_away": fixture['score']['fulltime']['away'] if fixture['score']['fulltime'][
                                                                              'away'] is not None else 0,
                    "status": fixture['fixture']['status']['short']
                }
                for fixture in data.get('response', [])
            ]
            if fixtures:
                write_to_fixtures(fixtures)  # Mérkőzések mentése az adatbázisba
            return fixtures
        else:
            print("Az API nem adott vissza mérkőzéseket a megadott paraméterekkel.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []


def get_match_statistics(match_id, league_name=None, home_team=None, away_team=None, formatted_date=None):
    # Először ellenőrizzük az adatbázisban, hogy a statisztikák már léteznek-e
    db_statistics = read_from_match_statistics(match_id)  # Ez a függvény lekéri az adatokat az adatbázisból
    if db_statistics:
        print("Statisztikák az adatbázisból:", db_statistics)
        return db_statistics  # Ha vannak adatok, azokat visszaadjuk és nem kérünk le API-t

    # Ha nincsenek statisztikai adatok az adatbázisban, API lekérést hajtunk végre
    url = f"{BASE_URL}fixtures/statistics"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {'fixture': match_id}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        # API válasz kiírása
        data = response.json()
        print("API válasz:", data)

        statistics_data = data.get('response', [])

        # Ha kaptunk adatot, elmentjük az adatbázisba
        if statistics_data:
            for team_stat in statistics_data:
                team_id = team_stat['team']['id']
                statistics = team_stat['statistics']
                write_to_match_statistics(match_id, team_id, statistics)  # Elmentjük az adatokat

        return statistics_data

    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []


def fetch_pre_match_fixtures(league_id, season):
    """
    Lekéri az aktuális pre-match (NS státuszú) mérkőzéseket az API-ból.
    :param league_id: Liga azonosítója.
    :param season: Szezon éve.
    :return: Mérkőzések listája az API válaszából.
    """
    url = f"{BASE_URL}fixtures"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,
        'season': season,
        'status': 'NS',  # Csak a Not Started mérkőzések
        'timezone': 'Europe/Budapest'
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        print(f"API válasz: {data}")  # Debug: az API válasz kiírása
        return data.get('response', [])
    except requests.exceptions.RequestException as e:
        print(f"API hiba a pre-match mérkőzések lekérdezésekor: {e}")
        return []

def fetch_odds_for_fixture(fixture_id):
    """
    Lekéri az oddsokat egy adott mérkőzéshez.
    :param fixture_id: A mérkőzés azonosítója.
    :return: Odds adatok az API válaszából.
    """
    url = f"{BASE_URL}odds"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'fixture': fixture_id
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        # Ellenőrizzük, hogy a "response" kulcs nem üres
        if not data.get("response"):
            print(f"Nincs odds a mérkőzéshez: {fixture_id}")
            return []

        # Lekérjük a Match Winner oddsokat
        for bookmaker in data["response"][0].get("bookmakers", []):
            for bet in bookmaker.get("bets", []):
                if bet.get("name") == "Match Winner":
                    return data["response"]  # Visszaadjuk a teljes odds adatokat, ha találunk Match Winner típust

        print(f"Match Winner odds nem található: {fixture_id}")
        return []

    except requests.exceptions.RequestException as e:
        print(f"API hiba az oddsok lekérdezésekor: {e}")
        return []


def save_pre_match_fixtures():
    """
    Lekéri az összes NS státuszú mérkőzést az API-ból, és csak azokat menti el az adatbázisba,
    amelyekhez legalább egy odds található.
    """
    url = f"{BASE_URL}fixtures"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    dates = get_next_days_dates(3)  # Következő 3 nap dátumai
    for match_date in dates:
        params = {
            'status': 'NS',  # Csak a Not Started státuszú mérkőzések
            'timezone': 'Europe/Budapest',
            'date': match_date  # Az adott napi mérkőzések lekérése
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            fixtures = response.json().get('response', [])

            for fixture in fixtures:
                fixture_id = fixture["fixture"]["id"]

                # Lekérdezzük, hogy van-e odds a mérkőzéshez
                odds = fetch_odds_for_fixture(fixture_id)
                if not odds:
                    print(f"Nincs odds a mérkőzéshez, kihagyva: {fixture_id}")
                    continue  # Ha nincs odds, a mérkőzés kimarad

                # Ha van odds, a mérkőzést elmentjük
                fixture_data = {
                    "id": fixture["fixture"]["id"],
                    "date": fixture["fixture"]["date"],
                    "home_team_id": fixture["teams"]["home"]["id"],
                    "home_team_name": fixture["teams"]["home"]["name"],
                    "home_team_country": fixture["league"].get("country", "Unknown"),
                    "home_team_logo": fixture["teams"]["home"]["logo"],
                    "away_team_id": fixture["teams"]["away"]["id"],
                    "away_team_name": fixture["teams"]["away"]["name"],
                    "away_team_country": fixture["league"].get("country", "Unknown"),
                    "away_team_logo": fixture["teams"]["away"]["logo"],
                    "score_home": None,
                    "score_away": None,
                    "status": "NS",
                }
                write_to_fixtures([fixture_data])
                print(
                    f"Mérkőzés mentve: {fixture_data['id']} - {fixture_data['home_team_name']} vs {fixture_data['away_team_name']} ({match_date})")

        except requests.exceptions.RequestException as e:
            print(f"API hiba történt ({match_date}): {e}")

def get_next_days_dates(days=3):
    """
    Legenerálja a következő `days` nap dátumait Budapest időzónában.
    :return: Lista a következő napok dátumaival (pl. ['2025-03-06', '2025-03-07', '2025-03-08'])
    """
    budapest_tz = pytz.timezone("Europe/Budapest")
    today = datetime.now(budapest_tz)
    return [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, days + 1)]  # Holnaptól kezdve

def fetch_bookmakers_from_odds(odds_response):
    """
    Lekéri a fogadóirodák adatait az odds válaszból.
    """
    bookmakers = {}
    for response in odds_response:
        for bookmaker in response.get("bookmakers", []):
            bookmakers[bookmaker["id"]] = bookmaker["name"]
    return bookmakers

def save_odds_for_fixture(fixture_id):
    # Ellenőrizzük, hogy az odds már el van-e mentve
    if odds_already_saved(fixture_id):
        print(f"Az odds már el van mentve a mérkőzéshez: {fixture_id}, nem mentünk újra.")
        return

    odds = fetch_odds_for_fixture(fixture_id)
    print(odds)  # Debug célból, ellenőrizd a visszakapott oddsokat
    if not odds:
        print(f"Nincs odds a mérkőzéshez: {fixture_id}")
        return

    bookmakers = fetch_bookmakers_from_odds(odds)
    save_bookmakers(bookmakers)  # Fogadóirodák mentése az adatbázisba

    odds_to_save = []
    for bookmaker in odds[0]["bookmakers"]:
        for bet in bookmaker["bets"]:
            if bet["name"] == "Match Winner":
                odds_to_save.append({
                    "fixture_id": fixture_id,
                    "bookmaker_id": bookmaker["id"],
                    "home_odds": bet["values"][0]["odd"],
                    "draw_odds": bet["values"][1]["odd"],
                    "away_odds": bet["values"][2]["odd"],
                    "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
    write_to_odds(odds_to_save)
    print(f"Odds mentve a mérkőzéshez: {fixture_id}")


def sync_bookmakers(api_response):
    """
    Ellenőrzi az API válaszában található fogadóirodák listáját, és frissíti az adatbázist, ha szükséges.
    :param api_response: Az API válasza oddsokkal és fogadóirodákkal.
    """
    # 1. Lekérjük a jelenlegi adatbázisban lévő fogadóirodákat
    current_bookmakers = {bookmaker['id']: bookmaker['name'] for bookmaker in read_from_bookmakers()}

    # 2. Az API válaszából kigyűjtjük a fogadóirodákat
    api_bookmakers = {}
    for response in api_response:
        for bookmaker in response.get("bookmakers", []):
            api_bookmakers[bookmaker["id"]] = bookmaker["name"]

    # 3. Új és frissítendő fogadóirodák azonosítása
    new_bookmakers = {}
    for bookmaker_id, bookmaker_name in api_bookmakers.items():
        if bookmaker_id not in current_bookmakers or current_bookmakers[bookmaker_id] != bookmaker_name:
            new_bookmakers[bookmaker_id] = bookmaker_name

    # 4. Frissítés, ha vannak változások
    if new_bookmakers:
        print(f"{len(new_bookmakers)} új vagy frissítendő fogadóiroda található.")
        save_bookmakers(new_bookmakers)
    else:
        print("Nincsenek új vagy frissítendő fogadóirodák.")

def ensure_simulation_data_available(fixture_list):
    """
    Biztosítja, hogy a modellekhez szükséges adatok rendelkezésre álljanak az adatbázisban.
    Ha hiányoznak, az API-ból lekérdezi és elmenti azokat.

    :param fixture_list: Mérkőzések listája ([(home_team_id, away_team_id, fixture_id), ...]).
    :param league_id: A liga azonosítója.
    :param season: Az aktuális szezon.
    """
    for home_team_id, away_team_id, fixture_id in fixture_list:
        print(f"\n🔎 **Adatok biztosítása a mérkőzéshez: {home_team_id} vs {away_team_id}** (Fixture ID: {fixture_id})")

        # **Csapatok utolsó 10 mérkőzésének és statisztikáinak biztosítása**
        for team_id in [home_team_id, away_team_id]:
            matches = get_last_10_matches(team_id)
            if len(matches) < 10:
                print(f"⚠️ Nincs elég múltbeli meccs (Csapat ID: {team_id}), API lekérés...")
                api_matches = get_fixtures_for_team(team_id, 10)
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
            # **Kiszűrjük a frissebb mérkőzéseket**
            new_h2h_matches = [
                match for match in h2h_stats
                if latest_h2h_date is None or parser.isoparse(match["date"]).replace(tzinfo=None) > latest_h2h_date.replace(tzinfo=None)
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


def get_fixtures_for_team(team_id, limit=10):
    """
    Lekéri az API-ból egy adott csapat utolsó N mérkőzését, és elmenti az adatbázisba.

    :param team_id: A csapat azonosítója.
    :param limit: Hány mérkőzést kérjen le az API-ból (alapértelmezés: 10).
    :return: Lista a csapat utolsó mérkőzéseiről.
    """

    url = f"{BASE_URL}fixtures"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'team': team_id,
        'last': limit,
        'timezone': 'Europe/Budapest' # Legfrissebb mérkőzések először
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if 'response' not in data or not data['response']:
            print(f"⚠️ Nincsenek múltbeli mérkőzések az API-ban (Csapat ID: {team_id}).")
            return []

        fixtures = []
        for fixture in data['response']:
            match_data = {
                "id": fixture['fixture']['id'],
                "date": fixture['fixture']['date'],
                "home_team_id": fixture['teams']['home']['id'],
                "home_team_name": fixture['teams']['home']['name'],
                "home_team_country": fixture['league'].get('country', 'Unknown'),
                "home_team_logo": fixture['teams']['home']['logo'],
                "away_team_id": fixture['teams']['away']['id'],
                "away_team_name": fixture['teams']['away']['name'],
                "away_team_country": fixture['league'].get('country', 'Unknown'),
                "away_team_logo": fixture['teams']['away']['logo'],
                "score_home": fixture['score']['fulltime']['home'],
                "score_away": fixture['score']['fulltime']['away'],
                "status": fixture['fixture']['status']['short'],
            }
            fixtures.append(match_data)

        return fixtures

    except requests.exceptions.RequestException as e:
        print(f"❌ API hiba történt mérkőzések lekérdezésekor: {e}")
        return []


def get_head_to_head_stats(home_team_id, away_team_id):
    """
    Lekéri az API-ból az utolsó 5 egymás elleni mérkőzést és elmenti az adatbázisba.

    :param home_team_id: Hazai csapat ID.
    :param away_team_id: Vendég csapat ID.
    :return: Lista az utolsó 5 H2H mérkőzésről.
    """
    url = f"{BASE_URL}fixtures/headtohead"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'h2h': f"{home_team_id}-{away_team_id}",
        'last': 5,  # Az utolsó 5 mérkőzés
        'timezone': 'Europe/Budapest'
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if 'response' not in data or not data['response']:
            print(f"⚠️ Nincsenek H2H statisztikák az API-ban ({home_team_id} vs {away_team_id}).")
            return []

        h2h_stats = [
            {
                "id": fixture['fixture']['id'],
                "date": fixture['fixture']['date'],
                "home_team_id": fixture['teams']['home']['id'],
                "home_team_name": fixture['teams']['home']['name'],
                "home_team_country": fixture['league'].get('country', 'Unknown'),
                "home_team_logo": fixture['teams']['home']['logo'],
                "away_team_id": fixture['teams']['away']['id'],
                "away_team_name": fixture['teams']['away']['name'],
                "away_team_country": fixture['league'].get('country', 'Unknown'),
                "away_team_logo": fixture['teams']['away']['logo'],
                "score_home": fixture['score']['fulltime'].get('home', 0),
                "score_away": fixture['score']['fulltime'].get('away', 0),
                "status": fixture['fixture']['status']['short']
            }
            for fixture in data['response']
        ]

        # Az adatok mentése az adatbázisba a write_to_fixtures függvénnyel
        write_to_fixtures(h2h_stats)
        print(f"✅ {len(h2h_stats)} H2H mérkőzés sikeresen elmentve ({home_team_id} vs {away_team_id}).")

        return h2h_stats

    except requests.exceptions.RequestException as e:
        print(f"❌ API hiba történt H2H statisztikák lekérésekor: {e}")
        return []


def get_team_statistics(league_id, season, team_id, date=None):
    """
    Lekéri egy csapat statisztikáit egy adott liga és szezon alapján.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve (YYYY formátumban).
    :param team_id: A csapat azonosítója.
    :param date: Opcionális dátum a statisztikák limitálásához.
    :return: A csapat statisztikái.
    """
    url = f"{BASE_URL}teams/statistics"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,
        'season': season,
        'team': team_id
    }

    if date:
        params['date'] = date  # Dátum hozzáadása, ha van

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json().get('response', {})

        # Itt kezelheted a csapat statisztikák mentését az adatbázisba
        # Például, ha az API válasz tartalmaz statisztikákat, akkor azt elmentheted:
        # write_to_team_statistics(data)
        # Az implementáció a konkrét API válasz struktúrájától függ
        return data
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt a csapat statisztikáinak lekérésekor: {e}")
        return {}