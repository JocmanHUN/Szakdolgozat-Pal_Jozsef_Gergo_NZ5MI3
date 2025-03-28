from src.Backend.API.endpoints import LEAGUES
from src.Backend.API.make_api_request import make_api_request
from src.Backend.DB.leagues import read_from_leagues


def get_leagues():
    """
    Ligák lekérése az API-ról és adatbázisba mentése.
    :return: A ligák listája.
    """
    leagues = read_from_leagues()
    if leagues:  # Ha az adatbázisban már vannak ligák, akkor azokat használjuk
        return leagues

    data = make_api_request(LEAGUES)

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
