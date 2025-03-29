from datetime import datetime, timedelta

import pytz

from src.Backend.API.odds import fetch_odds_for_fixture
from src.Backend.DB.bookmakers import save_bookmakers, read_from_bookmakers
from src.Backend.DB.odds import odds_already_saved, write_to_odds


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
