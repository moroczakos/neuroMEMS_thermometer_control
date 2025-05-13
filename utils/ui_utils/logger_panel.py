import logging
from tkinter import Frame, Text, Scrollbar, END


class LoggingPanel(Frame):
    """A reusable logging panel for Tkinter applications."""

    def __init__(self, master, logger=None, height=10, **kwargs):
        super().__init__(master, **kwargs)

        self.text_widget = Text(self, height = height, wrap = 'word')
        self.scrollbar = Scrollbar(self, command = self.text_widget.yview)

        self.text_widget.configure(yscrollcommand = self.scrollbar.set)
        self.text_widget.pack(side = 'left', fill = 'both', expand = True)
        self.scrollbar.pack(side = 'right', fill = 'y')

        self.handler = self.TextHandler(self.text_widget)
        self.handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        if logger:
            logger.addHandler(self.handler)

    def get_handler(self):
        return self.handler

    class TextHandler(logging.Handler):
        """Custom logging handler to insert log messages into a Tkinter Text widget."""

        def __init__(self, text_widget):
            super().__init__()
            self.text_widget = text_widget

        def emit(self, record):
            msg = self.format(record)
            self.text_widget.after(0, self._write, msg)

        def _write(self, msg):
            self.text_widget.insert(END, msg + '\n')
            self.text_widget.see(END)
