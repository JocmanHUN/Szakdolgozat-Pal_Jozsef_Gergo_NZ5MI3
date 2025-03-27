from tkinter import messagebox

from src.Backend.API.leagues import get_leagues
from src.Backend.helpersAPI import read_from_leagues, write_to_leagues

def save_leagues_if_not_exists():
    """
    Ligák lekérése és adatbázisba mentése, ha az adatbázis üres.
    """
    leagues = read_from_leagues()  # Ligák beolvasása az adatbázisból
    if not leagues:  # Ha az adatbázis üres, akkor API-ból kérjük le az adatokat
        leagues = get_leagues()
        if leagues:
            write_to_leagues(leagues)  # Mentés az adatbázisba
        else:
            messagebox.showerror("Hiba", "Nem sikerült lekérni a ligákat az API-ból.")
    return leagues
