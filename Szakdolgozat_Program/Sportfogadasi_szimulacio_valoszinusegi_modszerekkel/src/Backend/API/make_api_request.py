import time
import requests
from ratelimit import limits, sleep_and_retry
from src.config import BASE_URL, API_KEY, HOST

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

        if response.status_code == 429 or "rateLimit" in response.json().get("errors", {}):
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"⚠️ API rate limit elérve. Várakozás {retry_after} másodpercig...")
            time.sleep(retry_after)
            return make_api_request(endpoint, params)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ API hiba történt: {e}")
        return None