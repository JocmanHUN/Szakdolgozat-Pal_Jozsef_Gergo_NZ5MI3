from tkinter import ttk, messagebox
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from src.Backend.DB.odds import get_best_odds_for_fixture
from src.Backend.strategies.fibonacci import fibonacci
from src.Backend.strategies.flatBetting import flat_betting
from src.Backend.strategies.kellyCriterion import kelly_criterion
from src.Backend.strategies.martingale import martingale
from src.Backend.strategies.valueBetting import value_betting


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
