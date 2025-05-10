import csv
from datetime import datetime
import os


class CsvLogger:
    def __init__(self):
        self.filename = None
        self.csvfile = None
        self.writer = None

    def create(self, prefix, headers, directory=None):
        self.filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if directory:
            self.filename = os.path.join(directory, self.filename)
        self.csvfile = open(self.filename, 'w', newline = '')
        self.writer = csv.writer(self.csvfile)
        self.writer.writerow(headers)
        return self.filename, self.csvfile, self.writer

    def close(self):
        if self.csvfile:
            self.csvfile.close()

    def get_filename(self):
        return self.filename

    def write_row(self, row):
        self.writer.writerow(row)
        self.csvfile.flush()
