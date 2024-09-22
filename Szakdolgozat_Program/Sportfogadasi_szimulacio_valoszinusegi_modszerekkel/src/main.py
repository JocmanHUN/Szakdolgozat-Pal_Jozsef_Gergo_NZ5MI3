from src.Frontend.gui import SportsApp
import tkinter as tk

def main():
    root = tk.Tk()
    app = SportsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
