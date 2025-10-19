import sys, os
import tkinter as tk

# --- Dynamic path setup for local + PyInstaller ---
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(BASE_PATH)

# Add project root and key subfolders to sys.path
for folder in [PROJECT_ROOT, os.path.join(PROJECT_ROOT, "apps")]:
    if folder not in sys.path:
        sys.path.insert(0, folder)

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
