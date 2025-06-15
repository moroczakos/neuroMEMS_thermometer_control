import csv
import os
import time


class CsvLogger:
    def __init__(self):
        self.filename = None
        self.full_filename = None
        self.file_directory = None
        self.first_row = None
        self.csvfile = None
        self.writer = None

    def set_file_name(self, file_name):
        self.filename = file_name

    def set_file_directory(self, directory):
        os.makedirs(directory, exist_ok = True)  # Create the directory if it doesn't exist
        self.file_directory = directory

    def set_first_row(self, first_row):
        self.first_row = first_row

    def create(self):
        self.full_filename = os.path.join(self.file_directory, self.filename)
        self.csvfile = open(self.full_filename, 'w', newline = '')
        self.writer = csv.writer(self.csvfile)
        self.writer.writerow(self.first_row)
        return self.full_filename, self.csvfile, self.writer

    def close(self):
        if self.csvfile:
            time.sleep(0.5)
            self.csvfile.close()

    def get_full_filename(self):
        return self.full_filename

    def write_row(self, row):
        self.writer.writerow(row)
        self.csvfile.flush()
