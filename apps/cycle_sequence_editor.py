import os
import tkinter as tk
import traceback
from tkinter import ttk, messagebox, filedialog
import json

from utils.constants import Keys
from utils.ui_utils.tooltip import ToolTip


class CycleSequenceEditor(tk.Tk):
    def __init__(self, setting_manager, logger):
        super().__init__()

        self.title("Cycle Sequence Editor")
        self.geometry("650x450")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Settings
        self.project_root = ".."  # find_project_root()
        self.setting_manager = setting_manager
        self.input_file_path = os.path.join(self.project_root, self.setting_manager.load_setting("input_files"))
        self.logger = logger

        # Frame to hold Treeview and scrollbar together
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill = tk.BOTH, expand = True, padx = 10, pady = 10)

        # Treeview widget
        self.tree = ttk.Treeview(tree_frame, columns = ("Step", "Current", "Duration"), show = "headings",
                                 selectmode = "browse")
        self.tree.tag_configure("offset", background = "#e0e0e0")
        self.tree.heading("Step", text = "Step #")
        self.tree.heading("Current", text = "Current (A)")
        self.tree.heading("Duration", text = "Duration (s)")

        self.tree.column("Step", width = 40, anchor = "center")
        self.tree.column("Current", anchor = "center", width = 200)
        self.tree.column("Duration", anchor = "center", width = 200)
        self.tree.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)

        # Vertical scrollbar
        scrollbar = tk.Scrollbar(tree_frame, orient = tk.VERTICAL, command = self.tree.yview)
        scrollbar.pack(side = tk.RIGHT, fill = tk.Y)

        self.tree.configure(yscrollcommand = scrollbar.set)

        self.tree.bind("<Double-1>", self._on_double_click)

        # Control buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady = 5)

        tk.Button(button_frame, text = "Add Step", command = self._add_step).grid(row = 0, column = 0, padx = 5)
        tk.Button(button_frame, text = "Remove Selected", command = self._remove_selected).grid(row = 0, column = 1,
                                                                                                padx = 5)
        tk.Button(button_frame, text = "Move Up", command = self._move_up).grid(row = 0, column = 2, padx = 5)
        tk.Button(button_frame, text = "Move Down", command = self._move_down).grid(row = 0, column = 3, padx = 5)
        tk.Button(button_frame, text = "Load", command = self._import_json).grid(row = 0, column = 4, padx = 5)
        tk.Button(button_frame, text = "Save", command = self._export_json).grid(row = 0, column = 5, padx = 5)

        self.info_label = tk.Label(button_frame, text = "ⓘ", font = ("Arial", 12), bd = 1, relief = "solid",
                                   bg = "#e0e0e0", padx = 5, pady = 2)
        self.info_label.grid(row = 0, column = 6, padx = 5)
        ToolTip(self.info_label,
                "Description of the Cycle Sequence Editor.\n \n"
                "This editor is used to determine the shape of the current source.\n"
                "The consecutive steps determine one cycle. One step contains the \n"
                "duration of the set current.\n"
                "These steps within a cycle are repeated n times when the 'Current \n"
                "source app' is started. The number of cycles is determined by the \n"
                "'Cycles' field of the 'Current source app'. A preview is also shown \n"
                "in the app.\n"
                "The offset is used once before the first cycle.\n"
                "Is it possible to load/save the steps from/to a JSON file.",
                text_alignment = "left")

        self.entry_popup = None

        self.logger.info(f"Cycle Sequence Editor is opened.")

        # Load default cycle JSON on startup
        default_file = os.path.join(self.input_file_path, self.setting_manager.load_setting(Keys.CYCLE_SEQUENCE_FILE))
        if os.path.exists(default_file):
            self.logger.info(f"Loading default cycle file: {default_file}")
            self._load_json_file(default_file)
        else:
            self.logger.warning(f"Default file {default_file} not found, adding empty step.")
            self._add_step()  # Add default empty step if no file

    def _load_json_file(self, file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            self.tree.delete(*self.tree.get_children())
            for idx, step in enumerate(data, start = 1):
                current = step.get("current")
                duration = step.get("duration")
                self.tree.insert("", "end", values = (idx, current, duration))

            self._renumber_steps()
            self.logger.info(f"Successfully loaded cycle data from {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load default JSON: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to load default JSON:\n{e}")
            self._keep_window_top()

            self._add_step()

    def _add_step(self, current = "0.01", duration = "1.0"):
        step_number = len(self.tree.get_children())
        if step_number == 0:
            self.logger.info("Offset row is missing, inserting Offset.")
            self.tree.insert("", "end", values = ("Offset", "0.0", "0.0"), tags = ("offset",))  # Offset step
            step_number += 1

        self.logger.info(f"Added step #{step_number}: current={current} A, duration={duration} s")
        self.tree.insert("", "end", values = (step_number, current, duration))
        self._renumber_steps()

    def _renumber_steps(self):
        children = self.tree.get_children()
        for idx, row in enumerate(children):
            current, duration = self.tree.item(row, "values")[1:]
            if idx == 0:
                step_number = "Offset"
                self.tree.item(row, values = (step_number, current, duration), tags = ("offset",))
            else:
                step_number = str(idx)
                self.tree.item(row, values = (step_number, current, duration))

    def _remove_selected(self):
        selected = self.tree.selection()
        if selected:
            self.logger.info(
                f"Removed step: current: {self.tree.item(selected[0], "values")[0]} A for {self.tree.item(selected[0], "values")[1]} s")
            self.tree.delete(selected[0])
            self._renumber_steps()
        else:
            self.logger.warning("Select a step to remove.")
            messagebox.showwarning("Warning", "Select a step to remove.")
            self._keep_window_top()

    def _move_up(self):
        selected = self.tree.selection()
        if not selected:
            self.logger.warning("No item selected to move up.")
            return
        item = selected[0]
        index = self.tree.index(item)
        if index > 0:
            above = self.tree.get_children()[index - 1]
            self.logger.info(
                f"Move step #{self.tree.item(selected[0], "values")[0]} up: current={self.tree.item(selected[0], "values")[1]} A, duration={self.tree.item(selected[0], "values")[2]} s")
            self._swap_items(item, above)
            self._renumber_steps()

    def _move_down(self):
        selected = self.tree.selection()
        if not selected:
            self.logger.warning("No item selected to move down.")
            return
        item = selected[0]
        index = self.tree.index(item)
        children = self.tree.get_children()
        if index < len(children) - 1:
            below = children[index + 1]
            self.logger.info(
                f"Move step #{self.tree.item(selected[0], "values")[0]} down: current={self.tree.item(selected[0], "values")[1]} A, duration={self.tree.item(selected[0], "values")[2]} s")
            self._swap_items(item, below)
            self._renumber_steps()

    def _swap_items(self, item1, item2):
        vals1 = self.tree.item(item1, "values")
        vals2 = self.tree.item(item2, "values")
        self.tree.item(item1, values = vals2)
        self.tree.item(item2, values = vals1)
        self.tree.selection_set(item2)

    def _get_sequence(self):
        sequence = []
        for idx, row in enumerate(self.tree.get_children()):
            _, current_str, duration_str = self.tree.item(row)["values"]
            try:
                current = float(current_str)
                duration = float(duration_str)
                if duration <= 0:
                    raise ValueError("Duration must be positive.")
                sequence.append({"current": current, "duration": duration})
            except ValueError as e:
                self.logger.error(f"Invalid step: {e}")
                messagebox.showerror("Invalid Input", f"Invalid step: {e}")
                self._keep_window_top()
                return None
        return sequence

    def _export_json(self):
        try:
            sequence = self._get_sequence()
            if sequence is None:
                self.logger.warning("Export aborted due to invalid sequence.")
                return False

            file_path = filedialog.asksaveasfilename(
                defaultextension = ".json",
                filetypes = [("JSON files", "*.json")],
                title = "Export Cycle Sequence to JSON",
                initialdir = self.input_file_path
            )
            if not file_path:
                self.logger.info("Export canceled by user.")
                return False

            with open(file_path, "w") as f:
                json.dump(sequence, f, indent = 4)
            messagebox.showinfo("Export Successful", f"Cycle sequence saved to {file_path}")
            self._keep_window_top()
            self.logger.info(f"Cycle sequence exported to {file_path}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to export JSON: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Export Error", str(e))
            self._keep_window_top()

    def _import_json(self):
        file_path = filedialog.askopenfilename(
            title = "Import Cycle Sequence from JSON",
            filetypes = [("JSON files", "*.json")],
            initialdir = self.input_file_path
        )
        if not file_path:
            self.logger.info("Import canceled by user.")
            return

        try:
            with open(file_path, "r") as f:
                sequence = json.load(f)

            if not isinstance(sequence, list):
                raise ValueError("JSON root should be a list.")

            # Clear the tree
            self.tree.delete(*self.tree.get_children())

            # Offset as Step 0
            if sequence and "current" in sequence[0] and "duration" in sequence[0]:
                offset = sequence.pop(0)
                self.tree.insert("", "end", values = ("Offset", offset["current"], offset["duration"]),
                                 tags = ("offset",))

            # Add remaining steps
            for idx, step in enumerate(sequence, start = 1):
                self.tree.insert("", "end", values = (idx, step["current"], step["duration"]))

            messagebox.showinfo("Import Successful", f"Loaded {len(sequence)} steps.")
            self._keep_window_top()

            self.logger.info(f"Imported {len(sequence)} steps from {file_path}")

        except Exception as e:
            self.logger.error(f"Import failed: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Import Error", f"Could not load file: {e}")
            self._keep_window_top()

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        # Clean up previous entry popup if it exists
        if self.entry_popup and self.entry_popup.winfo_exists():
            try:
                self.entry_popup.destroy()
            except tk.TclError:
                pass
            self.entry_popup = None

        row_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        x, y, width, height = self.tree.bbox(row_id, column)
        value = self.tree.set(row_id, column)

        self.entry_popup = tk.Entry(self.tree)
        self.entry_popup.place(x = x, y = y, width = width, height = height)
        self.entry_popup.insert(0, value)
        self.entry_popup.focus()
        self.entry_popup.bind("<Return>", lambda e: self._save_edit(row_id, column))
        self.entry_popup.bind("<Escape>", lambda e: self._cancel_edit())

    def _save_edit(self, row_id, column):
        new_value = self.entry_popup.get()
        old_value = self.tree.set(row_id, column)
        self.tree.set(row_id, column, new_value)
        self.entry_popup.destroy()
        self.entry_popup = None
        self.logger.info(f"Edited cell at row '{row_id}', column '{column}': '{old_value}' -> '{new_value}'")

    def _cancel_edit(self):
        if self.entry_popup and self.entry_popup.winfo_exists():
            try:
                self.entry_popup.destroy()
            except tk.TclError:
                pass
        self.entry_popup = None

    def _keep_window_top(self):
        self.lift()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

    def on_close(self):
        self._cancel_edit()

        result = messagebox.askyesnocancel(
            "Exit Confirmation",
            "Do you want to save the cycle sequence before closing?\n\n"
            "Yes: Save changes\n"
            "No: Discard changes\n"
            "Cancel: Stay in editor"
        )
        self._keep_window_top()

        if result is None:
            self.logger.info("Close cancelled by user.")
            return  # Cancel: do nothing
        elif result:  # Yes: Save
            self.logger.info("User chose to save before exiting.")

            if not self._export_json():
                return

            self.logger.info("Cycle Sequence Editor closed after save.")
            self.destroy()
        else:  # No: Discard
            self.logger.info("User chose to discard changes and exit.")
            self.destroy()
