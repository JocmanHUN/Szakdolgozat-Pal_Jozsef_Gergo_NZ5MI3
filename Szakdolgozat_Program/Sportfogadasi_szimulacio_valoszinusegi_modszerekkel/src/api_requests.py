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

def get_fixtures(league_id, season, from_date=None, to_date=None, team_id=None, status=None, timezone="Europe/Budapest", file_type="actual"):
    """
    Mérkőzések lekérése az API-ról és fájlba mentése.
    :param league_id: A liga azonosítója.
    :param season: A szezon éve (4 számjegyű).
    :param from_date: Kezdő dátum (opcionális).
    :param to_date: Záró dátum (opcionális).
    :param team_id: Csapat azonosító (opcionális).
    :param status: Mérkőzés státusz (opcionális).
    :param timezone: Időzóna (alapértelmezett "Europe/Budapest").
    :param file_type: Fájl típusa ("actual" vagy "past") a megfelelő fájl megnevezéshez.
    :return: A mérkőzések listája.
    """
    filename = f"{file_type}_fixtures.json"

    # Mindig töröljük a fájlt, mielőtt friss adatokat kérünk le
    clear_file(filename)

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
                write_to_file(fixtures, filename)  # Írd felül az új adatokkal
                print(f"Sikeresen mentve a(z) {len(fixtures)} mérkőzés a {filename} fájlba.")
            else:
                print("Nincsenek mérkőzések a megadott paraméterek alapján.")
            return fixtures
        else:
            print("Az API nem adott vissza mérkőzéseket a megadott paraméterekkel.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt: {e}")
        return []

def create_directory(path):
    """
    Létrehozza a mappát, ha nem létezik.
    :param path: A mappa elérési útja.
    """
    try:
        os.makedirs(path, exist_ok=True)
        print(f"Mappa létrehozva: {path}")
    except OSError as e:
        print(f"Nem sikerült létrehozni a mappát: {path}, Hiba: {e}")


def normalize_filename(filename):
    # Helyettesíti az érvénytelen karaktereket és kisbetűsít mindent
    return filename.replace(":", "-").replace("/", "-").replace("\\", "-").replace(" ", "_").lower()

def get_match_statistics(match_id, league_name, home_team, away_team, match_date):
    """
    Lekéri a mérkőzés statisztikáit és fájlba menti a megfelelő mappastruktúrában.
    :param match_id: A mérkőzés azonosítója
    :param league_name: A liga neve
    :param home_team: Hazai csapat neve
    :param away_team: Vendég csapat neve
    :param match_date: A mérkőzés dátuma (pl. "2022-08-07")
    :return: A mérkőzés statisztikái
    """
    # Normálizált liga neve és fájl elérési útvonalak létrehozása
    league_path = os.path.join("statistics", normalize_filename(league_name))
    os.makedirs(league_path, exist_ok=True)  # Mappa létrehozása, ha nem létezik

    # Fájlnév generálása az év, hónap, nap formátumban a match_date alapján
    match_date_formatted = match_date.split("T")[0]  # Csak az év, hónap, nap
    filename = f"{home_team}_vs_{away_team}_{match_date_formatted}_statistics.json"
    filepath = os.path.join(league_path, normalize_filename(filename))

    # Ha a fájl már létezik, olvassuk be a statisztikákat
    if os.path.exists(filepath):
        print(f"Statisztikák betöltése fájlból: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    # API lekérdezés
    url = f"{BASE_URL}fixtures/statistics"
    headers = {
        'x-apisports-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {'fixture': match_id}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Hibakezelés HTTP hibákra
        data = response.json().get('response', [])

        # Statisztikák mentése fájlba
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Statisztikák mentése fájlba: {filepath}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Nem sikerült lekérni a statisztikákat: {e}")
        raise e


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
        return response.json().get('response', {})
    except requests.exceptions.RequestException as e:
        print(f"API hiba történt a csapat statisztikáinak lekérésekor: {e}")
        return {}

