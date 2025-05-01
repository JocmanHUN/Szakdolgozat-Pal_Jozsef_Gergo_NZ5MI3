import csv
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from src.Backend.DB.fixtures import get_fixture_result
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

        # Initialize instance variables
        self.predictions_by_fixture = predictions_by_fixture
        self.simulation_name = simulation_name or "ismeretlen"
        self.simulation_date = simulation_date or datetime.now().strftime("%Y-%m-%d")
        self.match_group_id = match_group_id
        self.summary_table_frame = None
        self.match_table_frame = None
        self.last_strategy_name = None
        self.match_details_by_model = {}

        # Configure window
        self.title("Fogadási stratégiák grafikonja")
        self.geometry("1300x800")
        self.minsize(1300, 800)

        # Create UI components
        self._create_main_layout()
        self._create_control_panel()
        self._create_graph_area()

    def _create_main_layout(self):
        """Create the main container layout"""
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)

        # Simulation label
        self.simulation_label = ttk.Label(
            self.main_container,
            text=f"Szimuláció: {self.simulation_name}",
            font=("Arial", 14, "bold")
        )
        self.simulation_label.pack(pady=(10, 5))

        # Back button (initially hidden)
        self.back_button = ttk.Button(
            self.main_container,
            text="🔙 Vissza",
            command=self.show_summary_view
        )

    def _create_control_panel(self):
        """Create the control panel with strategy buttons and stake input"""
        # Stake input
        stake_frame = ttk.Frame(self.main_container)
        stake_frame.pack(pady=5)

        ttk.Label(stake_frame, text="Kezdő tét (kelly esetében bankroll):").pack(side="left", padx=5)

        self.stake_entry = ttk.Entry(stake_frame, width=10)
        self.stake_entry.insert(0, "10")
        self.stake_entry.pack(side="left", padx=5)

        # Strategy buttons
        button_frame = ttk.Frame(self.main_container)
        button_frame.pack(pady=10)

        strategies = ["Flat Betting", "Value Betting", "Martingale", "Fibonacci", "Kelly Criterion"]
        for strategy in strategies:
            ttk.Button(
                button_frame,
                text=strategy,
                command=lambda s=strategy: self.plot_strategy(s)
            ).pack(side="left", padx=5)

        # Export button
        ttk.Button(
            button_frame,
            text="Eredmények exportálása (csv)",
            command=self.export_all_strategies
        ).pack(side="left", padx=5)

    def _create_graph_area(self):
        """Create the matplotlib graph canvas"""
        self.figure = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def plot_strategy(self, strategy_name, selected_model=None):
        """
        Plot the strategy performance for all models or a specific model

        Args:
            strategy_name: The strategy to simulate
            selected_model: Optional specific model to show details for
        """
        # Validate stake input
        try:
            stake = float(self.stake_entry.get())
        except ValueError:
            messagebox.showerror("Hiba", "A tét mezőbe csak számot adhatsz meg.")
            return

        self.last_strategy_name = strategy_name

        # Reset previous tables
        self._reset_display_tables()

        # Create summary table
        self._create_summary_table()

        # Clear and prepare the figure
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Process data and generate plots
        has_data = self._process_models_and_plot(ax, strategy_name, stake, selected_model)

        # Configure the plot
        if has_data:
            self._configure_plot(ax, strategy_name)

            # If a specific model is selected, show detailed match table
            if selected_model and selected_model in self.match_details_by_model:
                self._create_match_details_table(selected_model)

        # Update the canvas
        self.canvas.draw()

    def _reset_display_tables(self):
        """Clear previous tables"""
        if self.summary_table_frame:
            self.summary_table_frame.destroy()

        if self.match_table_frame:
            self.match_table_frame.destroy()

    def _create_summary_table(self):
        """Create the summary table frame and table"""
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

        # Add column widths for better appearance
        self.summary_table.column("model", width=120)
        self.summary_table.column("total_stake", width=120)
        self.summary_table.column("profit", width=120)

        self.summary_table.pack(fill="x", padx=10)
        self.summary_table.bind("<<TreeviewSelect>>", self.on_model_select)

    def _process_models_and_plot(self, ax, strategy_name, stake, selected_model=None):
        """Process all models and generate plot data"""
        has_data = False
        all_profits = {}
        all_stakes = {}
        self.match_details_by_model = {}

        model_names = ["bayes_classic", "monte_carlo", "poisson", "bayes_empirical", "log_reg", "elo"]

        for model_name in model_names:
            if selected_model and model_name != selected_model:
                continue

            # Get bets for this model
            bets, match_details = self._prepare_bets_for_model(model_name, strategy_name)

            if not bets:
                continue

            # Run the strategy simulation
            bankroll, stakes_used = self._run_strategy_simulation(strategy_name, bets, stake)

            if bankroll:
                # Calculate profit values for plot
                initial = bankroll[0]
                profits = [round(b - initial, 2) for b in bankroll[1:]]

                # Plot the profit curve
                ax.plot(range(1, len(bankroll)), profits, label=model_name)

                # Update match details with profit information
                for i, profit in enumerate(profits):
                    match_details[i]["profit"] = f"{profit:+.2f}"

                has_data = True
                all_profits[model_name] = profits
                all_stakes[model_name] = sum(stakes_used)
                self.match_details_by_model[model_name] = match_details

                # Add row to summary table
                total_stake = round(sum(stakes_used), 2)
                profit = round(profits[-1], 2) if profits else 0
                self.summary_table.insert("", "end", values=(model_name, total_stake, profit))

        return has_data

    def _prepare_bets_for_model(self, model_name, strategy_name):
        """Prepare bets and match details for a specific model"""
        bets = []
        match_details = []

        for fixture in self.predictions_by_fixture:
            fixture_data = fixture["fixture"]
            fixture_id = fixture_data["fixture_id"]
            match_date = fixture_data.get("match_date", "N/A")
            home_team = fixture_data.get("home_team", "Hazai")
            away_team = fixture_data.get("away_team", "Vendég")
            actual_outcome = self.determine_actual_outcome(fixture_data)

            # Skip if no prediction or no outcome
            db_prediction = get_prediction_from_db(fixture_id, model_name, self.match_group_id)
            if not db_prediction or not actual_outcome:
                continue

            predicted_code = db_prediction["predicted_outcome"]
            is_win = db_prediction["was_correct"] == 1
            model_prob = db_prediction.get("probability", 50) / 100

            actual_code = actual_outcome

            # Skip invalid predictions
            if predicted_code not in ["1", "X", "2"] or actual_code not in ["1", "X", "2"]:
                continue

            is_win = predicted_code == actual_code

            # Get odds information
            result = get_best_odds_for_fixture(fixture_id, predicted_code)
            odds = result["selected_odds"] if result and result.get("selected_odds") is not None else None

            if not odds or odds <= 1.01:
                continue

            model_prob = float(str(db_prediction["probability"]).replace(",", "."))

            # Determine if bet is placed (for certain strategies)
            placed_bet = True
            if strategy_name in ["Value Betting", "Kelly Criterion"]:
                placed_bet = (model_prob * odds) > 1

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
                "odds": odds if placed_bet else "-",
                "placed_bet": "✅" if placed_bet else "❌"
            })

        # Sort by date
        combined = list(zip(match_details, bets))
        combined.sort(key=lambda x: x[0]['date'])

        if not combined:
            return [], []

        match_details, bets = zip(*combined)
        return list(bets), list(match_details)

    def _run_strategy_simulation(self, strategy_name, bets, stake):
        """Run the selected betting strategy simulation"""
        if strategy_name == "Flat Betting":
            return flat_betting(bets, stake)
        elif strategy_name == "Value Betting":
            return value_betting(bets, stake)
        elif strategy_name == "Martingale":
            return martingale(bets, stake)
        elif strategy_name == "Fibonacci":
            return fibonacci(bets, stake)
        elif strategy_name == "Kelly Criterion":
            return kelly_criterion(bets, stake)
        else:
            return None, None

    def _configure_plot(self, ax, strategy_name):
        """Configure plot appearance"""
        ax.set_xlabel("Mérkőzések")
        ax.set_ylabel("Profit/Veszteség arány")
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend()
        ax.set_title(strategy_name, fontsize=12, fontweight="bold")
        ax.grid(True, linestyle='--', alpha=0.7)

    def _create_match_details_table(self, selected_model):
        """Create the detailed match table for a selected model"""
        self.match_table_frame = ttk.Frame(self.main_container)
        self.match_table_frame.pack(pady=10, fill="both", expand=True)

        # Add a label for better clarity
        ttk.Label(
            self.match_table_frame,
            text=f"{selected_model} modell részletes eredményei",
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 5))

        # Create scrollable container
        scroll_container = ttk.Frame(self.match_table_frame)
        scroll_container.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(scroll_container, orient="vertical")
        hsb = ttk.Scrollbar(scroll_container, orient="horizontal")

        # Create match details table
        match_table = ttk.Treeview(
            scroll_container,
            columns=("date", "match", "prediction", "actual", "result", "odds", "profit", "placed_bet"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        # Configure scrollbars
        vsb.config(command=match_table.yview)
        hsb.config(command=match_table.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        match_table.pack(fill="both", expand=True)

        # Set up column headings
        match_table.heading("date", text="Dátum")
        match_table.heading("match", text="Mérkőzés")
        match_table.heading("prediction", text="Tipp")
        match_table.heading("actual", text="Valós")
        match_table.heading("result", text="Eredmény")
        match_table.heading("odds", text="Odds")
        match_table.heading("profit", text="Profit")
        match_table.heading("placed_bet", text="Fogadtunk?")

        # Configure column widths
        match_table.column("date", anchor="center", width=120)
        match_table.column("match", anchor="center", width=220)
        match_table.column("prediction", anchor="center", width=60)
        match_table.column("actual", anchor="center", width=60)
        match_table.column("result", anchor="center", width=80)
        match_table.column("odds", anchor="center", width=80)
        match_table.column("profit", anchor="center", width=100)
        match_table.column("placed_bet", anchor="center", width=100)

        # Populate table with match data
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

        # Show back button when viewing details
        self.back_button.pack(pady=5)

    def on_model_select(self, event):
        """Handle model selection from summary table"""
        selected_item = self.summary_table.selection()
        if not selected_item:
            return
        model = self.summary_table.item(selected_item[0], "values")[0]
        self.plot_strategy(self.last_strategy_name, selected_model=model)

    def determine_actual_outcome(self, fixture):
        """Lekéri az aktuális eredményt az adatbázisból"""
        fixture_id = fixture.get("fixture_id")
        if not fixture_id:
            return None

        result = get_fixture_result(fixture_id)
        if not result:
            return None

        home = result.get("score_home")
        away = result.get("score_away")

        if home is None or away is None:
            return None

        if home > away:
            return "1"
        elif home < away:
            return "2"
        else:
            return "X"

    def show_summary_view(self):
        """Return to summary view from detailed view"""
        self.plot_strategy(self.last_strategy_name)
        self.back_button.pack_forget()

    def export_all_strategies(self):
        """Export strategy results to CSV file"""
        # Validate data exists
        if not hasattr(self, "match_details_by_model") or not self.match_details_by_model:
            messagebox.showwarning("Hiányzó adatok",
                                   "Előbb futtasd le a szimulációt valamelyik stratégiával a grafikonon!")
            return

        # Get export parameters
        stake = float(self.stake_entry.get())
        simulation_name = getattr(self, "simulation_name", "ismeretlen")
        date_str = getattr(self, "simulation_date", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        date_str = date_str.replace(":", "-").replace(" ", "_")

        # Get destination folder
        folder = filedialog.askdirectory(title="Válassz mappát az exporthoz")
        if not folder:
            return

        strategy_name = self.last_strategy_name or "ismeretlen_stratégia"
        match_details_by_model = self.match_details_by_model

        # Sort matches by date
        all_matches = sorted(set(
            f"{m['date']} - {m['match']}"
            for matches in match_details_by_model.values()
            for m in matches
        ))

        # Create filename and path
        filename = f"{simulation_name}-{strategy_name}-{date_str}.csv"
        full_path = f"{folder}/{filename}"

        try:
            with open(full_path, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([simulation_name, strategy_name, date_str, f"{stake} egység"])
                writer.writerow(["Model"] + all_matches)

                for model_name, matches in match_details_by_model.items():
                    profits_by_match = {
                        f"{m['date']} - {m['match']}": m.get("profit", "") for m in matches
                    }

                    row_profits = []
                    for match_id in all_matches:
                        val = profits_by_match.get(match_id, "")
                        row_profits.append(val)

                    writer.writerow([model_name] + row_profits)

            messagebox.showinfo("Sikeres mentés", f"A stratégia exportálása sikeresen megtörtént ide:\n{full_path}")

        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt a mentés során:\n{str(e)}")