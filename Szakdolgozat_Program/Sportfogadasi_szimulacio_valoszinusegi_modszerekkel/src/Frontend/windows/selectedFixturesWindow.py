# Globális lista a kiválasztott mérkőzésekhez
from datetime import datetime
from tkinter import ttk, messagebox
import tkinter as tk
from src.Backend.DB.simulations import check_group_name_exists, create_simulation, save_match_group, save_match_to_group
from src.Backend.DB.strategies import get_all_strategies
from src.Backend.DB.teams import get_team_id_by_name
from src.Backend.helpers.ensureDatas import ensure_simulation_data_available
from src.Backend.helpers.helpersModel import save_all_predictions
from src.Frontend.helpersGUI import refresh_main_menu_styles, selected_fixtures


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

        # Előző sorok törlése
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Új sorok hozzáadása
        for fixture in selected_fixtures:
            self.treeview.insert("", "end", values=fixture)

    def delete_selected_fixtures(self):

        selected_items = self.treeview.selection()
        for item in selected_items:
            fixture_data = self.treeview.item(item, "values")
            if fixture_data in selected_fixtures:
                selected_fixtures.remove(fixture_data)

        if not selected_items:
            messagebox.showwarning("Figyelmeztetés", "Nem választottál ki törlendő mérkőzést.",parent=self)
        else:
            messagebox.showinfo("Siker", f"{len(selected_items)} mérkőzés törölve.",parent=self)

        self.load_selected_fixtures()

        refresh_main_menu_styles(self.master.app)

        self.lift()
        self.focus_force()

    def run_simulation(self):
        """Szimuláció futtatása a kiválasztott mérkőzésekkel."""

        match_group_name = self.match_group_name_entry.get().strip()

        if not match_group_name:
            messagebox.showwarning("Figyelmeztetés", "Adj meg egy nevet a mérkőzéscsoportnak!",parent=self)
            return

        if len(selected_fixtures) > 25:
            messagebox.showwarning("Figyelmeztetés", "Legfeljebb 25 mérkőzést választhatsz ki egy szimulációhoz!",parent=self)
            return

        if check_group_name_exists(match_group_name):
            messagebox.showerror("Hiba", f"Már létezik egy mérkőzéscsoport ezzel a névvel: '{match_group_name}'!",parent=self)
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
            messagebox.showwarning("Figyelmeztetés", "Nem található érvényes mérkőzés. Ellenőrizd a csapatneveket!",parent=self)
            return

        print(f"🔄 Adatok biztosítása a szimulációhoz: {match_group_name}")
        valid_fixture_ids = ensure_simulation_data_available(fixture_list)

        if len(valid_fixture_ids) < 3:
            print("⛔ Nem elegendő felhasználható mérkőzés (minimum 3 kell).")
            messagebox.showerror("Hiba", "Legalább 3 valid meccs szükséges a szimulációhoz.",parent=self)
            return

        # Csak a valid fixture-eket mentjük el
        valid_fixtures_with_names = [id_to_fixture[fx_id] for fx_id in valid_fixture_ids]
        match_group_id = self.save_simulation_fixtures_to_database(match_group_name, valid_fixtures_with_names)

        if match_group_id is None:
            print("❌ Hiba: A mérkőzéscsoport ID nem található.")
            messagebox.showerror("Hiba", "Nem sikerült elmenteni a mérkőzéscsoportot!",parent=self)
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

        messagebox.showinfo("Siker", "Szimulációk és előrejelzések sikeresen mentve.",parent=self)
        selected_fixtures.clear()

        refresh_main_menu_styles(self.master.app)
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

        messagebox.showinfo("Siker", f"A '{match_group_name}' nevű mérkőzéscsoport sikeresen mentve!",parent=self)

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