from src.Backend.API.endpoints import HEAD_TO_HEAD, FIXTURES, FIXTURE_STATISTICS
from src.Backend.API.helpersAPI import get_next_days_dates
from src.Backend.API.make_api_request import make_api_request
from src.Backend.API.odds import fetch_odds_for_fixture
from src.Backend.helpersAPI import read_from_fixtures, write_to_fixtures, read_from_match_statistics, \
    write_to_match_statistics, read_head_to_head_stats, check_h2h_match_exists


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

def get_fixture_by_id(fixture_id):
    response = make_api_request(FIXTURES, {"id": fixture_id})
    if response and response.get("response"):
        return response["response"][0]
    else:
        print(f"❌ Nem sikerült lekérni a fixture részleteit (ID: {fixture_id})")
        return None

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

    data = make_api_request(FIXTURES, params)

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
    data = make_api_request(FIXTURE_STATISTICS , params)

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
        data = make_api_request(FIXTURES, params)

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

    data = make_api_request(FIXTURES, params=params)

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
    Lekéri az API-ból az utolsó 10 egymás elleni mérkőzést és elmenti az adatbázisba.
    Minden új mérkőzést ment, függetlenül attól, hogy van-e statisztika. A statokat külön menti.
    """
    existing_h2h_matches = read_head_to_head_stats(home_team_id, away_team_id)

    if len(existing_h2h_matches) >= 8:
        print(f"✅ H2H statisztikák már léteznek ({home_team_id} vs {away_team_id}).")
        return existing_h2h_matches

    params = {
        'h2h': f"{home_team_id}-{away_team_id}",
        'last': 10,
        'timezone': 'Europe/Budapest'
    }
    data = make_api_request(HEAD_TO_HEAD, params=params)

    if not data or 'response' not in data or not data['response']:
        print(f"⚠️ Nincsenek H2H meccsek az API-ban ({home_team_id} vs {away_team_id}).")
        return existing_h2h_matches

    new_h2h_matches = []
    for fixture in data['response']:
        match_id = fixture['fixture']['id']
        if check_h2h_match_exists(match_id):
            continue

        # Fixture mentés előkészítése
        fixture_data = {
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
        }

        write_to_fixtures([fixture_data])
        print(f"📁 Fixture mentve: {match_id}")
        new_h2h_matches.append(fixture_data)

        # Statok mentése külön (ha van)
        stats = get_match_statistics(match_id)
        if stats and any(
            any(item.get("value") not in [None, 0, ""] for item in team["statistics"]) for team in stats
        ):
            for team_stat in stats:
                team_id = team_stat['team']['id']
                write_to_match_statistics(match_id, team_id, team_stat['statistics'])
            print(f"✅ Statisztikák mentve: {match_id}")
        else:
            print(f"⚠️ Nincs statisztika vagy érvénytelen: {match_id}")

    all_matches = existing_h2h_matches + new_h2h_matches
    print(f"📊 Összesen {len(all_matches)} H2H meccs visszaadva ({home_team_id} vs {away_team_id})")
    return all_matches
