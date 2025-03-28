import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from src.Backend.DB.fixtures import update_fixtures_status, fetch_fixtures_for_simulation
from src.Backend.DB.odds import get_best_odds_for_fixture
from src.Backend.DB.predictions import evaluate_predictions, update_simulation_profit, get_predictions_for_fixture
from src.Backend.DB.simulations import load_simulations_from_db
from src.Backend.strategies.fibonacci import fibonacci
from src.Backend.strategies.flatBetting import flat_betting
from src.Backend.strategies.kellyCriterion import kelly_criterion
from src.Backend.strategies.martingale import martingale
from src.Backend.strategies.valueBetting import value_betting


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


class VisualizationWindow(tk.Toplevel):
    def __init__(self, master, predictions_by_fixture):
        super().__init__(master)
        self.predictions_by_fixture = predictions_by_fixture
        self.title("Fogadási stratégiák grafikonja")
        self.geometry("1000x700")  # ez maradhat
        self.minsize(1000, 800)

        # 📦 Fő konténer, ahol minden UI-elem van
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)

        # 🧮 Kezdő tét
        ttk.Label(self.main_container, text="Kezdő tét:").pack(pady=5)
        self.stake_entry = ttk.Entry(self.main_container)
        self.stake_entry.insert(0, "10")
        self.stake_entry.pack(pady=5)

        # 📊 Gombok
        button_frame = ttk.Frame(self.main_container)
        button_frame.pack(pady=10)
        strategies = ["Flat Betting", "Value Betting", "Martingale", "Fibonacci", "Kelly Criterion"]
        for strategy in strategies:
            ttk.Button(button_frame, text=strategy, command=lambda s=strategy: self.plot_strategy(s)).pack(side="left", padx=5)

        # 📋 Itt jön majd a tábla — helyet foglalunk neki
        self.summary_table_frame = None

        self.last_strategy_name = None

        # 📈 Matplotlib grafikon
        self.figure = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def plot_strategy(self, strategy_name, selected_model=None):
        try:
            stake = float(self.stake_entry.get())
        except ValueError:
            messagebox.showerror("Hiba", "A tét mezőbe csak számot adhatsz meg.")
            return

        self.last_strategy_name = strategy_name  # elmentjük az utolsó stratégiát visszatéréshez

        if self.summary_table_frame:
            self.summary_table_frame.destroy()

        self.summary_table_frame = ttk.Frame(self.main_container)
        self.summary_table_frame.pack(pady=10)

        self.summary_table = ttk.Treeview(
            self.summary_table_frame,
            columns=("model", "total_stake", "profit"),
            show="headings",
            height=6
        )
        self.summary_table.heading("model", text="Modell")
        self.summary_table.heading("total_stake", text="Tét (összesen)")
        self.summary_table.heading("profit", text="Profit")

        self.summary_table.column("model", anchor="center", width=150)
        self.summary_table.column("total_stake", anchor="center", width=120)
        self.summary_table.column("profit", anchor="center", width=100)

        self.summary_table.pack()

        # 🔗 Eseménykezelő: modell sorra kattintás
        self.summary_table.bind("<<TreeviewSelect>>", self.on_model_select)

        # GRAFIKON törlése és új rajz
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        has_data = False
        all_profits = {}
        all_bets_count = {}

        model_names = ["bayes_classic", "monte_carlo", "poisson", "bayes_empirical", "log_reg", "elo"]

        for model_name in model_names:
            if selected_model and model_name != selected_model:
                continue

            bets = []

            for fixture in self.predictions_by_fixture:
                fixture_data = fixture["fixture"]
                fixture_id = fixture_data["fixture_id"]
                actual_outcome = self.determine_actual_outcome(fixture_data)

                pred = fixture["predictions"].get(model_name)
                if not pred or " " not in pred or "(" not in pred:
                    continue

                predicted_code = pred.split(" ")[0]
                actual_code = self.determine_actual_outcome(fixture_data)

                if predicted_code not in ["1", "X", "2"] or actual_code not in ["1", "X", "2"]:
                    continue

                is_win = predicted_code == actual_code

                if is_win:
                    result = get_best_odds_for_fixture(fixture_id, predicted_code)
                    odds = result["selected_odds"] if result and result.get("selected_odds") is not None else 1.0
                else:
                    odds = 1.0

                try:
                    prob_str = pred.split("(")[-1].strip("%)")
                    model_prob = float(prob_str) / 100
                except:
                    model_prob = 0.5

                bet_data = {
                    "won": is_win,
                    "odds": odds,
                    "model_probability": model_prob
                }
                bets.append(bet_data)

            if not bets:
                continue

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
            else:
                continue

            if bankroll:
                profits = [round(b - bankroll[0], 2) for b in bankroll]
                ax.plot(range(len(profits)), profits, label=model_name)
                has_data = True
                all_profits[model_name] = profits
                all_bets_count[model_name] = len(bets)

        ax.set_xlabel("Mérkőzések")
        ax.set_ylabel("Profit/Veszteség arány")
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        if has_data:
            ax.legend()
            total_stake_sum = 0
            total_profit_sum = 0

            for model_name, profits in all_profits.items():
                stake_total = stake * all_bets_count[model_name] if strategy_name != "Kelly Criterion" else 0
                profit = round(profits[-1], 2) if profits else 0

                self.summary_table.insert(
                    "", "end",
                    values=(model_name, stake_total if stake_total != 0 else "Változó", profit)
                )

                if strategy_name != "Kelly Criterion":
                    total_stake_sum += stake_total
                total_profit_sum += profit

            # ➕ Összesítés sor
            self.summary_table.insert(
                "", "end",
                values=(
                    "Összesen",
                    total_stake_sum if strategy_name != "Kelly Criterion" else "Változó",
                    round(total_profit_sum, 2)
                )
            )

            ax.set_title(strategy_name, fontsize=12, fontweight="bold")

        self.canvas.draw()

    def on_model_select(self, event):
        selected_item = self.summary_table.selection()
        if not selected_item:
            return

        model = self.summary_table.item(selected_item[0], "values")[0]
        if model == "Összesen":
            self.plot_strategy(self.last_strategy_name)  # újra az összes modell
        else:
            self.plot_strategy(self.last_strategy_name, selected_model=model)

    def determine_actual_outcome(self, fixture):
        home = fixture.get("score_home")
        away = fixture.get("score_away")
        if home is None or away is None:
            return None
        if home > away:
            return "1"
        elif home < away:
            return "2"
        else:
            return "X"



