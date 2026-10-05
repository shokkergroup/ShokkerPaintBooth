"""Job/temp cleanup helpers extracted from the SPB server bootstrap."""

import gc
import logging
import os
import shutil
import threading
import time
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def cleanup_old_job_dirs(output_folder, max_age_hours=24, logger=None, *, log_prefix="Auto-cleanup"):
    """Remove stale job_* directories and return the number removed."""
    if not output_folder or not os.path.isdir(output_folder):
        return 0
    cutoff = time.time() - (max_age_hours * 3600)
    cleaned = 0
    for name in os.listdir(output_folder):
        if not name.startswith("job_"):
            continue
        job_path = os.path.join(output_folder, name)
        if not os.path.isdir(job_path):
            continue
        try:
            if os.path.getmtime(job_path) < cutoff:
                shutil.rmtree(job_path, ignore_errors=True)
                cleaned += 1
        except OSError as _spb_ex:
            _spb_swallow('cleanup_old_job_dirs@L27', _spb_ex); continue
    if cleaned and logger:
        logger.info(f"{log_prefix}: removed {cleaned} job dirs older than {max_age_hours}h")
    return cleaned


def cleanup_old_temp_entries(temp_folder, max_age_seconds=86400, logger=None):
    """Remove stale Shokker temp files/directories and return the number removed."""
    if not temp_folder:
        return 0
    os.makedirs(temp_folder, exist_ok=True)
    cleaned = 0
    now = time.time()
    prefixes = ("shokker_preview_", "shokker_render_", "shokker_decal_")
    for name in os.listdir(temp_folder):
        if not name.startswith(prefixes):
            continue
        path = os.path.join(temp_folder, name)
        try:
            if (now - os.path.getmtime(path)) <= max_age_seconds:
                continue
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
            cleaned += 1
        except OSError as _spb_ex:
            _spb_swallow('cleanup_old_temp_entries@L54', _spb_ex); continue
    if cleaned and logger:
        logger.info(f"janitor: removed {cleaned} stale tmp files")
    return cleaned


def log_janitor_stats(render_stats, render_stats_lock, logger=None):
    """Log lightweight memory/render stats for long-running local servers."""
    log = logger or logging.getLogger("shokker.janitor")
    obj_count = len(gc.get_objects())
    with render_stats_lock:
        renders = render_stats.get("total_renders", 0)
    log.info(f"janitor stats: gc_objects={obj_count} total_renders={renders}")
    if renders > 0 and renders % 1000 == 0:
        log.warning(
            f"janitor: {renders} renders served - consider restarting the server to reclaim memory."
        )


def auto_cleanup_old_jobs(output_folder, max_age_hours=24, logger=None):
    return cleanup_old_job_dirs(output_folder, max_age_hours, logger, log_prefix="Auto-cleanup")


def start_background_janitor(
    *,
    output_folder,
    temp_folder,
    render_stats,
    render_stats_lock,
    logger=None,
    interval_s=60 * 60,
):
    """Start the daemon janitor thread and return it for smoke tests/inspection."""
    log = logger or logging.getLogger("shokker.janitor")

    def _run():
        while True:
            try:
                time.sleep(interval_s)
            except Exception:
                return
            try:
                cleaned = cleanup_old_job_dirs(output_folder, 24, None, log_prefix="janitor")
                if cleaned:
                    log.info(f"janitor: removed {cleaned} stale job dirs")
            except Exception as exc:
                log.warning(f"janitor job-cleanup failed: {exc}")
            try:
                cleanup_old_temp_entries(temp_folder, 86400, log)
            except Exception as exc:
                log.warning(f"janitor tmp-cleanup failed: {exc}")
            try:
                log_janitor_stats(render_stats, render_stats_lock, log)
            except Exception as _spb_ex:
                _spb_swallow('_run@L108', _spb_ex)

    thread = threading.Thread(target=_run, daemon=True, name="spb-janitor")
    thread.start()
    return thread
