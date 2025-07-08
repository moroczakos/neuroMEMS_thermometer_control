class ThermometerController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_start_button_command(self.start_measurement)
        self.view.set_stop_button_command(self.stop_measurement)
        self.view.set_start_preview_button_command(self.start_preview)
        self.view.set_stop_preview_button_command(self.stop_preview)

        self.model.load_settings()
        self.model.attach(self.view)

    def is_running(self):
        return self.model.running or self.view.running or self.model.preview_running

    def attach_to_model(self, observer):
        self.model.attach(observer)

    def start_measurement(self):
        # Apply loading window
        visa_resource = self.view.get_visa_resource()
        if not self.view.loading_connection(lambda: self.model.connect_instrument(visa_resource)):
            return

        self.view.set_started_measurement_controls()
        self.model.load_settings()
        self.model.set_R0_TCR(self.view.get_R0_TCR())
        self.model.set_probe_name(self.view.get_probe_name())
        self.model.start_data_collection()
        self.view.start_live_display()

    def stop_measurement(self):
        self.model.stop_data_collection()
        self.model.stop_data_preview()
        self.view.enable_controls()
        self.view.show_measurement_stopped()
        self.view.stop_preview()

    def start_preview(self):
        # Apply loading window
        visa_resource = self.view.get_visa_resource()
        if not self.view.loading_connection(lambda: self.model.connect_instrument(visa_resource)):
            return

        self.view.set_started_preview_controls()
        self.model.set_R0_TCR(self.view.get_R0_TCR())
        self.model.start_data_preview()
        self.view.start_preview()

    def stop_preview(self):
        self.model.stop_data_preview()
        self.view.enable_controls()
        self.view.stop_preview()

    def enable_controls(self):
        self.view.enable_controls()

    def disable_controls(self):
        self.view.disable_controls()
