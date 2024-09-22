import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from src.Backend.api_requests import get_fixtures
from src.Backend.helpersAPI import write_to_file, clear_file
from src.Frontend.helpersGUI import save_leagues_if_not_exists
from src.Frontend.PastResultsApp import PastResultsApp
from src.Frontend.TeamsApp import TeamsApp

class SportsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Betting Simulation")
        self.current_frame = None  # Aktuálisan megjelenített frame

        self.show_main_menu()

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

class MainMenu(tk.Frame):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app

        # Ligák kiválasztása (Példa GUI)
        label = ttk.Label(self, text="Válaszd ki a ligát:")
        label.pack(pady=10)

        # Múltbéli eredmények gomb
        past_results_button = ttk.Button(self, text="Múltbéli eredmények megtekintése",
                                         command=self.app.show_past_results)
        past_results_button.pack(pady=10)

        # Csapatok megtekintése gomb
        teams_button = ttk.Button(self, text="Csapatok megtekintése", command=self.app.show_teams)
        teams_button.pack(pady=10)

