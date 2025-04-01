import csv
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from src.Backend.DB.odds import get_best_odds_for_fixture
from src.Backend.DB.predictions import get_prediction_from_db
from src.Backend.strategies.fibonacci import fibonacci
from src.Backend.strategies.flatBetting import flat_betting
from src.Backend.strategies.kellyCriterion import kelly_criterion
from src.Backend.strategies.martingale import martingale
from src.Backend.strategies.valueBetting import value_betting


class VisualizationWindow(tk.Toplevel):
    def __init__(self, master, predictions_by_fixture, simulation_name=None, simulation_date=None, match_group_id=None):
        super().__init__(master)
        self.predictions_by_fixture = predictions_by_fixture
        self.simulation_name = simulation_name or "ismeretlen"
        self.simulation_date = simulation_date or datetime.now().strftime("%Y-%m-%d")
        self.title("Fogadási stratégiák grafikonja")
        self.geometry("1300x800")
        self.minsize(1300, 800)
        self.match_group_id = match_group_id
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        self.simulation_label = ttk.Label(self.main_container, text=f"Szimuláció: {self.simulation_name}",
                                          font=("Arial", 14, "bold"))
        self.simulation_label.pack(pady=(0, 5))
        ttk.Label(self.main_container, text="Kezdő tét (kelly esetében bankroll):").pack(pady=5)
        self.stake_entry = ttk.Entry(self.main_container)
        self.stake_entry.insert(0, "10")
        self.stake_entry.pack(pady=5)


        button_frame = ttk.Frame(self.main_container)
        button_frame.pack(pady=10)
        strategies = ["Flat Betting", "Value Betting", "Martingale", "Fibonacci", "Kelly Criterion"]
        for strategy in strategies:
            ttk.Button(button_frame, text=strategy, command=lambda s=strategy: self.plot_strategy(s)).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Eredmények exportálása (csv)", command=self.export_all_strategies).pack(side="left",
                                                                                                         padx=5)
        self.summary_table_frame = None
        self.match_table_frame = None
        self.last_strategy_name = None

        self.back_button = ttk.Button(self.main_container, text="🔙 Vissza", command=self.show_summary_view)
        self.back_button.pack(pady=5)
        self.back_button.pack_forget()

        self.figure = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def plot_strategy(self, strategy_name, selected_model=None):
        try:
            stake = float(self.stake_entry.get())
        except ValueError:
            messagebox.showerror("Hiba", "A tét mezőbe csak számot adhatsz meg.")
            return

        self.last_strategy_name = strategy_name

        if self.summary_table_frame:
            self.summary_table_frame.destroy()

        if self.match_table_frame:
            self.match_table_frame.destroy()

        self.summary_table_frame = ttk.Frame(self.main_container)
        self.summary_table_frame.pack(pady=10)

        self.summary_table = ttk.Treeview(
            self.summary_table_frame,
            columns=("model", "total_stake", "profit"),
            show="headings",
            height=6
        )
        self.summary_table.heading("model", text="Modell")
        self.summary_table.heading("total_stake", text="Összes tét ")
        self.summary_table.heading("profit", text="Profit")

        self.summary_table.pack()
        self.summary_table.bind("<<TreeviewSelect>>", self.on_model_select)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        has_data = False
        all_profits = {}
        all_stakes = {}
        self.match_details_by_model = {}

        model_names = ["bayes_classic", "monte_carlo", "poisson", "bayes_empirical", "log_reg", "elo"]

        for model_name in model_names:
            if selected_model and model_name != selected_model:
                continue

            bets = []
            match_details = []

            for fixture in self.predictions_by_fixture:
                fixture_data = fixture["fixture"]
                fixture_id = fixture_data["fixture_id"]
                match_date = fixture_data.get("match_date", "N/A")
                home_team = fixture_data.get("home_team", "Hazai")
                away_team = fixture_data.get("away_team", "Vendég")
                actual_outcome = self.determine_actual_outcome(fixture_data)

                db_prediction = get_prediction_from_db(fixture_id, model_name, self.match_group_id)
                if not db_prediction:
                    continue

                predicted_code = db_prediction["predicted_outcome"]
                is_win = db_prediction["was_correct"] == 1
                model_prob = db_prediction.get("probability", 50) / 100  # fallback default: 0.5

                actual_code = actual_outcome

                if predicted_code not in ["1", "X", "2"] or actual_code not in ["1", "X", "2"]:
                    continue

                is_win = predicted_code == actual_code

                result = get_best_odds_for_fixture(fixture_id, predicted_code)
                odds = result["selected_odds"] if result and result.get("selected_odds") is not None else None

                if not odds or odds <= 1.01:
                    print(f"⚠️ Hibás vagy hiányzó odds (fixture_id={fixture_id}, kód={predicted_code})")
                    continue

                model_prob = float(str(db_prediction["probability"]).replace(",", ".")) / 100

                placed_bet = True
                if strategy_name in ["Value Betting", "Kelly Criterion"]:
                    placed_bet = (model_prob * odds) > 1
                    print(
                        f"[{strategy_name}] {match_date} | {home_team} vs {away_team} | "
                        f"Valószínűség: {model_prob:.2f}, Odds: {odds:.2f} => "
                        f"{'✅ Fogadunk' if placed_bet else '❌ Nem fogadunk'} "
                        f"(p * odds = {(model_prob * odds):.2f})"
                    )


                if strategy_name in ["Value Betting", "Kelly Criterion"]:
                    placed_bet = (float(model_prob) * odds) > 1

                bets.append({
                    "won": is_win,
                    "odds": odds,
                    "model_probability": model_prob
                })

                match_details.append({
                    "date": match_date,
                    "match": f"{home_team} vs {away_team}",
                    "prediction": predicted_code,
                    "actual": actual_code,
                    "result": "✅" if is_win else "❌",
                    "odds": odds if is_win else "-",
                    "placed_bet": "✅" if placed_bet else "❌"
                })

            combined = list(zip(match_details, bets))
            combined.sort(key=lambda x: x[0]['date'])

            if not combined:
                continue  # ugrik a modellre, ha nincs egyetlen meccs sem

            match_details, bets = zip(*combined)
            match_details = list(match_details)
            bets = list(bets)

            if not bets:
                continue

            if strategy_name == "Flat Betting":
                bankroll, stakes_used = flat_betting(bets, stake)
            elif strategy_name == "Value Betting":
                bankroll, stakes_used = value_betting(bets, stake)
            elif strategy_name == "Martingale":
                bankroll, stakes_used = martingale(bets, stake)
            elif strategy_name == "Fibonacci":
                bankroll, stakes_used = fibonacci(bets, stake)
            elif strategy_name == "Kelly Criterion":
                bankroll, stakes_used = kelly_criterion(bets, stake)
            else:
                continue

            if bankroll:
                initial = bankroll[0]
                profits = [round(b - initial, 2) for b in bankroll[1:]]
                ax.plot(range(1, len(bankroll)), profits, label=model_name)

                for i, profit in enumerate(profits):
                    match_details[i]["profit"] = f"{profit:+.2f}"

                has_data = True
                all_profits[model_name] = profits
                all_stakes[model_name] = sum(stakes_used)
                self.match_details_by_model[model_name] = match_details

                total_stake = round(sum(stakes_used), 2)
                profit = round(profits[-1], 2) if profits else 0

                self.summary_table.insert("", "end", values=(model_name, total_stake, profit))

        ax.set_xlabel("Mérkőzések")
        ax.set_ylabel("Profit/Veszteség arány")
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        if has_data:
            ax.legend()
            ax.set_title(strategy_name, fontsize=12, fontweight="bold")

            if selected_model and selected_model in self.match_details_by_model:
                if self.match_table_frame:
                    self.match_table_frame.destroy()

                self.match_table_frame = ttk.Frame(self.main_container)
                self.match_table_frame.pack(pady=10, fill="both", expand=True)

                scroll_container = ttk.Frame(self.match_table_frame)
                scroll_container.pack(fill="both", expand=True)

                vsb = ttk.Scrollbar(scroll_container, orient="vertical")
                hsb = ttk.Scrollbar(scroll_container, orient="horizontal")

                match_table = ttk.Treeview(
                    scroll_container,
                    columns=("date", "match", "prediction", "actual", "result", "odds", "profit", "placed_bet"),
                    show="headings",
                    yscrollcommand=vsb.set,
                    xscrollcommand=hsb.set
                )

                vsb.config(command=match_table.yview)
                hsb.config(command=match_table.xview)
                vsb.pack(side="right", fill="y")
                hsb.pack(side="bottom", fill="x")
                match_table.pack(fill="both", expand=True)

                match_table.heading("date", text="Dátum")
                match_table.heading("match", text="Mérkőzés")
                match_table.heading("prediction", text="Tipp")
                match_table.heading("actual", text="Valós")
                match_table.heading("result", text="Eredmény")
                match_table.heading("odds", text="Odds")
                match_table.heading("profit", text="Profit")
                match_table.heading("placed_bet", text="Fogadtunk?")

                match_table.column("date", anchor="center", width=120, stretch=True)
                match_table.column("match", anchor="center", width=220, stretch=True)
                match_table.column("prediction", anchor="center", width=60, stretch=True)
                match_table.column("actual", anchor="center", width=60, stretch=True)
                match_table.column("result", anchor="center", width=80, stretch=True)
                match_table.column("odds", anchor="center", width=80, stretch=True)
                match_table.column("profit", anchor="center", width=100, stretch=True)
                match_table.column("placed_bet", anchor="center", width=100, stretch=True)

                for match in self.match_details_by_model[selected_model]:
                    match_table.insert(
                        "", "end",
                        values=(
                            match["date"],
                            match["match"],
                            match["prediction"],
                            match["actual"],
                            match["result"],
                            match["odds"],
                            match["profit"],
                            match["placed_bet"]
                        )
                    )

        self.canvas.draw()

    def on_model_select(self, event):
        selected_item = self.summary_table.selection()
        if not selected_item:
            return
        model = self.summary_table.item(selected_item[0], "values")[0]
        self.back_button.pack(pady=5)
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

    def show_summary_view(self):
        self.plot_strategy(self.last_strategy_name)
        self.back_button.pack_forget()

    def export_all_strategies(self):
        if not hasattr(self, "match_details_by_model") or not self.match_details_by_model:
            messagebox.showwarning("Hiányzó adatok",
                                   "Előbb futtasd le a szimulációt valamelyik stratégiával a grafikonon!")
            return

        stake = float(self.stake_entry.get())
        simulation_name = getattr(self, "simulation_name", "ismeretlen")
        date_str = getattr(self, "simulation_date", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        date_str = date_str.replace(":", "-").replace(" ", "_")

        folder = filedialog.askdirectory(title="Válassz mappát az exporthoz")
        if not folder:
            return

        strategy_name = self.last_strategy_name or "ismeretlen_stratégia"
        match_details_by_model = self.match_details_by_model  # ez már a plot_strategy-ben generált adat

        # Meccsek sorba rendezése dátum szerint
        all_matches = sorted(set(
            f"{m['date']} - {m['match']}"
            for matches in match_details_by_model.values()
            for m in matches
        ))

        filename = f"{simulation_name}-{strategy_name}-{date_str}.csv"
        full_path = f"{folder}/{filename}"

        try:
            with open(full_path, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([simulation_name, strategy_name, date_str, f"{stake} egység"])
                writer.writerow(["Model"] + all_matches)  # ❌ Nincs többé "Összesített profit"

                for model_name, matches in match_details_by_model.items():
                    profits_by_match = {
                        f"{m['date']} - {m['match']}": m.get("profit", "") for m in matches
                    }

                    row_profits = []
                    for match_id in all_matches:
                        val = profits_by_match.get(match_id, "")
                        row_profits.append(val)

                    writer.writerow([model_name] + row_profits)  # ❌ Nincs többé összegzés

            messagebox.showinfo("Sikeres mentés", f"A stratégia exportálása sikeresen megtörtént ide:\n{full_path}")

        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt a mentés során:\n{str(e)}")







