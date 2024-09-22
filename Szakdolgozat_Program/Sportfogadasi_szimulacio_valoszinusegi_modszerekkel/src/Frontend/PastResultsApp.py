import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from src.Backend.api_requests import get_teams, get_fixtures, get_match_statistics, get_team_statistics
from src.Frontend.helpersGUI import save_leagues_if_not_exists


class PastResultsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Múltbéli Eredmények")

        # Liga választó lista
        self.leagues = save_leagues_if_not_exists()
        self.league_names = [f"{league['name']} - {league['country']}" for league in self.leagues]

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

        # Mérkőzések lekérő gomb
        self.fixtures_button = ttk.Button(root, text="Mérkőzések lekérése", command=self.get_past_fixtures)
        self.fixtures_button.pack(pady=10)

        # Treeview táblázat a múltbéli eredmények megjelenítéséhez
        self.results_tree = ttk.Treeview(root, columns=("ID", "Home Team", "Away Team", "Date", "Score", "Status"),
                                         show="headings")
        self.results_tree.heading("ID", text="Mérkőzés ID")
        self.results_tree.heading("Home Team", text="Hazai Csapat")
        self.results_tree.heading("Away Team", text="Vendég Csapat")
        self.results_tree.heading("Date", text="Dátum")
        self.results_tree.heading("Score", text="Eredmény")
        self.results_tree.heading("Status", text="Státusz")
        self.results_tree.pack(pady=20)

        # Kattintás esemény a sorokra
        self.results_tree.bind("<Double-1>", self.show_match_statistics)

    def get_past_fixtures(self):
        selected_league = self.league_combo.get()
        season = self.season_entry.get()
        from_date = self.from_date_entry.get()
        to_date = self.to_date_entry.get()

        if not selected_league or not season or not from_date or not to_date:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát, add meg a szezon évét és a dátumokat.")
            return

        try:
            int(season)  # Ellenőrizzük, hogy a szezon év számból áll
            datetime.strptime(from_date, "%Y-%m-%d")  # Kezdő dátum formátum ellenőrzése
            datetime.strptime(to_date, "%Y-%m-%d")  # Záró dátum formátum ellenőrzése
        except ValueError:
            messagebox.showerror("Hiba", "Kérlek, érvényes dátumformátumot adj meg (YYYY-MM-DD).")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')
        # A múltbéli mérkőzések lekérése a "past" file_type paraméterrel
        fixtures = get_fixtures(league_id, int(season), from_date=from_date, to_date=to_date, file_type="past")

        if fixtures:
            # Töröljük a régi adatokat a táblázatból
            for row in self.results_tree.get_children():
                self.results_tree.delete(row)

            # Új adatok hozzáadása a táblázathoz
            for fixture in fixtures:
                # Formázott eredmény létrehozása
                home_score = fixture['score']['home']
                away_score = fixture['score']['away']
                formatted_score = f"{home_score} - {away_score}"  # Olvasható formátum

                self.results_tree.insert("", "end", values=(
                    fixture['id'], fixture['home_team'], fixture['away_team'], fixture['date'], formatted_score,
                    fixture['status']
                ))
        else:
            messagebox.showinfo("Nincs találat", "Nincsenek találatok a megadott szezonban és dátumok között.")

    def show_match_statistics(self, event=None):
        selected_item = self.results_tree.selection()
        if not selected_item:
            return

        # Kiválasztott mérkőzés adatai
        match_data = self.results_tree.item(selected_item, 'values')
        match_id = match_data[0]  # Mérkőzés ID
        league_name = self.league_combo.get()  # A kiválasztott liga neve
        home_team = match_data[1]  # Hazai csapat neve
        away_team = match_data[2]  # Vendég csapat neve
        match_date = match_data[3]
        match_score = match_data[4]  # Eredmény
        formatted_date = datetime.fromisoformat(match_date[:-6]).strftime("%Y-%m-%d")

        try:
            statistics = get_match_statistics(match_id, league_name, home_team, away_team, formatted_date)
        except Exception as e:
            messagebox.showerror("Hiba", f"Nem sikerült lekérni a statisztikákat: {str(e)}")
            return

        # Új ablak a statisztikák megjelenítésére
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Mérkőzés Statisztikák")

        # A csapatok neve és a végeredmény megjelenítése
        match_info_label = tk.Label(stats_window, text=f"{home_team} vs {away_team} - Eredmény: {match_score}",
                                    font=("Arial", 16))
        match_info_label.pack(pady=10)

        # Létrehozunk egy frame-et a táblázat és a scrollbar számára
        table_frame = tk.Frame(stats_window)
        table_frame.pack(fill='both', expand=True)

        # Két oszlopos Treeview táblázat létrehozása a statisztikák megjelenítéséhez
        stats_tree = ttk.Treeview(table_frame, columns=("Statistic", home_team, away_team), show="headings")
        stats_tree.heading("Statistic", text="Statisztika")
        stats_tree.heading(home_team, text=home_team)
        stats_tree.heading(away_team, text=away_team)
        stats_tree.pack(side="left", fill='both', expand=True)

        # Görgetősáv hozzáadása a Treeview-hoz
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=stats_tree.yview)
        stats_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Adatok strukturálása két csapat statisztikáira
        home_stats = {}
        away_stats = {}

        # Statisztikák feldolgozása
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

            # Kombinált statisztikák hozzáadása a táblázathoz
            all_stats = set(home_stats.keys()).union(set(away_stats.keys()))
            for stat_type in all_stats:
                home_value = home_stats.get(stat_type, 'N/A')
                away_value = away_stats.get(stat_type, 'N/A')
                stats_tree.insert("", "end", values=(stat_type, home_value, away_value))
        else:
            stats_tree.insert("", "end", values=("Nincs adat", "N/A", "N/A"))