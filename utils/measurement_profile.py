class MeasurementProfile:
    def __init__(self, name, headers, y1_label, y2_label, measure_func, post_process_func=None):
        self.name = name
        self.headers = headers
        self.y1_label = y1_label
        self.y2_label = y2_label
        self.measure_func = measure_func
        self.post_process_func = post_process_func
