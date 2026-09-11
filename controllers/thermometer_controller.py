class ThermometerController:
    def __init__(self, model, view):
        self._model = model
        self._view = view
        self._view.set_start_button_command(self.start_measurement)
        self._view.set_stop_button_command(self.stop_measurement)
        self._view.set_start_preview_button_command(self.start_preview)
        self._view.set_stop_preview_button_command(self.stop_preview)

        self._model.load_settings()
        self._model.attach(self._view)

    def set_start_with_cycle_app(self, value):
        self._model.set_start_with_cycle_app(value)

    def is_running(self):
        return self._model.running or self._view.running or self._model.preview_running

    def attach_to_model(self, observer):
        self._model.attach(observer)

    def start_measurement(self):
        self._model.set_instrument_alias(self._view.get_instrument_alias())

        # Apply loading window
        visa_resource = self._view.get_visa_resource()
        if not self._view.loading_connection(lambda: self._model.connect_instrument(visa_resource)):
            return

        self._view.set_started_measurement_controls()
        self._model.load_settings()
        self._model.set_R0_TCR(self._view.get_R0_TCR())
        self._model.set_probe_name(self._view.get_probe_name())
        self._model.start_data_collection()
        self._view.start_live_display()

    def stop_measurement(self):
        self._model.stop_data_collection()
        self._model.stop_data_preview()
        self._view.show_measurement_stopped()
        self._view.stop_preview()
        self._view.enable_controls()

    def start_preview(self):
        self._model.set_instrument_alias(self._view.get_instrument_alias())

        # Apply loading window
        visa_resource = self._view.get_visa_resource()
        if not self._view.loading_connection(lambda: self._model.connect_instrument(visa_resource)):
            return

        self._view.set_started_preview_controls()
        self._model.load_settings()
        self._model.set_R0_TCR(self._view.get_R0_TCR())
        self._model.set_probe_name(self._view.get_probe_name())
        self._model.start_data_preview()
        self._view.start_preview()

    def stop_preview(self):
        self._model.stop_data_preview()
        self._view.enable_controls()
        self._view.stop_preview()

    def enable_controls(self):
        self._view.enable_controls()

    def disable_controls(self):
        self._view.disable_controls()
