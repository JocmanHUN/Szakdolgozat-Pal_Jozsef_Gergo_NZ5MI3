import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from src.Backend.API.helpersAPI import sync_bookmakers, save_odds_for_fixture
from src.Backend.API.odds import fetch_odds_for_fixture
from src.Backend.helpersModel import save_all_predictions, ensure_simulation_data_available
from src.Backend.helpersSim import get_all_strategies, create_simulation
from src.Frontend.PastResultsApp import PastResultsApp
from src.Frontend.SimulationsWindow import SimulationsWindow
from src.Frontend.TeamsApp import TeamsApp
from src.Backend.helpersAPI import get_pre_match_fixtures, get_odds_by_fixture_id,\
    check_group_name_exists, save_match_group, save_match_to_group, get_team_id_by_name
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
        # Rendezettségi állapot tárolása az oszlopokhoz
        self.sort_orders = {"fixture_id": False, "home_team": False, "away_team": False, "match_date": False}

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
        global selected_fixtures, selected_window
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
        if selected_window and selected_window.winfo_exists():
            selected_window.refresh_selected_fixtures()

        self.load_fixtures()

    def show_selected_fixtures(self):
        """Megjeleníti a kiválasztott mérkőzéseket egy új ablakban."""
        global selected_window

        if selected_window is None or not selected_window.winfo_exists():
            selected_window = SelectedFixturesWindow(self)
        else:
            selected_window.lift()

    def show_simulations(self):
        """Megnyitja a SimulationsWindow-t."""
        SimulationsWindow(self)

# Globális lista a kiválasztott mérkőzésekhez
selected_fixtures = []

class SelectedFixturesWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Kiválasztott mérkőzések és szimuláció")
        self.geometry("600x500")
        self.minsize(600, 500)  # Az ablak minimális mérete

        # Rendezettségi állapot tárolása az oszlopokhoz
        self.sort_orders = {"fixture_id": False, "home_team": False, "away_team": False, "match_date": False}

        # Treeview létrehozása a mérkőzések listájának megjelenítéséhez
        self.treeview = ttk.Treeview(self, columns=("fixture_id", "home_team", "away_team", "match_date"),
                                     show="headings")
        self.treeview.heading("fixture_id", text="Mérkőzés ID", command=lambda: self.sort_treeview("fixture_id"), anchor="center")
        self.treeview.heading("home_team", text="Hazai csapat", command=lambda: self.sort_treeview("home_team"))
        self.treeview.heading("away_team", text="Vendég csapat", command=lambda: self.sort_treeview("away_team"))
        self.treeview.heading("match_date", text="Dátum", command=lambda: self.sort_treeview("match_date"))
        self.treeview.pack(fill="both", expand=True)

        # Oszlopok beállítása
        self.treeview.column("fixture_id", width=100, minwidth=100, stretch=True, anchor="center")
        self.treeview.column("home_team", width=150, minwidth=150, stretch=True)
        self.treeview.column("away_team", width=150, minwidth=150, stretch=True)
        self.treeview.column("match_date", width=150, minwidth=150, stretch=True)

        # Gombok és textbox hozzáadása
        self.add_widgets()

        # Kiválasztott mérkőzések betöltése
        self.load_selected_fixtures()

    def add_widgets(self):
        """Hozzáadja a gombokat és a textboxot az ablakhoz."""
        frame = tk.Frame(self)
        frame.pack(pady=10)

        # Textbox a mérkőzéscsoport nevének megadásához
        self.match_group_name_label = ttk.Label(frame, text="Mérkőzéscsoport neve:")
        self.match_group_name_label.pack(side="left", padx=5)

        self.match_group_name_entry = ttk.Entry(frame, width=20)
        self.match_group_name_entry.pack(side="left", padx=5)

        # Gombok hozzáadása
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        self.simulate_button = ttk.Button(button_frame, text="Szimuláció futtatása", command=self.run_simulation)
        self.simulate_button.pack(side="left", padx=5)

        self.delete_button = ttk.Button(button_frame, text="Törlés", command=self.delete_selected_fixtures)
        self.delete_button.pack(side="left", padx=5)

        self.close_button = ttk.Button(button_frame, text="Bezárás", command=self.destroy)
        self.close_button.pack(side="left", padx=5)

    def load_selected_fixtures(self):
        """Betölti a kiválasztott mérkőzéseket a táblázatba."""
        global selected_fixtures

        # Előző sorok törlése
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Új sorok hozzáadása
        for fixture in selected_fixtures:
            self.treeview.insert("", "end", values=fixture)

    def delete_selected_fixtures(self):
        global selected_fixtures

        selected_items = self.treeview.selection()
        for item in selected_items:
            fixture_data = self.treeview.item(item, "values")
            if fixture_data in selected_fixtures:
                selected_fixtures.remove(fixture_data)

        if not selected_items:
            messagebox.showwarning("Figyelmeztetés", "Nem választottál ki törlendő mérkőzést.")
        else:
            messagebox.showinfo("Siker", f"{len(selected_items)} mérkőzés törölve.")

        self.load_selected_fixtures()

        # Frissítsük a főmenü Treeview stílusát, ha elérhető
        if isinstance(self.master.app.current_frame, MainMenu):
            self.master.app.current_frame.update_fixture_styles()

        self.lift()
        self.focus_force()

    def run_simulation(self):
        """Szimuláció futtatása a kiválasztott mérkőzésekkel."""
        global selected_fixtures

        match_group_name = self.match_group_name_entry.get().strip()

        if not match_group_name:
            messagebox.showwarning("Figyelmeztetés", "Adj meg egy nevet a mérkőzéscsoportnak!")
            return

        if len(selected_fixtures) > 25:
            messagebox.showwarning("Figyelmeztetés", "Legfeljebb 25 mérkőzést választhatsz ki egy szimulációhoz!")
            return

        if check_group_name_exists(match_group_name):
            messagebox.showerror("Hiba", f"Már létezik egy mérkőzéscsoport ezzel a névvel: '{match_group_name}'!")
            return

        # 🔍 Nevekből ID-k
        fixture_list = []
        id_to_fixture = {}  # hogy később visszatudjuk fordítani a neveket

        for fixture in selected_fixtures:
            fixture_id = fixture[0]
            home_team_name = fixture[1]
            away_team_name = fixture[2]

            home_team_id = get_team_id_by_name(home_team_name)
            away_team_id = get_team_id_by_name(away_team_name)

            if home_team_id is None or away_team_id is None:
                print(f"❌ Hiba: Nincs meg a csapat: {home_team_name} vs {away_team_name}")
                messagebox.showerror("Hiba", f"Nem található csapat: {home_team_name} vagy {away_team_name}")
                continue

            fixture_list.append((home_team_id, away_team_id, fixture_id))
            id_to_fixture[fixture_id] = (fixture_id, home_team_name, away_team_name)

        if not fixture_list:
            messagebox.showwarning("Figyelmeztetés", "Nem található érvényes mérkőzés. Ellenőrizd a csapatneveket!")
            return

        print(f"🔄 Adatok biztosítása a szimulációhoz: {match_group_name}")
        valid_fixture_ids = ensure_simulation_data_available(fixture_list)

        if len(valid_fixture_ids) < 3:
            print("⛔ Nem elegendő felhasználható mérkőzés (minimum 3 kell).")
            messagebox.showerror("Hiba", "Legalább 3 valid meccs szükséges a szimulációhoz.")
            return

        # Csak a valid fixture-eket mentjük el
        valid_fixtures_with_names = [id_to_fixture[fx_id] for fx_id in valid_fixture_ids]
        match_group_id = self.save_simulation_fixtures_to_database(match_group_name, valid_fixtures_with_names)

        if match_group_id is None:
            print("❌ Hiba: A mérkőzéscsoport ID nem található.")
            messagebox.showerror("Hiba", "Nem sikerült elmenteni a mérkőzéscsoportot!")
            return

        # 🔮 Predikciók mentése
        for fixture_id in valid_fixture_ids:
            home_team_name = id_to_fixture[fixture_id][1]
            away_team_name = id_to_fixture[fixture_id][2]
            home_team_id = get_team_id_by_name(home_team_name)
            away_team_id = get_team_id_by_name(away_team_name)

            save_all_predictions(fixture_id, home_team_id, away_team_id, match_group_id)

        # 🧠 Stratégia mentések
        strategies = get_all_strategies()
        for strategy in strategies:
            create_simulation(match_group_id, strategy['id'])

        messagebox.showinfo("Siker", "Szimulációk és előrejelzések sikeresen mentve.")
        selected_fixtures.clear()

        if isinstance(self.master.app.current_frame, MainMenu):
            self.master.app.current_frame.update_fixture_styles()

        self.destroy()

    def save_simulation_fixtures_to_database(self, match_group_name, fixtures):
        """
        A felhasználói interfész meghívja ezt a függvényt, amikor a szimulációt menteni kell.
        """
        # 1️⃣ Mérkőzéscsoport létrehozása vagy visszakeresése
        match_group_id = save_match_group(match_group_name)

        # 2️⃣ Minden kiválasztott mérkőzést hozzáadunk ehhez a csoporthoz
        for fixture in fixtures:
            fixture_id = fixture[0]  # Az első érték a mérkőzés ID-ja
            save_match_to_group(match_group_id, fixture_id)

        messagebox.showinfo("Siker", f"A '{match_group_name}' nevű mérkőzéscsoport sikeresen mentve!")

        return match_group_id  # 🔹 Az ID-t visszaadjuk a hívó függvénynek

    def sort_treeview(self, column):
        """Rendezi a Treeview tartalmát az adott oszlop alapján."""
        self.sort_orders[column] = not self.sort_orders[column]  # Fordítsuk meg a rendezési sorrendet
        reverse = self.sort_orders[column]

        # A Treeview sorainak lekérdezése és rendezése
        data = [(self.treeview.set(child, column), child) for child in self.treeview.get_children('')]

        if column == "fixture_id":
            data.sort(key=lambda x: int(x[0]), reverse=reverse)
        elif column == "match_date":
            data.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S"), reverse=reverse)
        else:
            data.sort(key=lambda x: x[0].lower(), reverse=reverse)

        for index, (value, item) in enumerate(data):
            self.treeview.move(item, '', index)

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
        """Frissíti a kiválasztott mérkőzések listáját a GUI-ban."""
        print("🔄 Kiválasztott mérkőzések frissítése...")
        self.load_selected_fixtures()





