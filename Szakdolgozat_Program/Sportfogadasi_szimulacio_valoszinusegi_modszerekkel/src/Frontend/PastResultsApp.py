import tkinter as tk
from tkinter import ttk, messagebox

from src.Backend.API.fixtures import get_fixtures, get_match_statistics
from src.Backend.helpersAPI import read_from_fixtures, write_to_fixtures, read_from_leagues, read_from_match_statistics, \
    get_team_id_by_name
from src.Frontend.helpersGUI import save_leagues_if_not_exists
from datetime import datetime
from tkcalendar import DateEntry
import pytz
from src.Backend.helpersAPI import get_db_connection

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
        self.from_date_entry = DateEntry(self, date_pattern='yyyy-mm-dd', state="disabled", readonlybackground="white")
        self.from_date_entry.set_date(datetime.now())  # Alapértelmezett mai dátum
        self.from_date_entry.pack(pady=10)

        # Záró dátum
        self.to_date_label = ttk.Label(self, text="Add meg a záró dátumot (YYYY-MM-DD):")
        self.to_date_label.pack(pady=10)
        self.to_date_entry = DateEntry(self, date_pattern='yyyy-mm-dd', state="disabled", readonlybackground="white")
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

        if season == "Válasszon szezont...":
            return

        start_year = int(season.split('/')[0])
        start_date = datetime(start_year, 7, 16)
        end_date = datetime(start_year + 1, 7, 15)

        try:
            self.from_date_entry.config(state='normal')
            self.to_date_entry.config(state='normal')
            self.from_date_entry.config(mindate=start_date, maxdate=end_date)
            self.to_date_entry.config(mindate=start_date, maxdate=end_date)
            self.from_date_entry.set_date(start_date)
            self.to_date_entry.set_date(end_date)
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

        league_id = self.leagues[self.league_combo.current()].get('id')
        season_year = int(season.split('/')[0])

        self.fixtures = read_from_fixtures(league_id, season_year, from_date, to_date)
        print(f"Adatbázisból lekért mérkőzések: {self.fixtures}")

        if not self.fixtures:
            try:
                self.fixtures = get_fixtures(league_id, season_year, from_date=from_date, to_date=to_date)
                print(f"API-ból lekért mérkőzések: {self.fixtures}")
                if self.fixtures:
                    write_to_fixtures(self.fixtures)  # Mentés az adatbázisba
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült lekérni a mérkőzéseket: {str(e)}")
                return

        self.show_fixtures_list()

    def load_leagues(self):
        # A ligákat betöltjük az adatbázisból
        return read_from_leagues()

    def get_team_name_from_db(self, team_id):
        """
        Lekéri a csapat nevét az adatbázisból a megadott csapat ID alapján.
        """
        connection = get_db_connection()  # Az adatbázis kapcsolat itt jön létre
        if connection is None:
            return 'Unknown'

        cursor = connection.cursor(dictionary=True)
        query = "SELECT name FROM teams WHERE id = %s"
        cursor.execute(query, (team_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        return result['name'] if result else 'Unknown'

    def show_fixtures_list(self):
        self.results_tree.delete(*self.results_tree.get_children())  # Előző adatok törlése

        for fixture in self.fixtures:
            # Ellenőrizni, hogy a 'date' mező string típusú-e, és ha igen, átalakítjuk datetime objektummá
            if isinstance(fixture['date'], str):
                try:
                    match_date = datetime.fromisoformat(
                        fixture['date'])  # ISO 8601 formátum string datetime-ra konvertálása
                except ValueError:
                    messagebox.showerror("Hiba", f"Érvénytelen dátumformátum: {fixture['date']}")
                    continue

            else:
                match_date = fixture['date']

            # A datetime objektum stringgé alakítása a megadott formátum szerint
            formatted_date = match_date.strftime("%Y-%m-%d %H:%M")

            # Hazai és vendég csapat nevének lekérése az adatbázisból
            home_team = self.get_team_name_from_db(fixture['home_team_id'])
            away_team = self.get_team_name_from_db(fixture['away_team_id'])

            # Mérkőzés adatok beszúrása a TreeView-be
            self.results_tree.insert("", "end", values=(
                fixture['id'], home_team, away_team, formatted_date,
                f"{fixture['score_home']} - {fixture['score_away']}", fixture['status']
            ))

        # TreeView megjelenítése
        self.results_tree.pack(pady=20)

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

        utc_dt = datetime.strptime(match_date, "%Y-%m-%d %H:%M")
        budapest_tz = pytz.timezone('Europe/Budapest')
        budapest_dt = utc_dt.astimezone(budapest_tz)
        formatted_date = budapest_dt.strftime("%Y-%m-%d %H:%M")

        # Először megpróbáljuk az adatokat az adatbázisból lekérni
        statistics = read_from_match_statistics(match_id)
        if statistics:
            print(f"Adatok az adatbázisból: {statistics}")
        else:
            print(f"Nem találtunk adatokat az adatbázisban a {match_id} azonosítójú mérkőzéshez.")
        if not statistics:
            # Ha nincs adat az adatbázisban, próbáljuk lekérni az API-ból
            try:
                statistics = get_match_statistics(match_id, league_name, home_team, away_team, formatted_date)
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült lekérni a statisztikákat: {str(e)}")
                return

        # Megjelenítjük a statisztikákat a GUI-ban, függetlenül attól, hogy az API-ból vagy adatbázisból jöttek
        self.display_statistics(league_name, season, home_team, away_team, match_score, formatted_date, statistics)

    def display_statistics(self, league_name, season, home_team, away_team, match_score, formatted_date, statistics):
        """Ez a függvény felelős a statisztikák megjelenítéséért."""
        # Elrejtjük a korábbi UI elemeket
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

        self.stats_frame = tk.Frame(self)
        self.stats_frame.pack(fill='both', expand=True)

        league_label = tk.Label(self.stats_frame, text=f"{league_name}", font=("Arial", 14))
        league_label.pack(pady=2)

        season_label = tk.Label(self.stats_frame, text=f"Szezon: {season}", font=("Arial", 14))
        season_label.pack(pady=2)

        date_label = tk.Label(self.stats_frame, text=f"Mérkőzés dátuma: {formatted_date} ", font=("Arial", 14))
        date_label.pack(pady=2)

        teams_label = tk.Label(self.stats_frame, text=f"{home_team} vs {away_team} - Eredmény: {match_score}",
                               font=("Arial", 14))
        teams_label.pack(pady=10)

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
            # Ellenőrizzük, hogy az adatok az API-ból vagy az adatbázisból származnak-e
            first_stat = statistics[0]
            if 'team' in first_stat:
                # Az adatok az API-ból származnak
                for stat in statistics:
                    team_name = stat.get('team', {}).get('name', 'Ismeretlen csapat')
                    for detail in stat.get('statistics', []):
                        stat_type = detail['type']
                        stat_value = detail['value']
                        if team_name == home_team:
                            home_stats[stat_type] = stat_value
                        elif team_name == away_team:
                            away_stats[stat_type] = stat_value
            else:
                # Az adatok az adatbázisból származnak
                # Lekérjük a csapatok ID-ját a nevük alapján
                home_team_id = get_team_id_by_name(home_team)
                away_team_id = get_team_id_by_name(away_team)
                if not home_team_id or not away_team_id:
                    messagebox.showerror("Hiba", "Nem sikerült lekérni a csapatok azonosítóját.")
                    return

                for stat in statistics:
                    team_id = stat.get('team_id')
                    # Azonosítók eltávolítása a statisztikákból
                    stat_data = stat.copy()
                    stat_data.pop('id', None)
                    stat_data.pop('fixture_id', None)
                    stat_data.pop('team_id', None)

                    for stat_type, stat_value in stat_data.items():
                        # A statisztika típusának formázása
                        stat_type_formatted = stat_type.replace('_', ' ').title()
                        if team_id == home_team_id:
                            home_stats[stat_type_formatted] = stat_value
                        elif team_id == away_team_id:
                            away_stats[stat_type_formatted] = stat_value

            # Az összes statisztikai típus összegyűjtése
            all_stats = set(home_stats.keys()).union(set(away_stats.keys()))
            for stat_type in all_stats:
                home_value = home_stats.get(stat_type, 'N/A')
                away_value = away_stats.get(stat_type, 'N/A')
                stats_tree.insert("", "end", values=(stat_type, home_value, away_value))
        else:
            stats_tree.insert("", "end", values=("Nincs adat", "N/A", "N/A"))

        back_button = ttk.Button(self.stats_frame, text="Vissza", command=self.back_to_fixtures_list)
        back_button.pack(pady=10)

    def back_to_fixtures_list(self):
        if hasattr(self, 'stats_frame'):
            self.stats_frame.destroy()

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
