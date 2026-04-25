#!/usr/bin/env python3
"""PUBot Watchdog

Runs main.py in a subprocess and automatically restarts it if it crashes.
This is what gets registered in Windows autostart / macOS LaunchAgent, not
main.py directly.

Exit behaviour
--------------
* Clean exit (returncode 0) after < 10 s  → single-instance guard fired;
  another PUBot is already running.  Stop.
* Clean exit (returncode 0) after >= 10 s → the app shut down normally.
  Stop (don't loop forever on a deliberate shutdown).
* Non-zero exit                           → crash.  Wait RESTART_DELAY
  seconds and restart.  After MAX_CRASHES consecutive failures, give up
  and log the situation — something is broken that a restart won't fix.
"""
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

MAIN          = Path(__file__).parent / 'main.py'
MAX_CRASHES   = 10     # stop after this many consecutive crashes
RESTART_DELAY = 20     # seconds to wait before restarting after a crash

# Re-use the same log file as main.py
_LOG = Path.home() / '.pubot' / 'pubot.log'
_LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_LOG),
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [watchdog] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logging.info('Watchdog started (PID %s).', os.getpid())

consecutive_crashes = 0

while consecutive_crashes < MAX_CRASHES:
    t_start = time.monotonic()

    result = subprocess.run([sys.executable, str(MAIN)])

    elapsed = time.monotonic() - t_start
    code    = result.returncode

    if code == 0:
        if elapsed < 10:
            logging.info(
                'main.py exited 0 after %.1f s — single-instance guard fired. Stopping.',
                elapsed,
            )
        else:
            logging.info(
                'main.py exited cleanly after %.0f s. Stopping watchdog.',
                elapsed,
            )
        break

    # Crash
    consecutive_crashes += 1
    logging.error(
        'main.py crashed (exit %d) after %.1f s. Crash #%d/%d. '
        'Restarting in %d s.',
        code, elapsed, consecutive_crashes, MAX_CRASHES, RESTART_DELAY,
    )

    if consecutive_crashes < MAX_CRASHES:
        time.sleep(RESTART_DELAY)
    else:
        logging.error(
            'Reached %d consecutive crashes. Giving up. '
            'Check %s for details.',
            MAX_CRASHES, _LOG,
        )
