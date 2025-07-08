class CurrentCycleController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_start_button_command(self.start_measurement)
        self.view.set_stop_button_command(self.stop_measurement)

        self.model.load_settings()
        self.model.attach(self.view)

    def is_running(self):
        return self.model.running or self.view.running

    def attach_to_model(self, observer):
        self.model.attach(observer)

    def start_measurement(self):
        # Apply loading window
        visa_resource = self.view.get_visa_resource()
        if not self.view.loading_connection(lambda: self.model.connect_instrument(visa_resource)):
            return

        self.model.configure_device()
        self.view.set_started_current_cycle_controls()
        self.model.load_settings()
        self.model.start_data_collection()
        self.view.start_live_display()

    def stop_measurement(self):
        self.model.stop_data_collection()
        self.view.enable_controls()
        self.view.show_measurement_stopped()

    def update_other_setting(self, key):
        self.model.update_other_setting(key)
        self.view.update_other_setting_display(self.model.other_setting_value)

    def enable_controls(self):
        self.view.enable_controls()

    def disable_controls(self):
        self.view.disable_controls()
