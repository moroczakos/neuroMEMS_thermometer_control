from tkinter import ttk
from tkinter import Frame
from apps.TemperatureMeasurementStationApp import TemperatureMeasurementStationApp
from apps.TemperaturePlotterApp import TemperaturePlotterApp
from apps.TemperatureByRecalibratedProbeDataApp import TemperatureByRecalibratedProbeDataApp
from apps.settings_app import SettingsApp


class CombinedApp:
    def __init__(self, root):
        self.root = root

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill = 'both', expand = True)

        # Create tab containers
        self.tab1 = Frame(self.notebook)
        self.tab2 = Frame(self.notebook)
        self.tab3 = Frame(self.notebook)
        self.tab4 = Frame(self.notebook)

        # Add tabs to the notebook
        self.notebook.add(self.tab1, text = "Temperature measurement station")
        self.notebook.add(self.tab2, text = "Temperature plotter")
        self.notebook.add(self.tab3, text = "Temperature recalculation")
        self.notebook.add(self.tab4, text = "Settings")

        # Instantiate apps into each tab
        self.station_app = TemperatureMeasurementStationApp(self.tab1)
        self.plotter_app = TemperaturePlotterApp(self.tab2)
        self.recalibration_app = TemperatureByRecalibratedProbeDataApp(self.tab3)
        self.settings_app = SettingsApp(self.tab4)

    def close_app(self):
        if self.station_app.close_app():
            self.plotter_app.close_app()
            self.recalibration_app.close_app()
            self.settings_app.close_app()
            return True

        return False
