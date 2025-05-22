import tkinter as tk

def get_widget_value(variable):
    try:
        return variable.get()
    except (tk.TclError, ValueError):
        return None
