import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from src.Backend.api_requests import get_fixtures
from src.Backend.helpersAPI import write_to_file, clear_file
from src.Frontend.helpersGUI import save_leagues_if_not_exists
from src.Frontend.PastResultsApp import PastResultsApp
from src.Frontend.TeamsApp import TeamsApp
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

