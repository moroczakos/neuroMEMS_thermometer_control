import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog, Button, Label, Frame, Spinbox, IntVar, StringVar, Entry, Checkbutton
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from base_classes.main_base import MainBase
from base_classes.view_base import ViewBase


class TemperaturePlotterApp(MainBase, ViewBase):
    def __init__(self, root):
        """Initialize the GUI app."""
        MainBase.__init__(self)
        ViewBase.__init__(self, root, self.setting_manager, self.logger)

        self.root = Frame(root)
        self.root.pack(fill = 'both', expand = True)

        self.file_path = None  # To store the file path selected by user
        self.plot_toolbar = None  # Toolbar for the plot (if it exists)
        self.degree_var = IntVar(value = 1)  # Default polynomial degree value
        self.smoothing_var = StringVar(value = "50")  # Default smoothing window value (as string)

        # Checkbox variables for showing/hiding plot elements
        self.show_temp = IntVar(value = 1)
        self.show_compensated = IntVar(value = 1)
        self.show_drift = IntVar(value = 1)
        self.show_smoothed = IntVar(value = 1)
        self.show_transitions = IntVar(value = 1)
        self.show_rise_fall_times = IntVar(value = 1)
        self.show_title = IntVar(value = 1)
        self.show_legend = IntVar(value = 1)

        # Logger
        self.setup_logger("temperature_plotter_app.log")

        self.setup_ui()
        self.setup_logger_panel()

    def setup_ui(self):
        """Set up the main user interface components."""
        self.file_label = Label(self.root, text = "No file selected.", width = 50)
        self.file_label.pack(pady = 10)

        self.plot_frame = Frame(self.root)  # Frame to hold the plot
        self.plot_frame.pack(padx = 10, pady = 10, fill = 'both', expand = True)

        checkbox_frame = Frame(self.root)
        checkbox_frame.pack(pady = 5)

        Label(checkbox_frame, text = "Show:").pack(side = "left", padx = (0, 10))
        text_width = 10

        def get_checkbox_state(state):
            if state.get() == 1:
                return "checked"
            else:
                return "unchecked"

        Checkbutton(checkbox_frame, text = "Raw Temp", variable = self.show_temp,
                    command = lambda: self.update_plot(f"Raw Temp checkbox {get_checkbox_state(self.show_temp)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Compensated", variable = self.show_compensated,
                    command = lambda: self.update_plot(
                        f"Compensated checkbox {get_checkbox_state(self.show_compensated)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Drift", variable = self.show_drift,
                    command = lambda: self.update_plot(
                        f"Drift checkbox {get_checkbox_state(self.show_drift)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Smoothed", variable = self.show_smoothed,
                    command = lambda: self.update_plot(
                        f"Smoothed checkbox {get_checkbox_state(self.show_smoothed)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Transitions", variable = self.show_transitions,
                    command = lambda: self.update_plot(
                        f"Transitions checkbox {get_checkbox_state(self.show_transitions)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Rise/Fall Times", variable = self.show_rise_fall_times,
                    command = lambda: self.update_plot(
                        f"Rise/Fall Times checkbox {get_checkbox_state(self.show_rise_fall_times)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Title", variable = self.show_title,
                    command = lambda: self.update_plot(
                        f"Title checkbox {get_checkbox_state(self.show_title)}."),
                    width = text_width).pack(side = "left")
        Checkbutton(checkbox_frame, text = "Legend", variable = self.show_legend,
                    command = lambda: self.update_plot(
                        f"Legend checkbox {get_checkbox_state(self.show_legend)}."),
                    width = text_width).pack(side = "left")

        controls_frame = Frame(self.root)  # Frame for control widgets (spinboxes, buttons, etc.)
        controls_frame.pack(pady = 10)

        # Polynomial Degree Controls (Spinbox)
        Label(controls_frame, text = "Polynomial Degree:").pack(side = "left", padx = (0, 5))
        Spinbox(controls_frame, from_ = 0, to = 5, textvariable = self.degree_var, width = 5).pack(side = "left",
                                                                                                   padx = (0, 20))
        self.degree_var.trace("w", lambda *args: self.update_plot(
            f"Polynomial Degree is {self.degree_var.get()}."))  # Update plot when value changes

        # Smoothing Window Controls (Entry)
        Label(controls_frame, text = "Smoothing Window (data point):").pack(side = "left")
        Entry(controls_frame, textvariable = self.smoothing_var, width = 5).pack(side = "left", padx = (0, 20))
        self.smoothing_var.trace("w", lambda *args: self.update_plot(
            f"Smoothing Window is {self.smoothing_var.get()}."))  # Update plot when value changes

        Button(self.root, text = "Select File and Plot", command = self.select_file_and_plot).pack(pady = 20)

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

    def update_plot(self, change_message = ""):
        """Update the plot if a file is loaded and input changes."""
        if self.file_path:
            self.logger.info(f"Plot update triggered by input change. {change_message}")
            self.plot_data()

    def plot_data(self):
        """Read the CSV file and plot the temperature data with drift correction."""
        try:
            df = pd.read_csv(self.file_path)
            self.logger.info("CSV file successfully read into DataFrame.")
            try:
                time = df['Timestamp']
            except Exception as e:
                messagebox.showerror("No time data",
                                     f"The imported csv file does not contain 'Timestamp' column.")
                self.logger.error(f"Error while plotting data: {e}", exc_info = True)
                return

            try:
                temp = df['Temperature (Celsius)']
            except Exception as e:
                messagebox.showerror("No temperature data",
                                     f"The imported csv file does not contain 'Temperature (Celsius)' column.")
                self.logger.error(f"Error while plotting data: {e}", exc_info = True)
                return

            poly_degree = self.degree_var.get()
            smoothing_window = self.get_smoothing_window()

            # Apply drift correction and smoothing
            self.logger.info(f"Applying drift correction (degree={poly_degree}, smoothing={smoothing_window})")
            drift, compensated, smoothed = self.apply_drift_correction(time, temp, poly_degree, smoothing_window)

            # Find transition points in the smoothed signal
            transitions = self.find_transitions(smoothed)

            # Compute average amplitude between transition points
            average_amplitude = self.compute_amplitudes(smoothed, transitions)

            # Compute average rise and fall time
            avg_rise_time, avg_fall_time, rise_fall_times = self.compute_rise_fall_times(time, smoothed, transitions)

            # Draw the plot with the processed data
            self.draw_plot(time, temp, drift, compensated, smoothed, transitions, average_amplitude, avg_rise_time,
                           avg_fall_time, rise_fall_times, poly_degree)
            self.logger.info("Plotting completed.")
        except Exception as e:
            self.logger.error(f"Error while plotting data: {e}", exc_info = True)

    def get_smoothing_window(self):
        """Retrieve and validate the smoothing window value."""
        try:
            val = int(self.smoothing_var.get())
            return max(1, val)
        except ValueError:
            self.logger.warning("Invalid smoothing value entered. Defaulting to 10.")
            return 10  # Default fallback

    def apply_drift_correction(self, time, temp, degree, window):
        """Apply polynomial drift correction and smoothing to the temperature data."""
        coeffs = np.polyfit(time, temp, degree)
        drift = np.polyval(coeffs, time)
        mean_signal = np.mean(temp)
        compensated = temp - drift + mean_signal
        smoothed = pd.Series(compensated).rolling(window = window, min_periods = 1).mean()
        return drift, compensated, smoothed

    def find_transitions(self, signal, threshold = None, min_distance = 50):
        """Find the transition points in the signal."""
        threshold = threshold if threshold is not None else np.mean(signal)
        transitions = np.where(np.diff(signal > threshold))[0] + 1  # Find points where signal crosses threshold

        # Filter transitions to ensure they are spaced by at least min_distance
        filtered = [transitions[0]]
        for i in range(1, len(transitions)):
            if transitions[i] - transitions[i - 1] >= min_distance:
                filtered.append(transitions[i])
        self.logger.info(f"Found {len(filtered)} transition point(s).")

        if len(filtered) < 2:
            self.logger.warning(f"No enough transition points.")
            return None

        return filtered

    def compute_amplitudes(self, signal, transitions):
        """Compute the amplitude between transition points."""
        if not transitions:
            self.logger.warning(f"No enough transition points. Average amplitude is not computed.")
            return None

        amplitudes = []
        start_idx = 0
        for i in range(len(transitions) - 1):
            wave = signal[start_idx:transitions[i + 1]]  # Extract segment between transitions
            amplitudes.append(np.max(wave) - np.min(wave))  # Calculate amplitude as the difference between max and min
            start_idx = transitions[i]  # Update start index for the next wave
        avg_amp = np.mean(amplitudes) if amplitudes else 0
        self.logger.info(f"Average amplitude computed: {avg_amp:.2f}")
        return avg_amp

    def compute_rise_fall_times(self, time, signal, transitions):
        """Compute rise and fall times between transitions based on 10%-90% amplitude crossing."""
        if not transitions:
            self.logger.warning(f"No enough transition points. Rise and fall times are not computed.")
            return None, None, None

        rise_times = []
        rise_time_starts = []
        rise_time_ends = []
        fall_times = []
        fall_time_starts = []
        fall_time_ends = []

        avg_distance = np.mean(np.diff(transitions))
        window = int(avg_distance // 2)  # Half the distance between transitions

        for mid_idx in transitions:
            start = max(0, mid_idx - window)
            end = min(len(signal), mid_idx + window)

            segment_time = time[start:end].reset_index(drop = True)
            segment_signal = signal[start:end].reset_index(drop = True)

            v_min = np.min(segment_signal)
            v_max = np.max(segment_signal)
            v_range = v_max - v_min
            v_10 = v_min + 0.1 * v_range
            v_90 = v_min + 0.9 * v_range

            # Rising or falling edge?
            rising = segment_signal.iloc[0] < segment_signal.iloc[-1]

            try:
                if rising:
                    t1 = segment_time[segment_signal >= v_10].iloc[0]
                    t2 = segment_time[segment_signal >= v_90].iloc[0]
                    rise_times.append(t2 - t1)
                    rise_time_starts.append(t1)
                    rise_time_ends.append(t2)
                else:
                    t1 = segment_time[segment_signal <= v_90].iloc[0]
                    t2 = segment_time[segment_signal <= v_10].iloc[0]
                    fall_times.append(t2 - t1)
                    fall_time_starts.append(t1)
                    fall_time_ends.append(t2)
            except IndexError:
                self.logger.warning(f"Edge near transition at {mid_idx} has insufficient slope/resolution.")

        avg_rise = np.mean(rise_times) if rise_times else 0
        avg_fall = np.mean(fall_times) if fall_times else 0

        self.logger.info(f"Average Rise Time: {avg_rise:.3f} s, Average Fall Time: {avg_fall:.3f} s")
        return avg_rise, avg_fall, [rise_time_starts, rise_time_ends, fall_time_starts, fall_time_ends]

    def draw_plot(self, time, temp, drift, compensated, smoothed, transitions, avg_amp, avg_rise_time, avg_fall_time,
                  rise_fall_times, degree):
        """Draw the temperature vs time plot with various corrections applied."""
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
                             f'Average rise and fall time: {avg_rise_time:.2f}s and {avg_fall_time:.2f}s')
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
        canvas = FigureCanvasTkAgg(fig, master = self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill = 'both', expand = True)

        self.plot_frame.pack(fill = 'x', pady = 10)
        self.plot_toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
        self.plot_toolbar.update()
        self.plot_toolbar.pack(side = 'top', fill = 'x')

        canvas.get_tk_widget().pack()

    def close_app(self):
        self.root.destroy()


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
