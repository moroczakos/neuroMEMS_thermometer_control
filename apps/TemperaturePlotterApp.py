import os
import sys
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog, Button, Label, Frame, Spinbox, IntVar, StringVar, Entry, Checkbutton
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from base_classes.main_base import MainBase
from base_classes.view_base import ViewBase
from utils.file_utils import CsvLogger
from utils.ui_utils.tooltip import ToolTip


class TemperaturePlotterApp(MainBase, ViewBase):
    CHECKBOX_CONFIGS = [
        ("Raw Temp", "show_temp", "raw_temp"),
        ("Compensated", "show_compensated", "compensated"),
        ("Drift", "show_drift", "drift"),
        ("Smoothed", "show_smoothed", "smoothed"),
        ("Transitions", "show_transitions", "transitions"),
        ("Rise/Fall Times", "show_rise_fall_times", "rise_fall_times"),
        ("Title", "show_title", "title"),
        ("Legend", "show_legend", None)
    ]

    def __init__(self, root):
        """Initialize the GUI app."""
        MainBase.__init__(self)
        ViewBase.__init__(self, root, self.setting_manager, self.logger)

        self.root = Frame(root)
        self.root.pack(fill = 'both', expand = True)

        self.file_path = None  # To store the file path selected by user
        self.plot_toolbar = None  # Toolbar for the plot (if it exists)
        self.degree_var = IntVar(value = 1)  # Default polynomial degree value
        self.smoothing_var = StringVar(value = "10")  # Default smoothing window value (as string)
        self.transition_min_dist_var = StringVar(value = "10")  # Default min dist value for two adjacent transition points (as string)

        # Checkbox variables for showing/hiding plot elements
        for _, var_name, _ in self.CHECKBOX_CONFIGS:
            if var_name:
                setattr(self, var_name, IntVar(value = 1))

        # Logger
        self.setup_logger("temperature_plotter_app.log")

        self.setup_ui()
        self.setup_logger_panel()

        # ----------------- UI SETUP ----------------- #

    def setup_ui(self):
        self.file_label = Label(self.root, text = "No file selected.", width = 50)
        self.file_label.pack(pady = 10)

        self.plot_frame = Frame(self.root)
        self.plot_frame.pack(padx = 10, pady = 10, fill = 'both', expand = True)

        self.create_checkboxes()
        self.create_controls()
        self.create_buttons()

    def create_checkboxes(self):
        frame = Frame(self.root)
        frame.pack(pady = 5)
        Label(frame, text = "Show:").pack(side = "left", padx = (0, 10))
        width = 15

        def get_checkbox_state(state):
            return "checked" if state.get() == 1 else "unchecked"

        for text, var_name, tooltip_key in self.CHECKBOX_CONFIGS:
            if var_name:
                var = getattr(self, var_name)
                cb = Checkbutton(frame, text = f"Ⓘ {text}", variable = var,
                                 command = lambda v = var, t = text: self.update_plot(
                                     f"{t} checkbox {get_checkbox_state(v)}."),
                                 width = width)
                cb.pack(side = "left")
                ToolTip(cb, self.tooltips.get(tooltip_key, ""))
            else:  # Legend checkbox without tooltip
                cb = Checkbutton(frame, text = text, variable = self.show_legend,
                                 command = lambda: self.update_plot("Legend checkbox changed."),
                                 width = width)
                cb.pack(side = "left")

    def create_controls(self):
        frame = Frame(self.root)
        frame.pack(pady = 10)

        # Polynomial Degree
        self._add_label_spinbox(frame, "Polynomial Degree:", self.degree_var, 0, 5, "polynomial_degree")
        self.degree_var.trace("w", lambda *a: self.update_plot(f"Polynomial Degree is {self.degree_var.get()}."))

        # Smoothing Window
        self._add_label_entry(frame, "Smoothing Window (data point):", self.smoothing_var, "smoothing_window")
        self.smoothing_var.trace("w", lambda *a: self.update_plot(f"Smoothing Window is {self.smoothing_var.get()}."))

        self._add_label_entry(frame, "Min dist. transition points:", self.transition_min_dist_var, "min_dist_trans")
        self.transition_min_dist_var.trace("w", lambda *a: self.update_plot(
            f"Min distance between transition points is {self.transition_min_dist_var.get()}."))

    def create_buttons(self):
        frame = Frame(self.root)
        frame.pack(pady = 20)

        self._add_button(frame, "Select File and Plot", self.select_file_and_plot, "select_file_and_plot")
        self._add_button(frame, "Select Folder and Analyze", self.select_folder_and_analyze,
                         "select_folder_and_analyze")

        # ----------------- UI HELPERS ----------------- #

    def _add_label_spinbox(self, parent, text, variable, min_val, max_val, tooltip_key):
        Label(parent, text = f"Ⓘ {text}").pack(side = "left", padx = (0, 5))
        ToolTip(parent.children[list(parent.children)[-1]], self.tooltips.get(tooltip_key, ""))
        Spinbox(parent, from_ = min_val, to = max_val, textvariable = variable, width = 5).pack(side = "left",
                                                                                                padx = (0, 20))

    def _add_label_entry(self, parent, text, variable, tooltip_key):
        Label(parent, text = f"Ⓘ {text}").pack(side = "left")
        ToolTip(parent.children[list(parent.children)[-1]], self.tooltips.get(tooltip_key, ""))
        Entry(parent, textvariable = variable, width = 5).pack(side = "left", padx = (0, 20))

    def _add_button(self, parent, text, command, tooltip_key):
        btn = Button(parent, text = f"Ⓘ {text}", command = command)
        btn.pack(side = "left", padx = (0, 20))
        ToolTip(btn, self.tooltips.get(tooltip_key, ""), wraplength = 350)

    # ----------------- FILE & DATA ----------------- #
    def select_file_and_plot(self):
        """Allow user to select a CSV file and plot the data."""
        self.file_path = filedialog.askopenfilename(
            title = "Select CSV File",
            filetypes = [("CSV Files", "*.csv")]
        )

        if self.file_path:
            self.file_label.config(text = f"Selected File: {os.path.basename(self.file_path)}")
            self.plot_data()
            self.logger.info(f"Selected File: {os.path.basename(self.file_path)}")
        else:
            self.file_label.config(text = "No file selected.")
            self.logger.warning("No file was selected.")

    def select_folder_and_analyze(self):
        folder_path = filedialog.askdirectory(
            title = "Select a folder to analyze"
        )

        csv_logger = CsvLogger()
        csv_logger.set_file_name("result.csv")
        csv_logger.set_file_directory(folder_path)
        csv_logger.set_first_row(["File name", "Avg amplitude [°C]", "Avg rise time [s]", "Avg fall time [s]"])
        csv_logger.create()

        temp_path = self.file_path
        pattern = r"^log_Resistance_Temperature.*\.csv$"

        regex = re.compile(pattern, re.IGNORECASE)

        self.logger.info(f"Start analyzing folder: {folder_path}")

        matching_files = [f for f in os.listdir(folder_path) if regex.match(f)]
        total_matches = len(matching_files)

        for i, fname in enumerate(matching_files, 1):
            self.logger.info(f"Processing {i}/{total_matches}: {fname}")

            self.file_path = os.path.join(folder_path, fname)
            self.plot_data()

            self.canvas.figure.savefig(os.path.join(folder_path, f"{fname}.png"))
            average_amplitude, avg_rise_time, avg_fall_time = self.plot_data()

            csv_logger.write_row([fname, average_amplitude, avg_rise_time, avg_fall_time])

        csv_logger.close()

        self.logger.info(f"Done analyzing folder: {folder_path}")

        self.file_path = temp_path

        if self.file_path:
            self.plot_data()
        else:
            for widget in self.plot_frame.winfo_children():
                widget.destroy()

    # ----------------- PLOTTING ----------------- #
    def update_plot(self, change_message = ""):
        """Update the plot if a file is loaded and input changes."""
        if self.file_path:
            self.logger.info(f"Plot update triggered by input change. {change_message}")
            self.plot_data()

    def plot_data(self):
        """Read the CSV file and plot the temperature data with drift correction."""
        try:
            df = pd.read_csv(self.file_path)
            time, temp = df['Timestamp'], df['Temperature (Celsius)']
        except Exception as e:
            messagebox.showerror("CSV Error", f"Failed to read required columns: {e}")
            self.logger.error(f"Error while plotting data: {e}", exc_info = True)
            return None, None, None

        drift, compensated, smoothed = self.apply_drift_correction(
            time, temp, self.degree_var.get(), self.validate_string_number(self.smoothing_var, "smoothing")
        )
        transitions = self.find_transitions(smoothed, self.validate_string_number(self.transition_min_dist_var,
                                                                                  "min distance between transition points"))
        avg_amp = self.compute_amplitudes(smoothed, transitions)
        avg_rise, avg_fall, rise_fall_times = self.compute_rise_fall_times(time, smoothed, transitions)

        self.draw_plot(time, temp, drift, compensated, smoothed, transitions, avg_amp, avg_rise, avg_fall,
                       rise_fall_times, self.degree_var.get())

        return avg_amp, avg_rise, avg_fall

    def validate_string_number(self, string_var, variable_descr, fallback_value=10):
        """Retrieve and validate the string number value."""
        current_text = string_var.get().strip()

        # If the user is currently deleting/typing (empty box),
        # don't force a fallback yet.
        if not current_text:
            return fallback_value

        try:
            val = int(current_text)

            if val < 1:
                raise ValueError

            return val
        except ValueError:
            self.logger.warning(f"Invalid {variable_descr} value. Defaulting to {fallback_value}.")
            string_var.set(str(fallback_value))
            return fallback_value

    def draw_plot(self, time, temp, drift, compensated, smoothed, transitions, avg_amp, avg_rise_time, avg_fall_time,
                  rise_fall_times, degree):
        """Draw the temperature vs time plot with various corrections applied."""
        plt.close()
        fig, ax = plt.subplots()

        # Plot various temperature signals
        if self.show_temp.get():
            ax.plot(time, temp, label = 'Temperature (°C)', color = 'red')
        if self.show_compensated.get():
            ax.plot(time, compensated, label = f'Compensated (Degree {degree})', color = 'blue')
        if self.show_drift.get():
            ax.plot(time, drift, label = f'Drift (Degree {degree})', color = 'black')
        if self.show_smoothed.get():
            ax.plot(time, smoothed, label = 'Smoothed', color = 'green')

        # Mark transition, rise and fall points on the plot
        smooth_mean = np.mean(smoothed)
        if self.show_transitions.get() and transitions:
            ax.plot(time[transitions], [smooth_mean] * len(transitions), "k*", label = "Transitions")

        if self.show_rise_fall_times.get() and transitions:
            flat_list = [item for sublist in rise_fall_times for item in sublist]
            indices = np.searchsorted(time, flat_list)
            for i, x in enumerate(time[indices]):
                ax.axvline(x = x, color = 'k', linestyle = '--', linewidth = 1,
                           label = "Rise/Fall Time" if i == 0 else "")

        # Title and axes labels
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Temperature (°C)')
        if self.show_title.get():
            if transitions:
                ax.set_title(f'Temperature vs Time with Drift Compensation, ΔT = {avg_amp:.2f}°C\n'
                             f'Average rise/fall time: {avg_rise_time:.2f}s / {avg_fall_time:.2f}s')
            else:
                ax.set_title(f'Temperature vs Time with Drift Compensation, ΔT = --°C\n'
                             f'Average rise and fall time: --s and --s')

        ax.grid(True)

        if self.show_legend.get():
            ax.legend()

        # Clear any existing plot in the plot_frame (if re-plotting)
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create a Tkinter-compatible canvas to display the plot
        self.canvas = FigureCanvasTkAgg(fig, master = self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill = 'both', expand = True)

        self.plot_frame.pack(fill = 'x', pady = 10)
        self.plot_toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.plot_toolbar.update()
        self.plot_toolbar.pack(side = 'top', fill = 'x')

        # self.canvas.get_tk_widget().pack()

    # ----------------- APP CLOSURE ----------------- #
    def close_app(self):
        self.root.destroy()

    # ----------------- DATA PROCESSING ----------------- #
    def apply_drift_correction(self, time, temp, degree, window):
        """Apply polynomial drift correction and smoothing to the temperature data."""
        coeffs = np.polyfit(time, temp, degree)
        drift = np.polyval(coeffs, time)
        mean_signal = np.mean(temp)
        compensated = temp - drift + mean_signal
        smoothed = pd.Series(compensated).rolling(window = window, min_periods = 1).mean()
        return drift, compensated, smoothed

    def find_transitions(self, signal, min_distance = 50):
        """Find transition points in the signal based on threshold crossing."""
        threshold = np.mean(signal)
        raw_transitions = np.where(np.diff(signal > threshold))[0] + 1

        if len(raw_transitions) < 2:
            self.logger.warning("Not enough transition points found.")
            return None

        # Filter transitions to enforce minimum spacing
        filtered = [raw_transitions[0]]
        for t in raw_transitions[1:]:
            if t - filtered[-1] >= min_distance:
                filtered.append(t)

        if len(filtered) < 2:
            self.logger.warning("Filtered transitions too few. Returning None.")
            return None

        self.logger.info(f"Found {len(filtered)} transition points.")
        return filtered

    def compute_amplitudes(self, signal, transitions):
        """Compute the amplitude between transition points."""
        if not transitions or len(transitions) < 2:
            self.logger.warning("Cannot compute amplitude: insufficient transition points.")
            return None

        amplitudes = []
        start_idx = 0
        for i in range(len(transitions) - 1):
            wave = signal[start_idx:transitions[i + 1]]  # Extract segment between transitions
            amplitudes.append(np.max(wave) - np.min(wave))  # Calculate amplitude as the difference between max and min
            start_idx = transitions[i]  # Update start index for the next wave

        avg_amp = np.mean(amplitudes) if amplitudes else 0

        self.logger.info(f"Average amplitude: {avg_amp:.2f}")

        return avg_amp

    def compute_rise_fall_times(self, time, signal, transitions):
        """Compute rise and fall times between transitions based on 10%-90% amplitude crossing."""
        if not transitions:
            self.logger.warning(f"No enough transition points. Rise and fall times are not computed.")
            return None, None, None

        rise_times, fall_times = [], []
        rise_fall_times = [[], [], [], []]  # rise_starts, rise_ends, fall_starts, fall_ends

        avg_distance = np.mean(np.diff(transitions))
        window = int(avg_distance // 2)  # Half the distance between transitions

        for mid in transitions:
            start = max(0, mid - window)
            end = min(len(signal), mid + window)

            seg_time = time[start:end].reset_index(drop = True)
            seg_signal = signal[start:end].reset_index(drop = True)

            v_min, v_max = np.min(seg_signal), np.max(seg_signal)
            v_10, v_90 = v_min + 0.1 * (v_max - v_min), v_min + 0.9 * (v_max - v_min)

            # Rising or falling edge?
            rising = seg_signal.iloc[0] < seg_signal.iloc[-1]

            try:
                if rising:
                    t1 = seg_time[seg_signal >= v_10].iloc[0]
                    t2 = seg_time[seg_signal >= v_90].iloc[0]
                    rise_times.append(t2 - t1)
                    rise_fall_times[0].append(t1)
                    rise_fall_times[1].append(t2)
                else:
                    t1 = seg_time[seg_signal <= v_90].iloc[0]
                    t2 = seg_time[seg_signal <= v_10].iloc[0]
                    fall_times.append(t2 - t1)
                    rise_fall_times[2].append(t1)
                    rise_fall_times[3].append(t2)
            except IndexError:
                self.logger.warning(f"Transition near index {mid} has insufficient slope.")

        avg_rise = np.mean(rise_times) if rise_times else 0
        avg_fall = np.mean(fall_times) if fall_times else 0

        self.logger.info(f"Average rise time: {avg_rise:.3f}s, Average fall time: {avg_fall:.3f}s")
        return avg_rise, avg_fall, rise_fall_times


# ----------------- MAIN ----------------- #
if __name__ == "__main__":
    # Create and run the Tkinter application
    root = Tk()
    root.title("CSV File Plotter")
    app = TemperaturePlotterApp(root)


    def on_close():
        app.close_app()
        sys.exit(0)


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
