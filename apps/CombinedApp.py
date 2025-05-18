import tkinter as tk
from tkinter import ttk
from tkinter import Frame
from apps.TemperatureMeasurementStationApp import TemperatureMeasurementStationApp
from apps.TemperaturePlotterApp import TemperaturePlotterApp
from apps.TemperatureByRecalibratedProbeDataApp import TemperatureByRecalibratedProbeDataApp


class CombinedApp:
    def __init__(self, root):
        self.root = root

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill = 'both', expand = True)

        # Create tab containers
        self.tab1 = Frame(self.notebook)
        self.tab2 = Frame(self.notebook)
        self.tab3 = Frame(self.notebook)

        # Add tabs to the notebook
        self.notebook.add(self.tab1, text = "Temperature measurement station")
        self.notebook.add(self.tab2, text = "Temperature plotter")
        self.notebook.add(self.tab3, text = "Temperature recalculation")

        # Instantiate apps into each tab
        self.app1 = TemperatureMeasurementStationApp(self.tab1)
        self.app2 = TemperaturePlotterApp(self.tab2)
        self.app3 = TemperatureByRecalibratedProbeDataApp(self.tab3)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Combined Apps in Tabs")
    root.geometry("1600x900")
    app = CombinedApp(root)
    root.mainloop()
