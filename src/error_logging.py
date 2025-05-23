import logging
import sys
import threading
from pathlib import Path


class LazyErrorFileHandler(logging.Handler):
    def __init__(self, path: Path):
        super().__init__(level=logging.ERROR)
        self._path = path
        self._file_handler = None

    def _ensure_file_handler(self):
        if self._file_handler is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(self._path, mode="a", encoding="utf-8")
            fh.setLevel(logging.ERROR)
            fh.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s\n%(exc_info)s"
            ))
            self._file_handler = fh
        return self._file_handler

    def emit(self, record: logging.LogRecord):
        self._ensure_file_handler().emit(record)


def init_error_logging(filename: str = "screensaver_errors.log") -> None:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    log_path = base_dir / filename
    handler = LazyErrorFileHandler(log_path)
    logging.getLogger().addHandler(handler)

    def _handle_exc(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        else:
            logging.getLogger().error(
                "Uncaught exception", exc_info=(exc_type, exc_value, exc_tb)
            )

    sys.excepthook = _handle_exc

    def _thread_exc(args: threading.ExceptHookArgs):
        logging.getLogger().error(
            f"Exception in thread {args.thread.name}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )

    threading.excepthook = _thread_exc
