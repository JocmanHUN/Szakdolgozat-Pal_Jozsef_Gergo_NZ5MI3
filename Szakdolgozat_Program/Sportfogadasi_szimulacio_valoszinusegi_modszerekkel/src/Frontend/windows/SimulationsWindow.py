import tkinter as tk
from tkinter import ttk, messagebox

from src.Backend.API.fixtures import update_fixtures
from src.Backend.DB.fixtures import fetch_fixtures_for_simulation
from src.Backend.DB.predictions import evaluate_predictions, get_predictions_for_fixture, update_strategy_profit
from src.Backend.DB.simulations import load_simulations_from_db
from src.Frontend.windows.aggregatedResultsWindow import AggregatedResultsWindow
from src.Frontend.windows.visualizationWindow import VisualizationWindow


class SimulationsWindow(tk.Toplevel):
    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.refresh_callback = refresh_callback
        self.title("Szimulációk és mérkőzések")
        self.geometry("1000x500")
        self.minsize(1000, 500)

        # Main container to manage layout
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)

        # Configure weight for rows to manage space distribution
        main_container.grid_rowconfigure(0, weight=0)  # Label row - no resize
        main_container.grid_rowconfigure(1, weight=1)  # Simulations table - expand
        main_container.grid_rowconfigure(2, weight=0)  # Label row - no resize
        main_container.grid_rowconfigure(3, weight=1)  # Fixtures table - expand
        main_container.grid_rowconfigure(4, weight=0)  # Buttons row - no resize
        main_container.grid_columnconfigure(0, weight=1)

        # ======= Szimulációk táblázatcímke =======
        self.simulation_label = ttk.Label(main_container, text="Elérhető szimulációk", font=("Arial", 12, "bold"))
        self.simulation_label.grid(row=0, column=0, pady=(10, 0), sticky="w", padx=10)

        # ======= Felső (szimulációk) táblázat =======
        sim_frame = ttk.Frame(main_container)
        sim_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))

        self.simulation_treeview = ttk.Treeview(sim_frame, columns=("id", "name", "date"), show="headings")
        self.simulation_treeview.heading("id", text="ID", anchor="center")
        self.simulation_treeview.heading("name", text="Szimuláció neve")
        self.simulation_treeview.heading("date", text="Dátum")

        self.simulation_treeview.column("id", width=50, anchor="center", minwidth=50)
        self.simulation_treeview.column("name", width=200, minwidth=150)
        self.simulation_treeview.column("date", width=150, minwidth=120)

        sim_vsb = ttk.Scrollbar(sim_frame, orient="vertical", command=self.simulation_treeview.yview)
        sim_hsb = ttk.Scrollbar(sim_frame, orient="horizontal", command=self.simulation_treeview.xview)
        self.simulation_treeview.configure(yscrollcommand=sim_vsb.set, xscrollcommand=sim_hsb.set)

        self.simulation_treeview.grid(row=0, column=0, sticky="nsew")
        sim_vsb.grid(row=0, column=1, sticky="ns")
        sim_hsb.grid(row=1, column=0, sticky="ew")

        sim_frame.grid_rowconfigure(0, weight=1)
        sim_frame.grid_columnconfigure(0, weight=1)

        self.simulation_treeview.bind("<Double-1>", self.on_simulation_select)
        self.load_simulations()

        # ======= Mérkőzések táblázatcímke =======
        self.fixture_label = ttk.Label(main_container, text="Szimulációhoz tartozó mérkőzések",
                                       font=("Arial", 12, "bold"))
        self.fixture_label.grid(row=2, column=0, pady=(10, 0), sticky="w", padx=10)

        # ======= Alsó (mérkőzések) táblázat =======
        fix_frame = ttk.Frame(main_container)
        fix_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 10))

        self.fixture_treeview = ttk.Treeview(fix_frame, columns=(
            "fixture_id", "home_team", "away_team", "match_date",
            "bayes_classic", "monte_carlo", "poisson",
            "bayes_empirical", "log_reg", "elo"
        ), show="headings")

        self.fixture_treeview.heading("fixture_id", text="Mérkőzés ID", anchor="center")
        self.fixture_treeview.heading("home_team", text="Hazai csapat")
        self.fixture_treeview.heading("away_team", text="Vendég csapat")
        self.fixture_treeview.heading("match_date", text="Dátum")
        self.fixture_treeview.heading("bayes_classic", text="Bayes Classic")
        self.fixture_treeview.heading("monte_carlo", text="Monte Carlo")
        self.fixture_treeview.heading("poisson", text="Poisson")
        self.fixture_treeview.heading("bayes_empirical", text="Bayes Empirical")
        self.fixture_treeview.heading("log_reg", text="Logistic Reg.")
        self.fixture_treeview.heading("elo", text="Elo")

        # Set minimum widths for columns
        for col in self.fixture_treeview["columns"]:
            self.fixture_treeview.column(col, minwidth=80)
        self.fixture_treeview.column("fixture_id", width=80, minwidth=80, anchor="center")
        self.fixture_treeview.column("home_team", width=120, minwidth=100)
        self.fixture_treeview.column("away_team", width=120, minwidth=100)
        self.fixture_treeview.column("match_date", width=120, minwidth=100)

        fix_vsb = ttk.Scrollbar(fix_frame, orient="vertical", command=self.fixture_treeview.yview)
        fix_hsb = ttk.Scrollbar(fix_frame, orient="horizontal", command=self.fixture_treeview.xview)
        self.fixture_treeview.configure(yscrollcommand=fix_vsb.set, xscrollcommand=fix_hsb.set)

        self.fixture_treeview.grid(row=0, column=0, sticky="nsew")
        fix_vsb.grid(row=0, column=1, sticky="ns")
        fix_hsb.grid(row=1, column=0, sticky="ew")

        fix_frame.grid_rowconfigure(0, weight=1)
        fix_frame.grid_columnconfigure(0, weight=1)

        # ======= Gombok =======
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=4, column=0, pady=10, sticky="ew")
        button_frame.columnconfigure(tuple(range(4)), weight=1)  # Distribute buttons evenly

        self.delete_simulation_button = ttk.Button(
            button_frame, text="Szimuláció törlése", command=self.delete_selected_simulation
        )
        self.delete_simulation_button.grid(row=0, column=0, padx=5, sticky="e")

        # Új gomb: Összesített szimulációs eredmények
        self.overall_results_button = ttk.Button(
            button_frame,
            text="Összesített szimulációs eredmények",
            command=self.show_aggregated_results
        )
        self.overall_results_button.grid(row=0, column=1, padx=5)

        self.close_button = ttk.Button(button_frame, text="Bezárás", command=self.destroy)
        self.close_button.grid(row=0, column=2, padx=5, sticky="w")

    def load_simulations(self):
        self.simulation_treeview.delete(*self.simulation_treeview.get_children())

        simulations = load_simulations_from_db()
        for simulation in simulations:
            self.simulation_treeview.insert("", "end",
                                            values=(simulation["id"], simulation["name"], simulation["created_at"]))

    def on_simulation_select(self, event):
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            return

        values = self.simulation_treeview.item(selected_item[0], "values")
        sim_id = int(values[0])  # Az 'id' már az 'match_group_id'-t tartalmazza
        simulation_name = values[1]
        simulation_date = values[2]

        # A mérkőzések frissítése
        update_fixtures()
        fixtures = fetch_fixtures_for_simulation(sim_id)
        predictions_by_fixture = []

        # Különválasztjuk a befejezett és folyamatban lévő mérkőzéseket
        completed_fixtures = [f for f in fixtures if isinstance(f, dict) and f.get("status") in ["FT", "AET", "PEN"]]
        pending_fixtures = [f for f in fixtures if isinstance(f, dict) and f.get("status") not in ["FT", "AET", "PEN"]]
        # Ha vannak befejezett mérkőzések, frissítjük az eredményeket
        if completed_fixtures:
            print(f"completed fixtures: {completed_fixtures}")
            for fixture in completed_fixtures:
                home_score = fixture.get("score_home")
                away_score = fixture.get("score_away")
                if home_score is not None and away_score is not None:
                    evaluate_predictions(fixture["fixture_id"], home_score, away_score)
                update_strategy_profit(sim_id, completed_fixtures)

        # Ha vannak folyamatban lévő mérkőzések, figyelmeztetést adunk
        if pending_fixtures:
            messagebox.showinfo("Részleges eredmények",
                                f"{len(pending_fixtures)} mérkőzés még nem ért véget.\nA diagram csak a befejezett mérkőzéseket tartalmazza.")

        # Az összes mérkőzés betöltése a táblázatba
        self.fixture_treeview.delete(*self.fixture_treeview.get_children())

        for fixture in fixtures:
            fixture_id = fixture["fixture_id"]
            predictions = get_predictions_for_fixture(fixture_id)
            predictions_by_fixture.append({"fixture": fixture, "predictions": predictions})

            self.fixture_treeview.insert("", "end", values=(
                fixture_id,
                fixture["home_team"],
                fixture["away_team"],
                fixture["match_date"],
                predictions["bayes_classic"],
                predictions["monte_carlo"],
                predictions["poisson"],
                predictions["bayes_empirical"],
                predictions["log_reg"],
                predictions["elo"]
            ))

        # A vizualizációs ablak megnyitása a szimulációval
        VisualizationWindow(self, predictions_by_fixture,
                            simulation_name=simulation_name,
                            simulation_date=simulation_date, match_group_id=sim_id)

    def delete_selected_simulation(self):
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            messagebox.showwarning("Figyelmeztetés", "Nem választottál ki törlendő szimulációt.")
            return

        sim_id = int(self.simulation_treeview.item(selected_item[0], "values")[0])
        # Adatbázisból törlő függvényt itt hívd meg!

        self.load_simulations()
        self.fixture_treeview.delete(*self.fixture_treeview.get_children())
        messagebox.showinfo("Siker", f"Szimuláció ID: {sim_id} törölve.")

        if self.refresh_callback:
            self.refresh_callback()

    def show_aggregated_results(self):
        # Létrehozzuk az új ablakot, ami MINDENT megmutat egy helyen
        AggregatedResultsWindow(self)