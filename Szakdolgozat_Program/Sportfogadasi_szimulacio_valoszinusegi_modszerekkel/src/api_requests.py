# src/api_requests.py
import requests
from config import API_KEY, BASE_URL, HOST


def get_leagues():
    url = f"{BASE_URL}leagues"
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        leagues = []
        for league in data['response']:
            league_id = league['league'].get('id')  # Ellenőrizd, hogy az azonosító elérhető-e
            if league_id:
                leagues.append({
                    "name": league['league']['name'],
                    "country": league['country']['name'],
                    "id": league_id  # Liga azonosító
                })
        return leagues
    else:
        print(f"Hiba történt: {response.status_code} - {response.text}")
        return []

def get_teams(league_id, season):
    url = f"{BASE_URL}teams"
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,  # A liga azonosítója
        'season': season      # A szezon évének megadása
    }

    # Kérés elküldése az API felé
    response = requests.get(url, headers=headers, params=params)

    # Ellenőrizd a státuszkódot
    if response.status_code == 200:
        data = response.json()
        if 'response' in data and data['response']:  # Ellenőrizd, hogy a 'response' kulcs elérhető-e és nem üres
            # Kinyerjük a csapatok listáját a válaszból
            teams = [{"id": team['team']['id'], "name": team['team']['name'], "country": team['team']['country'], "logo": team['team']['logo']} for team in data['response']]
            return teams
        else:
            print("Nincsenek csapatok a megadott liga és szezon alapján.")
            print(data)  # Logolja a teljes választ, hogy lásd, mi érkezik vissza
            return []
    else:
        # Hibakezelés és részletes logolás, ha a kérés sikertelen
        print(f"Hiba történt: {response.status_code} - {response.text}")
        return []

import requests
from config import API_KEY, BASE_URL, HOST

def get_fixtures(league_id, season, from_date=None, to_date=None, team_id=None, status=None, timezone="Europe/London"):
    url = f"{BASE_URL}fixtures"
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': HOST
    }
    params = {
        'league': league_id,   # A liga azonosítója
        'season': season,      # A szezon évének megadása
        'timezone': timezone   # Időzóna megadása
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

    # Kérés elküldése az API felé
    response = requests.get(url, headers=headers, params=params)

    # Ellenőrizd a státuszkódot
    if response.status_code == 200:
        data = response.json()
        print("API válasz:", data)  # Logolja a teljes API választ

        if 'response' in data and data['response']:  # Ellenőrizd, hogy a 'response' kulcs elérhető-e és nem üres
            # Kinyerjük a mérkőzések listáját a válaszból
            fixtures = [{
                "id": fixture['fixture']['id'],
                "date": fixture['fixture']['date'],
                "home_team": fixture['teams']['home']['name'],
                "away_team": fixture['teams']['away']['name'],
                "status": fixture['fixture']['status']['short'],
                "score": fixture['score']['fulltime']
            } for fixture in data['response']]
            return fixtures
        else:
            print("Nincsenek mérkőzések a megadott paraméterek alapján.")
            print(data)  # Logolja a teljes választ, hogy lásd, mi érkezik vissza
            return []
    else:
        # Hibakezelés és részletes logolás, ha a kérés sikertelen
        print(f"Hiba történt: {response.status_code} - {response.text}")
        return []
