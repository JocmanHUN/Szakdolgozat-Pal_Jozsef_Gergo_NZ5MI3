import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.Backend.helpersAPI import (
    load_simulations_from_db,
    fetch_fixtures_for_simulation,
    get_predictions_for_fixture,
)
from src.Backend.strategies import (
    flat_betting,
    value_betting,
    martingale,
    fibonacci,
    kelly_criterion,
)


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
        selected_item = self.simulation_treeview.selection()
        if not selected_item:
            return

        sim_id = int(self.simulation_treeview.item(selected_item[0], "values")[0])

        fixtures = fetch_fixtures_for_simulation(sim_id)
        predictions_by_fixture = []

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

        VisualizationWindow(self, predictions_by_fixture)

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


class VisualizationWindow(tk.Toplevel):
    def __init__(self, master, predictions_by_fixture):
        super().__init__(master)
        self.predictions_by_fixture = predictions_by_fixture
        self.title("Fogadási stratégiák grafikonja")
        self.geometry("1000x600")

        ttk.Label(self, text="Kezdő tét:", font=("Arial", 10)).pack(pady=5)
        self.stake_entry = ttk.Entry(self)
        self.stake_entry.insert(0, "10")
        self.stake_entry.pack(pady=5)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        strategies = ["Flat Betting", "Value Betting", "Martingale", "Fibonacci", "Kelly Criterion"]

        for strategy in strategies:
            ttk.Button(button_frame, text=strategy, command=lambda s=strategy: self.plot_strategy(s)).pack(side="left", padx=5)

        self.figure = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def plot_strategy(self, strategy_name):
        stake = float(self.stake_entry.get())
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        total_stake = 0
        final_balance = 1000  # Kezdő bankroll
        has_data = False  # Új változó, hogy ellenőrizzük, van-e kiábrázolható adat

        for model_name in ["bayes_classic", "monte_carlo", "poisson", "bayes_empirical", "log_reg", "elo"]:
            bets = []
            for fixture in self.predictions_by_fixture:
                pred = fixture["predictions"].get(model_name)

                if pred and "odds_list" in pred and len(pred["odds_list"]) > 0:
                    avg_odds = sum(pred["odds_list"]) / len(pred["odds_list"])  # Átlag odds
                    bet_data = {
                        "won": pred.get("outcome") == "Home",
                        "odds": avg_odds,
                        "model_probability": pred.get("model_probability", 0.5),
                    }
                    bets.append(bet_data)

            if not bets:
                continue  # Ha nincs adat, kihagyjuk ezt a modellt

            if strategy_name == "Flat Betting":
                bankroll = flat_betting(bets, stake)
            elif strategy_name == "Value Betting":
                bankroll = value_betting(bets, stake)
            elif strategy_name == "Martingale":
                bankroll = martingale(bets, stake)
            elif strategy_name == "Fibonacci":
                bankroll = fibonacci(bets, stake)
            elif strategy_name == "Kelly Criterion":
                bankroll = kelly_criterion(bets)

            if bankroll:  # Ha van kirajzolható adat
                ax.plot(bankroll, label=f"{model_name} (Avg. odds)")
                has_data = True  # Megjegyezzük, hogy volt legalább egy érvényes vonal

            total_stake += len(bets) * stake
            final_balance = bankroll[-1] if bankroll else final_balance

        profit = final_balance - 1000

        ax.set_title(f"Bankroll változása - {strategy_name}\nFelhasznált összeg: {total_stake} | Profit: {profit:.2f}")
        ax.set_xlabel("Mérkőzés sorszáma")
        ax.set_ylabel("Bankroll értéke")

        if has_data:
            ax.legend()  # Csak akkor hívjuk meg, ha valóban van kirajzolható vonal

        self.canvas.draw()


