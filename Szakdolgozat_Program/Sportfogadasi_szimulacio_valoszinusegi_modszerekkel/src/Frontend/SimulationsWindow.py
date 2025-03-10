from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from src.Backend.helpersAPI import load_simulations_from_db, fetch_fixtures_for_simulation

# Szimulációs és mérkőzésadatok (valós esetben adatbázisból)
simulations_data = [
    (1, "FirstList", "2025-03-10"),
    (2, "SecondList", "2025-03-11"),
]

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


class SimulationsWindow(tk.Toplevel):
    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.refresh_callback = refresh_callback  # A főmenü frissítéséhez
        self.title("Szimulációk és mérkőzések")
        self.geometry("700x500")
        self.minsize(700, 500)

        # Szimulációk táblázata
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
        self.fixture_label = ttk.Label(self, text="Szimulációhoz tartozó mérkőzések", font=("Arial", 12, "bold"))
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
        button_frame = tk.Frame(self)
        button_frame.pack(pady=5)

        self.delete_simulation_button = ttk.Button(button_frame, text="Szimuláció törlése", command=self.delete_selected_simulation)
        self.delete_simulation_button.pack(side="left", padx=5)

        self.close_button = ttk.Button(button_frame, text="Bezárás", command=self.destroy)
        self.close_button.pack(side="left", padx=5)

    def load_simulations(self):
        """Betölti az adatbázisból az elérhető szimulációkat a táblázatba."""
        self.simulation_treeview.delete(*self.simulation_treeview.get_children())  # Előző adatok törlése

        simulations = load_simulations_from_db()
        for simulation in simulations:
            self.simulation_treeview.insert("", "end",
                                            values=(simulation["id"], simulation["name"], simulation["created_at"]))

    def on_simulation_select(self, event):
        """Ha egy szimulációra kattintunk, megjeleníti a hozzá tartozó mérkőzéseket."""
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            return

        sim_id = int(self.simulation_treeview.item(selected_item[0], "values")[0])
        fixtures = fetch_fixtures_for_simulation(sim_id)

        # Töröljük az előző mérkőzéseket
        for item in self.fixture_treeview.get_children():
            self.fixture_treeview.delete(item)

        # Betöltjük az új mérkőzéseket
        for fixture in fixtures:
            self.fixture_treeview.insert("", "end", values=(
                fixture["fixture_id"], fixture["home_team"], fixture["away_team"], fixture["match_date"]
            ))

    def load_fixtures_for_simulation(self, simulation_id):
        """Betölti a kiválasztott szimulációhoz tartozó mérkőzéseket."""
        for item in self.fixture_treeview.get_children():
            self.fixture_treeview.delete(item)

        if simulation_id in fixtures_by_simulation:
            for fixture in fixtures_by_simulation[simulation_id]:
                self.fixture_treeview.insert("", "end", values=fixture)

    def delete_selected_simulation(self):
        """Törli a kiválasztott szimulációt és annak mérkőzéseit."""
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Nem választottál ki törlendő szimulációt.")
            return

        sim_id = int(self.simulation_treeview.item(selected_item[0], "values")[0])

        # Törlés a listából (valós esetben adatbázisból is)
        global simulations_data, fixtures_by_simulation
        simulations_data = [s for s in simulations_data if s[0] != sim_id]
        if sim_id in fixtures_by_simulation:
            del fixtures_by_simulation[sim_id]

        self.load_simulations()
        self.fixture_treeview.delete(*self.fixture_treeview.get_children())  # Törli a mérkőzéseket is

        messagebox.showinfo("Siker", f"Szimuláció ID: {sim_id} törölve.")

        # Hívjuk meg a callback függvényt a főmenü frissítésére, ha van
        if self.refresh_callback:
            self.refresh_callback()
