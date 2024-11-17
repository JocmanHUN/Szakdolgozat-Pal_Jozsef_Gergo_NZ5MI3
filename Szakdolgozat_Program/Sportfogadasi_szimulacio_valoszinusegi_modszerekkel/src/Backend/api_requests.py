# api_requests.py
import requests
import os
from src.config import API_KEY, BASE_URL, HOST
from src.Backend.helpersAPI import (
    write_to_leagues, read_from_leagues,
    write_to_teams, read_from_teams,
    write_to_fixtures, read_from_fixtures,
    write_to_match_statistics, read_from_match_statistics
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
