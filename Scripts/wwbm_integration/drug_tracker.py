# =============================================================================
# drug_tracker.py
# Tracks every time a Sim takes a substance, with both game-time and real-time
# stamps. Game-time is used for amphetamine/cocaine/alcohol windows.
# Real-time (seconds) is used for the G/GHB system.
# =============================================================================

import services
import time as _real_time

_intake_log = {}       # game-time log  { sim_id: { substance: [game_min, ...] } }
_realtime_log = {}     # real-time log  { sim_id: { substance: real_epoch_sec } }


def _game_now():
    ts = services.time_service()
    return ts.sim_now.absolute_minutes() if ts else 0.0


def record_intake(sim, substance: str):
    """
    Call this every time a Sim uses a substance.
    Substance values: "amphetamine"  "cocaine"  "alcohol"  "g"
    Basemental fires game events we hook — this just logs the moment.
    """
    sid = sim.sim_id
    _intake_log.setdefault(sid, {}).setdefault(substance, []).append(_game_now())
    _realtime_log.setdefault(sid, {})[substance] = _real_time.time()
    _prune(sid)


def _prune(sid):
    cutoff = _game_now() - 240   # drop anything older than 4 game-hours
    for sub in list(_intake_log.get(sid, {}).keys()):
        _intake_log[sid][sub] = [t for t in _intake_log[sid][sub] if t >= cutoff]


def count_in_window(sim, substance: str, game_minutes: float) -> int:
    """How many times did this Sim take this substance in the last N game-minutes?"""
    cutoff = _game_now() - game_minutes
    return sum(1 for t in _intake_log.get(sim.sim_id, {}).get(substance, []) if t >= cutoff)


def taken_in_window(sim, substance: str, game_minutes: float) -> bool:
    return count_in_window(sim, substance, game_minutes) > 0


def real_seconds_since(sim, substance: str) -> float:
    """Real-world seconds since this Sim last took this substance. inf if never."""
    last = _realtime_log.get(sim.sim_id, {}).get(substance)
    return (_real_time.time() - last) if last is not None else float('inf')


def clear_sim(sim):
    _intake_log.pop(sim.sim_id, None)
    _realtime_log.pop(sim.sim_id, None)
