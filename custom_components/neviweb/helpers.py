"""Helpers for debugging and logger setup in neviweb"""

import asyncio
import datetime
import logging
import os
import shutil

from logging.handlers import RotatingFileHandler
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

REQUEST_STORE_VERSION = 1
REQUEST_STORE_KEY = f"{DOMAIN}_request_count"


# ─────────────────────────────────────────────
# SECTION LOGGER SETUP
# ─────────────────────────────────────────────


def setup_logger(
    name: str,
    log_path: str,
    level: str = "INFO",
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 2,
    reset_on_start: bool = True
):
    if reset_on_start and os.path.exists(log_path):
        clear_log_file(log_path)

    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(numeric_level)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    # Delete hold handlers on same file
    logger.handlers = [
        h for h in logger.handlers
        if not (isinstance(h, RotatingFileHandler) and h.baseFilename == log_path)
    ]
    logger.addHandler(handler)
    logger.propagate = False

    logger.debug("Logger initialized early at level %s", level.upper())


def clear_log_file(log_path: str):
    if os.path.exists(log_path):
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            print(f"Failed to clear log file: {e}")


def update_logger_level(name: str, level: str):
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(numeric_level)
    for h in logger.handlers:
        h.setLevel(numeric_level)
    logger.debug("Logger level updated to %s", level.upper())


def update_logger_config(name: str, log_path: str, level: str, max_bytes: int, backup_count: int):
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(numeric_level)

    updated = False
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler) and os.path.samefile(h.baseFilename, log_path):
            h.setLevel(numeric_level)
            h.maxBytes = max_bytes
            h.backupCount = backup_count
            logger.debug("Logger handler mis à jour : max_bytes=%s, backup_count=%s", max_bytes, backup_count)
            updated = True

    if not updated:
        logger.warning("Aucun handler mis à jour — vérifie le log_path ou l’attachement initial")

    logger.debug("Logger config updated to level %s", level.upper())


def expose_log_file(hass, log_path: str, public_name: str = "neviweb.log", expire_after: int = 1800) -> str | None:
    """Copy log file to /config/www for browser download with forced filename."""
    www_dir = hass.config.path("www")
    os.makedirs(www_dir, exist_ok=True)

    www_path = os.path.join(www_dir, public_name)

    try:
        shutil.copy2(log_path, www_path)
        _LOGGER.debug("Log file copied to %s", www_path)

        # Schedule deletion
        hass.loop.create_task(_delete_file_later(www_path, expire_after))
        return www_path
    except Exception as e:
        _LOGGER.warning("Cannot expose log file: %s", e)
        return None


async def _delete_file_later(path: str, delay: int):
    """Wait for delay seconds then delete the file if it exists."""
    await asyncio.sleep(delay)
    try:
        if os.path.exists(path):
            os.remove(path)
            _LOGGER.info("Log file deleted after %s seconds : %s", delay, path)
    except Exception as e:
        _LOGGER.warning("Error during log file delete process : %s", e)


# ─────────────────────────────────────────────
# SECTION DAILY REQUEST COUNTER
# ─────────────────────────────────────────────


def init_request_counter(hass):
    """Initialise the persistent store for request counter data."""
    store: Store = Store(hass, REQUEST_STORE_VERSION, REQUEST_STORE_KEY)

    # Load data
    future = asyncio.run_coroutine_threadsafe(store.async_load(), hass.loop)
    data = future.result()

    if not data:
        data = {
            "date": datetime.date.today().isoformat(),
            "count": 0,
        }
        future = asyncio.run_coroutine_threadsafe(store.async_save(data), hass.loop)
        future.result()

    hass.data[DOMAIN]["request_store"] = store
    hass.data[DOMAIN]["request_data"] = data


def increment_request_counter(hass):
    """Increase counter by one."""
    data = hass.data[DOMAIN]["request_data"]
    today = datetime.date.today().isoformat()

    # Reset if day change
    if data["date"] != today:
        data["date"] = today
        data["count"] = 0

    data["count"] += 1

    # Persistent saving
    future = asyncio.run_coroutine_threadsafe(hass.data[DOMAIN]["request_store"].async_save(data), hass.loop)
    future.result()

    return data["count"]


def get_daily_request_count(hass):
    """Return the daily request count."""
    return hass.data[DOMAIN]["request_data"]["count"]
