import tkinter as tk
from tkinter import ttk, messagebox
from src.Frontend.PastResultsApp import PastResultsApp
from src.Frontend.TeamsApp import TeamsApp
from src.Backend.helpersAPI import get_pre_match_fixtures, get_odds_by_fixture_id, update_fixtures_status
from src.Backend.api_requests import save_pre_match_fixtures, save_odds_for_fixture, fetch_odds_for_fixture, sync_bookmakers

# Globális lista a kiválasztott mérkőzésekhez
selected_fixtures = []
selected_window = None  # Egyetlen példányban tartjuk a kiválasztott mérkőzések ablakát

class SportsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Betting Simulation")

        # Teljes képernyőre állítás
        self.root.state("zoomed")

        # Minimális méret beállítása, hogy minden látszódjon
        self.root.minsize(800, 600)  # Minimális méret 800x600

        # Fogadóirodák szinkronizálása az első indításkor
        self.sync_initial_bookmakers()

        update_fixtures_status()

        self.current_frame = None
        self.show_main_menu()

    def sync_initial_bookmakers(self):
        """
        Ellenőrzi és szinkronizálja a fogadóirodák listáját az első indításkor.
        """
        print("Fogadóirodák szinkronizálása az első indításkor...")
        fixtures = get_pre_match_fixtures()  # Mérkőzések lekérése
        if fixtures:
            fixture_id = fixtures[0]['fixture_id']  # Egy első mérkőzés ID kiválasztása
            odds = fetch_odds_for_fixture(fixture_id)  # Oddsok lekérése
            sync_bookmakers(odds)  # Fogadóirodák szinkronizálása
        else:
            print("Nincsenek elérhető mérkőzések az első indításhoz.")

    def show_frame(self, frame_class):
        """Eltávolítja a jelenlegi frame-et, és betölti az újat."""
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self)
        self.current_frame.pack(fill="both", expand=True)

    def show_main_menu(self):
        """Főmenü megjelenítése."""
        self.show_frame(MainMenu)

    def show_past_results(self):
        """Múltbéli eredmények nézet megjelenítése."""
        self.show_frame(PastResultsApp)

    def show_teams(self):
        """Csapatok nézet megjelenítése."""
        self.show_frame(TeamsApp)

class MainMenu(tk.Frame):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app

        # Adatok mentése (csak mérkőzések, odds nélkül)
        print("NS státuszú mérkőzések mentése...")
        save_pre_match_fixtures()

        # Főcím hozzáadása
        title_label = ttk.Label(self, text="Sportfogadás valószínűségi és statisztikai alapokon",
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        # Treeview elhelyezéséhez egy konténer keret létrehozása
        treeview_frame = tk.Frame(self)
        treeview_frame.pack(fill="both", expand=True, pady=10)

        # Scrollbar létrehozása
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Treeview widget létrehozása és csatolása a scrollbar-hoz
        self.treeview = ttk.Treeview(treeview_frame, columns=(
            "fixture_id", "home_team", "away_team", "match_date"
        ), show="headings", yscrollcommand=scrollbar.set)

        self.sort_orders = {"fixture_id": False, "home_team": False, "away_team": False, "match_date": False}

        self.treeview.heading("fixture_id", text="Mérkőzés ID", command=lambda: self.sort_treeview("fixture_id"))
        self.treeview.heading("home_team", text="Hazai csapat", command=lambda: self.sort_treeview("home_team"))
        self.treeview.heading("away_team", text="Vendég csapat", command=lambda: self.sort_treeview("away_team"))
        self.treeview.heading("match_date", text="Dátum", command=lambda: self.sort_treeview("match_date"))

        # Oszlopok méretezése
        self.treeview.column("fixture_id", width=100)
        self.treeview.column("home_team", width=150)
        self.treeview.column("away_team", width=150)
        self.treeview.column("match_date", width=150)

        # Treeview megjelenítése a containerben
        self.treeview.pack(side="left", fill="both", expand=True)

        # Scrollbar összekapcsolása a Treeview-el
        scrollbar.config(command=self.treeview.yview)

        # Adatok betöltése
        self.load_fixtures()

        # Gombok hozzáadása
        self.add_buttons()

        # Kattintási esemény hozzáadása
        self.treeview.bind("<Double-1>", self.on_fixture_click)

    def load_fixtures(self):
        """Betölti a pre-match mérkőzéseket a Treeview-be."""
        fixtures = get_pre_match_fixtures()

        # Treeview ürítése
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Adatok betöltése
        if fixtures:
            for row in fixtures:
                self.treeview.insert("", "end", values=(
                    row["fixture_id"],
                    row["home_team"],
                    row["away_team"],
                    row["match_date"]
                ))
            print(f"{len(fixtures)} mérkőzés betöltve.")
        else:
            print("Nincs elérhető pre-match mérkőzés.")

    def add_buttons(self):
        """Gombok hozzáadása a főképernyőhöz."""
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        refresh_button = ttk.Button(button_frame, text="Frissítés", command=self.load_fixtures)
        refresh_button.pack(side="left", padx=5)

        past_results_button = ttk.Button(button_frame, text="Múltbéli eredmények", command=self.app.show_past_results)
        past_results_button.pack(side="left", padx=5)

        teams_button = ttk.Button(button_frame, text="Csapatok megtekintése", command=self.app.show_teams)
        teams_button.pack(side="left", padx=5)

        add_button = ttk.Button(button_frame, text="Hozzáadás", command=self.add_to_selected)
        add_button.pack(side="left", padx=5)

        view_selected_button = ttk.Button(button_frame, text="Kiválasztott mérkőzések és szimulációk", command=self.show_selected_fixtures)
        view_selected_button.pack(side="left", padx=5)

    def on_fixture_click(self, event):
        """Kezeli a mérkőzésre való kattintást."""
        selected_item = self.treeview.selection()[0]
        fixture_data = self.treeview.item(selected_item, "values")

        # Adatok kiírása a konzolra (debug)
        print(f"Kiválasztott mérkőzés: {fixture_data}")

        # Odds mentése és megjelenítése
        fixture_id = fixture_data[0]  # Az első oszlop az `fixture_id`
        save_odds_for_fixture(fixture_id)
        self.show_odds_window(fixture_data)

    def show_odds_window(self, fixture_data):
        """
        Megjeleníti az oddsokat egy külön ablakban, a kiválasztott mérkőzés adataival együtt,
        és támogatja a rendezést az oszlopokra kattintva.
        """
        fixture_id = fixture_data[0]  # Az `fixture_id` az első oszlop
        home_team = fixture_data[1]  # Hazai csapat neve
        away_team = fixture_data[2]  # Vendég csapat neve
        match_date = fixture_data[3]  # Mérkőzés dátuma

        # Oddsok lekérdezése
        odds = get_odds_by_fixture_id(fixture_id)
        if not odds:
            print(f"Oddsok nincsenek mentve, lekérdezés és mentés szükséges: {fixture_id}")
            save_odds_for_fixture(fixture_id)
            odds = get_odds_by_fixture_id(fixture_id)  # Újra lekérjük az adatbázisból

        # Odds ablak létrehozása
        odds_window = tk.Toplevel(self)
        odds_window.title(f"Oddsok mérkőzéshez: {fixture_id}")
        odds_window.geometry("700x500")

        # Mérkőzés részleteinek megjelenítése
        details_frame = tk.Frame(odds_window)
        details_frame.pack(pady=10)

        tk.Label(details_frame, text=f"Mérkőzés: {home_team} vs {away_team}", font=("Arial", 14, "bold")).pack()
        tk.Label(details_frame, text=f"Dátum: {match_date}", font=("Arial", 12)).pack()

        # Scrollbar és Treeview konténer
        treeview_frame = tk.Frame(odds_window)
        treeview_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollbar hozzáadása
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Treeview widget a scrollbar-ral
        odds_treeview = ttk.Treeview(treeview_frame, columns=(
            "bookmaker", "home_odds", "draw_odds", "away_odds"
        ), show="headings", yscrollcommand=scrollbar.set)

        odds_treeview.heading("bookmaker", text="Iroda",
                              command=lambda: self.sort_treeview(odds_treeview, "bookmaker", False))
        odds_treeview.heading("home_odds", text="Hazai Odds",
                              command=lambda: self.sort_treeview(odds_treeview, "home_odds", False))
        odds_treeview.heading("draw_odds", text="Döntetlen Odds",
                              command=lambda: self.sort_treeview(odds_treeview, "draw_odds", False))
        odds_treeview.heading("away_odds", text="Vendég Odds",
                              command=lambda: self.sort_treeview(odds_treeview, "away_odds", False))

        odds_treeview.column("bookmaker", width=150)
        odds_treeview.column("home_odds", width=100)
        odds_treeview.column("draw_odds", width=100)
        odds_treeview.column("away_odds", width=100)

        odds_treeview.pack(fill="both", expand=True)

        # Scrollbar összekapcsolása a Treeview-vel
        scrollbar.config(command=odds_treeview.yview)

        # Betöltjük az oddsokat a Treeview-be
        for odd in odds:
            odds_treeview.insert("", "end", values=(
                odd["bookmaker"],
                odd["home_odds"],
                odd["draw_odds"],
                odd["away_odds"]
            ))

        # Vissza gomb hozzáadása
        back_button = ttk.Button(odds_window, text="Vissza", command=odds_window.destroy)
        back_button.pack(pady=10)

    def sort_treeview(self, column):
        """
        Rendezi a Treeview tartalmát az adott oszlop alapján.
        :param column: Az oszlop neve, amely alapján rendezünk.
        """
        # Rendelési sorrend megfordítása
        self.sort_orders[column] = not self.sort_orders[column]
        reverse = self.sort_orders[column]

        # A Treeview sorainak lekérdezése és rendezése
        data = [(self.treeview.set(child, column), child) for child in self.treeview.get_children('')]

        # Megpróbáljuk számként értelmezni az oszlopokat
        try:
            data.sort(reverse=reverse, key=lambda x: float(x[0]) if column in ["fixture_id", "match_date"] else x[0])
        except ValueError:
            data.sort(reverse=reverse, key=lambda x: x[0].lower())  # Ha nem szám, akkor szöveg szerint rendez

        # Sorok újra behelyezése rendezett sorrendben
        for index, (value, item) in enumerate(data):
            self.treeview.move(item, '', index)

    def add_to_selected(self):
        """Kiválasztott mérkőzések hozzáadása a listához."""
        global selected_fixtures, selected_window
        selected_items = self.treeview.selection()
        new_fixtures = []

        for item in selected_items:
            fixture_data = self.treeview.item(item, "values")
            if fixture_data not in selected_fixtures:
                selected_fixtures.append(fixture_data)
                new_fixtures.append(fixture_data)

        if not new_fixtures:
            messagebox.showinfo("Információ", "Nincs új mérkőzés a kiválasztott listában.")
            return

        messagebox.showinfo("Siker", f"{len(new_fixtures)} új mérkőzés hozzáadva a kiválasztott mérkőzésekhez.")

        # Ha a kiválasztott ablak nyitva van, frissítjük annak tartalmát
        if selected_window and selected_window.winfo_exists():
            selected_window.refresh_selected_fixtures()

    def show_selected_fixtures(self):
        """Megjeleníti a kiválasztott mérkőzéseket egy új ablakban."""
        global selected_window

        if selected_window is None or not selected_window.winfo_exists():
            selected_window = SelectedFixturesWindow(self)
        else:
            selected_window.lift()

class SelectedFixturesWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Kiválasztott mérkőzések")
        self.geometry("600x400")

        # Treeview a kiválasztott mérkőzésekhez
        self.treeview = ttk.Treeview(self, columns=("fixture_id", "home_team", "away_team", "match_date"), show="headings")
        self.treeview.heading("fixture_id", text="Mérkőzés ID")
        self.treeview.heading("home_team", text="Hazai csapat")
        self.treeview.heading("away_team", text="Vendég csapat")
        self.treeview.heading("match_date", text="Dátum")
        self.treeview.pack(fill="both", expand=True)

        # Gombok hozzáadása
        self.add_buttons()

        # Kiválasztott mérkőzések betöltése
        self.load_selected_fixtures()

    def add_buttons(self):
        """Gombok hozzáadása az ablakhoz."""
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        delete_button = ttk.Button(button_frame, text="Törlés", command=self.delete_selected_fixtures)
        delete_button.pack(side="left", padx=5)

        close_button = ttk.Button(button_frame, text="Bezárás", command=self.destroy)
        close_button.pack(side="left", padx=5)

    def load_selected_fixtures(self):
        """Betölti a kiválasztott mérkőzéseket a táblázatba."""
        global selected_fixtures

        # Előző sorok törlése
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Új sorok hozzáadása
        for fixture in selected_fixtures:
            self.treeview.insert("", "end", values=fixture)

    def refresh_selected_fixtures(self):
        """Frissíti a kiválasztott mérkőzések táblázatának tartalmát."""
        self.load_selected_fixtures()

    def delete_selected_fixtures(self):
        """Eltávolítja a kijelölt mérkőzéseket a listából és frissíti a táblázatot."""
        global selected_fixtures

        # Kijelölt elemek azonosítása
        selected_items = self.treeview.selection()
        for item in selected_items:
            fixture_data = self.treeview.item(item, "values")
            if fixture_data in selected_fixtures:
                selected_fixtures.remove(fixture_data)

        # Figyelmeztetés, ha nincs kijelölés
        if not selected_items:
            messagebox.showwarning("Figyelmeztetés", "Nem választottál ki törlendő mérkőzést.")
        else:
            messagebox.showinfo("Siker", f"{len(selected_items)} mérkőzés törölve.")

        # Lista frissítése
        self.load_selected_fixtures()
