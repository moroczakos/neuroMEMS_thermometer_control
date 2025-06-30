import tkinter as tk

class ToolTip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay  # milliseconds
        self.tip_window = None
        self.after_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<Motion>", self._on_motion)

    def _on_enter(self, event=None):
        self.after_id = self.widget.after(self.delay, self._show_tip)

    def _on_leave(self, event=None):
        self._hide_tip()
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def _on_motion(self, event=None):
        if self.tip_window:
            x, y = event.x_root + 10, event.y_root + 10
            self.tip_window.geometry(f"+{x}+{y}")

    def _show_tip(self):
        if self.tip_window or not self.text:
            return

        try:
            # Only widgets that support 'insert' index return a bbox
            bbox = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else None
            x, y, cx, cy = bbox if bbox else (0, 0, 0, 0)
        except Exception:
            x, y, cx, cy = 0, 0, 0, 0

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text = self.text, background = "#ffffe0",
            relief = "solid", borderwidth = 1,
            font = ("tahoma", "9", "normal")
        )
        label.pack(ipadx = 5, ipady = 2)

    def _hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None