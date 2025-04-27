import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import statistics  # Statisztikai számításokhoz

from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from src.Backend.DB.final_summary import fetch_completed_summary, get_odds_stats_by_strategy_and_model
from src.Backend.DB.predictions import get_all_predictions, get_all_models, get_models_odds_statistics
from src.Backend.DB.simulations import load_aggregated_simulations, load_simulation_profits_data
from src.Backend.DB.strategies import get_all_strategies


class AggregatedResultsWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Összesített szimulációs eredmények")
        self.geometry("950x700")
        self.minsize(850, 600)  # Ablak minimális mérete

        # Layout beállítások, hogy resizálásnál is rendeződjön
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.model_names = {row["model_id"]: row["model_name"] for row in get_all_models()}

        # Notebook létrehozása külön tabokhoz
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Fő keret a szimulációkhoz
        self.simulations_frame = ttk.Frame(self.notebook)
        self.simulations_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.simulations_frame.rowconfigure(3, weight=1)  # A TreeView része nyújtható
        self.simulations_frame.columnconfigure(0, weight=1)

        # Fő keret a predikciókhoz
        self.predictions_frame = ttk.Frame(self.notebook)
        self.predictions_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.predictions_frame.rowconfigure(2, weight=1)  # A TreeView része nyújtható
        self.predictions_frame.columnconfigure(0, weight=1)
        self.model_comparison_frame = ttk.Frame(self.notebook)

        # Hozzáadjuk a tabokat a notebookhoz
        self.notebook.add(self.simulations_frame, text="Szimulációk")
        self.notebook.add(self.predictions_frame, text="Modell predikciók")
        self.create_model_comparison_tab()  # ez hozzáadja a fület és felépíti a tartalmat is
        # Változók a szűréshez
        self.active_strategy = tk.IntVar(value=0)  # 0 = minden stratégia
        self.active_model = tk.IntVar(value=0)  # 0 = minden modell
        self.active_pred_model = tk.IntVar(value=0)  # 0 = minden predikciós modell
        self.show_correct_only = tk.BooleanVar(value=False)

        # 1) Lekérdezzük az összegző statisztikát
        self.summary = fetch_completed_summary()  # pl.: {"completed_groups": X, "total_simulations": Y, "total_fixtures": Z}
        if not self.summary or not isinstance(self.summary, dict):
            messagebox.showerror("Hiba", "Nem sikerült lekérdezni az összegző statisztikákat.")
            self.destroy()
            return

        # 2) Lekérdezzük a részletes, aggregált szimulációs listát
        self.simulation_data = load_aggregated_simulations()  # pl. list of dict
        if self.simulation_data is None:
            self.simulation_data = []

        # 3) Lekérdezzük a predikciós adatokat
        self.prediction_data = get_all_predictions()
        if self.prediction_data is None:
            self.prediction_data = []

        # Stratégiák és modellek megszámolása
        self.strategy_counts = self.count_by_field("strategy_id", self.simulation_data)
        self.model_counts = self.count_by_field("model_id", self.simulation_data)

        # Predikciós modellek megszámolása és statisztikái
        self.pred_model_counts, self.pred_model_stats = self.get_prediction_stats()

        # 4) GUI elemek létrehozása a szimulációs tabhoz
        self.create_summary_section()  # Fenti 3 szám + stratégiák és modellek száma
        self.create_strategy_buttons()  # Stratégia gombok
        self.create_simulation_treeview()  # A részletes listához TreeView

        # 5) GUI elemek létrehozása a predikciós tabhoz
        self.create_prediction_summary()
        self.create_prediction_model_buttons()
        self.create_prediction_treeview()

        # 6) Lábléc létrehozása mindkét tabhoz
        self.create_footer(self.simulations_frame)
        self.create_footer(self.predictions_frame)

        # 7) Ablak középre igazítása
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        # A create_widgets vagy __init__ végén:
        self.model_comparison_frame = ttk.Frame(self.notebook)


        # Az __init__ metódus végén (a self.geometry() hívás után)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def create_summary_section(self):
        """
        A befejezett csoportok számát, az összes szimulációt, az összes meccset,
        és a stratégia statisztikákat jeleníti meg, optimalizált elrendezéssel
        """
        summary_frame = ttk.LabelFrame(self.simulations_frame, text="Összefoglaló statisztikák", padding=10)
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)

        # A fő mutatók
        items = [
            ("Befejezett mérkőzéscsoportok száma:", str(self.summary.get("completed_groups", 0))),
            ("Összes szimuláció:", str(self.summary.get("total_simulations", 0))),
            ("Összes résztvevő mérkőzés:", str(self.summary.get("total_fixtures", 0))),
        ]

        for i, (label_text, value) in enumerate(items):
            ttk.Label(summary_frame, text=label_text).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Label(summary_frame, text=value, font=("Arial", 12, "bold")).grid(row=i, column=1, padx=10, sticky="w")

        # Stratégia statisztikák kerete - 3 oszlopos elrendezés
        self.strategy_stats_frame = ttk.LabelFrame(summary_frame, text="Stratégia statisztikák", padding=10)
        self.strategy_stats_frame.grid(row=len(items), column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self.strategy_stats_frame.columnconfigure(0, weight=1)
        self.strategy_stats_frame.columnconfigure(1, weight=1)
        self.strategy_stats_frame.columnconfigure(2, weight=2)  # Több hely a diagramnak

        # Alapértelmezett üzenet
        self.strategy_stats_label = ttk.Label(
            self.strategy_stats_frame,
            text="Válasszon stratégiát a részletes statisztikák megjelenítéséhez",
            font=("Arial", 10)
        )
        self.strategy_stats_label.grid(row=0, column=0, sticky="nw", columnspan=2)

        # Részletes statisztikák kerete
        self.detailed_stats_frame = ttk.Frame(self.strategy_stats_frame)
        self.detailed_stats_frame.grid(row=1, column=0, columnspan=2, sticky="nw", pady=(10, 0))
        self.detailed_stats_label = ttk.Label(
            self.detailed_stats_frame,
            text="",
            font=("Arial", 10)
        )
        self.detailed_stats_label.pack(anchor="nw")

        # Diagram keret - jobb oldalon, több helyet foglal
        self.chart_frame = ttk.Frame(self.strategy_stats_frame)
        self.chart_frame.grid(row=0, column=2, rowspan=2, padx=20, pady=10, sticky="nsew")
        ttk.Label(self.chart_frame, text="Válasszon stratégiát a diagram megjelenítéséhez").pack()

    def filter_by_strategy(self, strategy_id):
        """
        Stratégia szűrő alkalmazása és statisztikák megjelenítése, most már diagrammal is
        és kibővített statisztikákkal (min/max nyeremény, veszteség, szórás, medián)
        """
        self.active_strategy.set(strategy_id)

        # Stratégia információk frissítése
        if strategy_id == 0:
            self.strategy_info_var.set(
                f"Összes stratégia megjelenítése ({sum(self.strategy_counts.values())} szimuláció)")
            self.strategy_stats_label.config(
                text="Válasszon stratégiát a részletes statisztikák megjelenítéséhez")
            self.detailed_stats_label.config(text="")
            # Clear the chart if showing all strategies
            if hasattr(self, 'chart_frame'):
                for widget in self.chart_frame.winfo_children():
                    widget.destroy()
                ttk.Label(self.chart_frame, text="Válasszon stratégiát a diagram megjelenítéséhez").pack()
        else:
            # Stratégia nevének lekérése
            strategy_name = next(
                (s['strategy_name'] for s in get_all_strategies() if s['id'] == strategy_id),
                f"Stratégia {strategy_id}"
            )
            count = self.strategy_counts.get(strategy_id, 0)
            self.strategy_info_var.set(f"{strategy_name} kiválasztva ({count} szimuláció)")

            # Stratégia statisztikák kiszámítása
            strategy_sims = [s for s in self.simulation_data if s.get('strategy_id') == strategy_id]
            total_profit = sum(s.get('total_profit_loss', 0) for s in strategy_sims)
            winning_sims = [s for s in strategy_sims if s.get('total_profit_loss', 0) > 0]
            losing_sims = [s for s in strategy_sims if s.get('total_profit_loss', 0) < 0]

            win_count = len(winning_sims)
            win_profit = sum(s.get('total_profit_loss', 0) for s in winning_sims)
            loss_count = len(losing_sims)
            loss_profit = sum(s.get('total_profit_loss', 0) for s in losing_sims)

            # Kibővített statisztikák számítása
            all_profits = [s.get('total_profit_loss', 0) for s in strategy_sims]
            win_profits = [s.get('total_profit_loss', 0) for s in winning_sims]
            loss_profits = [abs(s.get('total_profit_loss', 0)) for s in losing_sims]  # Abszolút érték

            # Általános statisztikák
            profit_std_dev = statistics.stdev(all_profits) if len(all_profits) > 1 else 0
            profit_median = statistics.median(all_profits) if all_profits else 0

            # Nyereségek statisztikái
            win_std_dev = statistics.stdev(win_profits) if len(win_profits) > 1 else 0
            win_median = statistics.median(win_profits) if win_profits else 0

            # Veszteségek statisztikái (abszolút értékben)
            loss_std_dev = statistics.stdev(loss_profits) if len(loss_profits) > 1 else 0
            loss_median = statistics.median(loss_profits) if loss_profits else 0

            # Min/max értékek számítása
            min_win = min(win_profits) if win_profits else 0
            max_win = max(win_profits) if win_profits else 0
            min_loss = min(loss_profits) if loss_profits else 0
            max_loss = max(loss_profits) if loss_profits else 0

            # Statisztikák formázása
            stats_text = (
                f"{strategy_name} statisztikák:\n"
                f"Összes szimuláció: {count}\n"
                f"Nyerő szimulációk: {win_count} (Átlag nyereség: {win_profit / win_count if win_count else 0:.2f} Ft)\n"
                f"Vesztes szimulációk: {loss_count} (Átlag veszteség: {loss_profit / loss_count if loss_count else 0:.2f} Ft)\n"
                f"Teljes profit: {total_profit:.2f} Ft\n"
                f"Nyertes arány: {win_count / (win_count + loss_count) * 100 if (win_count + loss_count) > 0 else 0:.1f}%"
            )

            self.strategy_stats_label.config(text=stats_text)

            # Részletes statisztikák formázása (új)
            detailed_stats_text = (
                f"Részletes statisztikák:\n"
                f"Minimum nyeremény: {min_win:.2f} Ft\n"
                f"Maximum nyeremény: {max_win:.2f} Ft\n"
                f"Minimum veszteség: {min_loss:.2f} Ft\n"
                f"Maximum veszteség: {max_loss:.2f} Ft\n"
                f"Profit/veszteség együttes szórása: {profit_std_dev:.2f} Ft\n"
                f"Profit/veszteség együttes mediánja: {profit_median:.2f} Ft\n"
                f"Nyereségek szórása: {win_std_dev:.2f} Ft\n"
                f"Nyereségek mediánja: {win_median:.2f} Ft\n"
                f"Veszteségek szórása: {loss_std_dev:.2f} Ft\n"
                f"Veszteségek mediánja: {loss_median:.2f} Ft"
            )

            self.detailed_stats_label.config(text=detailed_stats_text)

            # Diagram frissítése
            self.update_strategy_chart(win_count, loss_count, strategy_name)

        # Táblázat frissítése
        self.populate_treeview()

    def create_strategy_buttons(self):
        """
        Stratégia gombok létrehozása, amelyekre kattintva szűrhetjük a táblázatot
        Most már csak a stratégia neveket jeleníti meg a gombokon
        """
        # Stratégia gombok kerete
        buttons_frame = ttk.LabelFrame(self.simulations_frame, text="Stratégiák szűrése", padding=10)
        buttons_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        buttons_frame.columnconfigure(0, weight=1)

        # Gombok kerete, hogy középre rendezzük őket
        btn_container = ttk.Frame(buttons_frame)
        btn_container.grid(row=0, column=0)

        # "Összes" gomb
        all_btn = ttk.Button(btn_container, text="Összes stratégia",
                             command=lambda: self.filter_by_strategy(0))
        all_btn.grid(row=0, column=0, padx=5, pady=5)

        # Stratégia gombok - csak a neveket jelenítjük meg
        strategies = get_all_strategies()
        for i, strategy in enumerate(strategies):
            btn = ttk.Button(btn_container, text=strategy['strategy_name'],
                             command=lambda s=strategy['id']: self.filter_by_strategy(s))
            btn.grid(row=0, column=i + 1, padx=5, pady=5)

        # Kijelzés a kiválasztott stratégiához
        self.strategy_info_var = tk.StringVar(value="Összes stratégia megjelenítése")
        ttk.Label(buttons_frame, textvariable=self.strategy_info_var,
                  font=("Arial", 11, "bold")).grid(row=1, column=0, pady=5)

    def create_prediction_summary(self):
        """
        A predikciós statisztikákat jeleníti meg
        """
        summary_frame = ttk.LabelFrame(self.predictions_frame, text="Predikciós statisztikák", padding=10)
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Összesített statisztikák
        self.total_pred_label = ttk.Label(summary_frame, text="Összes predikció: 0")
        self.total_pred_label.grid(row=0, column=0, sticky="w", pady=3)

        self.correct_pred_label = ttk.Label(summary_frame, text="Helyes predikciók: 0")
        self.correct_pred_label.grid(row=1, column=0, sticky="w", pady=3)

        self.accuracy_label = ttk.Label(summary_frame, text="Pontosság: 0%")
        self.accuracy_label.grid(row=2, column=0, sticky="w", pady=3)

        # Kiválasztott modell statisztikái (kezdetben üres)
        self.selected_model_frame = ttk.Frame(summary_frame)
        self.selected_model_frame.grid(row=0, column=1, rowspan=3, padx=20)

        self.selected_model_label = ttk.Label(self.selected_model_frame, text="Kiválasztott modell: -",
                                              font=("Arial", 10, "bold"))
        self.selected_model_label.grid(row=0, column=0, sticky="w")

        self.model_total_label = ttk.Label(self.selected_model_frame, text="Összes: 0")
        self.model_total_label.grid(row=1, column=0, sticky="w")

        self.model_correct_label = ttk.Label(self.selected_model_frame, text="Helyes: 0")
        self.model_correct_label.grid(row=2, column=0, sticky="w")

        self.model_accuracy_label = ttk.Label(self.selected_model_frame, text="Pontosság: 0%")
        self.model_accuracy_label.grid(row=3, column=0, sticky="w")

        # Helyesség szűrő
        filter_frame = ttk.Frame(summary_frame)
        filter_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # A create_prediction_summary metódusban
        self.cb_show_correct = ttk.Checkbutton(
            filter_frame,
            text="Csak a helyes predikciók mutatása"
        )
        self.cb_show_correct.grid(row=0, column=0, sticky="w")
        self.cb_show_correct.config(command=lambda: self.on_filter_change(self.cb_show_correct.instate(['selected'])))

    def on_filter_change(self, state):
        """Közvetlenül a widget állapotát használjuk"""
        print(f"Filter state: {state}")
        if state:
            self.show_correct_only.set(True)
        else:
            self.show_correct_only.set(False)
        self.filter_predictions()

    def create_prediction_model_buttons(self):
        """
        Predikciós modell gombok létrehozása
        """
        buttons_frame = ttk.LabelFrame(self.predictions_frame, text="Predikciós modellek", padding=10)
        buttons_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        buttons_frame.columnconfigure(0, weight=1)

        btn_container = ttk.Frame(buttons_frame)
        btn_container.grid(row=0, column=0)

        # "Összes" gomb
        all_btn = ttk.Button(btn_container, text="Összes modell",
                             command=lambda: self.filter_by_pred_model(0))
        all_btn.grid(row=0, column=0, padx=5, pady=5)

        # Modell gombok - csak a neveket jelenítjük meg
        for i, mid in enumerate(sorted(self.pred_model_counts.keys())):
            model_label = self.model_names.get(mid, f"Modell {mid}")
            btn = ttk.Button(btn_container, text=model_label,
                             command=lambda m=mid: self.filter_by_pred_model(m))
            btn.grid(row=0, column=i + 1, padx=5, pady=5)

    def filter_by_pred_model(self, model_id):
        """
        Predikciós modell szűrő alkalmazása
        """
        self.active_pred_model.set(model_id)
        self.update_prediction_stats(model_id)
        self.populate_prediction_treeview()

    def filter_predictions(self):
        """Predikciók szűrése a kiválasztott feltételek alapján"""
        # Mindig friss adatokkal dolgozunk
        self.prediction_data = get_all_predictions() or []
        self.populate_prediction_treeview()
        self.update_prediction_stats(self.active_pred_model.get())

    def create_simulation_treeview(self):
        """
        A részletes, befejezett szimulációk listája (csoportnév, stratégia, modell, profit, dátum).
        """
        tree_frame = ttk.LabelFrame(self.simulations_frame, text="Részletes eredmények", padding=10)
        tree_frame.grid(row=3, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ("id", "sim_name", "strategy", "profit", "date")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.tree.heading("id", text="Sim ID")
        self.tree.heading("sim_name", text="Csoport neve")
        self.tree.heading("strategy", text="Stratégia ID")
        self.tree.heading("profit", text="Total Profit/Loss")
        self.tree.heading("date", text="Dátum")

        self.tree.column("id", width=60, anchor="center", minwidth=50)
        self.tree.column("sim_name", width=180, minwidth=120)
        self.tree.column("strategy", width=100, anchor="center", minwidth=80)
        self.tree.column("profit", width=150, anchor="e", minwidth=120)
        self.tree.column("date", width=150, minwidth=120)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Töltsük fel adatokkal
        self.populate_treeview()

        # Dupla kattintás
        self.tree.bind("<Double-1>", self.show_simulation_details)

    def create_prediction_treeview(self):
        """
        A modell predikciók részletes listája
        """
        tree_frame = ttk.LabelFrame(self.predictions_frame, text="Predikciós eredmények", padding=10)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ("id", "fixture_id", "model", "outcome", "probability", "group_id", "correct")
        self.pred_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.pred_tree.heading("id", text="Pred ID")
        self.pred_tree.heading("fixture_id", text="Mérkőzés ID")
        self.pred_tree.heading("model", text="Modell")
        self.pred_tree.heading("outcome", text="Predikált kimenet")
        self.pred_tree.heading("probability", text="Valószínűség")
        self.pred_tree.heading("group_id", text="Csoport ID")
        self.pred_tree.heading("correct", text="Helyes?")

        self.pred_tree.column("id", width=60, anchor="center", minwidth=50)
        self.pred_tree.column("fixture_id", width=100, anchor="center", minwidth=80)
        self.pred_tree.column("model", width=120, anchor="center", minwidth=100)
        self.pred_tree.column("outcome", width=120, anchor="center", minwidth=100)
        self.pred_tree.column("probability", width=100, anchor="e", minwidth=80)
        self.pred_tree.column("group_id", width=100, anchor="center", minwidth=80)
        self.pred_tree.column("correct", width=80, anchor="center", minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.pred_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.pred_tree.xview)
        self.pred_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.pred_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Töltsük fel adatokkal
        self.populate_prediction_treeview()

        # Dupla kattintás
        self.pred_tree.bind("<Double-1>", self.show_prediction_details)

    def populate_treeview(self):
        """
        A TreeView feltöltése a befejezett szimulációkról kapott listából, szűrés alapján.
        """
        # Minden eddigit törlünk
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Lekérdezzük az aktív szűrőket
        active_sid = self.active_strategy.get()
        active_mid = self.active_model.get()

        for sim in self.simulation_data:
            sid = sim.get("strategy_id", 0)
            mid = sim.get("model_id", 0)

            # Szűrők alkalmazása - csak azokat mutatjuk, amik mindkét szűrőnek megfelelnek
            if (active_sid != 0 and sid != active_sid) or (active_mid != 0 and mid != active_mid):
                continue

            profit = sim.get("total_profit_loss", 0)
            # formázzuk a profitot, pl. 120.50 Ft
            if isinstance(profit, (int, float)):
                formatted_profit = f"{profit:,.2f} Ft"
            else:
                formatted_profit = str(profit)

            date_str = sim.get("simulation_date", "")
            # Ha string, marad, ha datetime, konvertálhatjuk
            if isinstance(date_str, datetime):
                formatted_date = date_str.strftime("%Y-%m-%d %H:%M")
            else:
                formatted_date = date_str  # pl. string

            self.tree.insert(
                "",
                "end",
                values=(
                    sim.get("id", ""),
                    sim.get("sim_name", ""),
                    sim.get("strategy_id", ""),
                    formatted_profit,
                    formatted_date
                )
            )

    def populate_prediction_treeview(self):
        """
        A TreeView feltöltése a predikciós adatokból, szűrés alapján.
        """
        # Minden eddigit törlünk
        for item in self.pred_tree.get_children():
            self.pred_tree.delete(item)

        # Lekérdezzük az aktív szűrőket
        active_model_id = self.active_pred_model.get()
        show_correct_only = self.show_correct_only.get()  # Itt használjuk a BooleanVar értékét

        for pred in self.prediction_data:
            mid = pred.get("model_id", 0)
            is_correct = pred.get("was_correct", 0)

            # Modell szűrés
            if active_model_id != 0 and mid != active_model_id:
                continue

            # Helyesség szűrés - csak akkor szűrünk, ha a show_correct_only True
            if show_correct_only and not is_correct:
                continue

            model_name = self.model_names.get(mid, str(mid))
            probability = pred.get("probability", 0)
            formatted_prob = f"{probability:.2f}" if isinstance(probability, (int, float)) else str(probability)
            correct_text = "Igen ✓" if is_correct == 1 else "Nem ✗"
            row_tags = ("correct",) if is_correct == 1 else ("incorrect",)

            self.pred_tree.insert(
                "",
                "end",
                values=(
                    pred.get("id", ""),
                    pred.get("fixture_id", ""),
                    model_name,
                    pred.get("predicted_outcome", ""),
                    formatted_prob,
                    pred.get("match_group_id", ""),
                    correct_text
                ),
                tags=row_tags
            )

        # Színek beállítása
        self.pred_tree.tag_configure('correct', background='#e6ffe6')
        self.pred_tree.tag_configure('incorrect', background='#ffe6e6')

    def show_simulation_details(self, event):
        """
        Ha duplán kattint a felhasználó egy szimuláción, megjelenít
        egy új ablakot a szimulációról részletes adatokkal.
        """
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        values = self.tree.item(item, "values")
        sim_id = values[0]
        sim_name = values[1]
        strategy_id = values[2]
        model_id = values[3]
        profit = values[4]
        date = values[5]

        # Részletes ablak létrehozása
        details_window = tk.Toplevel(self)
        details_window.title(f"Szimuláció részletei: {sim_id}")
        details_window.geometry("600x500")
        details_window.grab_set()  # Modális ablak

        # Reszponzív elrendezés
        details_window.columnconfigure(0, weight=1)
        details_window.rowconfigure(1, weight=1)  # A statisztikák kerete nyújtható

        # Alapinformációk keret
        info_frame = ttk.LabelFrame(details_window, text="Alapinformációk", padding=10)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # Alapinformációk megjelenítése
        ttk.Label(info_frame, text="Szimuláció azonosító:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(info_frame, text=sim_id, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=10,
                                                                            pady=2)

        ttk.Label(info_frame, text="Csoport neve:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(info_frame, text=sim_name, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky="w", padx=10,
                                                                              pady=2)

        # Stratégia nevének lekérdezése
        strategy_name = next(
            (s['strategy_name'] for s in get_all_strategies() if s['id'] == int(strategy_id)),
            f"Stratégia {strategy_id}"
        )

        ttk.Label(info_frame, text="Stratégia:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(info_frame, text=f"{strategy_name} (ID: {strategy_id})", font=("Arial", 10, "bold")).grid(row=2,
                                                                                                            column=1,
                                                                                                            sticky="w",
                                                                                                            padx=10,
                                                                                                            pady=2)

        # Modell nevének lekérdezése
        model_name = self.model_names.get(int(model_id), f"Modell {model_id}")

        ttk.Label(info_frame, text="Modell:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(info_frame, text=f"{model_name} (ID: {model_id})", font=("Arial", 10, "bold")).grid(row=3, column=1,
                                                                                                      sticky="w",
                                                                                                      padx=10, pady=2)

        ttk.Label(info_frame, text="Teljes profit/veszteség:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Label(info_frame, text=profit, font=("Arial", 10, "bold")).grid(row=4, column=1, sticky="w", padx=10,
                                                                            pady=2)

        ttk.Label(info_frame, text="Dátum:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Label(info_frame, text=date, font=("Arial", 10, "bold")).grid(row=5, column=1, sticky="w", padx=10, pady=2)

        # Részletes statisztikák keret
        stats_frame = ttk.LabelFrame(details_window, text="Stratégia részletes statisztikái", padding=10)
        stats_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Lekérjük a stratégiához tartozó összes szimulációt
        strategy_sims = [s for s in self.simulation_data if s.get('strategy_id') == int(strategy_id)]

        # Statisztikák kiszámítása
        if strategy_sims:
            # Nyerő/vesztes szimulációk szétválasztása
            winning_sims = [s for s in strategy_sims if s.get('total_profit_loss', 0) > 0]
            losing_sims = [s for s in strategy_sims if s.get('total_profit_loss', 0) < 0]

            # Profit/veszteség adatok gyűjtése
            all_profits = [s.get('total_profit_loss', 0) for s in strategy_sims]
            win_profits = [s.get('total_profit_loss', 0) for s in winning_sims]
            loss_profits = [s.get('total_profit_loss', 0) for s in losing_sims]

            # Szórás és medián számítása
            profit_std_dev = statistics.stdev(all_profits) if len(all_profits) > 1 else 0
            profit_median = statistics.median(all_profits) if all_profits else 0

            # Min/max értékek számítása
            min_win = min(win_profits) if win_profits else 0
            max_win = max(win_profits) if win_profits else 0
            min_loss = min(loss_profits, key=abs) if loss_profits else 0
            max_loss = max(loss_profits, key=abs) if loss_profits else 0

            # Általános statisztikák
            ttk.Label(stats_frame, text=f"Összes szimuláció:", font=("Arial", 11)).grid(row=0, column=0, sticky="w",
                                                                                        pady=5)
            ttk.Label(stats_frame, text=f"{len(strategy_sims)}", font=("Arial", 11, "bold")).grid(row=0, column=1,
                                                                                                  sticky="w", padx=10,
                                                                                                  pady=5)

            ttk.Label(stats_frame, text=f"Nyerő szimulációk:", font=("Arial", 11)).grid(row=1, column=0, sticky="w",
                                                                                        pady=5)
            ttk.Label(stats_frame, text=f"{len(winning_sims)}", font=("Arial", 11, "bold")).grid(row=1, column=1,
                                                                                                 sticky="w", padx=10,
                                                                                                 pady=5)

            ttk.Label(stats_frame, text=f"Vesztes szimulációk:", font=("Arial", 11)).grid(row=2, column=0, sticky="w",
                                                                                          pady=5)
            ttk.Label(stats_frame, text=f"{len(losing_sims)}", font=("Arial", 11, "bold")).grid(row=2, column=1,
                                                                                                sticky="w", padx=10,
                                                                                                pady=5)

            # Nyereség statisztikák
            ttk.Label(stats_frame, text="Nyereség statisztikák:", font=("Arial", 11, "bold")).grid(row=3, column=0,
                                                                                                   columnspan=2,
                                                                                                   sticky="w",
                                                                                                   pady=(15, 5))

            ttk.Label(stats_frame, text=f"Minimum nyeremény:").grid(row=4, column=0, sticky="w", pady=3)
            ttk.Label(stats_frame, text=f"{min_win:.2f} Ft", font=("Arial", 10, "bold")).grid(row=4, column=1,
                                                                                              sticky="w", padx=10,
                                                                                              pady=3)

            ttk.Label(stats_frame, text=f"Maximum nyeremény:").grid(row=5, column=0, sticky="w", pady=3)
            ttk.Label(stats_frame, text=f"{max_win:.2f} Ft", font=("Arial", 10, "bold")).grid(row=5, column=1,
                                                                                              sticky="w", padx=10,
                                                                                              pady=3)

            # Veszteség statisztikák
            ttk.Label(stats_frame, text="Veszteség statisztikák:", font=("Arial", 11, "bold")).grid(row=6, column=0,
                                                                                                    columnspan=2,
                                                                                                    sticky="w",
                                                                                                    pady=(15, 5))

            ttk.Label(stats_frame, text=f"Minimum veszteség:").grid(row=7, column=0, sticky="w", pady=3)
            ttk.Label(stats_frame, text=f"{min_loss:.2f} Ft", font=("Arial", 10, "bold")).grid(row=7, column=1,
                                                                                               sticky="w", padx=10,
                                                                                               pady=3)

            ttk.Label(stats_frame, text=f"Maximum veszteség:").grid(row=8, column=0, sticky="w", pady=3)
            ttk.Label(stats_frame, text=f"{max_loss:.2f} Ft", font=("Arial", 10, "bold")).grid(row=8, column=1,
                                                                                               sticky="w", padx=10,
                                                                                               pady=3)

            # Egyéb statisztikák
            ttk.Label(stats_frame, text="Egyéb statisztikák:", font=("Arial", 11, "bold")).grid(row=9, column=0,
                                                                                                columnspan=2,
                                                                                                sticky="w",
                                                                                                pady=(15, 5))

            ttk.Label(stats_frame, text=f"Profit szórása:").grid(row=10, column=0, sticky="w", pady=3)
            ttk.Label(stats_frame, text=f"{profit_std_dev:.2f} Ft", font=("Arial", 10, "bold")).grid(row=10, column=1,
                                                                                                     sticky="w",
                                                                                                     padx=10, pady=3)

            ttk.Label(stats_frame, text=f"Profit mediánja:").grid(row=11, column=0, sticky="w", pady=3)
            ttk.Label(stats_frame, text=f"{profit_median:.2f} Ft", font=("Arial", 10, "bold")).grid(row=11, column=1,
                                                                                                    sticky="w", padx=10,
                                                                                                    pady=3)

            # Statisztikai diagram készítése
            self.create_detail_chart(details_window, winning_sims, losing_sims, strategy_name)
        else:
            ttk.Label(stats_frame, text="Nincs elérhető adat ehhez a stratégiához.").grid(row=0, column=0, pady=10)

        # Bezárás gomb
        ttk.Button(details_window, text="Bezárás", command=details_window.destroy).grid(row=2, column=0, pady=10)

    def create_detail_chart(self, parent, winning_sims, losing_sims, strategy_name):
        """
        Létrehoz egy részletes diagramot a nyereség/veszteség eloszlásról
        nagyobb méretben és jobb elrendezéssel
        """
        # Chart keret
        chart_frame = ttk.LabelFrame(parent, text="Profit/Veszteség eloszlás", padding=10)
        chart_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.columnconfigure(0, weight=1)

        if winning_sims or losing_sims:
            # Adatok gyűjtése a hisztogramhoz
            win_profits = [s.get('total_profit_loss', 0) for s in winning_sims]
            loss_profits = [s.get('total_profit_loss', 0) for s in losing_sims]

            # Nagyobb diagram létrehozása
            fig, ax = plt.subplots(figsize=(6, 5))  # Növelt méret

            # Ha vannak nyereségek
            if win_profits:
                ax.hist(win_profits, bins=min(10, len(win_profits)),
                        alpha=0.7, color='green', label='Nyereség')

            # Ha vannak veszteségek
            if loss_profits:
                ax.hist(loss_profits, bins=min(10, len(loss_profits)),
                        alpha=0.7, color='red', label='Veszteség')

            ax.set_title(f'{strategy_name} profit/veszteség eloszlás', fontsize=12)
            ax.set_xlabel('Profit/Veszteség (Ft)', fontsize=11)
            ax.set_ylabel('Gyakoriság', fontsize=11)
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)

            # Beágyazás a Tkinter ablakba
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

            # Navigációs eszköztár hozzáadása
            toolbar = NavigationToolbar2Tk(canvas, chart_frame)
            toolbar.update()
            toolbar.grid(row=1, column=0, sticky="ew")
        else:
            ttk.Label(chart_frame, text="Nincs elegendő adat a diagram készítéséhez").grid(row=0, column=0, pady=20)

    def count_by_field(self, field_name, data_list):
        """
        Megszámolja, hogy a megadott listában hány elem van
        minden egyedi érték szerint a megadott mezőben.
        Eredmény: pl. {1: 10, 2: 12, 3: 15, ...}
        """
        counts = {}
        for item in data_list:
            value = item.get(field_name, 0)
            counts[value] = counts.get(value, 0) + 1
        return counts

    def get_prediction_stats(self):
        """
        Modell szintű predikciós statisztikák kiszámítása:
        - predikciók száma modell szerint
        - helyes predikciók aránya (pontosság) modell szerint
        - valószínűségi statisztikák
        """
        counts = {}
        stats = {}

        for pred in self.prediction_data:
            model_id = pred.get("model_id", 0)
            was_correct = pred.get("was_correct", 0)
            probability = pred.get("probability", 0)

            # Növeljük a számlálót
            if model_id not in counts:
                counts[model_id] = 0
                stats[model_id] = {
                    "correct": 0,
                    "win_probs": [],  # Győztes tippek valószínűségei
                    "loss_probs": []  # Vesztes tippek valószínűségei
                }

            counts[model_id] += 1
            if was_correct == 1:
                stats[model_id]["correct"] += 1
                stats[model_id]["win_probs"].append(probability)
            else:
                stats[model_id]["loss_probs"].append(probability)

        # Számítsuk ki a statisztikákat
        for model_id in stats:
            total = counts[model_id]
            correct = stats[model_id]["correct"]
            accuracy = (correct / total) * 100 if total > 0 else 0.0
            stats[model_id]["accuracy"] = accuracy

            # Győztes tippek valószínűségei
            win_probs = stats[model_id]["win_probs"]
            if win_probs:
                stats[model_id]["win_prob_avg"] = statistics.mean(win_probs)
                stats[model_id]["win_prob_std"] = statistics.stdev(win_probs) if len(win_probs) > 1 else 0
                stats[model_id]["win_prob_median"] = statistics.median(win_probs)
                stats[model_id]["max_win_prob"] = max(win_probs)
                stats[model_id]["min_win_prob"] = min(win_probs)
            else:
                stats[model_id].update({
                    "win_prob_avg": 0,
                    "win_prob_std": 0,
                    "win_prob_median": 0,
                    "max_win_prob": 0,
                    "min_win_prob": 0
                })

            # Vesztes tippek valószínűségei
            loss_probs = stats[model_id]["loss_probs"]
            if loss_probs:
                stats[model_id]["loss_prob_avg"] = statistics.mean(loss_probs)
                stats[model_id]["loss_prob_std"] = statistics.stdev(loss_probs) if len(loss_probs) > 1 else 0
                stats[model_id]["loss_prob_median"] = statistics.median(loss_probs)
                stats[model_id]["max_loss_prob"] = max(loss_probs)
                stats[model_id]["min_loss_prob"] = min(loss_probs)
            else:
                stats[model_id].update({
                    "loss_prob_avg": 0,
                    "loss_prob_std": 0,
                    "loss_prob_median": 0,
                    "max_loss_prob": 0,
                    "min_loss_prob": 0
                })

        return counts, stats

    def show_prediction_details(self, event):
        """
        Megjeleníti a kiválasztott predikció részleteit egy új ablakban.
        """
        sel = self.pred_tree.selection()
        if not sel:
            return
        item = sel[0]
        values = self.pred_tree.item(item, "values")

        # Részletes ablak létrehozása
        details_window = tk.Toplevel(self)
        details_window.title(f"Predikció részletei: {values[0]}")
        details_window.geometry("500x300")

        # Információk megjelenítése
        info_frame = ttk.LabelFrame(details_window, text="Predikció adatai", padding=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        labels = [
            ("Predikció ID:", values[0]),
            ("Mérkőzés ID:", values[1]),
            ("Modell:", values[2]),
            ("Predikált kimenet:", values[3]),
            ("Valószínűség:", values[4]),
            ("Csoport ID:", values[5]),
            ("Helyes predikció:", values[6])
        ]

        for i, (label_text, value) in enumerate(labels):
            ttk.Label(info_frame, text=label_text).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Label(info_frame, text=value, font=("Arial", 10, "bold")).grid(row=i, column=1, sticky="w", padx=10,
                                                                               pady=2)

        ttk.Button(details_window, text="Bezárás", command=details_window.destroy).pack(pady=10)

    def update_prediction_stats(self, model_id):
        """
        Frissíti a predikciós statisztikákat a kiválasztott modell alapján,
        most már a valószínűségi és odds statisztikákkal együtt.
        """
        # Mindig friss adatokkal dolgozunk
        self.prediction_data = get_all_predictions() or []
        self.pred_model_counts, self.pred_model_stats = self.get_prediction_stats()

        # Odds statisztikák lekérdezése
        self.odds_stats = get_models_odds_statistics()

        total = len(self.prediction_data)
        correct = sum(1 for p in self.prediction_data if p.get("was_correct", 0) == 1)
        accuracy = (correct / total) * 100 if total > 0 else 0

        # Összesített statisztikák frissítése
        self.total_pred_label.config(text=f"Összes predikció: {total}")
        self.correct_pred_label.config(text=f"Helyes predikciók: {correct}")
        self.accuracy_label.config(text=f"Pontosság: {accuracy:.1f}%")

        # Modellspecifikus statisztikák frissítése
        if model_id == 0:
            self.selected_model_label.config(text="Kiválasztott modell: Összes modell")
            self.model_total_label.config(text="Összes: -")
            self.model_correct_label.config(text="Helyes: -")
            self.model_accuracy_label.config(text="Pontosság: -")

            # Összesített valószínűségi statisztikák
            all_win_probs = []
            all_loss_probs = []
            for model_stats in self.pred_model_stats.values():
                all_win_probs.extend(model_stats["win_probs"])
                all_loss_probs.extend(model_stats["loss_probs"])

            if all_win_probs:
                win_avg = statistics.mean(all_win_probs)
                win_std = statistics.stdev(all_win_probs) if len(all_win_probs) > 1 else 0
                win_median = statistics.median(all_win_probs)
                max_win_prob = max(all_win_probs)
                min_win_prob = min(all_win_probs)
            else:
                win_avg = win_std = win_median = max_win_prob = min_win_prob = 0

            if all_loss_probs:
                loss_avg = statistics.mean(all_loss_probs)
                loss_std = statistics.stdev(all_loss_probs) if len(all_loss_probs) > 1 else 0
                loss_median = statistics.median(all_loss_probs)
                max_loss_prob = max(all_loss_probs)
                min_loss_prob = min(all_loss_probs)
            else:
                loss_avg = loss_std = loss_median = max_loss_prob = min_loss_prob = 0

            # Összesített odds statisztikák
            all_win_odds = [stats.get('win_odds_avg', 0) for stats in self.odds_stats.values() if
                            stats.get('win_odds_avg', 0) > 0]
            all_loss_odds = [stats.get('loss_odds_avg', 0) for stats in self.odds_stats.values() if
                             stats.get('loss_odds_avg', 0) > 0]
            all_total_odds = [stats.get('total_odds_avg', 0) for stats in self.odds_stats.values() if
                              stats.get('total_odds_avg', 0) > 0]

            win_odds_avg = statistics.mean(all_win_odds) if all_win_odds else 0
            loss_odds_avg = statistics.mean(all_loss_odds) if all_loss_odds else 0
            total_odds_avg = statistics.mean(all_total_odds) if all_total_odds else 0

            # További statisztikák megjelenítése
            additional_stats = (
                f"\nTalálati arány: {accuracy:.1f}%\n"
                f"Legnagyobb valószínűségű győztes tipp: {max_win_prob:.2f}\n"
                f"Legkisebb valószínűségű győztes tipp: {min_win_prob:.2f}\n"
                f"Legnagyobb valószínűségű vesztes tipp: {max_loss_prob:.2f}\n"
                f"Legkisebb valószínűségű vesztes tipp: {min_loss_prob:.2f}\n"
                f"Győztes tippek valószínűsége - Átlag: {win_avg:.2f}, Szórás: {win_std:.2f}, Medián: {win_median:.2f}\n"
                f"Vesztes tippek valószínűsége - Átlag: {loss_avg:.2f}, Szórás: {loss_std:.2f}, Medián: {loss_median:.2f}\n"
                f"\nOdds statisztikák:\n"
                f"Átlagos odds: {total_odds_avg:.2f}\n"
                f"Győztes tippek átlagos odds: {win_odds_avg:.2f}\n"
                f"Vesztes tippek átlagos odds: {loss_odds_avg:.2f}"
            )

        else:
            model_data = [p for p in self.prediction_data if p.get("model_id", 0) == model_id]
            model_total = len(model_data)
            model_correct = sum(1 for p in model_data if p.get("was_correct", 0) == 1)
            model_accuracy = (model_correct / model_total) * 100 if model_total > 0 else 0

            model_name = self.model_names.get(model_id, f"Modell {model_id}")
            self.selected_model_label.config(text=f"Kiválasztott modell: {model_name}")
            self.model_total_label.config(text=f"Összes: {model_total}")
            self.model_correct_label.config(text=f"Helyes: {model_correct}")
            self.model_accuracy_label.config(text=f"Pontosság: {model_accuracy:.1f}%")

            # Modellspecifikus valószínűségi statisztikák
            model_stats = self.pred_model_stats.get(model_id, {})

            # Modellspecifikus odds statisztikák
            odds_data = self.odds_stats.get(model_id, {})
            win_odds_avg = odds_data.get('win_odds_avg', 0)
            loss_odds_avg = odds_data.get('loss_odds_avg', 0)
            total_odds_avg = odds_data.get('total_odds_avg', 0)

            additional_stats = (
                f"\nTalálati arány: {model_accuracy:.1f}%\n"
                f"Legnagyobb valószínűségű győztes tipp: {model_stats.get('max_win_prob', 0):.2f}\n"
                f"Legkisebb valószínűségű győztes tipp: {model_stats.get('min_win_prob', 0):.2f}\n"
                f"Legnagyobb valószínűségű vesztes tipp: {model_stats.get('max_loss_prob', 0):.2f}\n"
                f"Legkisebb valószínűségű vesztes tipp: {model_stats.get('min_loss_prob', 0):.2f}\n"
                f"Győztes tippek valószínűsége - Átlag: {model_stats.get('win_prob_avg', 0):.2f}, "
                f"Szórás: {model_stats.get('win_prob_std', 0):.2f}, Medián: {model_stats.get('win_prob_median', 0):.2f}\n"
                f"Vesztes tippek valószínűsége - Átlag: {model_stats.get('loss_prob_avg', 0):.2f}, "
                f"Szórás: {model_stats.get('loss_prob_std', 0):.2f}, Medián: {model_stats.get('loss_prob_median', 0):.2f}\n"
                f"\nOdds statisztikák:\n"
                f"Átlagos odds: {total_odds_avg:.2f}\n"
                f"Győztes tippek átlagos odds: {win_odds_avg:.2f}\n"
                f"Vesztes tippek átlagos odds: {loss_odds_avg:.2f}"
            )

        # További statisztikák megjelenítése
        if hasattr(self, 'additional_stats_label'):
            self.additional_stats_label.config(text=additional_stats)
        else:
            self.additional_stats_label = ttk.Label(
                self.selected_model_frame,
                text=additional_stats,
                font=("Arial", 9)
            )
            self.additional_stats_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

    def update_strategy_chart(self, win_count, loss_count, strategy_name):
        """
        Frissíti a stratégia statisztikákhoz tartozó diagramot,
        optimalizálva a megjelenítést a címek és jelmagyarázat számára.
        """
        # Töröljük a korábbi diagramot
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if win_count + loss_count == 0:
            ttk.Label(self.chart_frame, text="Nincs adat a diagramhoz").pack()
            return

        # Nagyobb ábra létrehozása és jobb elrendezés
        fig = plt.figure(figsize=(7, 6), dpi=100)  # Növelt méret
        ax = fig.add_subplot(111)

        # Stílusbeállítások
        plt.rcParams.update({
            'font.size': 12,  # Növelt betűméret
            'axes.titlesize': 13,
            'axes.labelsize': 12,
            'legend.fontsize': 12,
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'axes.grid': True,
            'grid.alpha': 0.3
        })

        # Adatok előkészítése
        labels = ['Nyerő szimulációk', 'Vesztes szimulációk']
        sizes = [win_count, loss_count]
        colors = ['#4CAF50', '#F44336']
        explode = (0.03, 0)  # Enyhe kiemelés

        # Diagram rajzolása
        pie_result = ax.pie(
            sizes,
            explode=explode,
            colors=colors,
            startangle=90,
            shadow=True,
            wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
            textprops={'color': 'black', 'fontsize': 12},  # Növelt betűméret
            autopct='%1.1f%%'
        )

        # A visszatérési értékek kezelése
        wedges = pie_result[0]
        texts = pie_result[1]
        if len(pie_result) > 2:
            autotexts = pie_result[2]
        else:
            autotexts = [text for text in texts if '%' in text.get_text()]

        # Cím beállítása
        title = ax.set_title(
            f'{strategy_name}\nNyerő/Vesztes szimulációk aránya',
            fontsize=14,  # Növelt cím méret
            fontweight='bold',
            pad=25,
            loc='center'
        )
        title.set_y(1.05)  # Finomhangolt pozíció

        # Jelmagyarázat (legend) optimalizálása
        legend = ax.legend(
            wedges,
            labels,
            title="Jelmagyarázat:",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            frameon=True,
            shadow=True,
            edgecolor='black'
        )
        legend.get_title().set_fontweight('bold')
        legend.get_frame().set_alpha(0.9)

        # Százalékos értékek formázása
        for autotext in autotexts:
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold')

        # Középre igazítás
        ax.axis('equal')

        # Szünet a diagram körül
        plt.tight_layout(pad=3)

        # Beágyazás a Tkinter ablakba
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Navigációs eszköztár hozzáadása
        toolbar = NavigationToolbar2Tk(canvas, self.chart_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_footer(self, parent_frame):
        """
        Lábléc létrehozása az ablak aljára, mindkét tabhoz.
        """
        footer_frame = ttk.Frame(parent_frame)
        footer_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(5, 10))

        # Dátum és idő megjelenítése
        self.time_label = ttk.Label(footer_frame, text="")
        self.time_label.pack(side="left", padx=5)

        # Verzió vagy egyéb információ
        version_label = ttk.Label(footer_frame, text="Sportfogadási szimuláció v1.0")
        version_label.pack(side="right", padx=5)

        # Frissítjük az időt
        self.update_time()

    def update_time(self):
        """Frissíti a láblécben megjelenő dátumot és időt"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"Utolsó frissítés: {now}")
        self.after(1000, self.update_time)  # Minden másodpercben frissít

    def on_tab_changed(self, event):
        """A fülek váltásakor frissíti a megfelelő statisztikákat"""
        selected_tab = self.notebook.index(self.notebook.select())

        if selected_tab == 1:  # A predikciós fül indexe 1
            self.update_prediction_stats(self.active_pred_model.get())
            self.populate_prediction_treeview()

    def calculate_strategy_stats(self):
        """
        Kiszámítja minden stratégiára a nyereség és veszteség szórását és mediánját.
        Eredmény:
        {
            strategy_id: {
                'win_std_dev': float,   # Nyereségek szórása
                'win_median': float,     # Nyereségek mediánja
                'loss_std_dev': float,  # Veszteségek szórása
                'loss_median': float     # Veszteségek mediánja
            },
            ...
        }
        """
        strategy_stats = {}

        for strategy in get_all_strategies():
            strategy_id = strategy['id']
            strategy_sims = [s for s in self.simulation_data if s.get('strategy_id') == strategy_id]

            if not strategy_sims:
                continue

            # Nyerő és vesztes szimulációk szétválasztása
            winning_sims = [s for s in strategy_sims if s.get('total_profit_loss', 0) > 0]
            losing_sims = [s for s in strategy_sims if s.get('total_profit_loss', 0) < 0]

            # Nyereségek statisztikái
            win_profits = [s.get('total_profit_loss', 0) for s in winning_sims]
            win_std_dev = statistics.stdev(win_profits) if len(win_profits) > 1 else 0
            win_median = statistics.median(win_profits) if win_profits else 0

            # Veszteségek statisztikái (abszolút értékben)
            loss_profits = [abs(s.get('total_profit_loss', 0)) for s in losing_sims]
            loss_std_dev = statistics.stdev(loss_profits) if len(loss_profits) > 1 else 0
            loss_median = statistics.median(loss_profits) if loss_profits else 0

            strategy_stats[strategy_id] = {
                'win_std_dev': win_std_dev,
                'win_median': win_median,
                'loss_std_dev': loss_std_dev,
                'loss_median': loss_median
            }

        return strategy_stats

    def create_model_comparison_tab(self):
        """Hozzáad egy új fület a modellek összehasonlításához"""
        self.model_comparison_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.model_comparison_frame, text="Modellek összehasonlítása stratégiák szerint")

        # Betöltjük a szükséges adatokat
        self.strategies = get_all_strategies()
        self.models = [
            "bayes_classic_profit", "monte_carlo_profit", "poisson_profit",
            "bayes_empirical_profit", "log_reg_profit", "elo_profit"
        ]
        self.model_names_comparison = {
            "bayes_classic_profit": "Bayes Klasszikus",
            "monte_carlo_profit": "Monte Carlo",
            "poisson_profit": "Poisson",
            "bayes_empirical_profit": "Bayes Empirikus",
            "log_reg_profit": "Logisztikus Regresszió",
            "elo_profit": "ELO"
        }

        # Itt betöltjük a szimulációs adatokat
        try:
            self.simulation_data = load_simulation_profits_data()
            print(self.simulation_data)
            if not self.simulation_data:
                messagebox.showwarning("Figyelmeztetés", "Nem találhatók szimulációs adatok!")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt az adatok betöltésekor: {e}")
            self.simulation_data = []

        # Felület létrehozása
        self.create_comparison_widgets(self.model_comparison_frame)
        self.update_strategy_stats_comparison(0)

    def create_comparison_widgets(self, parent):
        """Létrehozza a tab UI elemeit"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Stratégia választó
        strategy_frame = ttk.LabelFrame(main_frame, text="Stratégia kiválasztása", padding=10)
        strategy_frame.pack(fill=tk.X, pady=(0, 10))

        # "Összes" gomb
        ttk.Button(
            strategy_frame,
            text="Összes stratégia",
            command=lambda: self.update_strategy_stats_comparison(0)
        ).pack(side=tk.LEFT, padx=5)

        # Stratégia gombok
        for strategy in self.strategies:
            strategy_id = strategy['id']
            ttk.Button(
                strategy_frame,
                text=strategy['strategy_name'],
                command=lambda sid=strategy_id: self.update_strategy_stats_comparison(sid)
            ).pack(side=tk.LEFT, padx=5)

        # Eredmények megjelenítése - Notebook a különböző nézeteknek
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 1. Tab: Statisztikai táblázat
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statisztikák")

        # 2. Tab: Diagramok
        self.chart_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.chart_frame, text="Diagramok")

        # Táblázat létrehozása
        self.create_comparison_table()

        # Diagram keret létrehozása
        self.create_chart_area_comparison()

    def create_comparison_table(self):
        """Létrehozza a statisztikai táblázatot"""
        columns = (
            "model", "avg_profit", "avg_profit_pct", "profitable_pct", "max_profit", "min_profit",
            "median_profit", "profit_std", "max_loss", "median_loss",
            "loss_std", "median_win", "max_win", "min_win",
            "avg_odds", "win_odds_avg", "loss_odds_avg"
        )

        self.model_comparison_tree = ttk.Treeview(self.stats_frame, columns=columns, show="headings")

        self.model_comparison_tree.heading("model", text="Modell")
        self.model_comparison_tree.heading("avg_profit", text="Átlagos profit")
        self.model_comparison_tree.heading("avg_profit_pct", text="Átlag profit %")
        self.model_comparison_tree.heading("profitable_pct", text="Sikeresség %")
        self.model_comparison_tree.heading("max_profit", text="Max Profit")
        self.model_comparison_tree.heading("min_profit", text="Min Profit")
        self.model_comparison_tree.heading("median_profit", text="Profit Medián")
        self.model_comparison_tree.heading("profit_std", text="Profit Szórás")
        self.model_comparison_tree.heading("max_loss", text="Max Veszteség")
        self.model_comparison_tree.heading("median_loss", text="Vesz. Medián")
        self.model_comparison_tree.heading("loss_std", text="Vesz. Szórás")
        self.model_comparison_tree.heading("median_win", text="Nyer. Medián")
        self.model_comparison_tree.heading("max_win", text="Max Nyereség")
        self.model_comparison_tree.heading("min_win", text="Min Nyereség")
        self.model_comparison_tree.heading("avg_odds", text="Átl. Odds")
        self.model_comparison_tree.heading("win_odds_avg", text="Nyer. Odds Átl.")
        self.model_comparison_tree.heading("loss_odds_avg", text="Vesz. Odds Átl.")

        col_widths = {
            "model": 120, "avg_profit": 100, "avg_profit_pct": 110, "profitable_pct": 90, "max_profit": 90,
            "min_profit": 90, "median_profit": 100, "profit_std": 90,
            "max_loss": 100, "median_loss": 90, "loss_std": 90,
            "median_win": 90, "max_win": 90, "min_win": 90,
            "avg_odds": 80, "win_odds_avg": 90, "loss_odds_avg": 90
        }

        for col, width in col_widths.items():
            self.model_comparison_tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(self.stats_frame, orient="vertical", command=self.model_comparison_tree.yview)
        hsb = ttk.Scrollbar(self.stats_frame, orient="horizontal", command=self.model_comparison_tree.xview)
        self.model_comparison_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.model_comparison_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.stats_frame.rowconfigure(0, weight=1)
        self.stats_frame.columnconfigure(0, weight=1)

    def create_chart_area_comparison(self):
        """Létrehozza a diagram területet"""
        # Fő keret
        self.chart_container = ttk.Frame(self.chart_frame)
        self.chart_container.pack(fill=tk.BOTH, expand=True)

        # Kezdeti üzenet
        ttk.Label(
            self.chart_container,
            text="Válasszon stratégiát a diagramok megjelenítéséhez",
            font=("Arial", 12)
        ).pack(pady=50)

    def update_strategy_stats_comparison(self, strategy_id):
        strategy_id = int(strategy_id)
        if strategy_id == 0:
            filtered_data = load_simulation_profits_data()
            strategy_name = "Összes stratégia"
        else:
            filtered_data = load_simulation_profits_data(strategy_id)
            strategy_name = next(
                (s['strategy_name'] for s in self.strategies if s['id'] == strategy_id),
                f"Stratégia {strategy_id}"
            )

        if not filtered_data:
            self.model_comparison_tree.delete(*self.model_comparison_tree.get_children())
            self.model_comparison_tree.insert("", "end", values=("Nincs elérhető adat", "", "", "", "", "", "", "", "", "", "", ""))
            self.update_charts_comparison([], "Nincs adat")
            return

        self.update_stats_table_comparison(filtered_data, strategy_name)
        self.update_charts_comparison(filtered_data, strategy_name)

    def update_stats_table_comparison(self, data, strategy_name):
        """Frissíti a statisztikai táblázatot"""
        for item in self.model_comparison_tree.get_children():
            self.model_comparison_tree.delete(item)

        if strategy_name == "Összes stratégia":
            models_odds = get_models_odds_statistics()
            self.odds_stats_all = models_odds
        else:
            self.odds_stats_by_strategy = get_odds_stats_by_strategy_and_model()

        current_strategy_id = next(
            (s['id'] for s in self.strategies if s['strategy_name'] == strategy_name),
            None
        )

        for model in self.models:
            model_name = self.model_names_comparison.get(model, model)

            model_id_map = {
                "bayes_classic_profit": 1,
                "monte_carlo_profit": 2,
                "poisson_profit": 3,
                "bayes_empirical_profit": 4,
                "log_reg_profit": 5,
                "elo_profit": 6
            }
            model_id = model_id_map.get(model)

            model_profits = [s.get(model, 0) for s in data]
            model_stakes_key = model.replace("profit", "stake")
            model_stakes = [s.get(model_stakes_key, 0) for s in data]

            total_sims = len(model_profits)
            profitable_sims = sum(1 for p in model_profits if p > 0)
            profitable_pct = (profitable_sims / total_sims * 100) if total_sims > 0 else 0

            max_profit = max(model_profits) if model_profits else 0
            min_profit = min(model_profits) if model_profits else 0
            median_profit = statistics.median(model_profits) if model_profits else 0
            profit_std = statistics.stdev(model_profits) if len(model_profits) > 1 else 0
            avg_profit = statistics.mean(model_profits) if model_profits else 0

            avg_stake = statistics.mean(model_stakes) if any(model_stakes) else 0
            avg_profit_pct = (avg_profit / avg_stake * 100) if avg_stake > 0 else 0

            losses = [abs(p) for p in model_profits if p < 0]
            max_loss = max(losses) if losses else 0
            median_loss = statistics.median(losses) if losses else 0
            loss_std = statistics.stdev(losses) if len(losses) > 1 else 0

            wins = [p for p in model_profits if p > 0]
            median_win = statistics.median(wins) if wins else 0
            max_win = max(wins) if wins else 0
            min_win = min(wins) if wins else 0

            avg_odds = "-"
            win_odds_avg = "-"
            loss_odds_avg = "-"

            if strategy_name == "Összes stratégia" and hasattr(self, 'odds_stats_all'):
                if model_id in self.odds_stats_all:
                    odds_data = self.odds_stats_all[model_id]
                    avg_odds = f"{odds_data.get('total_odds_avg', 0):.2f}" if odds_data.get('total_odds_avg') else "-"
                    win_odds_avg = f"{odds_data.get('win_odds_avg', 0):.2f}" if odds_data.get('win_odds_avg') else "-"
                    loss_odds_avg = f"{odds_data.get('loss_odds_avg', 0):.2f}" if odds_data.get(
                        'loss_odds_avg') else "-"
            elif current_strategy_id and hasattr(self,
                                                 'odds_stats_by_strategy') and current_strategy_id in self.odds_stats_by_strategy:
                if model_id in self.odds_stats_by_strategy[current_strategy_id]:
                    odds_data = self.odds_stats_by_strategy[current_strategy_id][model_id]
                    avg_odds = f"{odds_data.get('total_odds_avg', 0):.2f}" if odds_data.get('total_odds_avg') else "-"
                    win_odds_avg = f"{odds_data.get('win_odds_avg', 0):.2f}" if odds_data.get('win_odds_avg') else "-"
                    loss_odds_avg = f"{odds_data.get('loss_odds_avg', 0):.2f}" if odds_data.get(
                        'loss_odds_avg') else "-"

            self.model_comparison_tree.insert("", "end", values=(
                model_name,
                f"{avg_profit:.2f}",
                f"{avg_profit_pct:.2f}%",
                f"{profitable_pct:.1f}%",
                f"{max_profit:.2f}",
                f"{min_profit:.2f}",
                f"{median_profit:.2f}",
                f"{profit_std:.2f}",
                f"{max_loss:.2f}",
                f"{median_loss:.2f}",
                f"{loss_std:.2f}",
                f"{median_win:.2f}",
                f"{max_win:.2f}",
                f"{min_win:.2f}",
                avg_odds,
                win_odds_avg,
                loss_odds_avg
            ))

        self.model_comparison_tree.heading("model", text=f"Modell ({strategy_name})")

    def update_charts_comparison(self, data, strategy_name):
        """Frissíti a diagramokat a kiválasztott stratégiára"""
        # Előző diagramok törlése
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if not data:
            ttk.Label(
                self.chart_container,
                text="Nincs elérhető adat a kiválasztott stratégiához",
                font=("Arial", 12)
            ).pack(pady=50)
            return

        # 4 diagram létrehozása: boxplot, profit eloszlás, win/loss arány, odds összehasonlítás
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f"Modell teljesítmények - {strategy_name}", fontsize=14)

        # 1. Boxplot diagram
        self.create_boxplot_comparison(ax1, data)

        # 2. Profit eloszlás
        self.create_profit_distribution(ax2, data)

        # 3. Win/Loss arány
        self.create_win_loss_ratio(ax3, data)

        # 4. Odds összehasonlítás (új)
        self.create_odds_comparison(ax4, strategy_name)

        plt.tight_layout()

        # Beágyazás a Tkinter ablakba
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Navigációs eszköztár
        toolbar = NavigationToolbar2Tk(canvas, self.chart_container)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_odds_comparison(self, ax, strategy_name):
        """Odds összehasonlítás diagram létrehozása modellek szerint"""
        # Modell nevek és modellek ID-jei
        model_id_map = {
            1: "Bayes Klasszikus",
            2: "Monte Carlo",
            3: "Poisson",
            4: "Bayes Empirikus",
            5: "Logisztikus Regresszió",
            6: "ELO"
        }

        # Odds statisztikák forrásának kiválasztása
        if strategy_name == "Összes stratégia":
            # Ha az összes stratégia van kiválasztva, akkor az általános statisztikákat használjuk
            if not hasattr(self, 'odds_stats_all'):
                self.odds_stats_all = get_models_odds_statistics()

            if not self.odds_stats_all:
                ax.text(0.5, 0.5, "Nincs elérhető odds adat",
                        horizontalalignment='center', verticalalignment='center')
                return

            # Adatok előkészítése
            model_ids = []
            win_odds = []
            loss_odds = []
            total_odds = []
            model_names = []

            for model_id, model_name in model_id_map.items():
                if model_id in self.odds_stats_all:
                    odds_data = self.odds_stats_all[model_id]
                    model_ids.append(model_id)
                    model_names.append(model_name)
                    win_odds.append(odds_data.get('win_odds_avg', 0))
                    loss_odds.append(odds_data.get('loss_odds_avg', 0))
                    total_odds.append(odds_data.get('total_odds_avg', 0))
        else:
            # Ha konkrét stratégia van kiválasztva, akkor a stratégia szerinti statisztikákat használjuk
            current_strategy_id = next(
                (s['id'] for s in self.strategies if s['strategy_name'] == strategy_name),
                None
            )

            if not hasattr(self, 'odds_stats_by_strategy'):
                self.odds_stats_by_strategy = get_odds_stats_by_strategy_and_model()

            if not current_strategy_id or current_strategy_id not in self.odds_stats_by_strategy:
                ax.text(0.5, 0.5, "Nincs elérhető odds adat",
                        horizontalalignment='center', verticalalignment='center')
                return

            # Adatok előkészítése
            model_ids = []
            win_odds = []
            loss_odds = []
            total_odds = []
            model_names = []

            for model_id, odds_data in self.odds_stats_by_strategy[current_strategy_id].items():
                if model_id in model_id_map:
                    model_ids.append(model_id)
                    model_names.append(model_id_map[model_id])
                    win_odds.append(odds_data.get('win_odds_avg', 0))
                    loss_odds.append(odds_data.get('loss_odds_avg', 0))
                    total_odds.append(odds_data.get('total_odds_avg', 0))

        if not model_ids:
            ax.text(0.5, 0.5, "Nincs elérhető odds adat",
                    horizontalalignment='center', verticalalignment='center')
            return

        # X tengely pozíciói
        x = range(len(model_ids))
        width = 0.25

        # Oszlopdiagramok rajzolása
        ax.bar([i - width for i in x], win_odds, width, label='Győztes tippek odds', color='green')
        ax.bar(x, total_odds, width, label='Összes tipp odds', color='blue')
        ax.bar([i + width for i in x], loss_odds, width, label='Vesztes tippek odds', color='red')

        # Diagram formázása
        ax.set_title(f"Odds összehasonlítás - {strategy_name}")
        ax.set_ylabel("Átlagos odds")
        ax.set_xticks(x)
        ax.set_xticklabels(model_names)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    def create_boxplot_comparison(self, ax, data):
        """Boxplot diagram készítése a modellek profitjairól"""
        # Adatok előkészítése
        plot_data = []
        labels = []

        for model in self.models:
            model_profits = [s.get(model, 0) for s in data]
            if model_profits:
                plot_data.append(model_profits)
                labels.append(self.model_names_comparison.get(model, model))

        # Boxplot rajzolása
        ax.boxplot(plot_data, labels=labels, showmeans=True)
        ax.set_title("Profit eloszlás modellek szerint")
        ax.set_ylabel("Profit (Ft)")
        ax.grid(True, alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    def create_profit_distribution(self, ax, data):
        """Hisztogram a profit eloszlásáról"""
        # Minden modell adatainak összegyűjtése
        for model in self.models:
            model_profits = [s.get(model, 0) for s in data]
            model_name = self.model_names_comparison.get(model, model)  # Itt javítva

            if model_profits:
                sns.histplot(
                    model_profits,
                    kde=True,
                    label=model_name,
                    alpha=0.6,
                    ax=ax
                )

        ax.set_title("Profit eloszlás")
        ax.set_xlabel("Profit (Ft)")
        ax.set_ylabel("Gyakoriság")
        ax.legend()
        ax.grid(True, alpha=0.3)

    def create_win_loss_ratio(self, ax, data):
        """Win/Loss arány mutatója modellekre bontva"""
        # Adatok előkészítése
        win_ratios = []
        labels = []

        for model in self.models:
            model_profits = [s.get(model, 0) for s in data]
            if model_profits:
                wins = sum(1 for p in model_profits if p > 0)
                losses = sum(1 for p in model_profits if p < 0)
                total = wins + losses

                if total > 0:
                    win_ratio = (wins / total) * 100
                    win_ratios.append(win_ratio)
                    labels.append(self.model_names_comparison.get(model, model))  # Itt javítva

        # Oszlopdiagram rajzolása
        if win_ratios:
            bars = ax.bar(labels, win_ratios, color='green', alpha=0.6)
            ax.bar_label(bars, fmt='%.1f%%', padding=3)
            ax.set_title("Nyertes szimulációk aránya")
            ax.set_ylabel("Nyertes arány (%)")
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")