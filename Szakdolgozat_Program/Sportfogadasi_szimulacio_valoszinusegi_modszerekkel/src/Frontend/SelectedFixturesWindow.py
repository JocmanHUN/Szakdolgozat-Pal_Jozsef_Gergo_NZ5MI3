from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

selected_fixtures = []

simulations_data = [
    (1, "FirstList", "2025-03-10"),
    (2, "SecondList", "2025-03-11"),
]

# Tesztadatok a mérkőzésekhez (valós adatbázis lekérdezéssel kell helyettesíteni)
fixtures_by_simulation = {
    1: [
        (101, "Team A", "Team B", "2025-03-12 18:00:00"),
        (102, "Team C", "Team D", "2025-03-12 20:00:00"),
    ],
    2: [
        (103, "Team E", "Team F", "2025-03-13 18:00:00"),
        (104, "Team G", "Team H", "2025-03-13 20:00:00"),
    ],
}

class SelectedFixturesWindow(tk.Toplevel):
    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.refresh_callback = refresh_callback
        self.title("Kiválasztott mérkőzések és szimulációk")
        self.geometry("700x500")
        self.minsize(700, 500)  # Minimális méret

        # Szimulációk lista
        self.simulation_label = ttk.Label(self, text="Elérhető szimulációk", font=("Arial", 12, "bold"))
        self.simulation_label.pack(pady=5)

        self.simulation_treeview = ttk.Treeview(self, columns=("id", "name", "date"), show="headings")
        self.simulation_treeview.heading("id", text="ID", anchor="center")
        self.simulation_treeview.heading("name", text="Szimuláció neve")
        self.simulation_treeview.heading("date", text="Dátum")

        self.simulation_treeview.column("id", width=50, anchor="center")
        self.simulation_treeview.column("name", width=200)
        self.simulation_treeview.column("date", width=150)

        self.simulation_treeview.pack(fill="both", expand=True, padx=10, pady=5)

        self.simulation_treeview.bind("<Double-1>", self.on_simulation_select)

        self.load_simulations()

        # Kiválasztott mérkőzések listája
        self.fixture_label = ttk.Label(self, text="Aktuálisan kiválasztott mérkőzések", font=("Arial", 12, "bold"))
        self.fixture_label.pack(pady=5)

        self.fixture_treeview = ttk.Treeview(self, columns=("fixture_id", "home_team", "away_team", "match_date"),
                                             show="headings")
        self.fixture_treeview.heading("fixture_id", text="Mérkőzés ID", anchor="center")
        self.fixture_treeview.heading("home_team", text="Hazai csapat")
        self.fixture_treeview.heading("away_team", text="Vendég csapat")
        self.fixture_treeview.heading("match_date", text="Dátum")

        self.fixture_treeview.column("fixture_id", width=100, anchor="center")
        self.fixture_treeview.column("home_team", width=150)
        self.fixture_treeview.column("away_team", width=150)
        self.fixture_treeview.column("match_date", width=150)

        self.fixture_treeview.pack(fill="both", expand=True, padx=10, pady=5)

        # Gombok hozzáadása
        self.add_widgets()

    def add_widgets(self):
        """Gombok és input mező hozzáadása."""
        frame = tk.Frame(self)
        frame.pack(pady=5)

        self.match_group_name_label = ttk.Label(frame, text="Mérkőzéscsoport neve:")
        self.match_group_name_label.pack(side="left", padx=5)

        self.match_group_name_entry = ttk.Entry(frame, width=20)
        self.match_group_name_entry.pack(side="left", padx=5)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=5)

        self.simulate_button = ttk.Button(button_frame, text="Szimuláció futtatása", command=self.run_simulation)
        self.simulate_button.pack(side="left", padx=5)

        self.delete_button = ttk.Button(button_frame, text="Törlés", command=self.delete_selected_fixtures)
        self.delete_button.pack(side="left", padx=5)

        self.close_button = ttk.Button(button_frame, text="Bezárás", command=self.destroy)
        self.close_button.pack(side="left", padx=5)

    def load_simulations(self):
        """Betölti az elérhető szimulációkat a felső táblába."""
        for simulation in simulations_data:
            self.simulation_treeview.insert("", "end", values=simulation)

    def on_simulation_select(self, event):
        """Ha egy szimulációra kattintunk, megjeleníti a hozzá tartozó mérkőzéseket."""
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            return

        sim_id = int(self.simulation_treeview.item(selected_item[0], "values")[0])

        self.load_fixtures_for_simulation(sim_id)

    def load_fixtures_for_simulation(self, simulation_id):
        """Betölti a kiválasztott szimulációhoz tartozó mérkőzéseket."""
        for item in self.fixture_treeview.get_children():
            self.fixture_treeview.delete(item)

        if simulation_id in fixtures_by_simulation:
            for fixture in fixtures_by_simulation[simulation_id]:
                self.fixture_treeview.insert("", "end", values=fixture)

    def load_selected_fixtures(self):
        """Betölti a kiválasztott mérkőzéseket a táblázatba."""
        global selected_fixtures
        print(selected_fixtures)
        # Előző sorok törlése
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Új sorok hozzáadása
        for fixture in selected_fixtures:
            self.treeview.insert("", "end", values=fixture)

    def delete_selected_fixtures(self):
        global selected_fixtures

        selected_items = self.fixture_treeview.selection()
        for item in selected_items:
            fixture_data = self.fixture_treeview.item(item, "values")
            if fixture_data in selected_fixtures:
                selected_fixtures.remove(fixture_data)

        if not selected_items:
            messagebox.showwarning("Figyelmeztetés", "Nem választottál ki törlendő mérkőzést.")
        else:
            messagebox.showinfo("Siker", f"{len(selected_items)} mérkőzés törölve.")

        self.load_selected_fixtures()

        # Hívjuk meg a callback függvényt a főmenü frissítésére, ha van
        if self.refresh_callback:
            self.refresh_callback()

        self.lift()
        self.focus_force()
    def run_simulation(self):
        """Szimuláció futtatása a kiválasztott mérkőzésekkel."""
        global selected_fixtures

        match_group_name = self.match_group_name_entry.get().strip()

        if not match_group_name:
            messagebox.showwarning("Figyelmeztetés", "Adj meg egy nevet a mérkőzéscsoportnak!")
            return

        if not selected_fixtures:
            messagebox.showwarning("Figyelmeztetés", "Nincsenek kiválasztott mérkőzések a szimulációhoz!")
            return

        # Itt történik meg az adatok mentése az adatbázisba
        self.save_simulation_to_database(match_group_name, selected_fixtures)

        messagebox.showinfo("Siker", f"A '{match_group_name}' nevű mérkőzéscsoport sikeresen mentve!")
        self.destroy()

    def save_simulation_to_database(self, match_group_name, fixtures):
        """
        Mentés az adatbázisba.
        Ezt a funkciót a backend függvényeidhez kell kötni, pl. SQL lekérdezésekhez.
         # Feltételezve, hogy van ilyen függvényed

        match_group_id = save_match_group(match_group_name)  # Mérkőzéscsoport mentése
        for fixture in fixtures:
            fixture_id = fixture[0]
            save_match_to_group(match_group_id, fixture_id)  # Mérkőzés hozzárendelése a csoporthoz
        """
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

