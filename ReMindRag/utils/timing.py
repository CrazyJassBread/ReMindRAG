import time
from datetime import datetime


def emit_timing(logger, label, started_at=None, **details):
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    elapsed = f" elapsed={time.perf_counter() - started_at:.3f}s" if started_at is not None else ""
    detail_text = " ".join(f"{key}={value}" for key, value in details.items())
    suffix = f" {detail_text}" if detail_text else ""
    message = f"[TIMING] {timestamp} {label}{elapsed}{suffix}"
    print(message, flush=True)
    if logger is not None:
        logger.info(message)
