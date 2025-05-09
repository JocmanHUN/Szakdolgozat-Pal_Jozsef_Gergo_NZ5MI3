from datetime import datetime
from tkinter import ttk, messagebox
import tkinter as tk
from src.Backend.API.helpersAPI import save_odds_for_fixture
from src.Backend.DB.fixtures import get_pre_match_fixtures
from src.Backend.DB.odds import get_odds_by_fixture_id
from src.Frontend import helpersGUI
from src.Frontend.helpersGUI import selected_fixtures
from src.Frontend.windows.SimulationsWindow import SimulationsWindow
from src.Frontend.windows.selectedFixturesWindow import SelectedFixturesWindow


class MainMenu(tk.Frame):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        # Rendezettségi állapot tárolása az oszlopokhoz
        self.sort_orders = {"fixture_id": False, "home_team": False, "away_team": False, "match_date": False}

        # Főcím hozzáadása
        title_label = ttk.Label(self, text="Sportfogadás nyerességeségének vizsgálata",
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

        self.treeview.heading("fixture_id", text="Mérkőzés ID",
                              command=lambda: self.sort_treeview("fixture_id"), anchor="center")
        self.treeview.heading("home_team", text="Hazai csapat",
                              command=lambda: self.sort_treeview("home_team"))
        self.treeview.heading("away_team", text="Vendég csapat",
                              command=lambda: self.sort_treeview("away_team"))
        self.treeview.heading("match_date", text="Dátum",
                              command=lambda: self.sort_treeview("match_date"))

        # Oszlopok méretezése
        self.treeview.column("fixture_id", width=100,anchor="center")
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

        # Kattintási esemény tiltása a nem választható mérkőzésekre
        self.treeview.bind("<Double-1>", self.on_fixture_click)

    def load_fixtures(self):
        """
        Betölti a mérkőzéseket egyszer, ha még nem töltöttük be,
        és inicializálja a Treeview-t.
        """
        # Csak egyszeri betöltés, például egy attribútumban tárolva az adatokat
        if not hasattr(self, "fixtures_data"):
            self.fixtures_data = get_pre_match_fixtures()
            # Töltsd fel a Treeview-t a fixtures_data alapján
            for row in self.fixtures_data:
                fixture_id = row["fixture_id"]
                home_team = row["home_team"]
                away_team = row["away_team"]
                match_date_str = row["match_date"]
                # Alapértelmezetten minden mérkőzés kiválasztható
                self.treeview.insert("", "end", values=(fixture_id, home_team, away_team, match_date_str),
                                     tags=("normal",))

        # Frissítsd a stílusokat a kiválasztott mérkőzések alapján
        self.update_fixture_styles()

    def update_fixture_styles(self):
        """
        Frissíti a már betöltött mérkőzések stílusát, hogy
        a nem kiválasztható mérkőzések szürkések legyenek.
        """
        # Gyűjtsük össze a kiválasztott mérkőzések dátumait
        selected_times = []
        for fixture in selected_fixtures:
            _, _, _, selected_date_str = fixture
            # Ellenőrizzük, hogy datetime vagy string
            if isinstance(selected_date_str, datetime):
                selected_datetime = selected_date_str
            else:
                selected_datetime = datetime.strptime(selected_date_str, "%Y-%m-%d %H:%M:%S")
            selected_times.append(selected_datetime)

        # Frissítsük az egyes Treeview elemeket
        for item in self.treeview.get_children():
            fixture_data = self.treeview.item(item, "values")
            match_date_str = fixture_data[3]
            match_datetime = datetime.strptime(match_date_str, "%Y-%m-%d %H:%M:%S")
            # Ellenőrizzük, hogy a mérkőzés kiválasztható-e
            is_selectable = all(abs((match_datetime - t).total_seconds()) / 3600 >= 2 for t in selected_times)
            new_tag = "normal" if is_selectable else "disabled"
            self.treeview.item(item, tags=(new_tag,))

        # Stílusok beállítása a tag-ekhez
        self.treeview.tag_configure("disabled", background="#d3d3d3", foreground="gray")
        self.treeview.tag_configure("normal", background="white", foreground="black")

    def prevent_selection(self, event):
        """Megakadályozza a nem választható mérkőzések kijelölését."""
        selected_items = self.treeview.selection()
        for item in selected_items:
            tags = self.treeview.item(item, "tags")
            if "disabled" in tags:
                self.treeview.selection_remove(item)  # Kijelölés törlése

    def on_fixture_click(self, event):
        """Megakadályozza a nem választható mérkőzések kijelölését."""
        selected_items = self.treeview.selection()
        for item in selected_items:
            item_tags = self.treeview.item(item, "tags")
            if "disabled" in item_tags:
                self.treeview.selection_remove(item)  # Ha a mérkőzés "disabled", akkor ne lehessen kijelölni
                messagebox.showwarning("Figyelmeztetés",
                                       "Ezt a mérkőzést nem választhatod ki, mert túl közel kezdődik egy másikhoz!")
                return

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

        view_selected_button = ttk.Button(button_frame, text="Kiválasztott mérkőzések és szimuláció indítás", command=self.show_selected_fixtures)
        view_selected_button.pack(side="left", padx=5)

        simulations_button = ttk.Button(button_frame, text="Meglévő szimulációk", command=self.show_simulations)
        simulations_button.pack(side="left", padx=5)

    def on_fixture_click(self, event):
        # Ellenőrizzük, hogy a kattintás a fejlécen történt-e
        region = self.treeview.identify("region", event.x, event.y)
        if region == "heading":
            return  # Ha fejléc, akkor nem csinál semmit

        # További kód: csak ha cellára kattintottak, odds ablak megnyitása
        selected_items = self.treeview.selection()
        if not selected_items:
            print("Nincs kiválasztott elem a táblázatban.")
            return

        selected_item = selected_items[0]
        fixture_data = self.treeview.item(selected_item, "values")
        print(f"Kiválasztott mérkőzés: {fixture_data}")

        fixture_id = fixture_data[0]
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
            print(odds)

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
        """Kiválasztott mérkőzések hozzáadása a listához ±2 órás időkorláttal."""

        selected_items = self.treeview.selection()
        new_fixtures = []

        for item in selected_items:
            fixture_data = self.treeview.item(item, "values")
            fixture_id, home_team, away_team, match_date_str = fixture_data

            # Dátum formátum konvertálás
            match_datetime = datetime.strptime(match_date_str, "%Y-%m-%d %H:%M:%S")

            # Ellenőrizzük, hogy van-e már olyan mérkőzés, ami ±2 órán belül kezdődik
            conflict = False
            for selected_fixture in selected_fixtures:
                _, _, _, selected_date_str = selected_fixture
                selected_datetime = datetime.strptime(selected_date_str, "%Y-%m-%d %H:%M:%S")

                # Ugyanazon a napon ±2 órán belül lévő meccseket nem engedjük hozzáadni
                if match_datetime.date() == selected_datetime.date():
                    time_diff = abs((match_datetime - selected_datetime).total_seconds()) / 3600  # Órára konvertálva
                    if time_diff < 2:
                        conflict = True
                        break

            if conflict:
                messagebox.showwarning("Figyelmeztetés",
                                       f"{home_team} vs {away_team} mérkőzés túl közel kezdődik egy már kiválasztott mérkőzéshez!")
            else:
                if fixture_data not in selected_fixtures:
                    selected_fixtures.append(fixture_data)
                    new_fixtures.append(fixture_data)

        if not new_fixtures:
            messagebox.showinfo("Információ", "Nincs új mérkőzés a kiválasztott listában.")
            return

        messagebox.showinfo("Siker", f"{len(new_fixtures)} új mérkőzés hozzáadva a kiválasztott mérkőzésekhez.")

        # Ha a kiválasztott ablak nyitva van, frissítjük annak tartalmát
        if helpersGUI.selected_window and helpersGUI.selected_window.winfo_exists():
            helpersGUI.selected_window.refresh_selected_fixtures()

        self.load_fixtures()

    def show_selected_fixtures(self):
        """Megjeleníti a kiválasztott mérkőzéseket egy új ablakban."""

        if helpersGUI.selected_window is None or not helpersGUI.selected_window.winfo_exists():
            helpersGUI.selected_window = SelectedFixturesWindow(self)
        else:
            helpersGUI.selected_window.lift()

    def show_simulations(self):
        """Megnyitja a SimulationsWindow-t."""
        SimulationsWindow(self)