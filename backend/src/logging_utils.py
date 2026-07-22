"""Shared logging helpers for pipeline scripts."""

import logging


def get_jsonl_logger(name: str, path: str) -> logging.Logger:
    """Logger that appends one JSON-per-line record to `path`.

    Caller is expected to pass an already-`json.dumps`-encoded string as the log message.
    `propagate = False` so these lines don't also go through the root handler set up by
    `logging.basicConfig` in the calling script.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(path, mode="a", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger
