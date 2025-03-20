import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on their level."""

    # ANSI color codes
    COLORS = {
        "RESET": "\033[0m",
        "RED": "\033[31m",  # ERROR
        "YELLOW": "\033[33m",  # WARNING
        "GREEN": "\033[32m",  # INFO
        "BLUE": "\033[34m",  # DEBUG
        "MAGENTA": "\033[35m",  # CRITICAL
    }

    LEVEL_COLORS = {
        logging.ERROR: COLORS["RED"],
        logging.WARNING: COLORS["YELLOW"],
        logging.INFO: COLORS["GREEN"],
        logging.DEBUG: COLORS["BLUE"],
        logging.CRITICAL: COLORS["MAGENTA"],
    }

    def __init__(self, fmt=None, datefmt=None, style="%", use_colors=True):
        """Initialize the formatter with specified format strings."""
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors

    def format(self, record):
        """Format the specified record as text."""
        # First, format the record using the parent class's format method
        formatted_message = super().format(record)

        # Then, add colors if requested and if the system supports it
        if self.use_colors and hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            # Add the color code at the beginning and reset color at the end
            color = self.LEVEL_COLORS.get(record.levelno, self.COLORS["RESET"])
            formatted_message = f"{color}{
                formatted_message}{self.COLORS['RESET']}"

        return formatted_message


def configure_logging(level: str = "INFO", use_colors: bool = True):
    """
    Configure the logging system with optional colored output.

    Args:
        level: Logging level as string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        use_colors: Whether to use colored output in terminal (default: True)
    """
    # Create a formatter with timestamp, level, and message
    formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", use_colors=use_colors
    )

    # Create console handler and set level
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Configure root logger
    numeric_level = logging.getLevelName(level)
    root_logger = logging.getLogger()

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # Suppress verbose logging from libraries if needed
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Return logger for convenience
    return root_logger
