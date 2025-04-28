import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.Backend.DB.generateDatas import fetch_random_nonoverlapping_fixtures
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
        self.model_combobox.current(0)  # Should set first item as default
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

        # --- Gombok ---
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        self.generate_button = ttk.Button(button_frame, text="Szimuláció generálása", command=self.generate_simulation)
        self.generate_button.grid(row=0, column=0, padx=10)

        self.back_button = ttk.Button(button_frame, text="Vissza", command=self.destroy)
        self.back_button.grid(row=0, column=1, padx=10)

        self.import_button = ttk.Button(button_frame, text="CSV betöltése", command=self.load_simulation_csv)
        self.import_button.grid(row=0, column=2, padx=10)

        self.avg_chart_button = ttk.Button(button_frame, text="Átlag grafikon", command=self.show_average_chart)
        self.avg_chart_button.grid(row=0, column=3, padx=10)
        self.bankroll_start = None
        # --- Diagram és statisztikai táblázat inicializálása ---
        self.init_summary_widgets()

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

                    for _, row in group_df.iterrows():
                        if 'bankroll' in row and not pd.isna(row['bankroll']):
                            bankroll_actual = row['bankroll']
                        else:
                            # Ha nincs bankroll, akkor számolunk a kezdő bankrolllal
                            bankroll_actual = self.bankroll_start + row[
                                'profit'] if self.bankroll_start is not None else row['profit']

                        f.write(
                            f"{row['fixture_id']};{row['home_team']};{row['away_team']};{row['match_date']};"
                            f"{row['predicted_outcome']};{row['was_correct']};{row['odds']};"
                            f"{row['stake']};{bankroll_actual}\n"
                        )

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

    def load_simulation_csv(self):
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


