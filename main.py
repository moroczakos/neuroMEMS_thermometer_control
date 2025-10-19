import sys, os
import tkinter as tk

from apps.CombinedApp import CombinedApp

# Fix import paths for both local and PyInstaller environments
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS  # Temp folder used by PyInstaller
else:
    BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# Add project root to sys.path
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Combined Apps in Tabs")
    root.geometry("1600x900")

    icon_photo = tk.PhotoImage(file = "icon.png")
    root.iconphoto(True, icon_photo)

    app = CombinedApp(root)


    def on_close():
        if app.close_app():
            sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
