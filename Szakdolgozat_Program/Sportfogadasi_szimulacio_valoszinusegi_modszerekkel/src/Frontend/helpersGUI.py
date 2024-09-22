from tkinter import messagebox

from src.Backend.helpersAPI import  read_from_file, write_to_file
from src.Backend.api_requests import get_leagues
def save_leagues_if_not_exists():
    """
    Ligák lekérése és fájlba mentése, ha a fájl nem létezik.
    """
    leagues = read_from_file('leagues.json')
    if not leagues:  # Ha üres, akkor le kell kérni és menteni
        leagues = get_leagues()
        if leagues:
            write_to_file(leagues, 'leagues.json')
        else:
            messagebox.showerror("Hiba", "Nem sikerült lekérni a ligákat az API-ból.")
    return leagues