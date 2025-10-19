import sys
import tkinter as tk

from apps.CombinedApp import CombinedApp

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
