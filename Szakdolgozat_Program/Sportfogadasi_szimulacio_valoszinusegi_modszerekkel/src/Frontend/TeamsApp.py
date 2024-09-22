import tkinter as tk
from tkinter import ttk, messagebox
from src.Backend.api_requests import get_teams, get_team_statistics
from src.Backend.helpersAPI import write_to_file, clear_file
from src.Frontend.helpersGUI import save_leagues_if_not_exists
from PIL import Image, ImageTk
import requests
from io import BytesIO
class TeamsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Csapatok Megtekintése")
        self.root.geometry("400x600")  # Beállítjuk az ablak méretét

        # Liga választó lista
        self.leagues = save_leagues_if_not_exists()
        self.league_names = [f"{league['name']} - {league['country']}" for league in self.leagues]

        self.league_label = ttk.Label(root, text="Válaszd ki a ligát:")
        self.league_label.pack(pady=10)

        self.league_combo = ttk.Combobox(root, values=self.league_names)
        self.league_combo.pack(pady=10)

        # Szezon mező
        self.season_label = ttk.Label(root, text="Add meg a szezon évét:")
        self.season_label.pack(pady=10)

        self.season_entry = ttk.Entry(root)
        self.season_entry.pack(pady=10)

        # Csapatok lekérő gomb
        self.teams_button = ttk.Button(root, text="Csapatok lekérése", command=self.get_teams)
        self.teams_button.pack(pady=10)

        # Görgethető Canvas és Scrollbar
        self.canvas = tk.Canvas(root)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Képek tartásához szükséges lista, hogy ne törlődjenek a memóriából
        self.team_logos = []
        self.teams = []  # Csapatok tárolása a későbbi statisztikákhoz

    def get_teams(self):
        selected_league = self.league_combo.get()
        season = self.season_entry.get()

        if not selected_league or not season:
            messagebox.showwarning("Hiányzó adatok", "Kérlek válassz egy ligát és add meg a szezon évét.")
            return

        try:
            int(season)  # Ellenőrizzük, hogy a szezon év számból áll
        except ValueError:
            messagebox.showerror("Hiba", "Kérlek, érvényes évszámot adj meg a szezonhoz.")
            return

        league_id = self.leagues[self.league_combo.current()].get('id')
        clear_file('teams.json')  # Töröljük a csapatok fájlt
        teams = get_teams(league_id, season)

        if teams:
            write_to_file(teams, 'teams.json')  # Csapatok mentése
            self.teams = teams  # Mentjük a csapatokat
            # Töröljük a régi adatokat a csapatok frame-jéből
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Megjelenítjük a logókat és csapat neveket egy sorban
            self.show_teams(teams, league_id, season)
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
                    img = img.resize((50, 50))  # Méretezzük át a képet 50x50 pixelesre
                    photo = ImageTk.PhotoImage(img)

                    # Hozzunk létre egy frame-et minden csapatnak
                    team_frame = tk.Frame(self.scrollable_frame)
                    team_frame.pack(anchor="w", pady=5)

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

        if stats:
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Csapat Statisztikák")

            # Notebook (fülek) létrehozása
            notebook = ttk.Notebook(stats_window)
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
                "Scored", goals['for']['total']['home'], goals['for']['total']['away'], goals['for']['total']['total']))
                goals_tree.insert("", "end", values=(
                "Conceded", goals['against']['total']['home'], goals['against']['total']['away'],
                goals['against']['total']['total']))

            # Cards fül és tartalom
            cards_frame = ttk.Frame(notebook)
            notebook.add(cards_frame, text="Cards Statisztikák")

            # Yellow Cards statisztika
            yellow_frame = ttk.Frame(cards_frame)
            yellow_frame.pack(pady=10, fill='both', expand=True)

            yellow_table_frame = tk.Frame(yellow_frame)
            yellow_table_frame.pack(fill='both', expand=True)

            yellow_tree = ttk.Treeview(yellow_table_frame, columns=("Detail", "Home", "Away", "Total"), show="headings")
            yellow_tree.heading("Detail", text="Részletek")
            yellow_tree.heading("Home", text="Hazai")
            yellow_tree.heading("Away", text="Vendég")
            yellow_tree.heading("Total", text="Összesített")
            yellow_tree.pack(side="left", fill='both', expand=True)

            # Görgetősáv hozzáadása a yellow_tree-hez
            scrollbar_yellow = ttk.Scrollbar(yellow_table_frame, orient="vertical", command=yellow_tree.yview)
            yellow_tree.configure(yscroll=scrollbar_yellow.set)
            scrollbar_yellow.pack(side="right", fill="y")

            # Red Cards statisztika
            red_frame = ttk.Frame(cards_frame)
            red_frame.pack(pady=10, fill='both', expand=True)

            red_table_frame = tk.Frame(red_frame)
            red_table_frame.pack(fill='both', expand=True)

            red_tree = ttk.Treeview(red_table_frame, columns=("Detail", "Home", "Away", "Total"), show="headings")
            red_tree.heading("Detail", text="Részletek")
            red_tree.heading("Home", text="Hazai")
            red_tree.heading("Away", text="Vendég")
            red_tree.heading("Total", text="Összesített")
            red_tree.pack(side="left", fill='both', expand=True)

            # Görgetősáv hozzáadása a red_tree-hez
            scrollbar_red = ttk.Scrollbar(red_table_frame, orient="vertical", command=red_tree.yview)
            red_tree.configure(yscroll=scrollbar_red.set)
            scrollbar_red.pack(side="right", fill="y")

            if 'cards' in stats:
                cards = stats['cards']
                intervals = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '91-105', '106-120']

                total_yellow_home, total_yellow_away = 0, 0
                total_red_home, total_red_away = 0, 0

                for interval in intervals:
                    yellow_cards_home = cards['yellow'].get(interval, {}).get('total', 0) or 0
                    yellow_cards_away = cards['yellow'].get(interval, {}).get('total', 0) or 0
                    red_cards_home = cards['red'].get(interval, {}).get('total', 0) or 0
                    red_cards_away = cards['red'].get(interval, {}).get('total', 0) or 0

                    yellow_total = yellow_cards_home + yellow_cards_away
                    yellow_tree.insert("", "end", values=(
                    f"Yellow Cards ({interval} mins)", yellow_cards_home, yellow_cards_away, yellow_total))

                    red_total = red_cards_home + red_cards_away
                    red_tree.insert("", "end",
                                    values=(f"Red Cards ({interval} mins)", red_cards_home, red_cards_away, red_total))

                    total_yellow_home += yellow_cards_home
                    total_yellow_away += yellow_cards_away
                    total_red_home += red_cards_home
                    total_red_away += red_cards_away

                yellow_total_sum = total_yellow_home + total_yellow_away
                red_total_sum = total_red_home + total_red_away

                yellow_tree.insert("", "end", values=(
                "Total Yellow Cards", total_yellow_home, total_yellow_away, yellow_total_sum))
                red_tree.insert("", "end", values=("Total Red Cards", total_red_home, total_red_away, red_total_sum))

                total_laps_home = total_yellow_home + total_red_home
                total_laps_away = total_yellow_away + total_red_away
                total_laps = total_laps_home + total_laps_away
                yellow_tree.insert("", "end", values=("Total Cards", total_laps_home, total_laps_away, total_laps))

        else:
            messagebox.showinfo("Nincs adat", "Nem állnak rendelkezésre statisztikák.")