import tkinter as tk
from tkinter import ttk, messagebox
from src.Backend.DB.fixtures import update_fixtures_status, fetch_fixtures_for_simulation
from src.Backend.DB.predictions import evaluate_predictions, update_simulation_profit, get_predictions_for_fixture
from src.Backend.DB.simulations import load_simulations_from_db
from src.Frontend.windows.visualizationWindow import VisualizationWindow


class SimulationsWindow(tk.Toplevel):
    def __init__(self, master, refresh_callback=None):
        super().__init__(master)
        self.refresh_callback = refresh_callback
        self.title("Szimulációk és mérkőzések")
        self.geometry("1000x500")
        self.minsize(1000, 500)

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

        # Mérkőzések táblázata
        self.fixture_label = ttk.Label(self, text="Szimulációhoz tartozó mérkőzések", font=("Arial", 12, "bold"))
        self.fixture_label.pack(pady=5)

        self.fixture_treeview = ttk.Treeview(self, columns=(
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

        self.fixture_treeview.pack(fill="both", expand=True, padx=10, pady=5)

        self.add_widgets()

    def add_widgets(self):
        button_frame = tk.Frame(self)
        button_frame.pack(pady=5)

        self.delete_simulation_button = ttk.Button(
            button_frame, text="Szimuláció törlése", command=self.delete_selected_simulation
        )
        self.delete_simulation_button.pack(side="left", padx=5)

        self.close_button = ttk.Button(button_frame, text="Bezárás", command=self.destroy)
        self.close_button.pack(side="left", padx=5)

    def load_simulations(self):
        self.simulation_treeview.delete(*self.simulation_treeview.get_children())

        simulations = load_simulations_from_db()
        for simulation in simulations:
            self.simulation_treeview.insert("", "end",
                                            values=(simulation["id"], simulation["name"], simulation["created_at"]))

    def on_simulation_select(self, event):
        """Ha egy szimulációra kattintunk, frissíti az adatokat, ellenőrzi a státuszokat és megjeleníti a vizualizációt."""
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            return

        sim_id = int(self.simulation_treeview.item(selected_item[0], "values")[0])
        update_fixtures_status()
        # 🔍 Lekérjük az adott match group összes mérkőzését
        fixtures = fetch_fixtures_for_simulation(sim_id)
        predictions_by_fixture = []

        # 📌 Ellenőrizzük, hogy mely mérkőzések értek már véget
        completed_fixtures = [f for f in fixtures if isinstance(f, dict) and f.get("status") in ["FT", "AET", "PEN"]]
        pending_fixtures = [f for f in fixtures if isinstance(f, dict) and f.get("status") not in ["FT", "AET", "PEN"]]
        print(completed_fixtures)
        print(pending_fixtures)
        # 📌 Kiértékeljük a befejezett mérkőzéseket
        if completed_fixtures:
            for fixture in completed_fixtures:
                home_score = fixture.get("score_home")
                away_score = fixture.get("score_away")
                if home_score is not None and away_score is not None:
                    evaluate_predictions(fixture["fixture_id"],home_score,away_score)

            # 🔄 Frissítjük a szimuláció összegzett profitját
            update_simulation_profit(sim_id)

        # ⚠️ Figyelmeztetés, ha még nem minden mérkőzés ért véget
        if pending_fixtures:
            print(f"⚠️ Még {len(pending_fixtures)} mérkőzés zajlik a szimulációban (ID: {sim_id})")
            messagebox.showinfo("Részleges eredmények",
                                f"{len(pending_fixtures)} mérkőzés még nem ért véget.\nA diagram csak a befejezett mérkőzéseket tartalmazza.")

        # 📊 Frissített adatokat jelenítsük meg a táblázatban
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

        # 📈 Megnyitjuk a vizualizációs ablakot a predikciókkal
        VisualizationWindow(self, predictions_by_fixture)

        print(
            f"✅ Szimuláció ({sim_id}) frissítve! {len(completed_fixtures)} befejezett mérkőzés, {len(pending_fixtures)} folyamatban.")

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



