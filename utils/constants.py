from enum import Enum


class Keys:
    CYCLES = "cycles"
    INTERVAL = "interval"
    AVG_COUNT = "avg_count"
    CURRENT_RANGE_KEY = "Current range (A)"
    VOLTAGE_LIMIT_KEY = "Voltage limit (V)"
    CYCLE_SEQUENCE = "cycle_sequence"
    CYCLE_SEQUENCE_FILE = "cycle_sequence_file"


class EntryConfig:
    WIDTH = 6
    JUSTIFY = 'center'


class States:
    NORMAL = "normal"
    DISABLED = "disabled"
    READONLY = "readonly"


class Labels:
    CURRENT_SOURCE_SETTINGS = "----------Current source settings----------"
    CURRENT_MEASUREMENT_SETTINGS = "--------Current measurement settings-------"
    OTHER_SETTINGS = "Other settings:"
    SAVE = "Save"
    STARTS_WITH_LOW = "Starts with low current:"


class Logger(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class UI:
    TOOLTIPS = "tooltips"
    SHOW_TOOLTIP = "show_tooltip"
    MAX_QUEUE_SIZE = "max_queue_size"
    MAX_POINTS_TO_PLOT = "max_points_to_plot"
    ENABLE_DIGITAL_IO = "enable_digital_io"


class Other:
    HIGH = "high"
    LOW = "low"
