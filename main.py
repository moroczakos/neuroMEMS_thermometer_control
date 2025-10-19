import sys, os
import tkinter as tk

# --- Dynamic path setup for local + PyInstaller ---
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running from source
    base_path = os.path.abspath(os.path.dirname(__file__))

# Add both base path and its subfolders (apps, etc.) to sys.path
for folder in ["", "apps", "controllers", "instruments", "models", "utils", "views", "base_classes"]:
    path_to_add = os.path.join(base_path, folder)
    if os.path.isdir(path_to_add) and path_to_add not in sys.path:
        sys.path.insert(0, path_to_add)

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
