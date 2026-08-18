"""Process-wide Zoey state for the API server.

The backend keeps exactly one Zoey instance (and therefore exactly one
Orchestrator) so plan/approval/execution state is shared across every
request. A single lock serializes state-mutating operations; the status
endpoint and the cooperative-cancel path intentionally avoid it (see
api/server.py) so live execution progress is always readable.
"""

import threading

from core.zoey import Zoey

_lock = threading.Lock()
_zoey = None


def get_zoey():
    """Return the shared Zoey instance, creating the real one lazily.

    Tests swap in a fake via set_zoey() before creating the app.
    """
    global _zoey

    if _zoey is None:
        _zoey = Zoey()

    return _zoey


def set_zoey(instance):
    """Replace the shared instance (used by tests)."""
    global _zoey

    _zoey = instance


def lock():
    """Return the lock serializing state-mutating operations."""
    return _lock
