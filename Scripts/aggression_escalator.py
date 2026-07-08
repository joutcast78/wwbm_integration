# =============================================================================
# aggression_escalator.py
# When a male Sim has taken 3+ lines of amphetamine in 90 game-minutes,
# this system runs a repeating timer that escalates his anger moodlets
# over time. The longer it goes on, the angrier he gets.
# =============================================================================

import services
import alarms
import date_and_time
from wwbm_integration import moodlets

# Tracks which sims currently have the escalator running
# { sim_id: (alarm_handle, escalation_level) }
_active_escalators = {}

# How often we step up the anger (every 15 game minutes)
ESCALATION_INTERVAL_MINUTES = 15

# Max level before it just stays at peak fury
MAX_LEVEL = 3


def start_escalator(sim):
    """
    Call this when we confirm the amphetamine ED condition is triggered.
    Begins the anger ramp — starts mild, gets worse every 15 game minutes.
    """
    sim_id = sim.sim_id
    if sim_id in _active_escalators:
        return  # already running for this sim

    print(f"[WWBM] Starting aggression escalator for {sim.full_name}")

    # Add the first (mild) aggression moodlet immediately
    moodlets.add_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_1, duration_game_minutes=60)

    # Schedule the first escalation step
    _schedule_next_step(sim, level=1)


def _schedule_next_step(sim, level: int):
    """Schedules the next anger escalation step after ESCALATION_INTERVAL_MINUTES."""
    interval = date_and_time.create_time_span(minutes=ESCALATION_INTERVAL_MINUTES)

    def _step(handle):
        _escalate(sim, level + 1)

    handle = alarms.add_alarm(sim, interval, _step, repeating=False)
    _active_escalators[sim.sim_id] = (handle, level)


def _escalate(sim, new_level: int):
    """
    Steps up to the next anger level.
    Removes the previous moodlet and adds a stronger one.
    """
    sim_id = sim.sim_id
    if sim_id not in _active_escalators:
        return  # escalator was stopped (session ended)

    print(f"[WWBM] Escalating {sim.full_name} to anger level {new_level}")

    # Remove previous level moodlets
    moodlets.remove_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_1)
    moodlets.remove_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_2)
    moodlets.remove_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_3)

    # Add the appropriate level moodlet
    if new_level == 2:
        moodlets.add_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_2, duration_game_minutes=90)
    elif new_level >= 3:
        moodlets.add_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_3, duration_game_minutes=120)
        new_level = MAX_LEVEL  # cap it here

    # Schedule next step if not at max
    if new_level < MAX_LEVEL:
        _schedule_next_step(sim, new_level)
    else:
        # At max — just keep the alarm handle but stop scheduling more steps
        _active_escalators[sim_id] = (None, MAX_LEVEL)


def stop_escalator(sim):
    """
    Call this when the session ends.
    Clears the anger ramp and transitions to the post-session frustrated moodlet.
    """
    sim_id = sim.sim_id
    if sim_id not in _active_escalators:
        return

    handle, level = _active_escalators.pop(sim_id)

    # Cancel the pending alarm if there is one
    if handle:
        alarms.cancel_alarm(handle)

    # Remove all in-session anger moodlets
    moodlets.remove_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_1)
    moodlets.remove_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_2)
    moodlets.remove_buff(sim, moodlets.BUFF_AMPH_AGGRESSION_3)

    # Add the post-session frustrated moodlet — lasts 4 game hours
    moodlets.add_buff(sim, moodlets.BUFF_AMPH_FRUSTRATED, duration_game_minutes=240)
    print(f"[WWBM] Escalator stopped for {sim.full_name} — applying frustrated moodlet")
