import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from api_requests import get_teams, get_fixtures
from helpersAPI import write_to_file, clear_file
from helpersGUI import save_leagues_if_not_exists


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
        self.league_combo.bind("<<ComboboxSelected>>", self.show_upcoming_matches)

        # Aktuális mérkőzések szövegmező
        self.upcoming_matches_label = ttk.Label(root, text="Aktuális, még le nem játszott mérkőzések:")
        self.upcoming_matches_label.pack(pady=10)

        # Treeview táblázat létrehozása
        self.upcoming_matches_tree = ttk.Treeview(root, columns=("ID", "Home Team", "Away Team", "Date", "Status"),
                                                  show="headings")
        self.upcoming_matches_tree.heading("ID", text="Mérkőzés ID")
        self.upcoming_matches_tree.heading("Home Team", text="Hazai Csapat")
        self.upcoming_matches_tree.heading("Away Team", text="Vendég Csapat")
        self.upcoming_matches_tree.heading("Date", text="Dátum")
        self.upcoming_matches_tree.heading("Status", text="Státusz")
        self.upcoming_matches_tree.pack(pady=10)

        # Múltbéli eredményekhez vezető gomb
        self.past_results_button = ttk.Button(root, text="Múltbéli eredmények megtekintése",
                                              command=self.open_past_results_window)
        self.past_results_button.pack(pady=10)

        # Csapatok megtekintése gomb
        self.teams_button = ttk.Button(root, text="Csapatok megtekintése", command=self.open_teams_window)
        self.teams_button.pack(pady=10)

    def show_upcoming_matches(self, event):
        selected_league = self.league_combo.get()
        league_id = self.leagues[self.league_combo.current()].get('id')

        # Az aktuális, még le nem játszott mérkőzések lekérdezése
        current_date = datetime.now().strftime("%Y-%m-%d")
        clear_file('actual_fixtures.json')  # Töröljük az aktuális mérkőzések fájlt
        fixtures = get_fixtures(league_id, datetime.now().year, from_date=current_date, status="NS")  # NS: Not Started

        if fixtures:
            write_to_file(fixtures, 'actual_fixtures.json')  # Aktuális mérkőzések mentése
            # Töröljük a régi adatokat a táblázatból
            for row in self.upcoming_matches_tree.get_children():
                self.upcoming_matches_tree.delete(row)

            # Új adatok hozzáadása a táblázathoz
            for fixture in fixtures:
                self.upcoming_matches_tree.insert("", "end", values=(
                    fixture['id'], fixture['home_team'], fixture['away_team'], fixture['date'], fixture['status']
                ))
        else:
            messagebox.showinfo("Nincs találat", "Jelenleg nincsenek aktuális, még le nem játszott mérkőzések.")

    def open_past_results_window(self):
        # Új ablak megnyitása a múltbéli eredmények megtekintéséhez
        past_results_window = tk.Toplevel(self.root)
        PastResultsApp(past_results_window)

    def open_teams_window(self):
        # Új ablak megnyitása a csapatok megtekintéséhez
        teams_window = tk.Toplevel(self.root)
        TeamsApp(teams_window)


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
        clear_file('past_fixtures.json')  # Töröljük a múltbéli mérkőzések fájlt
        fixtures = get_fixtures(league_id, int(season), from_date=from_date, to_date=to_date)

        if fixtures:
            write_to_file(fixtures, 'past_fixtures.json')  # Múltbéli mérkőzések mentése

            # Töröljük a régi adatokat a táblázatból
            for row in self.results_tree.get_children():
                self.results_tree.delete(row)

            # Új adatok hozzáadása a táblázathoz
            for fixture in fixtures:
                score = f"{fixture['score']['home']} - {fixture['score']['away']}" if fixture['score'] else "N/A"
                self.results_tree.insert("", "end", values=(
                    fixture['id'], fixture['home_team'], fixture['away_team'], fixture['date'], score, fixture['status']
                ))
        else:
            messagebox.showinfo("Nincs találat", "Nincsenek találatok a megadott szezonban és dátumok között.")

class TeamsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Csapatok Megtekintése")

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

        # Csapatok lekérő gomb
        self.teams_button = ttk.Button(root, text="Csapatok lekérése", command=self.get_teams)
        self.teams_button.pack(pady=10)

        # Eredmények szövegmező
        self.result_text = tk.Text(root, height=20, width=80)
        self.result_text.pack(pady=20)

    def get_teams(self):
        selected_league = self.league_combo.get()
        season = self.season_entry.get()

        if not selected_league or not season:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát és add meg a szezon évét.")
            return

        try:
            int(season)  # Ellenőrizzük, hogy a szezon év számból áll
        except ValueError:
            messagebox.showerror("Hiba", "Kérlek, érvényes évszámot adj meg a szezonhoz.")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')
        clear_file('teams.json')  # Töröljük a csapatok fájlt
        teams = get_teams(league_id, season)

        if teams:
            write_to_file(teams, 'teams.json')  # Csapatok mentése
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"Csapatok a {selected_league} ligában - {season} szezon:\n")
            for team in teams:
                self.result_text.insert(tk.END,
                                        f"Csapat: {team['name']} - Ország: {team['country']} - Logo: {team['logo']}\n")
        else:
            messagebox.showinfo("Nincs találat", "Nincsenek csapatok a megadott szezonban.")

