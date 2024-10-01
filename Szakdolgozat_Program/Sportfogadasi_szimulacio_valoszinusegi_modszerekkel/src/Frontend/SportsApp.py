import tkinter as tk
from tkinter import ttk
from src.Frontend.PastResultsApp import PastResultsApp
from src.Frontend.TeamsApp import TeamsApp

class SportsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sports Betting Simulation")

        # Minimális és maximális méret beállítása
        self.root.minsize(800, 600)  # Minimális méret 800x600
        self.root.maxsize(1200, 900)  # Maximális méret 1200x900

        self.current_frame = None
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

        # Főcím hozzáadása
        title_label = ttk.Label(self, text="Sportfogadás valószínűségi és statisztikai alapokon", font=("Arial", 12, "italic"))
        title_label.pack(pady=20)  # Hozzáadtam egy kis helyet a cím köré

        # Múltbéli eredmények gomb
        past_results_button = ttk.Button(self, text="Múltbéli eredmények megtekintése",
                                         command=self.app.show_past_results)
        past_results_button.pack(pady=10)

        # Csapatok megtekintése gomb
        teams_button = ttk.Button(self, text="Csapatok megtekintése", command=self.app.show_teams)
        teams_button.pack(pady=10)

        # Kilépés gomb
        exit_button = ttk.Button(self, text="Kilépés", command=self.app.root.destroy)
