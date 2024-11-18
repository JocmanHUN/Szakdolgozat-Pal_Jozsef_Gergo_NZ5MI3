import tkinter as tk
from tkinter import ttk, messagebox
from src.Backend.api_requests import get_teams, get_team_statistics
from src.Backend.helpersAPI import write_to_teams, read_from_teams, read_from_cards, write_to_cards
from src.Frontend.helpersGUI import save_leagues_if_not_exists
from PIL import Image, ImageTk
import requests
from io import BytesIO

class TeamsApp(tk.Frame):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app

        # Itt végigmegyünk a ligákon és hozzáadjuk a 'name' és 'country' adatokat a listához
        self.leagues = save_leagues_if_not_exists()
        self.league_names = [f"{league['name']} - {league['country']}" for league in self.leagues]

        self.seasons = [f"{year}/{year+1}" for year in range(2024, 1999, -1)]  # Szezon kiválasztás listája

        self.create_widgets()

    def create_widgets(self):
        # Konténerek
        self.left_frame = tk.Frame(self)
        self.left_frame.pack(side="left", fill="both", padx=10, pady=10, expand=True)

        self.right_frame = tk.Frame(self)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # Liga kiválasztása
        self.league_label = ttk.Label(self.left_frame, text="Válasszon ligát:")
        self.league_label.pack(pady=5, anchor="w")

        self.league_combo = ttk.Combobox(self.left_frame, values=self.league_names, state="readonly")
        self.league_combo.set("Válasszon ligát...")
        self.league_combo.pack(pady=5, anchor="w", fill="x")

        # Szezon kiválasztása
        self.season_label = ttk.Label(self.left_frame, text="Válasszon szezont:")
        self.season_label.pack(pady=5, anchor="w")

        self.season_combo = ttk.Combobox(self.left_frame, values=self.seasons, state="readonly")
        self.season_combo.set("Válasszon szezont...")
        self.season_combo.pack(pady=5, anchor="w", fill="x")

        # Gombok
        self.button_frame = tk.Frame(self.left_frame)
        self.button_frame.pack(pady=10, anchor="w")

        self.teams_button = ttk.Button(self.button_frame, text="Csapatok lekérése", command=self.get_teams)
        self.teams_button.pack(side="left", padx=5)

        self.back_button = ttk.Button(self.button_frame, text="Vissza", command=self.app.show_main_menu)
        self.back_button.pack(side="left", padx=5)

        # Görgethető canvas a csapatok megjelenítéséhez
        self.canvas = tk.Canvas(self.right_frame)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Hely az elmentett csapatlogóknak
        self.team_logos = []

    def get_teams(self):
        selected_league = self.league_combo.get()
        selected_season = self.season_combo.get()

        if not selected_league or selected_league == "Válasszon ligát..." or not selected_season or selected_season == "Válasszon szezont...":
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát és egy szezont.")
            return

        season_year = int(selected_season.split('/')[0])
        league_id = self.leagues[self.league_combo.current()].get('id')

        teams = get_teams(league_id, season_year)

        if teams:
            write_to_teams(teams, league_id)  # Csapatok mentése az adatbázisba a helyes paraméterekkel
            self.teams = teams  # Mentjük a csapatokat
            # Töröljük a régi adatokat a csapatok frame-jéből
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Megjelenítjük a logókat és csapat neveket egy sorban
            self.show_teams(teams, league_id, season_year)
        else:
            messagebox.showinfo("Nincs találat", "Nincsenek csapatok a megadott szezonban.")

    def show_teams(self, teams, league_id, season):
        self.team_logos.clear()  # Töröljük az előző logók referenciáit

        for team in teams:
            logo_url = team['logo']
            if logo_url:
                try:
                    response = requests.get(logo_url)
                    img_data = response.content
                    img = Image.open(BytesIO(img_data))
                    img = img.resize((50, 50))
                    photo = ImageTk.PhotoImage(img)

                    # Hozzunk létre egy frame-et minden csapatnak
                    team_frame = tk.Frame(self.scrollable_frame)
                    team_frame.pack(anchor="w", pady=5, fill="x")

                    # Kép megjelenítése egy labelben
                    logo_label = tk.Label(team_frame, image=photo)
                    logo_label.pack(side="left", padx=10)

                    # Csapat neve megjelenítése a logó mellett
                    name_label = tk.Label(team_frame, text=team['name'], font=("Arial", 14))
                    name_label.pack(side="left")

                    # Elmentjük a képet, hogy ne törlődjön a memóriából
                    self.team_logos.append(photo)

                    # Hozzáadunk egy eseményt a csapat nevéhez
                    name_label.bind("<Button-1>", lambda e, team_id=team['id']: self.show_team_statistics(team_id, league_id, season))

                except Exception as e:
                    print(f"Nem sikerült betölteni a képet: {e}")

    def show_team_statistics(self, team_id, league_id, season):
        stats = get_team_statistics(league_id, season, team_id)
        selected_team = next((team for team in self.teams if team['id'] == team_id), None)  # A kiválasztott csapat

        # Töröljük az előző statisztikákat megjelenítő frame-et, ha van
        if hasattr(self, 'stats_frame'):
            self.stats_frame.destroy()

        # Töröljük a korábbi UI elemeket, hogy csak a csapat és statisztika jelenjen meg
        self.left_frame.pack_forget()
        self.right_frame.pack_forget()

        if stats and selected_team:
            # Új frame létrehozása a statisztikák számára
            self.stats_frame = tk.Frame(self)
            self.stats_frame.pack(fill='both', expand=True)

            # Csapat neve és logója megjelenítése a tetején
            header_frame = tk.Frame(self.stats_frame)
            header_frame.pack(pady=10)

            # Csapat logója
            logo_url = selected_team['logo']
            if logo_url:
                try:
                    response = requests.get(logo_url)
                    img_data = response.content
                    img = Image.open(BytesIO(img_data))
                    img = img.resize((100, 100))
                    logo_photo = ImageTk.PhotoImage(img)

                    logo_label = tk.Label(header_frame, image=logo_photo)
                    logo_label.image = logo_photo
                    logo_label.pack(side="left", padx=10)
                except Exception as e:
                    print(f"Nem sikerült betölteni a képet: {e}")

            # Csapat neve és szezon
            team_info_label = tk.Label(header_frame, text=f"{selected_team['name']} - {season}/{season + 1}",
                                       font=("Arial", 16))
            team_info_label.pack(side="left", padx=10)

            # Statisztikák megjelenítése notebookkal
            notebook = ttk.Notebook(self.stats_frame)
            notebook.pack(pady=10, fill='both', expand=True)

            # Fixtures fül és tartalom
            fixtures_frame = ttk.Frame(notebook)
            notebook.add(fixtures_frame, text="Fixtures Statisztikák")
            fixtures_tree = ttk.Treeview(fixtures_frame, columns=("Detail", "Home", "Away", "Total"), show="headings")
            fixtures_tree.heading("Detail", text="Részletek")
            fixtures_tree.heading("Home", text="Hazai")
            fixtures_tree.heading("Away", text="Vendég")
            fixtures_tree.heading("Total", text="Összesített")
            fixtures_tree.pack(pady=10, fill='both', expand=True)

            if 'fixtures' in stats:
                fixtures = stats['fixtures']
                fixtures_tree.insert("", "end", values=(
                    "Played", fixtures['played']['home'], fixtures['played']['away'], fixtures['played']['total']))
                fixtures_tree.insert("", "end", values=(
                    "Wins", fixtures['wins']['home'], fixtures['wins']['away'], fixtures['wins']['total']))
                fixtures_tree.insert("", "end", values=(
                    "Draws", fixtures['draws']['home'], fixtures['draws']['away'], fixtures['draws']['total']))
                fixtures_tree.insert("", "end", values=(
                    "Loses", fixtures['loses']['home'], fixtures['loses']['away'], fixtures['loses']['total']))

            # Goals fül és tartalom
            goals_frame = ttk.Frame(notebook)
            notebook.add(goals_frame, text="Goals Statisztikák")
            goals_tree = ttk.Treeview(goals_frame, columns=("Detail", "Home", "Away", "Total"), show="headings")
            goals_tree.heading("Detail", text="Részletek")
            goals_tree.heading("Home", text="Hazai")
            goals_tree.heading("Away", text="Vendég")
            goals_tree.heading("Total", text="Összesített")
            goals_tree.pack(pady=10, fill='both', expand=True)

            if 'goals' in stats:
                goals = stats['goals']
                goals_tree.insert("", "end", values=(
                    "Scored", goals['for']['total']['home'], goals['for']['total']['away'],
                    goals['for']['total']['total']))
                goals_tree.insert("", "end", values=(
                    "Conceded", goals['against']['total']['home'], goals['against']['total']['away'],
                    goals['against']['total']['total']))

            # Cards fül és tartalom
            cards_frame = ttk.Frame(notebook)
            notebook.add(cards_frame, text="Cards Statisztikák")

            # Directly call the card statistics function using team_id
            self.show_card_statistics(cards_frame, stats, team_id)

            # Vissza gomb hozzáadása
            back_button = ttk.Button(self.stats_frame, text="Vissza", command=self.show_teams_screen)
            back_button.pack(pady=10)

    def show_teams_screen(self):
        """Visszaállítja a csapatok listáját és az eredeti layoutot."""
        # Eltávolítjuk a statisztikai frame-et
        if hasattr(self, 'stats_frame'):
            self.stats_frame.destroy()

        # Újra megjelenítjük az eredeti UI elemeket
        self.left_frame.pack(side="left", fill="both", padx=10, pady=10, expand=True)
        self.right_frame.pack(side="right", fill="both", expand=True)

    def show_card_statistics(self, cards_frame, stats, team_id):
        # Hozzunk létre egy Canvas-t a görgetéshez
        canvas = tk.Canvas(cards_frame)
        canvas.pack(side="left", fill="both", expand=True)

        # Görgetősáv hozzáadása
        scrollbar = ttk.Scrollbar(cards_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Görgethető tartalom terület
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Ellenőrizzük, van-e 'cards' adat az API statisztikáiban
        if 'cards' in stats:
            cards = stats['cards']

            # Szezon meghatározása a GUI-ból
            season = self.season_combo.get().split('/')[0]  # Példa: "2020/21" -> "2020"

            # Ellenőrizzük, van-e már adat az adatbázisban
            existing_cards = read_from_cards(team_id, season)  # Szezon hozzáadása az ellenőrzéshez

            if not existing_cards:
                # Ha nincs adat az adatbázisban, az API-ból kapott adatok mentése
                yellow_total = sum(
                    [cards['yellow'].get(interval, {}).get('total', 0) or 0 for interval in cards['yellow']]
                )
                red_total = sum(
                    [cards['red'].get(interval, {}).get('total', 0) or 0 for interval in cards['red']]
                )

                # Mentendő adat összeállítása
                card_data = {
                    'team_id': team_id,
                    'season': season,
                    'yellow_cards': yellow_total,
                    'red_cards': red_total,
                    'yellow_cards_0_15': cards['yellow'].get('0-15', {}).get('total', 0),
                    'yellow_cards_16_30': cards['yellow'].get('16-30', {}).get('total', 0),
                    'yellow_cards_31_45': cards['yellow'].get('31-45', {}).get('total', 0),
                    'yellow_cards_46_60': cards['yellow'].get('46-60', {}).get('total', 0),
                    'yellow_cards_61_75': cards['yellow'].get('61-75', {}).get('total', 0),
                    'yellow_cards_76_90': cards['yellow'].get('76-90', {}).get('total', 0),
                    'yellow_cards_91_105': cards['yellow'].get('91-105', {}).get('total', 0),
                    'yellow_cards_106_120': cards['yellow'].get('106-120', {}).get('total', 0),
                    'red_cards_0_15': cards['red'].get('0-15', {}).get('total', 0),
                    'red_cards_16_30': cards['red'].get('16-30', {}).get('total', 0),
                    'red_cards_31_45': cards['red'].get('31-45', {}).get('total', 0),
                    'red_cards_46_60': cards['red'].get('46-60', {}).get('total', 0),
                    'red_cards_61_75': cards['red'].get('61-75', {}).get('total', 0),
                    'red_cards_76_90': cards['red'].get('76-90', {}).get('total', 0),
                    'red_cards_91_105': cards['red'].get('91-105', {}).get('total', 0),
                    'red_cards_106_120': cards['red'].get('106-120', {}).get('total', 0),
                }
                write_to_cards(card_data, team_id, season)  # Mentés az adatbázisba

                # Frissen mentett adatokat újra lekérjük
                existing_cards = read_from_cards(team_id, season)

            # Összesített lapok kiszámítása
            yellow_total = sum([
                existing_cards[0].get(f'yellow_cards_{interval}', 0) or 0
                for interval in ['0_15', '16_30', '31_45', '46_60', '61_75', '76_90', '91_105', '106_120']
            ])
            red_total = sum([
                existing_cards[0].get(f'red_cards_{interval}', 0) or 0
                for interval in ['0_15', '16_30', '31_45', '46_60', '61_75', '76_90', '91_105', '106_120']
            ])
            total_cards = yellow_total + red_total

            # GUI komponensek frissítése
            summary_label = tk.Label(scrollable_frame, text=f"Összesített lapok száma: {total_cards}",
                                     font=("Arial", 16, "bold"))
            summary_label.pack(pady=10)

            # Fő frame a táblázatok egymás mellé helyezéséhez
            tables_frame = tk.Frame(scrollable_frame)
            tables_frame.pack(pady=10, fill='both', expand=True)

            # Yellow Cards statisztika
            yellow_frame = ttk.LabelFrame(tables_frame, text="Sárga lapok statisztikák")
            yellow_frame.pack(side="left", padx=10, fill='both', expand=True)

            yellow_summary_label = tk.Label(yellow_frame, text=f"Összes sárga lap: {yellow_total}",
                                            font=("Arial", 14, "bold"))
            yellow_summary_label.pack(pady=5)

            yellow_table_frame = tk.Frame(yellow_frame)
            yellow_table_frame.pack(fill='both', expand=True)

            yellow_tree = ttk.Treeview(yellow_table_frame, columns=("Interval", "Yellow Cards"), show="headings")
            yellow_tree.heading("Interval", text="Időintervallum")
            yellow_tree.heading("Yellow Cards", text="Sárga lapok")
            yellow_tree.pack(side="left", fill='both', expand=True)

            intervals = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '91-105', '106-120']
            for interval in intervals:
                yellow_cards = existing_cards[0].get(f'yellow_cards_{interval.replace("-", "_")}', 0) or 0 if len(
                    existing_cards) > 0 else cards['yellow'].get(interval, {}).get('total', 0)
                yellow_tree.insert("", "end", values=(interval, yellow_cards))

            # Red Cards statisztika
            red_frame = ttk.LabelFrame(tables_frame, text="Piros lapok statisztikák")
            red_frame.pack(side="left", padx=10, fill='both', expand=True)

            red_summary_label = tk.Label(red_frame, text=f"Összes piros lap: {red_total}", font=("Arial", 14, "bold"))
            red_summary_label.pack(pady=5)

            red_table_frame = tk.Frame(red_frame)
            red_table_frame.pack(fill='both', expand=True)

            red_tree = ttk.Treeview(red_table_frame, columns=("Interval", "Red Cards"), show="headings")
            red_tree.heading("Interval", text="Időintervallum")
            red_tree.heading("Red Cards", text="Piros lapok")
            red_tree.pack(side="left", fill='both', expand=True)

            for interval in intervals:
                red_cards = existing_cards[0].get(f'red_cards_{interval.replace("-", "_")}', 0) or 0 if len(
                    existing_cards) > 0 else cards['red'].get(interval, {}).get('total', 0)
                red_tree.insert("", "end", values=(interval, red_cards))

           
