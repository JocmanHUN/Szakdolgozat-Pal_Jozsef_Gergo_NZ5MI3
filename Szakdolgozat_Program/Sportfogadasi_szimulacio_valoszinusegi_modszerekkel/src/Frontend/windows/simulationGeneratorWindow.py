import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.Backend.DB.generateDatas import fetch_random_nonoverlapping_fixtures, fetch_matches_for_all_models
from src.Backend.strategies.fibonacci import fibonacci
from src.Backend.strategies.flatBetting import flat_betting
from src.Backend.strategies.kellyCriterion import kelly_criterion
from src.Backend.strategies.martingale import martingale
from src.Backend.strategies.valueBetting import value_betting

# Modellek név - ID párosok
MODEL_MAPPING = {
    "Összes modell": [1, 2, 3, 4, 5, 6],  # Új opció az összes modellhez
    "Bayes Classic": [1],
    "Monte Carlo": [2],
    "Poisson": [3],
    "Bayes Empirical": [4],
    "Logistic Regression": [5],
    "Elo": [6]
}
ODDS_BUCKETS = {
    "Nagyon kis odds (1.01-1.30)": (1.01, 1.30),
    "Kis odds (1.31-1.60)": (1.31, 1.60),
    "Közepes odds (1.61-2.20)": (1.61, 2.20),
    "Nagy odds (2.21-3.50)": (2.21, 3.50),
    "Nagyon nagy odds (3.51-10.00)": (3.51, 10.00),
    "Extrém odds (10.01-1000.0)": (10.01, 1000.0)
}


# Stratégiák listája
STRATEGY_LIST = ["Flat Betting", "Martingale", "Fibonacci", "Kelly Criterion", "Value Betting"]

class SimulationGeneratorWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Új szimuláció generálása")
        self.geometry("900x700")
        self.minsize(900, 700)

        self.selected_fixtures = None

        # --- Felirat ---
        description = (
            "Ezen az oldalon a már megprediktált mérkőzések közül választunk ki meccseket, "
            "hogy még több adattal tudjunk szimulálni.\n"
            "Random választunk ki minimum 5 mérkőzést, figyelve az időintervallumra."
        )
        ttk.Label(self, text=description, wraplength=850, justify="center", font=("Arial", 10, "italic")).pack(pady=10)

        # --- Odds szűrők ---
        odds_frame = ttk.Frame(self)
        odds_frame.pack(pady=5)

        ttk.Label(odds_frame, text="Odds tól:").grid(row=0, column=0, padx=5)
        self.odds_min_entry = ttk.Entry(odds_frame, width=10)
        self.odds_min_entry.grid(row=0, column=1, padx=5)

        ttk.Label(odds_frame, text="Odds ig:").grid(row=0, column=2, padx=5)
        self.odds_max_entry = ttk.Entry(odds_frame, width=10)
        self.odds_max_entry.grid(row=0, column=3, padx=5)

        model_frame = ttk.Frame(self)
        model_frame.pack(pady=5)

        ttk.Label(model_frame, text="Modell kiválasztása:").grid(row=0, column=0, padx=5)
        self.model_var = tk.StringVar()
        self.model_combobox = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly", width=30)
        self.model_combobox["values"] = list(MODEL_MAPPING.keys())
        self.model_combobox.set('')  # NE legyen alapértelmezett kiválasztás!
        self.model_combobox.grid(row=0, column=1, padx=5)

        # --- Stratégia kiválasztó ---
        strategy_frame = ttk.Frame(self)
        strategy_frame.pack(pady=5)

        ttk.Label(strategy_frame, text="Stratégia kiválasztása:").grid(row=0, column=0, padx=5)
        self.strategy_var = tk.StringVar()
        self.strategy_combobox = ttk.Combobox(strategy_frame, textvariable=self.strategy_var, state="readonly", width=30)
        self.strategy_combobox["values"] = STRATEGY_LIST
        self.strategy_combobox.current(0)
        self.strategy_combobox.grid(row=0, column=1, padx=5)

        # --- Mérkőzések száma egy csoportban (új mező) ---
        match_count_frame = ttk.Frame(self)
        match_count_frame.pack(pady=5)

        ttk.Label(match_count_frame, text="Mérkőzések száma csoportonként:").grid(row=0, column=0, padx=5)
        self.match_count_entry = ttk.Entry(match_count_frame, width=10)
        self.match_count_entry.insert(0, "25")  # Alapértelmezett 25
        self.match_count_entry.grid(row=0, column=1, padx=5)

        # --- Mérkőzéscsoportok száma (új) ---
        group_frame = ttk.Frame(self)
        group_frame.pack(pady=5)

        ttk.Label(group_frame, text="Mérkőzéscsoportok száma:").grid(row=0, column=0, padx=5)
        self.group_count_entry = ttk.Entry(group_frame, width=10)
        self.group_count_entry.insert(0, "1")  # Alapértelmezett érték: 1 csoport
        self.group_count_entry.grid(row=0, column=1, padx=5)

        # --- Alap tét megadása ---
        stake_frame = ttk.Frame(self)
        stake_frame.pack(pady=5)

        ttk.Label(stake_frame, text="Alap tét (pl. 10):").grid(row=0, column=0, padx=5)
        self.base_stake_entry = ttk.Entry(stake_frame, width=10)
        self.base_stake_entry.insert(0, "10")  # Default 10
        self.base_stake_entry.grid(row=0, column=1, padx=5)

        # --- Bankroll megadása ---
        bankroll_frame = ttk.Frame(self)
        bankroll_frame.pack(pady=5)

        ttk.Label(bankroll_frame, text="Kezdő bankroll (opcionális):").grid(row=0, column=0, padx=5)
        self.bankroll_entry = ttk.Entry(bankroll_frame, width=10)
        self.bankroll_entry.grid(row=0, column=1, padx=5)

        # A modell kiválasztás megváltoztatásakor ellenőrizzük, hogy az "Összes modell" van-e kiválasztva
        def on_model_selected(event):
            selected_model = self.model_combobox.get()
            if selected_model == "Összes modell":
                self.simulate_button.config(text="Szimuláció generálása (Összes modell)")
                self.bankroll_entry.config(style="Required.TEntry")
            else:
                self.simulate_button.config(text="Szimuláció generálása")
                self.bankroll_entry.config(style="TEntry")


        self.model_combobox.bind("<<ComboboxSelected>>", on_model_selected)

        # Létrehozzuk a kötelező mező stílusát
        s = ttk.Style()
        s.configure("Required.TEntry", fieldbackground="#ffe6e6")

        # --- Gombok ---
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        self.simulate_button = ttk.Button(self, text="Szimuláció generálása", command=self.handle_simulation)
        self.simulate_button.pack(pady=10)

        # Többi gomb változatlan
        self.back_button = ttk.Button(button_frame, text="Vissza", command=self.destroy)
        self.back_button.grid(row=0, column=1, padx=10)

        self.import_button = ttk.Button(button_frame, text="CSV betöltése", command=self.auto_load_csv)
        self.import_button.grid(row=0, column=2, padx=10)

        self.avg_chart_button = ttk.Button(button_frame, text="Átlag grafikon", command=self.show_average_chart)
        self.avg_chart_button.grid(row=0, column=3, padx=10)


        self.init_summary_widgets()

    def auto_load_csv(self):
        file_path = filedialog.askopenfilename(
            title="Válassz ki egy szimulációs CSV fájlt",
            filetypes=[("CSV fájlok", "*.csv")],
            initialdir="simulations"
        )

        if not file_path:
            return

        filename = os.path.basename(file_path)

        if "osszes_modell" in filename.lower():
            success = self.load_all_modell_csv(file_path)
            if success:
                self.compare_all_models()

        else:
            self.load_one_modell_csv(file_path)

    # Beállítjuk a callback-et
    def handle_simulation(self):
        model = self.model_combobox.get().strip()
        strategy = self.strategy_combobox.get().strip()

        if not model:
            messagebox.showerror("Hiba", "Válassz ki egy modellt!")
            return

        if not strategy:
            messagebox.showerror("Hiba", "Válassz ki egy stratégiát!")
            return

        if model == "Összes modell":
            self.generate_simulations_for_all()
        else:
            self.generate_simulation()

    def validate_odds(self):
        try:
            odds_min = float(self.odds_min_entry.get()) if self.odds_min_entry.get() else 1.01
            odds_max = float(self.odds_max_entry.get()) if self.odds_max_entry.get() else 1000.0
        except ValueError:
            messagebox.showerror("Hiba", "Az odds mezőkbe csak számot írj!")
            return None, None

        if odds_min < 1.01 or odds_min > odds_max:
            messagebox.showerror("Hiba", "Az odds alsó értéke helytelen!")
            return None, None

        return odds_min, odds_max

    def generate_simulation(self):
        odds_min, odds_max = self.validate_odds()
        if odds_min is None:
            return

        selected_model = self.model_combobox.get()
        if not selected_model:
            messagebox.showerror("Hiba", "Nem választottál modellt!")
            return

        model_ids = MODEL_MAPPING.get(selected_model, [])
        if not model_ids:
            messagebox.showerror("Hiba", "Ismeretlen modell!")
            return

        model_id = model_ids[0]
        selected_strategy = self.strategy_combobox.get().strip()

        if not selected_strategy:
            messagebox.showerror("Hiba", "Nem választottál stratégiát!")
            return

        # --- Hány csoportot kérünk ---
        try:
            group_count = int(self.group_count_entry.get())
        except (TypeError, ValueError):
            messagebox.showerror("Hiba", "Érvénytelen csoportszám!")
            return

        if group_count < 1:
            messagebox.showerror("Hiba", "A csoportszámnak legalább 1-nek kell lennie.")
            return

        # --- Hány meccs legyen egy csoportban ---
        try:
            match_count = int(self.match_count_entry.get())
        except (TypeError, ValueError):
            messagebox.showerror("Hiba", "Érvénytelen mérkőzésszám!")
            return

        if match_count < 5:
            messagebox.showerror("Hiba", "Legalább 5 mérkőzést kell megadni csoportonként!")
            return

        all_results = []
        bankruptcy_count = 0  # Csőd számláló
        bankruptcy_details = []  # Csőd részletek gyűjtője

        try:
            base_stake = float(self.base_stake_entry.get())
        except ValueError:
            messagebox.showerror("Hiba", "Érvénytelen alap tét érték!")
            return

        # Bankroll opcionális, lehet üres is
        bankroll_text = self.bankroll_entry.get().strip()
        self.bankroll_start = float(bankroll_text) if bankroll_text else None

        # --- Generálás ---
        for group_number in range(1, group_count + 1):
            fixtures = fetch_random_nonoverlapping_fixtures(model_id, odds_min, odds_max)
            df = pd.DataFrame(fixtures)

            if df.empty:
                messagebox.showwarning("Nincs adat", f"{group_number}. csoporthoz nincs elég mérkőzés.")
                continue

            selected = self.select_random_nonoverlapping_matches(df, target_count=match_count)

            if selected is None or len(selected) < match_count:
                messagebox.showwarning("Kevés találat",
                                       f"{group_number}. csoporthoz nem sikerült {match_count} meccset találni.")
                continue

            selected = selected.sort_values("match_date").reset_index(drop=True)

            # 🔥 Szimuláció végrehajtása
            bets = []
            for _, row in selected.iterrows():
                bets.append({
                    'won': row['was_correct'],
                    'odds': row['odds'],
                    'model_probability': row['model_probability']  # már lesz ilyen kulcs
                })

            # Stratégia futtatása
            if selected_strategy == "Flat Betting":
                bankroll, stakes = flat_betting(bets, stake=base_stake, bankroll_start=self.bankroll_start or 0)
            elif selected_strategy == "Martingale":
                bankroll, stakes = martingale(bets, base_stake=base_stake, bankroll_start=self.bankroll_start or 0)
            elif selected_strategy == "Fibonacci":
                bankroll, stakes = fibonacci(bets, base_stake=base_stake, bankroll_start=self.bankroll_start or 0)
            elif selected_strategy == "Kelly Criterion":
                if self.bankroll_start is None:
                    self.bankroll_start = 1000  # Helyesen saját self változót állítunk
                bankroll, stakes = kelly_criterion(bets, bankroll_start=self.bankroll_start)
            elif selected_strategy == "Value Betting":
                bankroll, stakes = value_betting(bets, stake=base_stake, bankroll_start=self.bankroll_start or 0)
            else:
                messagebox.showerror("Hiba", "Ismeretlen stratégia!")
                return

            # --- Szimuláció végrehajtása után:
            group_went_bankrupt = False  # Csőd jelző az aktuális csoportra
            bankruptcy_position = None  # Hányadik fogadásnál történt a csőd

            if self.bankroll_start is not None:
                # Ha van bankroll, ellenőrizzük, hogy mikor merül ki
                corrected_stakes = []
                corrected_profits = []
                current_bankroll = self.bankroll_start
                bankroll_depleted = False

                for i, (profit_step, stake) in enumerate(zip(bankroll[1:], stakes)):
                    # Ellenőrizzük, hogy a bankroll kimerült-e már
                    if bankroll_depleted:
                        # Ha igen, a tét 0, a profit változatlan marad
                        corrected_stakes.append(0)
                        corrected_profits.append(corrected_profits[-1])  # Előző profit értéket használjuk
                        continue

                    # Kiszámoljuk a következő bankrollt
                    next_bankroll = self.bankroll_start + profit_step

                    # Ha a bankroll 0 alá menne
                    if next_bankroll <= 0:
                        bankroll_depleted = True
                        group_went_bankrupt = True
                        bankruptcy_position = i + 1  # +1 mert 1-től indexeljük a fogadásokat
                        bankruptcy_count += 1  # Növeljük a csőd számlálót

                        # Jelezzük a felhasználónak, de nem állítjuk meg a szimulációt
                        # (Átmenetileg kikommentezzük, hogy ne zavarjuk a felhasználót túl sok üzenettel)
                        # messagebox.showinfo("Figyelmeztetés",
                        #     f"{group_number}. csoport: A bankroll kimerült {i+1} fogadás után. "
                        #     f"A további fogadások 0 téttel folytatódnak.")

                        # Az aktuális fogadástól kezdve minden tétet 0-ra állítunk és a profitot fixáljuk
                        corrected_stakes.append(0)

                        # A profit itt a teljes bankroll elvesztése
                        corrected_profits.append(-self.bankroll_start)

                        # Csőd részletek tárolása
                        bankruptcy_details.append({
                            'group': group_number,
                            'position': bankruptcy_position,
                            'match': f"{selected.iloc[i]['home_team']} vs {selected.iloc[i]['away_team']}"
                        })

                        # Továbbmegyünk a következő iterációra
                        continue

                    # Normál eset, a bankroll még pozitív
                    current_bankroll = next_bankroll
                    corrected_stakes.append(stake)
                    corrected_profits.append(profit_step)

                # Frissítjük az eredeti értékeket
                if corrected_stakes:
                    stakes = corrected_stakes

                if corrected_profits:
                    bankroll = [self.bankroll_start] + corrected_profits

            # Hozzáadjuk a tétet és a profitot a selected DataFrame-hez
            # Ez marad
            selected["stake"] = stakes

            if selected_strategy == "Kelly Criterion":
                selected["bankroll"] = bankroll[1:]
            else:
                selected["profit"] = bankroll[1:]

            selected["group_number"] = group_number  # EZT mindig kell!

            # Csőd jelölése a DataFrame-ben (ha van bankroll)
            if self.bankroll_start is not None:
                selected["went_bankrupt"] = group_went_bankrupt
                if group_went_bankrupt and bankruptcy_position is not None:
                    selected["bankruptcy_position"] = bankruptcy_position

            all_results.append(selected)

        if not all_results:
            messagebox.showerror("Hiba", "Egyetlen csoport sem jött létre!")
            return

        # Összefűzés
        self.selected_fixtures = pd.concat(all_results, ignore_index=True)
        self.selected_fixtures = self.selected_fixtures.sort_values(["group_number", "match_date"]).reset_index(
            drop=True)

        # Csőd statisztikák hozzáadása az osztály attribútumaihoz
        if self.bankroll_start is not None:
            self.bankruptcy_count = bankruptcy_count
            self.bankruptcy_details = bankruptcy_details

        self.save_simulated_results_to_csv()
        self.update_summary_widgets()

    def save_simulated_results_to_csv(self):
        if self.selected_fixtures is None:
            messagebox.showwarning("Hiba", "Nincs adat a mentéshez!")
            return

        model_name = self.model_combobox.get().replace(" ", "_")
        strategy_name = self.strategy_combobox.get().replace(" ", "_")
        odds_min = self.odds_min_entry.get().strip()
        odds_max = self.odds_max_entry.get().strip()

        # Odds infó hozzáadása a fájlnévhez, ha nem default érték
        odds_suffix = ""
        if odds_min and odds_max and (odds_min != "1.01" or odds_max != "1000.0"):
            odds_suffix = f"_odds_{odds_min.replace('.', '_')}_{odds_max.replace('.', '_')}"

        # Bankroll infó hozzáadása a fájlnévhez - csak ezt tartjuk meg
        bankroll_suffix = ""
        if self.bankroll_start is not None:
            bankroll_suffix = f"_bankroll_{int(self.bankroll_start)}"

        save_dir = os.path.join(os.getcwd(), "generated_simulations")
        os.makedirs(save_dir, exist_ok=True)

        number = 1
        while True:
            save_path = os.path.join(save_dir,
                                     f"{model_name}_{strategy_name}{odds_suffix}{bankroll_suffix}_{number}.csv")
            if not os.path.exists(save_path):
                break
            number += 1

        try:
            with open(save_path, "w", encoding="utf-8-sig", newline="") as f:
                # Egyszerű fejléc
                f.write(f"# Modell: {model_name}\n")
                f.write(f"# Stratégia: {strategy_name}\n")
                if self.bankroll_start is not None:
                    f.write(f"# Kezdeti bankroll: {self.bankroll_start}\n")
                f.write(f"# Alap tét: {self.base_stake_entry.get()}\n")
                f.write("\n")  # Üres sor a fejléc után

                for group_number in sorted(self.selected_fixtures["group_number"].unique()):
                    group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group_number]

                    # Csoport fejléc
                    f.write(f"# Csoport: {group_number}\n")

                    for idx, (_, row) in enumerate(group_df.iterrows()):
                        if 'bankroll' in row and not pd.isna(row['bankroll']):
                            bankroll_actual = row['bankroll']
                        else:
                            bankroll_actual = self.bankroll_start + row[
                                'profit'] if self.bankroll_start is not None else row['profit']

                        f.write(
                            f"{row['fixture_id']};{row['home_team']};{row['away_team']};{row['match_date']};"
                            f"{row['predicted_outcome']};{row['was_correct']};{row['odds']};"
                            f"{row['stake']};{bankroll_actual}\n"
                        )

                        # 🔥 Újítás: minden 25. meccs után egy üres sor
                        if (idx + 1) % int(self.match_count_entry.get()) == 0:
                            f.write("\n")

            messagebox.showinfo("Siker", f"A szimulált adatok automatikusan elmentve lettek:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Hiba", f"Nem sikerült menteni a fájlt:\n{e}")

    def select_random_nonoverlapping_matches(self, df, target_count=25):
        df['match_date'] = pd.to_datetime(df['match_date'])
        available = df.copy().sort_values('match_date').reset_index(drop=True)
        selected = []

        while not available.empty and len(selected) < target_count:
            candidate = available.sample(1).iloc[0]

            selected.append(candidate)
            chosen_time = candidate['match_date']

            available = available[
                ~(
                    (available['match_date'] >= chosen_time - pd.Timedelta(hours=2)) &
                    (available['match_date'] <= chosen_time + pd.Timedelta(hours=2))
                )
            ]

        if len(selected) < target_count:
            return None

        return pd.DataFrame(selected).sort_values('match_date').reset_index(drop=True)


    def create_summary_widgets(self):
        # --- Frame a diagramnak és a táblázatnak ---
        self.summary_frame = ttk.Frame(self)
        self.summary_frame.pack(fill="both", expand=True, pady=10)

        # --- Diagram ---
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.summary_frame)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        # --- Táblázat ---
        self.stats_tree = ttk.Treeview(self.summary_frame, columns=("metric", "value"), show="headings")
        self.stats_tree.heading("metric", text="Metrika")
        self.stats_tree.heading("value", text="Érték")
        self.stats_tree.pack(side="right", fill="both", expand=True)

    def update_summary_widgets(self):
        if self.selected_fixtures is None:
            return

            # Ellenőrizzük, hogy a grafikon létezik-e
        if not hasattr(self, 'ax') or not hasattr(self, 'figure'):
            self.init_summary_widgets()

        group_numbers = self.selected_fixtures["group_number"].unique()
        final_profits = []
        all_stakes = []
        group_profit_percents = []
        total_stakes_per_group = []
        active_bets_per_group = []
        total_bets_per_group = []

        for group in group_numbers:
            group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
            if not group_df.empty:
                if "profit" in group_df.columns:
                    final_profit = group_df["profit"].iloc[-1]
                else:
                    final_profit = group_df["bankroll"].iloc[-1]

                if self.bankroll_start is not None:
                    final_bankroll = final_profit
                    netto_profit = final_bankroll - self.bankroll_start
                else:
                    final_bankroll = final_profit
                    netto_profit = final_profit

                non_zero_stakes = group_df[group_df["stake"] > 0]["stake"]
                total_stake_in_group = non_zero_stakes.sum()
                active_bets_count = len(non_zero_stakes)
                total_bets_count = len(group_df)

                total_stakes_per_group.append(total_stake_in_group)
                active_bets_per_group.append(active_bets_count)
                total_bets_per_group.append(total_bets_count)

                final_profits.append(final_bankroll)
                all_stakes.extend(group_df["stake"].tolist())

                if self.bankroll_start is not None:
                    # Ha van bankroll, akkor a bankrollhoz képest számoljuk
                    group_profit_percent = (netto_profit / self.bankroll_start) * 100
                else:
                    # Ha nincs bankroll, akkor a befektetett tét megtérülését számoljuk (ROI)
                    if total_stake_in_group > 0:
                        group_profit_percent = (final_profit / total_stake_in_group) * 100
                    else:
                        group_profit_percent = 0

                group_profit_percents.append(group_profit_percent)

        if not final_profits:
            return

        total_groups = len(group_numbers)
        if self.bankroll_start is not None:
            wins = sum(1 for p in final_profits if p > self.bankroll_start)
        else:
            wins = sum(1 for p in final_profits if p > 0)

        losses = total_groups - wins
        avg_profit = sum(final_profits) / total_groups
        avg_profit_percent = sum(group_profit_percents) / len(group_profit_percents) if group_profit_percents else 0
        final_total_profit = sum(final_profits)

        avg_total_stake_per_group = sum(total_stakes_per_group) / len(
            total_stakes_per_group) if total_stakes_per_group else 0
        avg_active_bets_per_group = sum(active_bets_per_group) / len(
            active_bets_per_group) if active_bets_per_group else 0
        avg_total_bets_per_group = sum(total_bets_per_group) / len(total_bets_per_group) if total_bets_per_group else 0
        active_bets_rate = (
                    avg_active_bets_per_group / avg_total_bets_per_group * 100) if avg_total_bets_per_group > 0 else 100

        non_zero_stakes = [s for s in all_stakes if s > 0]
        avg_stake = sum(non_zero_stakes) / len(non_zero_stakes) if non_zero_stakes else 0
        max_stake = max(non_zero_stakes) if non_zero_stakes else 0
        min_stake = min(non_zero_stakes) if non_zero_stakes else 0
        stake_std = pd.Series(non_zero_stakes).std() if non_zero_stakes else 0

        max_profit = max(final_profits)
        min_profit = min(final_profits)
        profit_std = pd.Series(final_profits).std()

        # --- Grafikon frissítés ---
        self.ax.clear()
        strategy_name = self.strategy_combobox.get()
        model_name = self.model_combobox.get()
        self.ax.set_title(f"{strategy_name} - {model_name}")
        self.ax.set_xlabel("Mérkőzések száma")

        if self.bankroll_start is not None:
            self.ax.set_ylabel("Bankroll")
        else:
            self.ax.set_ylabel("Kumulált profit")

        for group in group_numbers:
            group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]

            if "profit" in group_df.columns:
                y_values = group_df["profit"]
            else:
                y_values = group_df["bankroll"]

            went_bankrupt = False
            if self.bankroll_start is not None:
                final_val = y_values.iloc[-1]
                went_bankrupt = final_val <= 0

            if went_bankrupt:
                self.ax.plot(range(1, len(y_values) + 1), y_values, linewidth=1, linestyle='--', color='red',
                             label=f"Csoport {group} (csőd)")
            else:
                self.ax.plot(range(1, len(y_values) + 1), y_values, linewidth=1, label=f"Csoport {group}")

        if len(group_numbers) <= 5:
            self.ax.legend(loc='best')

        if self.bankroll_start is not None:
            self.ax.axhline(y=self.bankroll_start, color='black', linestyle='-', linewidth=0.5)
            self.ax.axhline(y=0, color='red', linestyle='-', linewidth=0.5)

        self.canvas.draw()

        # --- Táblázat frissítés ---
        for i in self.stats_tree.get_children():
            self.stats_tree.delete(i)

        self.stats_tree.insert("", "end", values=("Összes csoport", total_groups))
        self.stats_tree.insert("", "end", values=("Nyertes csoportok aránya", f"{wins / total_groups * 100:.2f}%"))
        self.stats_tree.insert("", "end", values=("Vesztes csoportok aránya", f"{losses / total_groups * 100:.2f}%"))

        if self.bankroll_start is not None:
            bankruptcy_count = sum(1 for p in final_profits if p <= 0)
            bankruptcy_rate = (bankruptcy_count / total_groups) * 100 if total_groups > 0 else 0
            self.stats_tree.insert("", "end", values=("Csődbe ment csoportok száma", bankruptcy_count))
            self.stats_tree.insert("", "end", values=("Csőd valószínűsége", f"{bankruptcy_rate:.2f}%"))
            self.stats_tree.insert("", "end",
                                   values=("Átlagos fogadások száma csoportonként", f"{avg_total_bets_per_group:.2f}"))
            self.stats_tree.insert("", "end",
                                   values=("Átlagos aktív fogadások száma", f"{avg_active_bets_per_group:.2f}"))
            self.stats_tree.insert("", "end", values=("Aktív fogadások aránya", f"{active_bets_rate:.2f}%"))

        self.stats_tree.insert("", "end", values=("Átlagos profit arányosan (%)", f"{avg_profit_percent:.2f}%"))

        if self.bankroll_start is not None:
            self.stats_tree.insert("", "end", values=("Kezdő bankroll", f"{self.bankroll_start:.2f}"))
            self.stats_tree.insert("", "end", values=("Átlagos végső bankroll", f"{avg_profit:.2f}"))
            self.stats_tree.insert("", "end", values=("Összesített végső bankroll", f"{final_total_profit:.2f}"))
        else:
            self.stats_tree.insert("", "end", values=("Átlagos végső profit", f"{avg_profit:.2f}"))
            self.stats_tree.insert("", "end", values=("Összesített végső profit", f"{final_total_profit:.2f}"))

        self.stats_tree.insert("", "end",
                               values=("Átlagos összes tét csoportonként", f"{avg_total_stake_per_group:.2f}"))
        self.stats_tree.insert("", "end", values=("Átlagos tét (csak aktív fogadások)", f"{avg_stake:.2f}"))
        self.stats_tree.insert("", "end", values=("Legnagyobb tét", f"{max_stake:.2f}"))
        self.stats_tree.insert("", "end", values=("Legkisebb tét (nem 0)", f"{min_stake:.2f}"))
        self.stats_tree.insert("", "end", values=("Tétek szórása (csak aktív fogadások)", f"{stake_std:.2f}"))

        if self.bankroll_start is not None:
            self.stats_tree.insert("", "end", values=("Legjobb csoport bankroll", f"{max_profit:.2f}"))
            self.stats_tree.insert("", "end", values=("Legrosszabb csoport bankroll", f"{min_profit:.2f}"))
            self.stats_tree.insert("", "end", values=("Bankroll szórása", f"{profit_std:.2f}"))
        else:
            self.stats_tree.insert("", "end", values=("Legjobb csoport profit", f"{max_profit:.2f}"))
            self.stats_tree.insert("", "end", values=("Legrosszabb csoport profit", f"{min_profit:.2f}"))
            self.stats_tree.insert("", "end", values=("Profit szórása", f"{profit_std:.2f}"))

        # --- Odds bucket elemzés ---
        odds_bucket_counts = {bucket: [] for bucket in ODDS_BUCKETS}

        for group in group_numbers:
            group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
            if not group_df.empty:
                for bucket_name, (low, high) in ODDS_BUCKETS.items():
                    count_in_bucket = group_df[(group_df["odds"] >= low) & (group_df["odds"] <= high)].shape[0]
                    odds_bucket_counts[bucket_name].append(count_in_bucket)

        for bucket_name, counts in odds_bucket_counts.items():
            avg_count = sum(counts) / len(counts) if counts else 0
            self.stats_tree.insert("", "end", values=(f"Átlag {bucket_name}", f"{avg_count:.2f}"))

    def load_one_modell_csv(self, file_path=None):
        if file_path is None:
            file_path = filedialog.askopenfilename(
                title="Válassz ki egy szimulációs CSV fájlt",
                filetypes=[("CSV fájlok", "*.csv")]
            )
            if not file_path:
                return

        try:
            filename = os.path.basename(file_path)

            # ÚJ: Fájl alapján kitaláljuk a stratégiát
            self.selected_strategy_name = None
            if "Kelly_Criterion" in filename:
                self.selected_strategy_name = "Kelly Criterion"
            elif "Flat_Betting" in filename:
                self.selected_strategy_name = "Flat Betting"
            elif "Martingale" in filename:
                self.selected_strategy_name = "Martingale"
            elif "Fibonacci" in filename:
                self.selected_strategy_name = "Fibonacci"
            elif "Value_Betting" in filename:
                self.selected_strategy_name = "Value Betting"

            if "bankroll_" in filename:
                bankroll_part = filename.split("bankroll_")[1]
                bankroll_value = bankroll_part.split("_")[0]
                self.bankroll_start = float(bankroll_value)
            else:
                self.bankroll_start = None

            with open(file_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()

            data = []
            group_number = 1

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    if line.startswith("# Csoport:"):
                        group_number = int(line.split(":")[1].strip())
                    continue

                parts = line.split(";")
                if len(parts) < 9:
                    raise ValueError("Érvénytelen sor a CSV fájlban!")

                value = float(parts[8])

                if self.selected_strategy_name == "Kelly Criterion":
                    # 🔥 Kelly: a value maga a bankroll!
                    data.append({
                        "fixture_id": parts[0],
                        "home_team": parts[1],
                        "away_team": parts[2],
                        "match_date": parts[3],
                        "predicted_outcome": parts[4],
                        "was_correct": int(parts[5]),
                        "odds": float(parts[6]),
                        "stake": float(parts[7]),
                        "bankroll": value,
                        "group_number": group_number
                    })
                else:
                    # 🔥 Többi stratégia: profit kiszámítása
                    if self.bankroll_start is not None:
                        profit = value - self.bankroll_start
                    else:
                        profit = value

                    data.append({
                        "fixture_id": parts[0],
                        "home_team": parts[1],
                        "away_team": parts[2],
                        "match_date": parts[3],
                        "predicted_outcome": parts[4],
                        "was_correct": int(parts[5]),
                        "odds": float(parts[6]),
                        "stake": float(parts[7]),
                        "profit": profit,
                        "group_number": group_number
                    })

            df = pd.DataFrame(data)
            df["match_date"] = pd.to_datetime(df["match_date"])

            self.selected_fixtures = df
            self.update_summary_widgets()

            messagebox.showinfo("Siker", f"A szimulációs CSV sikeresen betöltve!\nBankroll: {self.bankroll_start}")

        except Exception as e:
            messagebox.showerror("Hiba", f"Nem sikerült a CSV betöltése: {e}")

    def init_summary_widgets(self):
        # Frame a grafikonhoz és táblázathoz
        summary_frame = ttk.Frame(self)
        summary_frame.pack(fill="both", expand=True, pady=10)

        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, summary_frame)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        # --- Statisztikai táblázat ---
        stats_frame = ttk.Frame(summary_frame)
        stats_frame.pack(side="right", fill="y")

        self.stats_tree = ttk.Treeview(stats_frame, columns=("Leírás", "Érték"), show="headings", height=20)
        self.stats_tree.heading("Leírás", text="Leírás")
        self.stats_tree.heading("Érték", text="Érték")
        self.stats_tree.column("Leírás", anchor="center", width=200)
        self.stats_tree.column("Érték", anchor="center", width=100)
        self.stats_tree.pack(fill="both", expand=True)

    def show_average_chart(self):
        """
        Külön gombra kattintva megjeleníti a mérkőzéscsoportok átlagos teljesítményét
        egy vonallal a grafikonon.
        """
        if self.selected_fixtures is None:
            messagebox.showwarning("Figyelmeztetés", "Nincs adat a megjelenítéshez!")
            return

        # Létrehozunk egy új ablakot az átlag grafikonnak
        avg_window = tk.Toplevel(self)
        avg_window.title("Átlagos teljesítmény")
        avg_window.geometry("800x600")
        avg_window.minsize(800, 600)

        # Csoport számok lekérése
        group_numbers = self.selected_fixtures["group_number"].unique()

        # Meghatározzuk a leghosszabb sorozat hosszát
        max_length = 0
        for group in group_numbers:
            group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
            max_length = max(max_length, len(group_df))

        # Inicializáljuk a kumulált értékek és számláló listákat
        cumulative_values = [0] * max_length
        counts = [0] * max_length

        # Gyűjtsük az értékeket minden csoportból
        for group in group_numbers:
            group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]

            # Ellenőrizzük, melyik oszlop tartalmazza az értékeket (profit vagy bankroll)
            if "profit" in group_df.columns:
                values = group_df["profit"].tolist()
            else:
                values = group_df["bankroll"].tolist()

            # Adjuk hozzá az értékeket a kumulált összeghez
            for i, value in enumerate(values):
                cumulative_values[i] += value
                counts[i] += 1

        # Számoljuk ki az átlagokat
        average_values = []
        for i in range(max_length):
            if counts[i] > 0:
                average_values.append(cumulative_values[i] / counts[i])
            else:
                # Ha nincs adat ebben a pozícióban, használjuk az előző értéket vagy nullát
                if average_values:
                    average_values.append(average_values[-1])
                else:
                    average_values.append(0)

        # Rajzoljuk meg a grafikont
        figure, ax = plt.subplots(figsize=(8, 6))

        # Átlag vonal megjelenítése
        ax.plot(range(1, len(average_values) + 1), average_values, linewidth=2, color='blue',
                label='Csoportok átlaga')

        # Ha van bankroll, jelöljük a kiindulási pontot
        if self.bankroll_start is not None:
            ax.axhline(y=self.bankroll_start, color='black', linestyle='-', linewidth=0.5)
            ax.axhline(y=0, color='red', linestyle='-', linewidth=0.5)
            ax.set_ylabel("Bankroll")
        else:
            ax.set_ylabel("Kumulált profit")

        # Szórás számítása és megjelenítése (opcionális)
        if len(group_numbers) > 1:
            # Számítsuk ki a szórást minden pozícióra
            std_values = []
            for i in range(max_length):
                if counts[i] > 1:
                    group_values = []
                    for group in group_numbers:
                        group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
                        if i < len(group_df):
                            if "profit" in group_df.columns:
                                group_values.append(group_df["profit"].iloc[i])
                            else:
                                group_values.append(group_df["bankroll"].iloc[i])

                    std_values.append(pd.Series(group_values).std())
                else:
                    std_values.append(0)

            # Töltsük ki a variancia területet
            ax.fill_between(
                range(1, len(average_values) + 1),
                [av - std for av, std in zip(average_values, std_values)],
                [av + std for av, std in zip(average_values, std_values)],
                color='blue', alpha=0.2, label='±1 szórás'
            )

        ax.set_title(f"{self.strategy_combobox.get()} - {self.model_combobox.get()} - Átlagos teljesítmény")
        ax.set_xlabel("Mérkőzések száma")
        ax.legend(loc='best')
        ax.grid(True, linestyle='--', alpha=0.7)

        # Statisztikai információk a grafikonhoz
        stats_frame = ttk.Frame(avg_window)
        stats_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # Létrehozunk néhány statisztikát az átlagról
        ttk.Label(stats_frame, text=f"Csoportok száma: {len(group_numbers)}").pack(side="left", padx=10)

        if average_values:
            final_avg = average_values[-1]
            if self.bankroll_start is not None:
                profit_percent = ((
                                              final_avg - self.bankroll_start) / self.bankroll_start) * 100 if self.bankroll_start > 0 else 0
                ttk.Label(stats_frame,
                          text=f"Végső átlag bankroll: {final_avg:.2f} ({profit_percent:+.2f}%)").pack(side="left",
                                                                                                       padx=10)
            else:
                ttk.Label(stats_frame,
                          text=f"Végső átlag profit: {final_avg:.2f}").pack(side="left", padx=10)

        # Elhelyezzük a grafikont az ablakban
        canvas = FigureCanvasTkAgg(figure, master=avg_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Mentés gomb
        def save_chart():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG fájlok", "*.png"), ("JPEG fájlok", "*.jpg"), ("PDF fájlok", "*.pdf")]
            )
            if file_path:
                figure.savefig(file_path, dpi=300, bbox_inches="tight")
                messagebox.showinfo("Siker", f"A grafikon sikeresen elmentve: {file_path}")

        button_frame = ttk.Frame(avg_window)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Grafikon mentése", command=save_chart).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Bezárás", command=avg_window.destroy).pack(side="right", padx=10)

    def generate_simulations_for_all(self):
        """
        Az összes modellre szimuláció generálása egyszerre, helyes struktúrával és a stratégiák helyes alkalmazásával.
        """
        # --- Paraméterek validálása ---
        odds_min, odds_max = self.validate_odds()
        if odds_min is None:
            return

        selected_strategy = self.strategy_combobox.get().strip()
        if not selected_strategy:
            messagebox.showerror("Hiba", "Nem választottál stratégiát!")
            return

        bankroll_text = self.bankroll_entry.get().strip()
        if not bankroll_text:
            messagebox.showerror("Hiba", "Az 'Összes modell' opciónál kötelező megadni a kezdő bankrollt!")
            return

        try:
            self.bankroll_start = float(bankroll_text)
        except ValueError:
            messagebox.showerror("Hiba", "Érvénytelen bankroll érték!")
            return

        try:
            group_count = int(self.group_count_entry.get())
            if group_count < 1:
                messagebox.showerror("Hiba", "Legalább 1 csoportot meg kell adni.")
                return
        except (TypeError, ValueError):
            messagebox.showerror("Hiba", "Érvénytelen csoportszám!")
            return

        try:
            match_count = int(self.match_count_entry.get())
            if match_count < 5:
                messagebox.showerror("Hiba", "Legalább 5 mérkőzést kell kiválasztani csoportonként!")
                return
        except (TypeError, ValueError):
            messagebox.showerror("Hiba", "Érvénytelen mérkőzésszám!")
            return

        try:
            base_stake = float(self.base_stake_entry.get())
        except ValueError:
            messagebox.showerror("Hiba", "Érvénytelen alap tét!")
            return

        # --- Generálás kezdete ---
        all_groups_data = []
        for group_number in range(1, group_count + 1):
            fixtures_df = fetch_matches_for_all_models(odds_min, odds_max, match_count)

            if fixtures_df.empty:
                messagebox.showwarning("Figyelmeztetés", f"{group_number}. csoporthoz nincs elég mérkőzés.")
                continue

            fixtures_df["group_number"] = group_number
            all_groups_data.append(fixtures_df)

        if not all_groups_data:
            messagebox.showerror("Hiba", "Nem sikerült egyetlen csoportot sem létrehozni.")
            return

        self.selected_fixtures = pd.concat(all_groups_data, ignore_index=True)

        # FONTOS: Időrendi sorrendbe rendezzük az adatokat
        self.selected_fixtures = self.selected_fixtures.sort_values("match_date").reset_index(drop=True)

        model_names = ["Bayes_Classic", "Monte_Carlo", "Poisson",
                       "Bayes_Empirical", "Logistic_Regression", "Elo"]

        group_numbers = sorted(self.selected_fixtures["group_number"].unique())

        for model in model_names:
            required_columns = [
                f"{model}_predicted_outcome",
                f"{model}_was_correct",
                f"{model}_odds",
                f"{model}_model_probability"
            ]

            if not all(col in self.selected_fixtures.columns for col in required_columns):
                continue

            for group in group_numbers:
                group_fixtures = self.selected_fixtures[self.selected_fixtures["group_number"] == group].sort_values(
                    "match_date")

                bets = []

                for idx, row in group_fixtures.iterrows():
                    was_correct = row[f"{model}_was_correct"]
                    odds = row[f"{model}_odds"]
                    model_probability = row[f"{model}_model_probability"]

                    if pd.isna(was_correct) or pd.isna(odds) or pd.isna(model_probability):
                        bets.append({
                            "won": None,
                            "odds": None,
                            "model_probability": None
                        })
                    else:
                        bets.append({
                            "won": int(was_correct),
                            "odds": float(odds),
                            "model_probability": float(model_probability)
                        })

                if selected_strategy == "Flat Betting":
                    bankroll, stakes = flat_betting(bets, stake=base_stake, bankroll_start=self.bankroll_start)
                elif selected_strategy == "Martingale":
                    bankroll, stakes = martingale(bets, base_stake=base_stake, bankroll_start=self.bankroll_start)
                elif selected_strategy == "Fibonacci":
                    bankroll, stakes = fibonacci(bets, base_stake=base_stake, bankroll_start=self.bankroll_start)
                elif selected_strategy == "Kelly Criterion":
                    bankroll, stakes = kelly_criterion(bets, bankroll_start=self.bankroll_start)
                elif selected_strategy == "Value Betting":
                    bankroll, stakes = value_betting(bets, stake=base_stake, bankroll_start=self.bankroll_start)
                else:
                    messagebox.showerror("Hiba", "Ismeretlen stratégia!")
                    return

                for i, idx in enumerate(group_fixtures.index):
                    if i < len(stakes):
                        self.selected_fixtures.at[idx, f"{model}_stake"] = stakes[i]
                    else:
                        self.selected_fixtures.at[idx, f"{model}_stake"] = None

                    if i + 1 < len(bankroll):
                        self.selected_fixtures.at[idx, f"{model}_bankroll"] = bankroll[i + 1]
                    else:
                        self.selected_fixtures.at[idx, f"{model}_bankroll"] = None

        self.save_simulations_to_csv_auto()
        # --- Mentés és grafikon ---
        self.compare_all_models()

    def compare_all_models(self):
        """
        Összes modell összehasonlítása magyar nyelvű felülettel és részletes adatmegjelenítéssel.
        """
        if self.selected_fixtures is None:
            messagebox.showwarning("Figyelmeztetés", "Nincs adat a megjelenítéshez!")
            return

        # Stratégia és bankroll információ meghatározása a címhez
        selected_strategy = self.strategy_combobox.get().strip() if hasattr(self, 'strategy_combobox') else "ismeretlen"
        bankroll_info = f" - Kezdő bankroll: {self.bankroll_start:.2f}" if hasattr(self,
                                                                                   'bankroll_start') and self.bankroll_start is not None else ""

        compare_window = tk.Toplevel(self)
        compare_window.title(f"Modellek összehasonlítása - {selected_strategy}{bankroll_info}")
        compare_window.geometry("1200x800")
        compare_window.minsize(1000, 700)

        # --- Fő modell adatok gyűjtése és feldolgozása ---
        colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown']
        model_names = ["Bayes_Classic", "Monte_Carlo", "Poisson", "Bayes_Empirical", "Logistic_Regression", "Elo"]
        model_results = {}

        # Automatikusan meghatározzuk, hogy mely modellek adatai vannak a CSV-ben
        available_models = []
        for model in model_names:
            bankroll_col = f"{model}_bankroll"
            if bankroll_col in self.selected_fixtures.columns:
                available_models.append(model)

        if not available_models:
            messagebox.showwarning("Figyelmeztetés", "Nincs elérhető modell adat a CSV-ben!")
            return

        # Csak az elérhető modellekkel dolgozunk
        model_names = available_models

        # Odds buckets elemzés előkészítése
        ODDS_BUCKETS = {
            "Nagyon kis odds (1.01-1.30)": (1.01, 1.30),
            "Kis odds (1.31-1.60)": (1.31, 1.60),
            "Közepes odds (1.61-2.20)": (1.61, 2.20),
            "Nagy odds (2.21-3.50)": (2.21, 3.50),
            "Nagyon nagy odds (3.51-10.00)": (3.51, 10.00),
            "Extrém odds (10.01-1000.0)": (10.01, 1000.0)
        }

        for idx, model in enumerate(model_names):
            bankroll_col = f"{model}_bankroll"
            stake_col = f"{model}_stake"
            was_correct_col = f"{model}_was_correct"
            odds_col = f"{model}_odds"
            model_prob_col = f"{model}_model_probability"

            if bankroll_col not in self.selected_fixtures.columns:
                continue

            group_numbers = sorted(self.selected_fixtures["group_number"].unique())

            max_length = 0
            for group in group_numbers:
                group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
                group_bankroll = group_df[bankroll_col].dropna()
                max_length = max(max_length, len(group_bankroll))

            cumulative_values = [0] * max_length
            counts = [0] * max_length

            all_final_bankrolls = []
            bankruptcies = 0
            all_group_series = []  # Az összes csoport bankroll sorozata

            # Fogadási adatok gyűjtése
            all_bets = []
            total_stake = 0
            active_bets = 0
            max_stake = 0
            min_stake = float('inf')
            stakes = []

            # Odds bucket adatok
            odds_buckets_stats = {bucket_name: {'count': 0, 'correct': 0} for bucket_name in ODDS_BUCKETS}

            for group in group_numbers:
                group_df = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
                bankroll_series = group_df[bankroll_col].dropna().tolist()

                if not bankroll_series:
                    continue

                # Teljes bankroll sorozat mentése a csoporthoz
                all_group_series.append({
                    'group': group,
                    'series': bankroll_series
                })

                # Bankroll széria feldolgozása
                for i, value in enumerate(bankroll_series):
                    if i < max_length:
                        cumulative_values[i] += value
                        counts[i] += 1

                # Csőd detektálás
                if any(val <= 0 for val in bankroll_series):
                    bankruptcies += 1

                # Végső bankroll rögzítése
                all_final_bankrolls.append(bankroll_series[-1])

                # Fogadási adatok gyűjtése
                for _, row in group_df.iterrows():
                    if pd.notna(row.get(stake_col)) and row[stake_col] > 0:
                        stake = row[stake_col]
                        stakes.append(stake)
                        total_stake += stake
                        active_bets += 1
                        max_stake = max(max_stake, stake)
                        min_stake = min(min_stake, stake)

                        # Ha van odds és was_correct, akkor fogadási adatokat is gyűjtünk
                        if pd.notna(row.get(odds_col)) and pd.notna(row.get(was_correct_col)):
                            odds = row[odds_col]
                            correct = row[was_correct_col]
                            all_bets.append({
                                'stake': stake,
                                'odds': odds,
                                'correct': correct,
                                'model_prob': row.get(model_prob_col) if pd.notna(row.get(model_prob_col)) else None,
                                'row_data': row  # Új: mentjük a teljes sor adatait
                            })

                            # Odds bucket elemzés
                            for bucket_name, (low, high) in ODDS_BUCKETS.items():
                                if low <= odds <= high:
                                    odds_buckets_stats[bucket_name]['count'] += 1
                                    if correct:
                                        odds_buckets_stats[bucket_name]['correct'] += 1
                                    break

            # Átlag számítás
            average_values = []
            for i in range(max_length):
                if counts[i] > 0:
                    average_values.append(cumulative_values[i] / counts[i])
                else:
                    if average_values:
                        average_values.append(average_values[-1])  # utolsó értéket visszük tovább
                    else:
                        average_values.append(0)  # ha még semmi nincs

            # Odds bucket elemzés véglegesítése - találati arány számítása
            for bucket in odds_buckets_stats:
                if odds_buckets_stats[bucket]['count'] > 0:
                    odds_buckets_stats[bucket]['hit_rate'] = (
                                                                     odds_buckets_stats[bucket]['correct'] /
                                                                     odds_buckets_stats[bucket]['count']
                                                             ) * 100
                else:
                    odds_buckets_stats[bucket]['hit_rate'] = 0

            # Nyerő/vesztő sorozatok számítása
            win_streak = 0
            max_win_streak = 0
            loss_streak = 0
            max_loss_streak = 0
            current_streak = 0
            current_streak_type = None

            for bet in all_bets:
                if bet['correct']:
                    if current_streak_type == 'win':
                        current_streak += 1
                    else:
                        if current_streak_type == 'loss':
                            max_loss_streak = max(max_loss_streak, current_streak)
                        current_streak = 1
                        current_streak_type = 'win'
                else:
                    if current_streak_type == 'loss':
                        current_streak += 1
                    else:
                        if current_streak_type == 'win':
                            max_win_streak = max(max_win_streak, current_streak)
                        current_streak = 1
                        current_streak_type = 'loss'

            # Utolsó sorozat ellenőrzése
            if current_streak_type == 'win':
                max_win_streak = max(max_win_streak, current_streak)
            elif current_streak_type == 'loss':
                max_loss_streak = max(max_loss_streak, current_streak)

            model_results[model] = {
                "average_curve": average_values,
                "final_bankrolls": all_final_bankrolls,
                "bankruptcies": bankruptcies,
                "all_group_series": all_group_series,
                "stakes": stakes,
                "total_stake": total_stake,
                "active_bets": active_bets,
                "max_stake": max_stake,
                "min_stake": min_stake if min_stake != float('inf') else 0,
                "all_bets": all_bets,
                "max_win_streak": max_win_streak,
                "max_loss_streak": max_loss_streak,
                "odds_buckets": odds_buckets_stats
            }

        # --- Felület kialakítása split pane-nel ---
        # Felső rész: grafikon
        main_pane = ttk.PanedWindow(compare_window, orient=tk.VERTICAL)
        main_pane.pack(fill="both", expand=True)

        chart_frame = ttk.Frame(main_pane)
        main_pane.add(chart_frame, weight=2)  # Grafikonnak több helyet adunk

        figure, ax = plt.subplots(figsize=(8, 6))
        canvas = FigureCanvasTkAgg(figure, master=chart_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- Vezérlés keret a grafikon alatt ---
        control_frame = ttk.Frame(chart_frame)
        control_frame.pack(fill="x", pady=5)

        # Vissza gomb - kezdetben inaktív
        back_button = ttk.Button(control_frame, text="Vissza az összehasonlításhoz", state="disabled")
        back_button.pack(side="left", padx=10)

        # Címke a jelenlegi nézethez
        view_label = ttk.Label(control_frame, text="Nézet: Összehasonlítás", font=("Arial", 10, "bold"))
        view_label.pack(side="left", padx=10)

        # --- Alsó rész: táblázatok ---
        bottom_frame = ttk.Frame(main_pane)
        main_pane.add(bottom_frame, weight=1)

        # Notebook az alsó részen a különböző táblákhoz
        notebook = ttk.Notebook(bottom_frame)
        notebook.pack(fill="both", expand=True)

        # 1. Tab: Összesítő táblázat
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Összesítés")

        # Magyar nyelvű oszlopnevek
        tree = ttk.Treeview(summary_frame,
                            columns=("Model", "Átlagos Bankroll", "Profit %", "Szórás", "Csődök", "Maximum", "Minimum"),
                            show="headings")
        tree.pack(fill="both", expand=True)

        # Magyar fejlécek beállítása
        column_mapping = {
            "Model": "Modell",
            "Átlagos Bankroll": "Átlagos Bankroll",
            "Profit %": "Profit %",
            "Szórás": "Szórás",
            "Csődök": "Csődök",
            "Maximum": "Maximum",
            "Minimum": "Minimum"
        }

        for col in tree["columns"]:
            tree.heading(col, text=column_mapping[col])
            tree.column(col, anchor="center")

        # Kitöltés adatokkal
        for model, data in model_results.items():
            avg_bankroll = sum(data["final_bankrolls"]) / len(data["final_bankrolls"]) if data["final_bankrolls"] else 0
            profit_percent = (
                    (avg_bankroll - self.bankroll_start) / self.bankroll_start * 100) if self.bankroll_start else 0
            std_dev = pd.Series(data["final_bankrolls"]).std() if data["final_bankrolls"] else 0
            max_bankroll = max(data["final_bankrolls"]) if data["final_bankrolls"] else 0
            min_bankroll = min(data["final_bankrolls"]) if data["final_bankrolls"] else 0
            bankruptcies = data["bankruptcies"]

            tree.insert("", "end", iid=model, values=(
                model.replace("_", " "),
                f"{avg_bankroll:.2f}",
                f"{profit_percent:+.2f}%",
                f"{std_dev:.2f}",
                bankruptcies,
                f"{max_bankroll:.2f}",
                f"{min_bankroll:.2f}"
            ))

        # 2. Tab: Részletes statisztikák (kezdetben üres, majd kiválasztáskor töltődik)
        detail_frame = ttk.Frame(notebook)
        notebook.add(detail_frame, text="Részletes statisztikák")

        # Részletes statisztika táblázat
        detail_tree = ttk.Treeview(detail_frame, columns=("Leírás", "Érték"), show="headings")
        detail_tree.pack(fill="both", expand=True)
        detail_tree.heading("Leírás", text="Leírás")
        detail_tree.heading("Érték", text="Érték")
        detail_tree.column("Leírás", width=300, anchor="w")
        detail_tree.column("Érték", width=150, anchor="center")

        # 3. Tab: Odds elemzés
        odds_frame = ttk.Frame(notebook)
        notebook.add(odds_frame, text="Odds elemzés")

        # Odds elemzés táblázat
        odds_tree = ttk.Treeview(odds_frame, columns=("Odds tartomány", "Találati arány", "Meccsek", "ROI"),
                                 show="headings")
        odds_tree.pack(fill="both", expand=True)
        odds_tree.heading("Odds tartomány", text="Odds tartomány")
        odds_tree.heading("Találati arány", text="Találati arány")
        odds_tree.heading("Meccsek", text="Meccsek száma")
        odds_tree.heading("ROI", text="ROI")
        odds_tree.column("Odds tartomány", width=250, anchor="w")
        odds_tree.column("Találati arány", width=100, anchor="center")
        odds_tree.column("Meccsek", width=100, anchor="center")
        odds_tree.column("ROI", width=100, anchor="center")

        # 4. Tab: Mérkőzés részletek a kiválasztott odds kategóriához
        matches_frame = ttk.Frame(notebook)
        notebook.add(matches_frame, text="Mérkőzés részletek")

        # Mérkőzés részletek táblázat
        matches_tree = ttk.Treeview(matches_frame,
                                    columns=("Dátum", "Hazai", "Vendég", "Eredmény", "Odds", "Tét", "Nyereség",
                                             "Modell valószínűség"),
                                    show="headings")

        # Scrollbar hozzáadása a mérkőzés táblázathoz
        matches_scrollbar = ttk.Scrollbar(matches_frame, orient="vertical", command=matches_tree.yview)
        matches_tree.configure(yscrollcommand=matches_scrollbar.set)
        matches_scrollbar.pack(side="right", fill="y")
        matches_tree.pack(side="left", fill="both", expand=True)

        # Oszlopfejlécek beállítása
        matches_tree.heading("Dátum", text="Dátum")
        matches_tree.heading("Hazai", text="Hazai")
        matches_tree.heading("Vendég", text="Vendég")
        matches_tree.heading("Eredmény", text="Eredmény")
        matches_tree.heading("Odds", text="Odds")
        matches_tree.heading("Tét", text="Tét")
        matches_tree.heading("Nyereség", text="Nyereség")
        matches_tree.heading("Modell valószínűség", text="Modell valószínűség")

        # Oszlopszélességek beállítása
        matches_tree.column("Dátum", width=100, anchor="center")
        matches_tree.column("Hazai", width=150, anchor="w")
        matches_tree.column("Vendég", width=150, anchor="w")
        matches_tree.column("Eredmény", width=80, anchor="center")
        matches_tree.column("Odds", width=80, anchor="center")
        matches_tree.column("Tét", width=80, anchor="center")
        matches_tree.column("Nyereség", width=80, anchor="center")
        matches_tree.column("Modell valószínűség", width=120, anchor="center")

        # --- Funkciódefiniálás a nézetek megjelenítéséhez ---
        def draw_comparison_view():
            """Összehasonlító nézet megjelenítése az összes modellel"""
            ax.clear()

            # Átlaggörbék rajzolása
            for idx, model in enumerate(model_results.keys()):
                if "average_curve" in model_results[model]:
                    average_values = model_results[model]["average_curve"]
                    ax.plot(
                        range(1, len(average_values) + 1),
                        average_values,
                        linewidth=2,
                        color=colors[idx % len(colors)],
                        label=model.replace("_", " ")
                    )

            # Általános grafikon beállítások
            if self.bankroll_start is not None:
                ax.axhline(y=self.bankroll_start, color='black', linestyle='--', linewidth=0.7)
                ax.axhline(y=0, color='red', linestyle='--', linewidth=0.7)
                ax.set_ylabel("Bankroll")
            else:
                ax.set_ylabel("Profit")

            ax.set_title(f"Modellek összehasonlítása - {selected_strategy}")
            ax.set_xlabel("Mérkőzések száma")
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)

            canvas.draw()

            # Gomb és címke frissítése
            back_button.config(state="disabled")
            view_label.config(text="Nézet: Összehasonlítás")

            # Részletes statisztika és odds táblák törlése
            for item in detail_tree.get_children():
                detail_tree.delete(item)

            for item in odds_tree.get_children():
                odds_tree.delete(item)

            for item in matches_tree.get_children():
                matches_tree.delete(item)

            # Alapértelmezett tab kiválasztása
            notebook.select(0)  # Összesítés tab

        def draw_model_detail_view(model_name):
            """Egy adott modell részletes nézete az összes csoporttal és statisztikákkal"""
            ax.clear()

            if model_name not in model_results:
                return

            # Az adott modell összes csoportja
            group_series = model_results[model_name]["all_group_series"]

            # Csoportonkénti bankroll sorozatok
            for idx, group_data in enumerate(group_series):
                group_num = group_data['group']
                series = group_data['series']

                # Csőd ellenőrzése
                went_bankrupt = any(val <= 0 for val in series)

                if went_bankrupt:
                    ax.plot(
                        range(1, len(series) + 1),
                        series,
                        linewidth=1,
                        linestyle='--',
                        color='red',
                        # Eltávolítva a label
                    )
                else:
                    ax.plot(
                        range(1, len(series) + 1),
                        series,
                        linewidth=1,
                        # Eltávolítva a label
                    )

            # Átlag görbe hozzáadása vastagabb vonallal
            average_curve = model_results[model_name]["average_curve"]
            ax.plot(
                range(1, len(average_curve) + 1),
                average_curve,
                linewidth=3,
                color='black',
                label="Átlag"  # Ezt a labelt megtartjuk, csak ez jelenjen meg
            )

            # Általános grafikon beállítások
            if self.bankroll_start is not None:
                ax.axhline(y=self.bankroll_start, color='black', linestyle='--', linewidth=0.7)
                ax.axhline(y=0, color='red', linestyle='--', linewidth=0.7)
                ax.set_ylabel("Bankroll")
            else:
                ax.set_ylabel("Profit")

            ax.set_title(f"{model_name.replace('_', ' ')} - Részletes elemzés - {selected_strategy}")
            ax.set_xlabel("Mérkőzések száma")
            ax.legend()  # A legend megtartva, de most csak az "Átlag" felirat lesz benne
            ax.grid(True, linestyle='--', alpha=0.7)

            canvas.draw()

            # Gomb és címke frissítése
            back_button.config(state="normal")
            view_label.config(text=f"Nézet: {model_name.replace('_', ' ')} részletes")

            # Részletes statisztikák megjelenítése
            update_detail_statistics(model_name)

            # Odds elemzés megjelenítése
            update_odds_analysis(model_name)

            # Mérkőzés lista törlése
            for item in matches_tree.get_children():
                matches_tree.delete(item)

            # Váltás a részletes nézetre
            notebook.select(1)  # Részletes statisztikák tab

        def update_detail_statistics(model_name):
            """Részletes statisztikák frissítése a kiválasztott modellhez"""
            if model_name not in model_results:
                return

            # Meglévő adatok törlése
            for item in detail_tree.get_children():
                detail_tree.delete(item)

            data = model_results[model_name]

            # Statisztikák számítása
            avg_bankroll = sum(data["final_bankrolls"]) / len(data["final_bankrolls"]) if data["final_bankrolls"] else 0
            profit_percent = (
                    (avg_bankroll - self.bankroll_start) / self.bankroll_start * 100) if self.bankroll_start else 0

            # Átlag profit arányosan (%)
            detail_tree.insert("", "end", values=("Átlagos profit arányosan (%)", f"{profit_percent:.2f}%"))

            # Bankroll adatok
            if self.bankroll_start is not None:
                detail_tree.insert("", "end", values=("Kezdő bankroll", f"{self.bankroll_start:.2f}"))
                detail_tree.insert("", "end", values=("Átlagos végső bankroll", f"{avg_bankroll:.2f}"))

                final_total = sum(data["final_bankrolls"])
                detail_tree.insert("", "end", values=("Összesített végső bankroll", f"{final_total:.2f}"))

            # Fogadási adatok
            avg_total_stake = data["total_stake"] / len(data["all_group_series"]) if data["all_group_series"] else 0
            detail_tree.insert("", "end", values=("Átlagos összes tét csoportonként", f"{avg_total_stake:.2f}"))

            if data["active_bets"] > 0:
                avg_stake = data["total_stake"] / data["active_bets"]
                detail_tree.insert("", "end", values=("Átlagos tét (csak aktív fogadások)", f"{avg_stake:.2f}"))

            detail_tree.insert("", "end", values=("Legnagyobb tét", f"{data['max_stake']:.2f}"))

            if data["min_stake"] > 0:
                detail_tree.insert("", "end", values=("Legkisebb tét (nem 0)", f"{data['min_stake']:.2f}"))

            if data["stakes"]:
                stake_std = pd.Series(data["stakes"]).std()
                detail_tree.insert("", "end", values=("Tétek szórása (csak aktív fogadások)", f"{stake_std:.2f}"))

            # Bankroll szélsőértékek
            if data["final_bankrolls"]:
                detail_tree.insert("", "end",
                                   values=("Legjobb csoport bankroll", f"{max(data['final_bankrolls']):.2f}"))
                detail_tree.insert("", "end",
                                   values=("Legrosszabb csoport bankroll", f"{min(data['final_bankrolls']):.2f}"))

                bankroll_std = pd.Series(data["final_bankrolls"]).std()
                detail_tree.insert("", "end", values=("Bankroll szórása", f"{bankroll_std:.2f}"))

            # Sorozatok
            if data["max_win_streak"] > 0:
                detail_tree.insert("", "end", values=("Leghosszabb nyerő sorozat", f"{data['max_win_streak']}"))

            if data["max_loss_streak"] > 0:
                detail_tree.insert("", "end", values=("Leghosszabb vesztő sorozat", f"{data['max_loss_streak']}"))

            # Csőd statisztikák
            if self.bankroll_start is not None:
                total_groups = len(data["all_group_series"])
                if total_groups > 0:
                    bankrupt_rate = (data["bankruptcies"] / total_groups) * 100
                    detail_tree.insert("", "end", values=("Csődbe ment csoportok száma", f"{data['bankruptcies']}"))
                    detail_tree.insert("", "end", values=("Csőd valószínűsége", f"{bankrupt_rate:.2f}%"))

            # Odds elemzés rövid összegzése
            for bucket_name, stats in data["odds_buckets"].items():
                if stats['count'] > 0:
                    detail_tree.insert("", "end", values=(
                        f"Átlag {bucket_name}",
                        f"{stats['count']:.2f}"
                    ))

        def update_odds_analysis(model_name):
            """Odds elemzési táblázat frissítése a kiválasztott modellhez"""
            if model_name not in model_results:
                return

            # Meglévő adatok törlése
            for item in odds_tree.get_children():
                odds_tree.delete(item)

            data = model_results[model_name]

            # Odds buckets elemzés
            for bucket_name, stats in data["odds_buckets"].items():
                if stats['count'] > 0:
                    # Találati arány
                    hit_rate = stats['hit_rate']

                    # ROI számítása erre az odds kategóriára
                    correct = stats['correct']
                    total = stats['count']

                    # Átlagos odds becslése (bucket közép értéke)
                    low, high = ODDS_BUCKETS[bucket_name]
                    avg_odds = (low + high) / 2

                    # A tényleges ROI számításához keressük ki az ehhez az odds tartományhoz tartozó fogadásokat
                    total_stake = 0
                    total_profit = 0

                    # Fogadások gyűjtése az adott odds tartományhoz
                    bucket_bets = [bet for bet in data["all_bets"] if low <= bet['odds'] <= high]

                    for bet in bucket_bets:
                        stake = bet['stake']
                        total_stake += stake

                        if bet['correct']:
                            # Nyertes fogadás: (odds - 1) * tét a nyereség
                            total_profit += stake * (bet['odds'] - 1)
                        else:
                            # Vesztes fogadás: a tét elveszett
                            total_profit -= stake

                    # ROI számítása a tényleges tét és nyereség adatokkal
                    roi = (total_profit / total_stake) * 100 if total_stake > 0 else 0

                    odds_tree.insert("", "end", iid=f"{model_name}_{bucket_name}", values=(
                        bucket_name,
                        f"{hit_rate:.2f}%",
                        total,
                        f"{roi:+.2f}%"
                    ))

        def show_match_details(model_name, odds_range):
            """Kiválasztott odds kategóriához tartozó mérkőzések megjelenítése"""
            # Meglévő adatok törlése
            for item in matches_tree.get_children():
                matches_tree.delete(item)

            if model_name not in model_results:
                return

            data = model_results[model_name]

            # Odds tartomány határértékei
            low, high = ODDS_BUCKETS[odds_range]

            # Fogadások gyűjtése az adott odds tartományhoz
            bucket_bets = [bet for bet in data["all_bets"] if low <= bet['odds'] <= high]

            # A már hozzáadott egyedi mérkőzés azonosítók nyomon követése
            added_match_ids = set()

            # Mérkőzések megjelenítése
            for idx, bet in enumerate(bucket_bets):
                row_data = bet.get('row_data')
                if row_data is None:
                    continue

                # Mérkőzés adatok kinyerése
                date = row_data.get("match_date", "")
                home_team = row_data.get("home_team", "")
                away_team = row_data.get("away_team", "")

                # Tipp és eredmény meghatározása
                predicted_outcome_col = f"{model_name}_predicted_outcome"
                predicted_outcome = row_data.get(predicted_outcome_col, "")
                was_correct = bet['correct']

                # Eredmény helyett a tippet és hogy helyes volt-e
                if predicted_outcome in ["1", 1]:
                    prediction_text = "Hazai"
                elif predicted_outcome in ["2", 2]:
                    prediction_text = "Vendég"
                elif predicted_outcome in ["X", "x"]:
                    prediction_text = "Döntetlen"
                else:
                    prediction_text = str(predicted_outcome)

                result_text = "✓" if was_correct else "✗"

                odds = bet['odds']
                stake = bet['stake']
                model_prob = bet.get('model_prob', None)

                # Nyereség számítása
                profit = (odds - 1) * stake if was_correct else -stake

                # Formázás
                formatted_date = date if isinstance(date, str) else date.strftime("%Y-%m-%d") if hasattr(date,
                                                                                                         "strftime") else str(
                    date)

                # Alap azonosító
                base_match_id = f"{formatted_date}_{home_team}_{away_team}"

                # Ellenőrizzük, hogy ez a mérkőzés már hozzá lett-e adva
                match_id = base_match_id
                counter = 1

                # Ha már létezik ilyen ID, akkor hozzáadunk egy számot, amíg egyedi nem lesz
                while match_id in added_match_ids:
                    match_id = f"{base_match_id}_{counter}"
                    counter += 1

                # Hozzáadjuk az egyedi azonosítót a listához
                added_match_ids.add(match_id)

                # Modell valószínűség helyes formázása:
                # Ha már százalékban van (>1), akkor csak simán kiírjuk
                # Ha decimális formában van (<=1), akkor százalékká alakítjuk
                if model_prob is not None:
                    if model_prob > 1:  # Ha már százalékban van
                        prob_display = f"{model_prob:.2f}%"
                    else:  # Ha decimális formában van
                        prob_display = f"{model_prob * 100:.2f}%"
                else:
                    prob_display = "N/A"

                # Hozzáadás a táblázathoz (külön színezéssel a nyertes/vesztes fogadásokhoz)
                matches_tree.insert("", "end", iid=match_id, values=(
                    formatted_date,
                    home_team,
                    away_team,
                    f"{prediction_text} {result_text}",  # Az eredmény helyett a tipp és annak helyességét mutatjuk
                    f"{odds:.2f}",
                    f"{stake:.2f}",
                    f"{profit:+.2f}",
                    prob_display
                ), tags=('win' if was_correct else 'loss',))

            # Színek beállítása
            matches_tree.tag_configure('win', background='#c6ecc6')  # Zöldes háttér a nyertes fogadásokhoz
            matches_tree.tag_configure('loss', background='#ffcccc')  # Pirosas háttér a vesztes fogadásokhoz

            # Váltás a mérkőzés részletek tabra
            notebook.select(3)  # A 4. tab (index=3)

            # Cím frissítése
            view_label.config(text=f"Nézet: {model_name.replace('_', ' ')} - {odds_range} mérkőzések")

        def on_back_button():
            draw_comparison_view()

        back_button.config(command=on_back_button)

        # --- Táblázat sor kiválasztás ---
        def on_row_selected(event):
            selected_item = tree.focus()
            if not selected_item:
                return

            model = selected_item
            draw_model_detail_view(model)

        tree.bind("<<TreeviewSelect>>", on_row_selected)

        # --- Odds táblázat sor kiválasztás ---
        def on_odds_row_selected(event):
            selected_item = odds_tree.focus()
            if not selected_item:
                return

            # Kiválasztott odds kategória kinyerése
            values = odds_tree.item(selected_item, 'values')
            if not values:
                return

            odds_range = values[0]  # Az első oszlop tartalmazza az odds tartomány nevét

            # Az aktuálisan kiválasztott modell neve
            for item in tree.selection():
                model_name = item
                show_match_details(model_name, odds_range)
                return

            # Ha nincs kiválasztott modell, használjuk az aktuális nézet modelljét
            current_view = view_label.cget("text")
            for model in model_results.keys():
                if model.replace("_", " ") in current_view:
                    show_match_details(model, odds_range)
                    return

        odds_tree.bind("<<TreeviewSelect>>", on_odds_row_selected)

        # Kezdeti nézet megrajzolása
        draw_comparison_view()

    def save_simulations_to_csv_auto(self, directory="simulations"):
        """
        A generált szimulációs adatok mentése CSV fájlba automatikusan generált névvel.
        A fájlnév formátuma: osszes_strategia_{modell_nev}_bankroll{bankroll_ertek}_{szam}.csv

        Args:
            directory (str): A mentés könyvtára (alapértelmezett: aktuális könyvtár)
        """
        if not hasattr(self, 'selected_fixtures') or self.selected_fixtures.empty:
            messagebox.showerror("Hiba", "Nincsenek elérhető adatok a mentéshez!")
            return

        try:
            # Könyvtár létrehozása, ha nem létezik
            os.makedirs(directory, exist_ok=True)

            # Stratégia nevének meghatározása
            selected_strategy = self.strategy_combobox.get().strip() if hasattr(self,
                                                                                'strategy_combobox') else "ismeretlen"
            strategy_name = selected_strategy.lower().replace(" ", "_")

            # Bankroll értékének meghatározása a fájlnévhez
            bankroll_info = f"_bankroll{int(self.bankroll_start)}" if hasattr(self,
                                                                              'bankroll_start') and self.bankroll_start is not None else ""

            # Egyedi fájlnév generálása
            counter = 1
            while True:
                filename = os.path.join(directory, f"osszes_modell_{strategy_name}{bankroll_info}_{counter}.csv")
                if not os.path.exists(filename):
                    break
                counter += 1

            # Releváns oszlopok kiválasztása
            relevant_columns = ['group_number', 'match_date', 'home_team', 'away_team', 'result']

            # Modell specifikus oszlopok hozzáadása
            models = ["Bayes_Classic", "Monte_Carlo", "Poisson",
                      "Bayes_Empirical", "Logistic_Regression", "Elo"]

            for model in models:
                relevant_columns.extend([
                    f"{model}_predicted_outcome",
                    f"{model}_was_correct",
                    f"{model}_odds",
                    f"{model}_stake",
                    f"{model}_bankroll",
                    f"{model}_model_probability"
                ])

            # Csak a létező oszlopok megtartása
            columns_to_export = [col for col in relevant_columns if col in self.selected_fixtures.columns]

            # Üres DataFrame a végeredménynek
            final_df = pd.DataFrame()
            group_numbers = sorted(self.selected_fixtures["group_number"].unique())

            for group in group_numbers:
                group_data = self.selected_fixtures[self.selected_fixtures["group_number"] == group]
                group_data = group_data.sort_values("match_date")[columns_to_export]

                # Csoport hozzáadása
                final_df = pd.concat([final_df, group_data], axis=0)

                # Üres sor hozzáadása (egy üres DataFrame sor)
                empty_row = pd.DataFrame([[""] * len(columns_to_export)], columns=columns_to_export)
                final_df = pd.concat([final_df, empty_row], axis=0)

            # Mentés
            final_df.to_csv(filename, index=False, encoding='utf-8')
            messagebox.showinfo("Sikeres mentés",
                                f"Az adatok sikeresen el lettek mentve a következő fájlba:\n{filename}")
            return filename

        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt a mentés során:\n{str(e)}")
            return None


    def load_all_modell_csv(self, filename=None):
        """
        Összes stratégia CSV fájl betöltése.

        Args:

            filename (str, optional): A betöltendő fájl útvonala. Ha nincs megadva, kiválasztó ablak jelenik meg.

        Returns:
            bool: Sikeres betöltés esetén True, egyébként False
        """
        try:
            # Ha nincs megadva fájlnév, megjelenítjük a fájlválasztó ablakot
            if filename is None:
                filename = filedialog.askopenfilename(
                    title="Összes modell CSV fájl betöltése",
                    filetypes=[("CSV fájlok", "*.csv"), ("Minden fájl", "*.*")],
                    initialdir="simulations"
                )

            if not filename:  # Ha a felhasználó visszalépett
                return False

            # CSV fájl beolvasása
            df = pd.read_csv(filename)

            # Ellenőrizzük, hogy tartalmazza-e a szükséges oszlopokat
            required_columns = ['group_number', 'match_date', 'home_team', 'away_team']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                messagebox.showerror("Hiba",
                                     f"A következő kötelező oszlopok hiányoznak a CSV-ből: {', '.join(missing_columns)}")
                return False

            # Ellenőrizzük, hogy tartalmaz-e legalább egy modell adatait
            model_names = ["Bayes_Classic", "Monte_Carlo", "Poisson", "Bayes_Empirical", "Logistic_Regression", "Elo"]
            has_model_data = False

            for model in model_names:
                if any(col.startswith(f"{model}_") for col in df.columns):
                    has_model_data = True
                    break

            if not has_model_data:
                messagebox.showerror("Hiba", "A CSV nem tartalmaz modell adatokat!")
                return False

            # A group_number oszlop konvertálása egész számmá, ha szöveg formátumban van
            if df['group_number'].dtype == 'object':
                df['group_number'] = pd.to_numeric(df['group_number'], errors='coerce')
                df = df.dropna(subset=['group_number'])
                df['group_number'] = df['group_number'].astype(int)

            # Dátum oszlop konvertálása datetime formátumba
            if 'match_date' in df.columns:
                df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')

            # Üres sorok eltávolítása (a csoportok közötti elválasztók)
            df = df.dropna(subset=['match_date'], how='all')

            # Fájlnévből bankroll információ kinyerése
            try:
                bankroll_pattern = r"bankroll(\d+)"
                bankroll_match = re.search(bankroll_pattern, os.path.basename(filename))

                if bankroll_match:
                    self.bankroll_start = float(bankroll_match.group(1))
                else:
                    # Ha nincs bankroll a fájlnévben, alapértelmezett érték
                    self.bankroll_start = 100.0
            except:
                self.bankroll_start = 100.0

            # Adatok tárolása
            self.selected_fixtures = df

            # Stratégia kiválasztása a fájlnévből vagy alapértelmezett beállítása
            try:
                strategy_pattern = r"osszes_modell_([^_]+)(?:_bankroll|_\d+)"
                strategy_match = re.search(strategy_pattern, os.path.basename(filename))

                if strategy_match:
                    strategy_name = strategy_match.group(1).replace("_", " ")

                    # Stratégia beállítása a comboboxban, ha létezik
                    if hasattr(self, 'strategy_combobox'):
                        if strategy_name in self.strategy_combobox['values']:
                            self.strategy_combobox.set(strategy_name)
            except:
                pass

            messagebox.showinfo("Sikeres betöltés", f"A CSV fájl sikeresen betöltve: {os.path.basename(filename)}")
            return True

        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba történt a CSV betöltése során:\n{str(e)}")
            return False





