from src.Backend.API.endpoints import ODDS
from src.Backend.API.make_api_request import make_api_request


def fetch_odds_for_fixture(fixture_id):
    """
    Lekéri az oddsokat egy adott mérkőzéshez.
    """
    params = {'fixture': fixture_id}
    data = make_api_request(ODDS, params)  # Itt használjuk a közös API hívó függvényt

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
