# api_requests.py
import requests
import os
import json
from config import API_KEY, BASE_URL, HOST
from helpersAPI import write_to_file, read_from_file, clear_file
def get_leagues():
    """
    Ligák lekérése az API-ról és fájlba mentése.
    :return: A ligák listája.
    """
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
                "name": league['league']['name'],
                "country": league['country']['name'],
                "id": league['league']['id']
            }
            for league in data.get('response', []) if league['league'].get('id')
        ]
        write_to_file(leagues, 'leagues.json')
        return leagues
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []

def get_teams(league_id, season):
    """
    Csapatok lekérése az API-ról és fájlba mentése.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve.
    :return: A csapatok listája.
    """
    url = f"{BASE_URL}teams"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,
        'season': season
    }

    # A teams.json fájl törlése, ha létezik
    clear_file('teams.json')

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Hibakezelés HTTP hibákra
        data = response.json()
        teams = [
            {
                "id": team['team']['id'],
                "name": team['team']['name'],
                "country": team['team']['country'],
                "logo": team['team']['logo']
            }
            for team in data.get('response', [])
        ]
        if teams:
            write_to_file(teams, 'teams.json')
        else:
            print("Nincsenek csapatok a megadott liga és szezon alapján.")
        return teams
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []

def get_fixtures(league_id, season, from_date=None, to_date=None, team_id=None, status=None, timezone="Europe/Budapest"):
    """
    Mérkőzések lekérése az API-ról és fájlba mentése.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve (4 számjegyű).
    :param from_date: Kezdő dátum (opcionális).
    :param to_date: Záró dátum (opcionális).
    :param team_id: Csapat azonosító (opcionális).
    :param status: Mérkőzés státusz (opcionális).
    :param timezone: Időzóna (alapértelmezett "Europe/Budapest").
    :return: A mérkőzések listája.
    """
    print('asd')
    # Töröljük a fixtures.json fájlt, ha létezik
    clear_file('fixtures.json')

    url = f"{BASE_URL}fixtures"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,
        'season': season,  # A szezon négyjegyű évszámként
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

        # Ellenőrizzük, hogy van-e válasz és az tartalmaz mérkőzéseket
        if 'response' in data and data['response']:
            fixtures = [
                {
                    "id": fixture['fixture']['id'],
                    "date": fixture['fixture']['date'],
                    "home_team": fixture['teams']['home']['name'],
                    "away_team": fixture['teams']['away']['name'],
                    "status": fixture['fixture']['status']['short'],
                    "score": fixture['score']['fulltime']
                }
                for fixture in data.get('response', [])
            ]
            if fixtures:
                write_to_file(fixtures, 'fixtures.json')
                print(f"Sikeresen mentve a(z) {len(fixtures)} mérkőzés a fixtures.json fájlba.")
            else:
                print("Nincsenek mérkőzések a megadott paraméterek alapján.")
            return fixtures
        else:
            print("Az API nem adott vissza mérkőzéseket a megadott paraméterekkel.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []