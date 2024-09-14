import tkinter as tk
from tkinter import ttk, messagebox
from api_requests import get_leagues, get_teams, get_fixtures
from datetime import datetime

class SportsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Betting Simulation")

        # Ligák lekérése
        self.leagues = get_leagues()
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

        teams = get_teams(league_id, season)
        if teams:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"{selected_league} liga csapatai ({season} szezon):\n")
            for team in teams:
                self.result_text.insert(tk.END, f"Csapat: {team['name']} - Ország: {team['country']} - Logo: {team['logo']}\n")
        else:
            messagebox.showerror("Hiba", "Nem sikerült csapatokat lekérni.")

    def get_fixtures(self):
        selected_league = self.league_combo.get()
        season = self.season_entry.get()
        from_date = self.from_date_entry.get()
        to_date = self.to_date_entry.get()

        if not selected_league or not season or not from_date or not to_date:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát, add meg a szezon évét és a dátumokat.")
            return

        # Szezon dátumok ellenőrzése
        try:
            season_start = datetime.strptime(f"{int(season)-1}-08-01", "%Y-%m-%d")  # Pl. 2020 szezon: 2019-08-01 kezdettel
            season_end = datetime.strptime(f"{season}-07-31", "%Y-%m-%d")  # Pl. 2020 szezon: 2020-07-31 véggel
            from_date_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_date_dt = datetime.strptime(to_date, "%Y-%m-%d")

            if not (season_start <= from_date_dt <= season_end and season_start <= to_date_dt <= season_end):
                messagebox.showerror("Hiba", "A megadott dátumok nem illeszkednek a kiválasztott szezonhoz.")
                return
        except ValueError:
            messagebox.showerror("Hiba", "Kérlek, érvényes dátumformátumot adj meg (YYYY-MM-DD).")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')

        fixtures = get_fixtures(league_id, season, from_date=from_date, to_date=to_date, timezone="Europe/London")
        if fixtures:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"{selected_league} liga mérkőzései ({season} szezon) - {from_date} és {to_date} között:\n")
            for fixture in fixtures[:10]:  # Csak az első 10 mérkőzés megjelenítése
                self.result_text.insert(tk.END, f"Mérkőzés ID: {fixture['id']} - {fixture['home_team']} vs {fixture['away_team']} - Dátum: {fixture['date']} - Eredmény: {fixture['score']} - Státusz: {fixture['status']}\n")
        else:
            messagebox.showerror("Hiba", "Nem sikerült mérkőzéseket lekérni.")

