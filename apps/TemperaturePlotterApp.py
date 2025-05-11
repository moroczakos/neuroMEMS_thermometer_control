import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog, Button, Label, Frame, Spinbox, IntVar, StringVar, Entry
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import Scrollbar, Text, END
import logging

# -------------------------------
# Logger Configuration
# -------------------------------
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    filename = 'app.log',
    filemode = 'a'  # Append log entries (instead of overwriting)
)
logger = logging.getLogger(__name__)


class TextHandler(logging.Handler):
    """Custom logging handler to display logs in a Tkinter Text widget."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        """Emit a log record."""
        msg = self.format(record)
        self.text_widget.after(0, self._write, msg)

    def _write(self, msg):
        """Insert log message into the Text widget."""
        self.text_widget.insert(END, msg + '\n')
        self.text_widget.see(END)  # Auto-scroll


class TemperaturePlotterApp:
    def __init__(self, root):
        """Initialize the GUI app."""
        self.root = root
        self.root.title("CSV File Plotter")

        self.file_path = None  # To store the file path selected by user
        self.plot_toolbar = None  # Toolbar for the plot (if it exists)
        self.degree_var = IntVar(value = 1)  # Default polynomial degree value
        self.smoothing_var = StringVar(value = "50")  # Default smoothing window value (as string)

        self.setup_ui()
        self.setup_logger_panel()
        logger.info("Application started and UI initialized.")

    def setup_logger_panel(self):
        """Set up a panel in the UI to display logs."""
        log_frame = Frame(self.root)
        log_frame.pack(fill = 'both', padx = 10, pady = (5, 10), expand = False)

        scrollbar = Scrollbar(log_frame)
        scrollbar.pack(side = 'right', fill = 'y')

        self.log_text = Text(log_frame, height = 10, wrap = 'word', yscrollcommand = scrollbar.set)
        self.log_text.pack(side = 'left', fill = 'both', expand = True)
        scrollbar.config(command = self.log_text.yview)

        # Attach the custom TextHandler to capture log entries and display them
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_handler)

    def setup_ui(self):
        """Set up the main user interface components."""
        self.file_label = Label(self.root, text = "No file selected.", width = 50)
        self.file_label.pack(pady = 10)

        self.plot_frame = Frame(self.root)  # Frame to hold the plot
        self.plot_frame.pack(padx = 10, pady = 10, fill = 'both', expand = True)

        controls_frame = Frame(self.root)  # Frame for control widgets (spinboxes, buttons, etc.)
        controls_frame.pack(pady = 10)

        # Polynomial Degree Controls (Spinbox)
        Label(controls_frame, text = "Polynomial Degree:").pack(side = "left", padx = (0, 5))
        Spinbox(controls_frame, from_ = 0, to = 5, textvariable = self.degree_var, width = 5).pack(side = "left",
                                                                                                   padx = (0, 20))
        self.degree_var.trace("w", self.update_plot_if_file_loaded)  # Update plot when value changes

        # Smoothing Window Controls (Entry)
        Label(controls_frame, text = "Smoothing Window (data point):").pack(side = "left")
        Entry(controls_frame, textvariable = self.smoothing_var, width = 5).pack(side = "left", padx = (0, 20))
        self.smoothing_var.trace("w", self.update_plot_if_file_loaded)  # Update plot when value changes

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
        else:
            self.file_label.config(text = "No file selected.")
            logger.warning("No file was selected.")

    def update_plot_if_file_loaded(self, *args):
        """Update the plot if a file is loaded and input changes."""
        if self.file_path:
            logger.info("Plot update triggered by input change.")
            self.plot_data()

    def plot_data(self):
        """Read the CSV file and plot the temperature data with drift correction."""
        try:
            df = pd.read_csv(self.file_path)
            logger.info("CSV file successfully read into DataFrame.")
            time = df['Timestamp']
            temp = df['Temperature (°C)']
            poly_degree = self.degree_var.get()
            smoothing_window = self.get_smoothing_window()

            # Apply drift correction and smoothing
            logger.info(f"Applying drift correction (degree={poly_degree}, smoothing={smoothing_window})")
            drift, compensated, smoothed = self.apply_drift_correction(time, temp, poly_degree, smoothing_window)

            # Find transition points in the smoothed signal
            transitions = self.find_transitions(smoothed)

            # Compute average amplitude between transition points
            average_amplitude = self.compute_amplitudes(smoothed, transitions)

            # Draw the plot with the processed data
            self.draw_plot(time, temp, drift, compensated, smoothed, transitions, average_amplitude, poly_degree)
            logger.info("Plotting completed.")
        except Exception as e:
            logger.error(f"Error while plotting data: {e}", exc_info = True)

    def get_smoothing_window(self):
        """Retrieve and validate the smoothing window value."""
        try:
            val = int(self.smoothing_var.get())
            return max(1, val)
        except ValueError:
            logger.warning("Invalid smoothing value entered. Defaulting to 10.")
            return 10  # Default fallback

    def apply_drift_correction(self, time, temp, degree, window):
        """Apply polynomial drift correction and smoothing to the temperature data."""
        coeffs = np.polyfit(time, temp, degree)
        drift = np.polyval(coeffs, time)
        mean_signal = np.mean(temp)
        compensated = temp - drift + mean_signal
        smoothed = pd.Series(compensated).rolling(window = window, min_periods = 1).mean()
        return drift, compensated, smoothed

    def find_transitions(self, signal, threshold=None, min_distance=50):
        """Find the transition points in the signal."""
        threshold = threshold if threshold is not None else np.mean(signal)
        transitions = np.where(np.diff(signal > threshold))[0] + 1  # Find points where signal crosses threshold

        # Filter transitions to ensure they are spaced by at least min_distance
        filtered = [transitions[0]]
        for i in range(1, len(transitions)):
            if transitions[i] - transitions[i - 1] >= min_distance:
                filtered.append(transitions[i])
        logger.info(f"Found {len(filtered)} transition points.")
        return filtered

    def compute_amplitudes(self, signal, transitions):
        """Compute the amplitude between transition points."""
        amplitudes = []
        start_idx = 0
        for i in range(len(transitions) - 1):
            wave = signal[start_idx:transitions[i + 1]]  # Extract segment between transitions
            amplitudes.append(np.max(wave) - np.min(wave))  # Calculate amplitude as the difference between max and min
            start_idx = transitions[i]  # Update start index for the next wave
        avg_amp = np.mean(amplitudes) if amplitudes else 0
        logger.info(f"Average amplitude computed: {avg_amp:.2f}")
        return avg_amp

    def draw_plot(self, time, temp, drift, compensated, smoothed, transitions, avg_amp, degree):
        """Draw the temperature vs time plot with various corrections applied."""
        fig, ax = plt.subplots(figsize = (8, 6))

        # Plot various temperature signals
        ax.plot(time, temp, label = 'Temperature (°C)', color = 'red')
        ax.plot(time, compensated, label = f'Compensated (Degree {degree})', color = 'blue')
        ax.plot(time, drift, label = f'Drift (Degree {degree})', color = 'black')
        ax.plot(time, smoothed, label = 'Smoothed', color = 'green')

        # Mark transition points on the plot
        ax.plot(time[transitions], [np.mean(smoothed)] * len(transitions), "k*", label = "Transitions")

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Temperature (°C)')
        ax.set_title(f'Temperature vs Time with Drift Compensation, ΔT = {avg_amp:.2f}°C')
        ax.grid(True)
        ax.legend()

        # Clear any existing plot in the plot_frame (if re-plotting)
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create a Tkinter-compatible canvas to display the plot
        canvas = FigureCanvasTkAgg(fig, master = self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill = 'both', expand = True)

        # Initialize the plot toolbar if it does not already exist
        if self.plot_toolbar is None:
            toolbar_frame = Frame(self.root)
            toolbar_frame.pack(fill = 'x', pady = 10)
            self.plot_toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            self.plot_toolbar.update()
            self.plot_toolbar.pack(side = 'top', fill = 'x')

        canvas.get_tk_widget().pack()


if __name__ == "__main__":
    # Create and run the Tkinter application
    root = Tk()
    app = TemperaturePlotterApp(root)
    root.mainloop()
