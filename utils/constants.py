from enum import Enum


class Keys:
    CURRENT_HIGH = "current_high"
    CURRENT_LOW = "current_low"
    DURATION_HIGH = "duration_high"
    DURATION_LOW = "duration_low"
    CYCLES = "cycles"
    INTERVAL = "interval"
    AVG_COUNT = "avg_count"
    CURRENT_RANGE_KEY = "Current range (A)"
    VOLTAGE_LIMIT_KEY = "Voltage limit (V)"


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
    MAX_POINTS = 1000


class Other:
    MAX_QUEUE_SIZE = 100
