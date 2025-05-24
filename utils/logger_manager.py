import logging
from functools import wraps
from tkinter import messagebox


class LoggerManager:
    def __init__(self, log_file="../logs/app.log"):
        self.logger = logging.getLogger(f"{id(self)}")
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_file, mode = 'a')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger


def safe_execute(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}", exc_info = True)
            messagebox.showerror("Unexpected Error", f"An error occurred:\n{e}")

    return wrapper
