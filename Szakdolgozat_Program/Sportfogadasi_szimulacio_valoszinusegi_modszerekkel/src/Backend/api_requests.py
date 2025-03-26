# api_requests.py
import time
from datetime import datetime, timedelta

import requests
from dateutil import parser
import pytz
from ratelimit import limits, sleep_and_retry
from src.Backend.helpersAPI import (
    write_to_leagues, read_from_leagues,
    write_to_teams, read_from_teams,
    write_to_fixtures, read_from_fixtures,
    write_to_match_statistics, read_from_match_statistics, write_to_odds, get_odds_by_fixture_id, save_bookmakers,
    odds_already_saved, read_from_bookmakers, get_last_matches, read_odds_by_fixture, get_or_create_team,
    read_head_to_head_stats, get_existing_h2h_matches, check_h2h_match_exists
)
from src.config import BASE_URL, API_KEY, HOST

# Beállítjuk a rate limitet: 300 API hívás / perc
CALLS = 300
PERIOD = 60  # Másodperc (1 perc)

@sleep_and_retry
@limits(calls=CALLS, period=PERIOD)
def make_api_request(endpoint, params=None):
    """
    Egy API kérést indít a megadott végpontra és figyeli a rate limitet.
    Ha eléri a 300 hívást, akkor csak a szükséges időt várja ki, nem az egész 60 másodpercet.
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        # Ellenőrizzük a válaszból, hogy van-e Rate Limit hiba
        if response.status_code == 429 or "rateLimit" in response.json().get("errors", {}):
            retry_after = int(response.headers.get("Retry-After", 60))  # Ha van Retry-After header, azt használjuk
            print(f"⚠️ API rate limit elérve. Várakozás {retry_after} másodpercig...")
            time.sleep(retry_after)  # Várunk a megadott időt
            return make_api_request(endpoint, params)  # Újra próbáljuk a hívást

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ API hiba történt: {e}")
        return None

def get_leagues():
    """
    Ligák lekérése az API-ról és adatbázisba mentése.
    :return: A ligák listája.
    """
    leagues = read_from_leagues()
    if leagues:  # Ha az adatbázisban már vannak ligák, akkor azokat használjuk
        return leagues

    data = make_api_request("leagues")

    if not data or 'response' not in data:
        print("⚠️ Nincsenek elérhető ligák az API válaszban.")
        return []

    leagues = [
        {
            "id": league['league']['id'],
            "name": league['league']['name'],
            "country": league['country']['name']
        }
        for league in data.get('response', []) if league['league'].get('id')
    ]

    if leagues:
        write_to_leagues(leagues)  # Mentés az adatbázisba

    return leagues


def get_teams(league_id, season):
    """
    Csapatok lekérése az API-ról és az adatbázissal összehasonlítva az újak mentése.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve.
    :return: A csapatok listája.
    """
    # Lekérjük az adatbázisból a már mentett csapatokat ehhez a ligához
    db_teams = read_from_teams(league_id)
    db_team_ids = {team['id'] for team in db_teams}  # csak az ID-k összehasonlításához

    # API lekérés az általános függvényen keresztül
    endpoint = "teams"
    params = {
        'league': league_id,
        'season': season
    }

    data = make_api_request(endpoint, params)

    if not data:
        print("❌ Nem sikerült lekérni az API csapat adatokat.")
        return []

    api_teams = []
    new_teams = []

    for item in data.get('response', []):
        team_data = {
            "id": item['team']['id'],
            "name": item['team']['name'],
            "country": item['team']['country'],
            "logo": item['team']['logo'],
            "league_id": league_id
        }
        api_teams.append(team_data)
        if team_data['id'] not in db_team_ids:
            new_teams.append(team_data)

    if new_teams:
        print(f"Mentendő új csapatok száma: {len(new_teams)}")
        write_to_teams(new_teams, league_id)

    return api_teams


def get_fixtures(league_id, season, from_date=None, to_date=None, team_id=None, status=None,
                 timezone="Europe/Budapest"):
    """
    Mérkőzések lekérése az API-ról és adatbázisba mentése, rate limit figyelembevételével.
    """
    fixtures = read_from_fixtures(league_id, season, from_date, to_date)
    if fixtures:
        return fixtures

    params = {
        'league': league_id,
        'season': season,
        'timezone': timezone
    }

    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    if team_id:
        params['team'] = team_id
    if status:
        params['status'] = status

    data = make_api_request("fixtures", params)

    if not data or 'response' not in data or not data['response']:
        print("Az API nem adott vissza mérkőzéseket a megadott paraméterekkel.")
        return []

    fixtures = [
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
            "score_home": fixture['score']['fulltime']['home'] if fixture['score']['fulltime']['home'] is not None else 0,
            "score_away": fixture['score']['fulltime']['away'] if fixture['score']['fulltime']['away'] is not None else 0,
            "status": fixture['fixture']['status']['short']
        }
        for fixture in data.get('response', [])
    ]

    if fixtures:
        write_to_fixtures(fixtures)
    return fixtures

def get_match_statistics(match_id):
    """
    Lekéri egy adott mérkőzés statisztikáit az API-ból, ha még nem szerepelnek az adatbázisban.
    """
    # Először ellenőrizzük az adatbázisban, hogy a statisztikák már léteznek-e
    db_statistics = read_from_match_statistics(match_id)
    if db_statistics:
        print("Statisztikák az adatbázisból:", db_statistics)
        return db_statistics

    # API lekérés rate limit mellett
    params = {'fixture': match_id}
    data = make_api_request("fixtures/statistics", params)

    if not data:
        print("❌ Nem érkezett válasz az API-tól.")
        return []

    print("API válasz:", data)

    statistics_data = data.get('response', [])
    if statistics_data:
        for team_stat in statistics_data:
            team_id = team_stat['team']['id']
            statistics = team_stat['statistics']
            write_to_match_statistics(match_id, team_id, statistics)

    return statistics_data

def fetch_odds_for_fixture(fixture_id):
    """
    Lekéri az oddsokat egy adott mérkőzéshez.
    """
    params = {'fixture': fixture_id}
    data = make_api_request("odds", params)  # Itt használjuk a közös API hívó függvényt

    if not data or not data.get("response"):
        print(f"Nincs odds a mérkőzéshez: {fixture_id}")
        return []

    # Lekérjük a Match Winner oddsokat
    for bookmaker in data["response"][0].get("bookmakers", []):
        for bet in bookmaker.get("bets", []):
            if bet.get("name") == "Match Winner":
                return data["response"]  # Visszaadjuk a teljes odds adatokat, ha találunk Match Winner típust

    print(f"Match Winner odds nem található: {fixture_id}")
    return []


def save_pre_match_fixtures():
    """
    Lekéri az összes NS státuszú mérkőzést az API-ból, és csak azokat menti el az adatbázisba,
    amelyekhez legalább egy odds található.
    """
    dates = get_next_days_dates(5)  # Következő 3 nap dátumai
    for match_date in dates:
        params = {
            'status': 'NS',  # Csak a Not Started mérkőzések
            'timezone': 'Europe/Budapest',
            'date': match_date  # Az adott napi mérkőzések lekérése
        }

        # API kérés a "fixtures" végpontra
        data = make_api_request("fixtures", params)

        if not data:
            print(f"❌ Nem sikerült lekérni a mérkőzéseket a dátumra: {match_date}")
            continue

        fixtures = data.get('response', [])
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
    if odds_already_saved(fixture_id):
        print(f"Az odds már el van mentve a mérkőzéshez: {fixture_id}")
        return

    odds = fetch_odds_for_fixture(fixture_id)
    if not odds or "bookmakers" not in odds[0]:
        print(f"Nincs odds a mérkőzéshez: {fixture_id}")
        return

    bookmakers = fetch_bookmakers_from_odds(odds)
    save_bookmakers(bookmakers)

    odds_to_save = []
    for bookmaker in odds[0]["bookmakers"]:
        if "bets" not in bookmaker:
            continue

        for bet in bookmaker["bets"]:
            if bet["name"] == "Match Winner" and len(bet["values"]) >= 3:
                odds_entry = {
                    "fixture_id": fixture_id,
                    "bookmaker_id": bookmaker["id"],
                    "home_odds": bet["values"][0]["odd"],
                    "draw_odds": bet["values"][1]["odd"],
                    "away_odds": bet["values"][2]["odd"],
                    "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                odds_to_save.append(odds_entry)

    if odds_to_save:
        write_to_odds(odds_to_save)
        print(f"{len(odds_to_save)} odds mentve.")
    else:
        print(f"Nincs érvényes 'Match Winner' odds a mérkőzéshez: {fixture_id}")


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

def get_fixtures_for_team(team_id, limit=10):
    """
    Lekéri az API-ból egy adott csapat utolsó N mérkőzését.
    :param team_id: A csapat azonosítója.
    :param limit: Hány mérkőzést kérjen le az API-ból (alapértelmezés: 10).
    :return: Lista a csapat utolsó mérkőzéseiről.
    """
    params = {
        'team': team_id,
        'last': limit,
        'timezone': 'Europe/Budapest'
    }

    data = make_api_request("fixtures", params=params)

    if not data or 'response' not in data or not data['response']:
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


def get_head_to_head_stats(home_team_id, away_team_id):
    """
    Lekéri az API-ból az utolsó 5 egymás elleni mérkőzést és elmenti az adatbázisba.
    Ha az adatok már léteznek, akkor nem hívja újra az API-t, hanem az adatbázisból lekéri.
    """
    # 🔹 Megpróbáljuk először az adatbázisból lekérni az adatokat
    existing_h2h_matches = get_existing_h2h_matches(home_team_id, away_team_id)

    # 🔹 Ha már van legalább 5 H2H meccs az adatbázisban, visszaadjuk azokat
    if len(existing_h2h_matches) >= 5:
        print(f"✅ H2H statisztikák már léteznek ({home_team_id} vs {away_team_id}).")
        return existing_h2h_matches

    # 🔹 Ha nincs elég adat, akkor API hívás a make_api_request segítségével
    params = {
        'h2h': f"{home_team_id}-{away_team_id}",
        'last': 5,
        'timezone': 'Europe/Budapest'
    }
    data = make_api_request("fixtures/headtohead", params=params)

    if not data or 'response' not in data or not data['response']:
        print(f"⚠️ Nincsenek H2H statisztikák az API-ban ({home_team_id} vs {away_team_id}).")
        return existing_h2h_matches  # 🔹 Ha nincs API adat, visszaadjuk az adatbázis tartalmát

    new_h2h_stats = []
    for fixture in data['response']:
        match_id = fixture['fixture']['id']

        # 🔹 Ellenőrizzük, hogy a mérkőzés már létezik-e az adatbázisban
        if check_h2h_match_exists(match_id):
            continue

        new_h2h_stats.append({
            "id": match_id,
            "date": fixture['fixture']['date'],
            "home_team_id": fixture['teams']['home']['id'],
            "home_team_name": fixture['teams']['home']['name'],
            "home_team_country": fixture['league'].get('country', 'Unknown'),
            "home_team_logo": fixture['teams']['home']['logo'],
            "away_team_id": fixture['teams']['away']['id'],
            "away_team_name": fixture['teams']['away']['name'],
            "away_team_country": fixture['league'].get('country', 'Unknown'),
            "away_team_logo": fixture['teams']['away']['logo'],
            "score_home": fixture.get('score', {}).get('fulltime', {}).get('home', 0),
            "score_away": fixture.get('score', {}).get('fulltime', {}).get('away', 0),
            "status": fixture['fixture']['status']['short']
        })

    # 🔹 Ha van új mérkőzés, elmentjük
    if new_h2h_stats:
        write_to_fixtures(new_h2h_stats)
        print(f"✅ {len(new_h2h_stats)} új H2H mérkőzés sikeresen elmentve ({home_team_id} vs {away_team_id}).")

    return existing_h2h_matches + new_h2h_stats


def get_team_statistics(league_id, season, team_id, date=None):
    """
    Lekéri egy csapat statisztikáit egy adott liga és szezon alapján.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve (YYYY formátumban).
    :param team_id: A csapat azonosítója.
    :param date: Opcionális dátum a statisztikák limitálásához.
    :return: A csapat statisztikái.
    """
    params = {
        'league': league_id,
        'season': season,
        'team': team_id
    }

    if date:
        params['date'] = date

    data = make_api_request("teams/statistics", params=params)

    if not data or 'response' not in data:
        print(f"⚠️ Nincsenek statisztikák elérhetőek (team_id={team_id}, league_id={league_id}, season={season})")
        return {}

    return data['response']

def get_league_id_by_fixture(fixture_id):
    """
    Fixture ID alapján liga ID lekérdezése API-ból.
    """
    response = make_api_request("fixtures", params={"id": fixture_id})

    if response and response.get('response'):
        fixture_data = response['response'][0]
        league_id = fixture_data['league']['id']
        print(f"✅ Liga ID lekérve fixture_id alapján: {fixture_id} → league_id: {league_id}")
        return league_id
    else:
        print(f"⚠️ Nem sikerült lekérni a liga azonosítót fixture alapján (fixture_id: {fixture_id}).")
        return None
