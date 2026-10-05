import logging
import sys
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_dir: str = "logs",
                  log_level: int = logging.INFO,
                  max_bytes: int = 5_242_880,  # 5 MB
                  backup_count: int = 7):
    """
    Setup logging configuration with console and rotating file handlers.

    Args:
        log_dir (str): Directory to store log files
        log_level (int): Logging level (logging.INFO, logging.DEBUG, etc.)
        max_bytes (int): Maximum size of each log file before rotation
        backup_count (int): Number of backup files to keep
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicate logs
    if logger.handlers:
        logger.handlers.clear()

    # Create log directory
    os.makedirs(log_dir, exist_ok=True)

    # Create log filename with date
    log_filename = os.path.join(
        log_dir,
        f"birthday_wisher_{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    try:
        # ====================== FILE HANDLER (Rotating) ======================
        file_handler = TimedRotatingFileHandler(
            filename=log_filename,
            when="midnight",  # Rotate at midnight
            interval=1,
            backupCount=backup_count,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(log_level)

        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # ====================== CONSOLE HANDLER ======================
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Windows UTF-8 fix for console
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
        except:
            pass

        # Startup message
        logging.info("=" * 70)
        logging.info("🚀 Birthday Notifier Started")
        logging.info(f"📁 Log file: {log_filename}")
        logging.info(f"📊 Log Level: {logging.getLevelName(log_level)}")
        logging.info("=" * 70)

    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        # Fallback to console only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        logging.warning("Running with console logging only.")