import os
import sys
import json
import logging

from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """ A JSON formatter for logging records. """

    def format(self, record: logging.LogRecord) -> str:
        """ 
        Format a logging record as a JSON string.
        
        ==================== Arguments ====================
        record: The logging record to format.

        ==================== Returns ====================
        A JSON string representing the logging record.
        """
        # Create a log entry.
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception information if it exists.
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Filter our the default logging fields from our log output.
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process",
        }

        for key, value in record.__dict__.items():
            if key not in reserved:
                log_entry[key] = value

        # Return the log entry as a JSON string.
        return json.dumps(log_entry)


def configure_logging(logger_name: str) -> logging.Logger:
    """
    Configure logging for the given logger name.

    ==================== Arguments ====================
    logger_name: The name of the logger to configure.

    ==================== Returns ====================
    The configured logger.
    """
    # Get the log level and format from the environment variables.
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "pretty").lower()

    # Create and setup the logger..
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.handlers.clear()
    logger.propagate = False

    # Create and setup the handler.
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Create and setup the formatter.
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    # Set the formatter for the handler.
    handler.setFormatter(formatter)
    # Add the handler to the logger.
    logger.addHandler(handler)

    return logger