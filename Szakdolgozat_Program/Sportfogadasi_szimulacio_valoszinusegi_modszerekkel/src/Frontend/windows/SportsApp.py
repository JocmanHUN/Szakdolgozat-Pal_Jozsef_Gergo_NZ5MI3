from src.Backend.API.helpersAPI import sync_bookmakers
from src.Backend.API.odds import fetch_odds_for_fixture
from src.Backend.DB.fixtures import get_pre_match_fixtures
from src.Frontend.windows.MainMenu import MainMenu
from src.Frontend.windows.PastResultsApp import PastResultsApp
from src.Frontend.windows.TeamsApp import TeamsApp


class SportsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Betting Simulation")

        # Teljes képernyőre állítás
        self.root.state("zoomed")

        # Minimális méret beállítása, hogy minden látszódjon
        self.root.minsize(800, 600)  # Minimális méret 800x600

        # Fogadóirodák szinkronizálása az első indításkor
        self.sync_initial_bookmakers()

        self.current_frame = None
        self.show_main_menu()

    def sync_initial_bookmakers(self):
        """
        Ellenőrzi és szinkronizálja a fogadóirodák listáját az első indításkor.
        """
        print("Fogadóirodák szinkronizálása az első indításkor...")
        fixtures = get_pre_match_fixtures()  # Mérkőzések lekérése
        if fixtures:
            fixture_id = fixtures[0]['fixture_id']  # Egy első mérkőzés ID kiválasztása
            odds = fetch_odds_for_fixture(fixture_id)  # Oddsok lekérése
            sync_bookmakers(odds)  # Fogadóirodák szinkronizálása
        else:
            print("Nincsenek elérhető mérkőzések az első indításhoz.")

    def show_frame(self, frame_class):
        """Eltávolítja a jelenlegi frame-et, és betölti az újat."""
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self)
        self.current_frame.pack(fill="both", expand=True)

    def show_main_menu(self):
        """Főmenü megjelenítése."""
        self.show_frame(MainMenu)

    def show_past_results(self):
        """Múltbéli eredmények nézet megjelenítése."""
        self.show_frame(PastResultsApp)

    def show_teams(self):
        """Csapatok nézet megjelenítése."""
        self.show_frame(TeamsApp)









