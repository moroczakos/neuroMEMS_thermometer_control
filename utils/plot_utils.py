import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DualAxisPlot:
    def __init__(self, root, title, x_label, y1_label, y2_label,
                 color1 = 'black', color2 = 'red', on_limits_changed = None):
        self.on_limits_changed = on_limits_changed
        self.y_lim_mins = [None, None]  # mutated in place, safe to share
        self.y_lim_maxs = [None, None]

        self.fig, self.ax1 = plt.subplots(figsize = (6, 4))
        self.ax2 = self.ax1.twinx()
        self.axes = [self.ax1, self.ax2]

        self.line1, = self.ax1.plot([], [], label = y1_label, color = color1)
        self.line2, = self.ax2.plot([], [], label = y2_label, color = color2)
        self.lines = [self.line1, self.line2]

        self.ax1.set_title(title)
        self.ax1.set_xlabel(x_label)
        self.ax1.set_ylabel(y1_label, color = color1)
        self.ax2.set_ylabel(y2_label, color = color2)
        self.ax1.grid(True)

        self.frame = tk.Frame(root)
        self.frame.pack(side = tk.TOP, fill = 'both', expand = True)

        self.canvas = FigureCanvasTkAgg(self.fig, master = self.frame)
        self.canvas.get_tk_widget().pack(side = tk.TOP, fill = 'both', expand = True)

        self.scrollbar = tk.Scrollbar(self.frame, orient = tk.HORIZONTAL)
        self.scrollbar.pack(side = tk.BOTTOM, fill = tk.X)

        self._build_limit_controls()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_limit_controls(self):
        self.limits_enabled = tk.BooleanVar(value = False)
        self._vars = [(tk.StringVar(), tk.StringVar()),  # y1 min/max
                      (tk.StringVar(), tk.StringVar())]  # y2 min/max

        bar = ttk.Frame(self.frame)
        bar.pack(side = tk.BOTTOM, fill = tk.X, pady = 2)

        ttk.Checkbutton(bar, text = "Set Y limits", variable = self.limits_enabled,
                        command = self._on_toggle).pack(side = tk.LEFT, padx = 5)

        self._entries = []
        for idx, name in enumerate(("Y1", "Y2")):
            for j, kind in enumerate(("min", "max")):
                ttk.Label(bar, text = f"{name} {kind}:").pack(side = tk.LEFT, padx = (8, 2))
                e = ttk.Entry(bar, textvariable = self._vars[idx][j], width = 8,
                              justify = 'center', state = 'disabled')
                e.pack(side = tk.LEFT)
                e.bind("<Return>", self.apply_limits)
                e.bind("<FocusOut>", self.apply_limits)
                self._entries.append(e)

    def _on_toggle(self):
        state = 'normal' if self.limits_enabled.get() else 'disabled'
        for e in self._entries:
            e.config(state = state)
        self.apply_limits()

    # ── Logic ─────────────────────────────────────────────────────────────
    @staticmethod
    def _parse(text):
        text = text.strip().replace(",", ".")
        return float(text) if text else None

    def apply_limits(self, event = None):
        if self.limits_enabled.get():
            try:
                mins = [self._parse(v[0].get()) for v in self._vars]
                maxs = [self._parse(v[1].get()) for v in self._vars]
            except ValueError:
                messagebox.showwarning("Warning", "Y limits must be numbers (or empty for auto).")
                return
            if any(lo is not None and hi is not None and lo >= hi
                   for lo, hi in zip(mins, maxs)):
                messagebox.showwarning("Warning", "Y min must be smaller than Y max.")
                return
        else:
            mins, maxs = [None, None], [None, None]

        self.y_lim_mins[:] = mins
        self.y_lim_maxs[:] = maxs

        for ax, lo, hi in zip(self.axes, mins, maxs):
            if lo is None and hi is None:
                ax.relim()
                ax.autoscale(axis = 'y')
            else:
                ax.set_ylim(bottom = lo, top = hi)

        self.canvas.draw_idle()
        if self.on_limits_changed:
            self.on_limits_changed()


def update_plot(line_data_pairs, axes, canvas, y_lim_mins = None, y_lim_maxs = None):
    for line, data in line_data_pairs:
        line.set_data(*data)
    for i in range(len(axes)):
        axes[i].relim()
        if y_lim_mins is None or y_lim_maxs is None or y_lim_mins[i] is None or y_lim_maxs[i] is None:
            axes[i].autoscale_view()
        else:
            axes[i].set_ylim(y_lim_mins[i], y_lim_maxs[i])
    canvas.draw_idle()
