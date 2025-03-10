from src.Backend.api_requests import save_pre_match_fixtures
from src.Backend.helpersAPI import update_fixtures_status
from src.Frontend.SportsApp import SportsApp
import tkinter as tk

def main():
    #save_pre_match_fixtures()
    update_fixtures_status()
    root = tk.Tk()
    app = SportsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
