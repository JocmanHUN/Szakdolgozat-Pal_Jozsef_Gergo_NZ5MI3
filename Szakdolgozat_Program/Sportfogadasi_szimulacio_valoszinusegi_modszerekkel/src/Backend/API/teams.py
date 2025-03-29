from src.Backend.API.endpoints import TEAMS, TEAM_STATISTICS
from src.Backend.API.make_api_request import make_api_request
from src.Backend.DB.teams import read_from_teams, write_to_teams


def get_team_country_by_id(team_id):
    """
    Visszaadja a csapat országát az API-ból lekérve.
    """
    response = make_api_request(TEAMS, params={"id": team_id})
    if response and response.get("response"):
        try:
            return response["response"][0]["team"].get("country", None)
        except (KeyError, IndexError):
            pass
    print(f"⚠️ Nem sikerült lekérni a csapat országát (team_id: {team_id})")
    return None

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
    params = {
        'league': league_id,
        'season': season
    }

    data = make_api_request(TEAMS, params)

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

    data = make_api_request(TEAM_STATISTICS, params=params)

    if not data or 'response' not in data:
        print(f"⚠️ Nincsenek statisztikák elérhetőek (team_id={team_id}, league_id={league_id}, season={season})")
        return {}

    return data['response']