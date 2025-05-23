from src.Backend.API.fixtures import save_pre_match_fixtures, update_fixtures
from src.Backend.DB.predictions import batch_evaluate_all_predictions
from src.Frontend.windows.SportsApp import SportsApp
import tkinter as tk
from tkinter import messagebox

def main():
    # Tkinter inicializálása üzenetablakhoz
    root = tk.Tk()
    root.withdraw()  # Az alapablakot elrejtjük, csak az üzenetablak jelenik meg

    # Üzenetablak megjelenítése
    response = messagebox.askyesno("Frissítés", "Szeretné frissíteni az aktuális mérkőzések listáját?")

    if response:  # Ha a felhasználó Igen-t választott
        print("🔄 Mérkőzések frissítése...")
        save_pre_match_fixtures()
        update_fixtures()
        batch_evaluate_all_predictions()
        print("✅ Frissítés kész!")

    # Az alkalmazás főablakának indítása
    root = tk.Tk()
    app = SportsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
