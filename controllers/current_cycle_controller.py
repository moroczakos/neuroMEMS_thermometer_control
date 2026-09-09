class CurrentCycleController:
    def __init__(self, model, view):
        self._model = model
        self._view = view
        self._view.set_start_button_command(self.start_measurement)
        self._view.set_stop_button_command(self.stop_measurement)

        self._model.load_settings()
        self._model.attach(self._view)

    def is_running(self):
        return self._model.running or self._view.running

    def attach_to_model(self, observer):
        self._model.attach(observer)

    def get_current(self):
        return self._model.get_current()

    def set_current_and_start(self, current_value):
        # Apply loading window
        visa_resource = self._view.get_visa_resource()
        if not self._view.loading_connection(lambda: self._model.connect_instrument(visa_resource)):
            return

        self._model.configure_device()
        self._view.set_started_current_cycle_controls()
        self._model.load_settings()
        self._model.set_current_and_start(current_value)

    def stop_current(self):
        self._model.stop_current()
        self._view.enable_controls()

    def start_measurement(self):
        # Apply loading window
        visa_resource = self._view.get_visa_resource()
        if not self._view.loading_connection(lambda: self._model.connect_instrument(visa_resource)):
            return

        self._model.configure_device()
        self._view.set_started_current_cycle_controls()
        self._model.load_settings()
        self._model.start_data_collection()
        self._view.start_live_display()

    def stop_measurement(self):
        self._model.stop_data_collection()
        self._view.enable_controls()
        self._view.show_measurement_stopped()

    def update_other_setting(self, key):
        self._model.update_other_setting(key)
        self._view.update_other_setting_display(self._model.other_setting_value)

    def enable_controls(self):
        self._view.enable_controls()

    def disable_controls(self):
        self._view.disable_controls()
