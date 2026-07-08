# =============================================================================
# partner_reactions.py
# Handles the unaffected partner's experience during the ED session.
# - Boredom/frustration moodlets that ramp up over time
# - Post-session aggravated moodlet
# =============================================================================

import alarms
import date_and_time
from wwbm_integration import moodlets

_active_partner_timers = {}   # { partner_sim_id: alarm_handle }
STEP_INTERVAL_MINUTES = 20    # Partner gets more annoyed every 20 game minutes


def start_partner_reaction(partner_sim):
    """
    Call this when the ED condition is detected and the session continues anyway.
    The partner starts out just bored, gets increasingly annoyed.
    """
    sim_id = partner_sim.sim_id
    if sim_id in _active_partner_timers:
        return

    print(f"[WWBM] Starting partner reaction for {partner_sim.full_name}")
    moodlets.add_buff(partner_sim, moodlets.BUFF_PARTNER_BORED_1, duration_game_minutes=60)
    _schedule_partner_step(partner_sim, level=1)


def _schedule_partner_step(partner_sim, level: int):
    interval = date_and_time.create_time_span(minutes=STEP_INTERVAL_MINUTES)

    def _step(handle):
        _escalate_partner(partner_sim, level + 1)

    handle = alarms.add_alarm(partner_sim, interval, _step, repeating=False)
    _active_partner_timers[partner_sim.sim_id] = handle


def _escalate_partner(partner_sim, new_level: int):
    sim_id = partner_sim.sim_id
    if sim_id not in _active_partner_timers:
        return

    moodlets.remove_buff(partner_sim, moodlets.BUFF_PARTNER_BORED_1)
    moodlets.remove_buff(partner_sim, moodlets.BUFF_PARTNER_BORED_2)

    if new_level == 2:
        moodlets.add_buff(partner_sim, moodlets.BUFF_PARTNER_BORED_2, duration_game_minutes=90)
        _schedule_partner_step(partner_sim, new_level)
    elif new_level >= 3:
        # Peak annoyance — done escalating
        moodlets.add_buff(partner_sim, moodlets.BUFF_PARTNER_AGGRAVATED, duration_game_minutes=120)
        _active_partner_timers.pop(sim_id, None)


def stop_partner_reaction(partner_sim):
    """
    Call this when the session ends.
    Clears boredom moodlets and applies the final aggravated/done moodlet.
    """
    sim_id = partner_sim.sim_id
    handle = _active_partner_timers.pop(sim_id, None)
    if handle:
        alarms.cancel_alarm(handle)

    moodlets.remove_buff(partner_sim, moodlets.BUFF_PARTNER_BORED_1)
    moodlets.remove_buff(partner_sim, moodlets.BUFF_PARTNER_BORED_2)

    # Apply lingering aggravated feeling — lasts 6 game hours
    moodlets.add_buff(partner_sim, moodlets.BUFF_PARTNER_AGGRAVATED, duration_game_minutes=360)
    print(f"[WWBM] Partner {partner_sim.full_name} left the session aggravated")
