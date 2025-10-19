import sys, os
import tkinter as tk
from apps.CombinedApp import CombinedApp

if __name__ == "__main__":
    # handle PyInstaller frozen path
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))

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
