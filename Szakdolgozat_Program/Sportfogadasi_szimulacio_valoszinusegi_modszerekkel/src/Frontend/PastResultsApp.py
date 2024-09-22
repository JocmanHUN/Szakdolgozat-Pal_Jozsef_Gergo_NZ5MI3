from src.Backend.api_requests import get_teams, get_fixtures, get_match_statistics, get_team_statistics
import tkinter as tk
from tkinter import ttk, messagebox
from src.Backend.api_requests import get_fixtures
from src.Frontend.helpersGUI import save_leagues_if_not_exists
from datetime import datetime
from tkcalendar import DateEntry
import pytz

class PastResultsApp(tk.Frame):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.fixtures = []  # A lekért mérkőzések tárolása a listához való visszatéréshez

        self.leagues = save_leagues_if_not_exists()
        self.league_names = [f"{league['name']} - {league['country']}" for league in self.leagues]

        # Szezon lista létrehozása
        seasons = [f"{year}/{year+1}" for year in range(2024, 1999, -1)]

        # Liga kiválasztása
        self.league_label = ttk.Label(self, text="Válaszd ki a ligát:")
        self.league_label.pack(pady=10)

        self.league_combo = ttk.Combobox(self, values=self.league_names, state="readonly")
        self.league_combo.set("Válasszon ligát...")  # Placeholder szöveg
        self.league_combo.pack(pady=10)
        self.league_combo.bind("<<ComboboxSelected>>", self.update_date_range)

        # Szezon kiválasztása
        self.season_label = ttk.Label(self, text="Válaszd ki a szezont:")
        self.season_label.pack(pady=10)

        self.season_combo = ttk.Combobox(self, values=seasons, state="readonly")
        self.season_combo.set("Válasszon szezont...")  # Placeholder szöveg
        self.season_combo.pack(pady=10)
        self.season_combo.bind("<<ComboboxSelected>>", self.update_date_range)

        # Kezdő dátum
        self.from_date_label = ttk.Label(self, text="Add meg a kezdő dátumot (YYYY-MM-DD):")
        self.from_date_label.pack(pady=10)
        self.from_date_entry = DateEntry(self, date_pattern='yyyy-mm-dd', state="normal", readonlybackground="white")
        self.from_date_entry.set_date(datetime.now())  # Alapértelmezett mai dátum
        self.from_date_entry.pack(pady=10)

        # Záró dátum
        self.to_date_label = ttk.Label(self, text="Add meg a záró dátumot (YYYY-MM-DD):")
        self.to_date_label.pack(pady=10)
        self.to_date_entry = DateEntry(self, date_pattern='yyyy-mm-dd', state="normal", readonlybackground="white")
        self.to_date_entry.set_date(datetime.now())  # Alapértelmezett mai dátum
        self.to_date_entry.pack(pady=10)

        # Gomb a mérkőzések lekérdezéséhez
        self.fixtures_button = ttk.Button(self, text="Mérkőzések lekérése", command=self.get_past_fixtures)
        self.fixtures_button.pack(pady=10)

        # Treeview a mérkőzések megjelenítéséhez - itt hozzuk létre, hogy biztosan létezzen
        self.results_tree = ttk.Treeview(self, columns=("ID", "Home Team", "Away Team", "Date", "Score", "Status"), show="headings")
        self.results_tree.heading("ID", text="Mérkőzés ID")
        self.results_tree.heading("Home Team", text="Hazai Csapat")
        self.results_tree.heading("Away Team", text="Vendég Csapat")
        self.results_tree.heading("Date", text="Dátum")
        self.results_tree.heading("Score", text="Eredmény")
        self.results_tree.heading("Status", text="Státusz")

        # Kattintási esemény kötése a mérkőzésekhez
        self.results_tree.bind("<Double-1>", self.show_match_statistics)

        # Vissza gomb
        self.back_button = ttk.Button(self, text="Vissza", command=self.app.show_main_menu)
        self.back_button.pack(pady=10)

    def update_date_range(self, event=None):
        """Frissíti a dátumválasztó minimum és maximum dátumát az adott szezon alapján."""
        season = self.season_combo.get()

        # Ellenőrizzük, hogy a felhasználó választott-e szezont, vagy még mindig a placeholder van kiválasztva
        if season == "Válasszon szezont...":
            return  # Ha a felhasználó nem választott ki szezont, kilépünk ebből a függvényből

        # A szezon kezdete július 1., a zárása június 30.
        start_year = int(season.split('/')[0])
        start_date = datetime(start_year, 7, 1)  # Július 1-jén kezdődik a szezon
        end_date = datetime(start_year + 1, 6, 30)  # Június 30-án ér véget a szezon

        try:
            # Először újrakonfiguráljuk a widgeteket, hogy frissüljenek megfelelően
            self.from_date_entry.config(state='normal')
            self.to_date_entry.config(state='normal')

            # Átállítjuk a dátumválasztók határait, hogy biztosan az előre váltás működjön
            self.from_date_entry.config(mindate=start_date, maxdate=end_date)
            self.to_date_entry.config(mindate=start_date, maxdate=end_date)

            # Az alapértelmezett dátum beállítása a szezon kezdő dátumára (július 1) és záró dátumára (június 30)
            self.from_date_entry.set_date(start_date)
            self.to_date_entry.set_date(end_date)

            # Visszaállítjuk a read-only állapotot, ha szükséges
            self.from_date_entry.config(state='readonly')
            self.to_date_entry.config(state='readonly')

        except Exception as e:
            messagebox.showerror("Hiba", f"A dátumválasztó frissítése nem sikerült: {str(e)}")
    def get_past_fixtures(self):
        selected_league = self.league_combo.get()
        season = self.season_combo.get()
        from_date = self.from_date_entry.get()
        to_date = self.to_date_entry.get()

        if not selected_league or not season or not from_date or not to_date:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát, egy szezont, és add meg a dátumokat.")
            return

        try:
            league_id = self.leagues[self.league_combo.current()].get('id')
            self.fixtures = get_fixtures(league_id, int(season.split('/')[0]), from_date=from_date, to_date=to_date, file_type="past")
        except Exception as e:
            messagebox.showerror("Hiba", f"Nem sikerült lekérni a mérkőzéseket: {str(e)}")
            return

        self.show_fixtures_list()  # A lekért mérkőzések megjelenítése

    def show_fixtures_list(self):
        """Visszatér a mérkőzések listájához a statisztikák nézetéből."""
        # Ha a statisztikák frame meg van nyitva, töröljük
        if hasattr(self, 'stats_frame'):
            self.stats_frame.destroy()

        # Újra megjelenítjük a mérkőzések listáját és a gombokat
        self.results_tree.pack(pady=20)
        self.fixtures_button.pack(pady=10)
        self.back_button.pack(pady=10)

        # A mezők engedélyezése újra
        self.league_combo.config(state="normal")
        self.season_combo.config(state="normal")
        self.from_date_entry.config(state="normal")
        self.to_date_entry.config(state="normal")

        # Töröljük az előző adatokat a táblázatból, ha vannak
        for row in self.results_tree.get_children():
            self.results_tree.delete(row)

        # Új adatok hozzáadása a táblázathoz
        if self.fixtures:
            budapest_tz = pytz.timezone('Europe/Budapest')
            for fixture in self.fixtures:
                home_score = fixture['score']['home']
                away_score = fixture['score']['away']
                formatted_score = f"{home_score} - {away_score}"

                # Dátum formázása (UTC-ről Budapesti időzónára konvertálva)
                match_date_utc = datetime.strptime(fixture['date'], "%Y-%m-%dT%H:%M:%S%z")
                match_date_budapest = match_date_utc.astimezone(budapest_tz)
                formatted_date = match_date_budapest.strftime("%Y-%m-%d %H:%M")

                self.results_tree.insert("", "end", values=(
                    fixture['id'], fixture['home_team'], fixture['away_team'], formatted_date, formatted_score,
                    fixture['status']
                ))
        else:
            messagebox.showinfo("Nincs találat", "Nincsenek találatok a megadott szezonban és dátumok között.")

    def get_past_fixtures(self):
        selected_league = self.league_combo.get()
        selected_season = self.season_combo.get()  # Lekérjük a kiválasztott szezont
        from_date = self.from_date_entry.get()
        to_date = self.to_date_entry.get()

        if not selected_league or not selected_season or not from_date or not to_date:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát, szezont, és add meg a dátumokat.")
            return

        # Az API híváshoz csak az első évszámot használjuk (pl. 2024/2025 esetén 2024)
        season_year = int(selected_season.split("/")[0])

        try:
            datetime.strptime(from_date, "%Y-%m-%d")  # Kezdő dátum formátum ellenőrzése
            datetime.strptime(to_date, "%Y-%m-%d")  # Záró dátum formátum ellenőrzése
        except ValueError:
            messagebox.showerror("Hiba", "Kérlek, érvényes dátumformátumot adj meg (YYYY-MM-DD).")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')
        # A múltbéli mérkőzések lekérése
        self.fixtures = get_fixtures(league_id, season_year, from_date=from_date, to_date=to_date, file_type="past")

        self.show_fixtures_list()  # Töltsük be a mérkőzéseket

    def show_match_statistics(self, event=None):
        selected_item = self.results_tree.selection()
        if not selected_item:
            return

        match_data = self.results_tree.item(selected_item, 'values')
        match_id = match_data[0]
        league_name = self.league_combo.get()
        season = self.season_combo.get()
        home_team = match_data[1]
        away_team = match_data[2]
        match_date = match_data[3]
        match_score = match_data[4]

        # Dátum konvertálása budapesti időzónára
        # Mivel a dátum már formázva van, nem tartalmaz időzónát, így az alábbi formátumot kell használni
        utc_dt = datetime.strptime(match_date, "%Y-%m-%d %H:%M")  # A formázott dátum formátuma alapján
        budapest_tz = pytz.timezone('Europe/Budapest')
        budapest_dt = utc_dt.astimezone(budapest_tz)
        formatted_date = budapest_dt.strftime("%Y-%m-%d %H:%M")

        try:
            statistics = get_match_statistics(match_id, league_name, home_team, away_team, formatted_date)
        except Exception as e:
            messagebox.showerror("Hiba", f"Nem sikerült lekérni a statisztikákat: {str(e)}")
            return

        # Elrejtjük az összes fölösleges mezőt és feliratot
        self.league_label.pack_forget()
        self.league_combo.pack_forget()
        self.season_label.pack_forget()
        self.season_combo.pack_forget()
        self.from_date_label.pack_forget()
        self.from_date_entry.pack_forget()
        self.to_date_label.pack_forget()
        self.to_date_entry.pack_forget()
        self.results_tree.pack_forget()
        self.fixtures_button.pack_forget()
        self.back_button.pack_forget()

        # Új frame létrehozása a statisztikák és a mérkőzés információinak megjelenítéséhez
        self.stats_frame = tk.Frame(self)
        self.stats_frame.pack(fill='both', expand=True)

        # Mérkőzés információk megjelenítése (liga, szezon, dátum, végeredmény)
        league_label = tk.Label(self.stats_frame, text=f"{league_name}", font=("Arial", 14))
        league_label.pack(pady=2)

        season_label = tk.Label(self.stats_frame, text=f"Szezon: {season}", font=("Arial", 14))
        season_label.pack(pady=2)

        date_label = tk.Label(self.stats_frame, text=f"Mérkőzés dátuma: {formatted_date} ",
                              font=("Arial", 14))
        date_label.pack(pady=2)

        teams_label = tk.Label(self.stats_frame, text=f"{home_team} vs {away_team} - Eredmény: {match_score}",
                               font=("Arial", 14))
        teams_label.pack(pady=10)

        # Statisztikák megjelenítése
        table_frame = tk.Frame(self.stats_frame)
        table_frame.pack(fill='both', expand=True)

        stats_tree = ttk.Treeview(table_frame, columns=("Statistic", home_team, away_team), show="headings", height=10)
        stats_tree.heading("Statistic", text="Statisztika")
        stats_tree.heading(home_team, text=home_team)
        stats_tree.heading(away_team, text=away_team)
        stats_tree.column("Statistic", anchor="center")
        stats_tree.column(home_team, anchor="center")
        stats_tree.column(away_team, anchor="center")
        stats_tree.pack(side="left", fill='both', expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=stats_tree.yview)
        stats_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        home_stats = {}
        away_stats = {}

        if statistics:
            for stat in statistics:
                team_name = stat.get('team', {}).get('name', 'Ismeretlen csapat')
                for detail in stat.get('statistics', []):
                    stat_type = detail['type']
                    stat_value = detail['value']
                    if team_name == home_team:
                        home_stats[stat_type] = stat_value
                    elif team_name == away_team:
                        away_stats[stat_type] = stat_value

            all_stats = set(home_stats.keys()).union(set(away_stats.keys()))
            for stat_type in all_stats:
                home_value = home_stats.get(stat_type, 'N/A')
                away_value = away_stats.get(stat_type, 'N/A')
                stats_tree.insert("", "end", values=(stat_type, home_value, away_value))
        else:
            stats_tree.insert("", "end", values=("Nincs adat", "N/A", "N/A"))

        # Vissza gomb hozzáadása a mérkőzések listájához való visszatéréshez
        back_button = ttk.Button(self.stats_frame, text="Vissza", command=self.back_to_fixtures_list)
        back_button.pack(pady=10)

    def back_to_fixtures_list(self):
        """Visszatér a mérkőzések listájához a statisztikák nézetéből."""
        if hasattr(self, 'stats_frame'):
            self.stats_frame.destroy()

        # Újra megjelenítjük az összes mezőt
        self.league_label.pack(pady=10)
        self.league_combo.pack(pady=10)
        self.season_label.pack(pady=10)
        self.season_combo.pack(pady=10)
        self.from_date_label.pack(pady=10)
        self.from_date_entry.pack(pady=10)
        self.to_date_label.pack(pady=10)
        self.to_date_entry.pack(pady=10)
        self.results_tree.pack(pady=20)
        self.fixtures_button.pack(pady=10)
        self.back_button.pack(pady=10)
