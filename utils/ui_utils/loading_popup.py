import tkinter as tk
from tkinter import ttk


class LoadingPopup:
    def __init__(self, parent, message="Connecting..."):
        self.popup = tk.Toplevel(parent)
        self.popup.title("Please wait")
        self.popup.geometry("200x100")
        self.popup.resizable(False, False)
        ttk.Label(self.popup, text = message).pack(pady = 20)
        self.popup.grab_set()
        self.popup.update()

    def close(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
