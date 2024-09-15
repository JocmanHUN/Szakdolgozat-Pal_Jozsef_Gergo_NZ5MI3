import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from api_requests import get_leagues, get_teams, get_fixtures, write_to_file, read_from_file

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

class SportsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Betting Simulation")

        # Ligák beolvasása vagy lekérése és mentése, ha szükséges
        self.leagues = save_leagues_if_not_exists()
        self.league_names = [f"{league['name']} - {league['country']}" for league in self.leagues]

        # Liga választó lista
        self.league_label = ttk.Label(root, text="Válaszd ki a ligát:")
        self.league_label.pack(pady=10)

        self.league_combo = ttk.Combobox(root, values=self.league_names)
        self.league_combo.pack(pady=10)

        # Szezon mező
        self.season_label = ttk.Label(root, text="Add meg a szezon évét:")
        self.season_label.pack(pady=10)

        self.season_entry = ttk.Entry(root)
        self.season_entry.pack(pady=10)

        # Kezdő dátum mező
        self.from_date_label = ttk.Label(root, text="Add meg a kezdő dátumot (YYYY-MM-DD):")
        self.from_date_label.pack(pady=10)

        self.from_date_entry = ttk.Entry(root)
        self.from_date_entry.pack(pady=10)

        # Záró dátum mező
        self.to_date_label = ttk.Label(root, text="Add meg a záró dátumot (YYYY-MM-DD):")
        self.to_date_label.pack(pady=10)

        self.to_date_entry = ttk.Entry(root)
        self.to_date_entry.pack(pady=10)

        # Csapatok lekérő gomb
        self.teams_button = ttk.Button(root, text="Csapatok lekérése", command=self.get_teams)
        self.teams_button.pack(pady=10)

        # Mérkőzések lekérő gomb
        self.fixtures_button = ttk.Button(root, text="Mérkőzések lekérése", command=self.get_fixtures)
        self.fixtures_button.pack(pady=10)

        # Eredmények szövegmező
        self.result_text = tk.Text(root, height=20, width=80)
        self.result_text.pack(pady=20)

    def get_teams(self):
        selected_league = self.league_combo.get()
        season = self.season_entry.get()

        if not selected_league or not season:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát és add meg a szezon évét.")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')

        # Csapatok lekérdezése és mentése fájlba
        teams = get_teams(league_id, season)
        if teams:
            write_to_file(teams, 'teams.json')
        else:
            messagebox.showerror("Hiba", "Nem sikerült csapatokat lekérni.")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"{selected_league} liga csapatai ({season} szezon):\n")
        for team in teams:
            self.result_text.insert(tk.END, f"Csapat: {team['name']} - Ország: {team['country']} - Logo: {team['logo']}\n")

    def get_fixtures(self):
        print("get_fixtures meghívódott")  # Debug üzenet
        selected_league = self.league_combo.get()
        season = self.season_entry.get()
        from_date = self.from_date_entry.get()
        to_date = self.to_date_entry.get()

        if not selected_league or not season or not from_date or not to_date:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát, add meg a szezon évét és a dátumokat.")
            return

        # Ellenőrizzük, hogy a szezon négyjegyű szám, és a dátumok helyesen vannak-e formázva
        try:
            int(season)  # Ellenőrizzük, hogy a szezon év számból áll
            datetime.strptime(from_date, "%Y-%m-%d")  # Kezdő dátum formátum ellenőrzése
            datetime.strptime(to_date, "%Y-%m-%d")  # Záró dátum formátum ellenőrzése
        except ValueError:
            messagebox.showerror("Hiba", "Kérlek, érvényes dátumformátumot adj meg (YYYY-MM-DD).")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')

        # Mérkőzések lekérdezése és fájlba mentése
        fixtures = get_fixtures(league_id, int(season), from_date=from_date, to_date=to_date)
        if not fixtures:
            messagebox.showerror("Hiba", "Nem sikerült mérkőzéseket lekérni.")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END,
                                f"{selected_league} liga mérkőzései ({season} szezon) - {from_date} és {to_date} között:\n")
        for fixture in fixtures:  # Csak az első 10 mérkőzés megjelenítése
            self.result_text.insert(tk.END,
                                    f"Mérkőzés ID: {fixture['id']} - {fixture['home_team']} vs {fixture['away_team']} - Dátum: {fixture['date']} - Eredmény: {fixture['score']} - Státusz: {fixture['status']}\n")