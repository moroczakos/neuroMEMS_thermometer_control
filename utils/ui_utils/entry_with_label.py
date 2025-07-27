from tkinter import Widget, ttk


class EntryWithLabel(ttk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master)

        self.label_text = kw["labeltext"]
        self.entry_text_variable = kw["entrytextvariable"]
        self.entry_with = kw["entrywidth"]
        self.entry_justify = kw["entryjustify"]
        self.command = kw.get("command")
        self.save_entry_text_variable_command = kw.get("saveentrytextvariablecommand")
        self.save_command_key = kw.get("savecommandkey")

        self.label_widget = ttk.Label(self, text = self.label_text)
        self.entry = ttk.Entry(self, textvariable = self.entry_text_variable, width = self.entry_with,
                               justify = self.entry_justify)

        self.label_widget.grid(row = 0, column = 0, sticky = "w")
        self.entry.grid(row = 0, column = 1, sticky = "ew")

        def all_trace_callback(k, v):
            if self.save_entry_text_variable_command:
                self.save_entry_text_variable_command(k, v)
            if self.command:
                self.command()

        if self.save_entry_text_variable_command and self.save_command_key:
            self.entry_text_variable.trace_add("write",
                                               lambda *args: all_trace_callback(self.save_command_key,
                                                                                self.entry_text_variable))

    def get_entry(self):
        return self.entry

    def get_label(self):
        return self.label_widget

    def get_widgets(self):
        return self.get_label(), self.get_entry()
