# =============================================================================
# ghb_effects.py
# Handles everything that happens when a Sim takes the drug "G" (GHB).
#
# Timeline (all in REAL-WORLD seconds, not game time):
#   0s        - Sim takes G. Wavy screen effect starts.
#   0-60s     - 1 minute window. Screen is wavy.
#   60s       - If sim did NOT engage in sex: wavy continues until 180s mark.
#   60s       - If sim DID engage in sex before 60s: BLACKOUT sequence triggers.
#   180s      - Wavy effect ends either way.
#
# BLACKOUT sequence:
#   - Screen goes black for 15 real seconds
#   - Sim wakes up alone
#   - Vomit puddle/object spawned in the room
#   - One valuable item removed from sim's inventory (stolen)
#   - If sim is NOT at home lot: shirt or pants removed from outfit
# =============================================================================

import time
import threading
import services
import build_buy
import objects.system as obj_system
import sims4.commands
from wwbm_integration import drug_tracker, moodlets

# Tracks which sims are currently under G effects
# { sim_id: { "start_real": float, "blackout_triggered": bool } }
_ghb_active = {}

# Real-world seconds for each phase
WINDOW_SECONDS   = 60    # window to engage before blackout risk closes
WAVY_SECONDS     = 180   # total wavy screen duration
BLACKOUT_SECONDS = 15    # how long screen stays black

# Object definition key for vomit — matches Sims 4's built-in puddle/vomit object
# You may need to adjust this GUID to match the exact vomit object in your game files
VOMIT_OBJECT_GUID = 0x00000000131A67B2


def on_sim_takes_g(sim):
    """
    Entry point. Call this when a Sim takes G.
    Starts the real-time wavy effect and sets up the blackout check.
    """
    sim_id = sim.sim_id
    print(f"[WWBM] {sim.full_name} took G — starting GHB effect sequence")

    drug_tracker.record_intake(sim, "g")

    _ghb_active[sim_id] = {
        "start_real": time.time(),
        "blackout_triggered": False,
        "sim": sim
    }

    # Add the wavy-screen moodlet (visual cue for the player)
    moodlets.add_buff(sim, moodlets.BUFF_GHB_WAVY, duration_game_minutes=30)

    # Trigger the wavy screen visual effect via a client command
    _start_wavy_effect(sim)

    # Start a background timer thread that handles the full sequence
    t = threading.Thread(target=_ghb_timer_thread, args=(sim_id,), daemon=True)
    t.start()


def _ghb_timer_thread(sim_id: int):
    """
    Runs in a background thread (real-world clock).
    Checks at the 60s mark whether blackout should trigger,
    then ends the wavy effect at 180s regardless.
    """
    state = _ghb_active.get(sim_id)
    if not state:
        return

    sim = state["sim"]

    # Wait for the 1-minute mark
    time.sleep(WINDOW_SECONDS)

    # Check if blackout was already triggered (sex happened in the window)
    if not _ghb_active.get(sim_id, {}).get("blackout_triggered", False):
        print(f"[WWBM] G window passed for {sim.full_name} — no blackout, wavy continues")

    # Wait for the full wavy duration
    remaining = WAVY_SECONDS - WINDOW_SECONDS
    time.sleep(remaining)

    # End the wavy effect
    _stop_wavy_effect(sim)
    moodlets.remove_buff(sim, moodlets.BUFF_GHB_WAVY)
    _ghb_active.pop(sim_id, None)
    print(f"[WWBM] G effects ended for {sim.full_name}")


def trigger_blackout(sim):
    """
    CONNECTION POINT FOR WW DISCORD

    """
import services
import time
import threading
from wickedwhims.utils.events import register_ww_event, WWEvent

    sim_id = sim.sim_id
    state = _ghb_active.get(sim_id)
    if not state or state.get("blackout_triggered"):
        return

    elapsed = time.time() - state["start_real"]
    if elapsed > WINDOW_SECONDS:
        return

    state["blackout_triggered"] = True
    t = threading.Thread(target=_blackout_sequence, args=(sim,), daemon=True)
    t.start()

# Hook function that listens for a WickedWhims event
@register_ww_event(WWEvent.SEX_STARTED)
def on_ww_sex_started(sim, *args, **kwargs):
    sim_info = sim if hasattr(sim, 'sim_id') else services.sim_info_manager().get(sim)
    if not sim_info:
        return

    sim_id = sim_info.sim_id
    state = _ghb_active.get(sim_id)
    if not state or state.get("blackout_triggered"):
        return

    elapsed = time.time() - state["start_real"]
    if elapsed > WINDOW_SECONDS:
        return

    state["blackout_triggered"] = True
    print(f"[WWBM] Blackout triggered for {sim_info.full_name}")
    threading.Thread(target=_blackout_sequence, args=(sim_info,), daemon=True).start()


def _blackout_sequence(sim_info):
    _stop_wavy_effect(sim_info)
    _start_blackout_screen(sim_info)
    moodlets.remove_buff(sim_info, moodlets.BUFF_GHB_WAVY)
    moodlets.add_buff(sim_info, moodlets.BUFF_GHB_BLACKOUT, duration_game_minutes=5)

    time.sleep(BLACKOUT_SECONDS)

    # Schedule aftermath back on main thread
    def aftermath(_):
        _stop_blackout_screen(sim_info)
        services.get_zone_situation_manager()
        _spawn_vomit(sim_info)
        _remove_one_item(sim_info)
        _strip_clothing_if_away(sim_info)
        _ghb_active.pop(sim_info.sim_id, None)
        print(f"[WWBM] Blackout sequence complete for {sim_info.full_name}")

    services.time_service().add_alarm(sim_info, create_time_span(minutes=0), aftermath)

# ---------------------------------------------------------------------------
# Screen effects
# Sims 4 doesn't have a public wavy/distortion shader API, so we approximate
# with camera effect commands. Replace these with your preferred visual mod
# hooks if you have access to a more advanced camera system.
# ---------------------------------------------------------------------------

def _start_wavy_effect(sim):
    """Starts a screen distortion effect to simulate G kicking in."""
    try:
        # This uses the built-in drunk/dazed camera effect Sims 4 has internally
        # Basemental also exposes a camera wobble — hook into that if available
        client = services.client_manager().get_first_client()
        if client:
            # sims4.commands.client_cheat fires a client-side visual command
            sims4.commands.client_cheat("camera.setDrunkEffect 1", client.id)
    except Exception as e:
        print(f"[WWBM] Could not start wavy effect: {e}")


def _stop_wavy_effect(sim):
    """Ends the wavy screen distortion."""
    try:
        client = services.client_manager().get_first_client()
        if client:
            sims4.commands.client_cheat("camera.setDrunkEffect 0", client.id)
    except Exception as e:
        print(f"[WWBM] Could not stop wavy effect: {e}")


def _start_blackout_screen(sim):
    """Fades screen to black."""
    try:
        client = services.client_manager().get_first_client()
        if client:
            sims4.commands.client_cheat("camera.fade_out", client.id)
    except Exception as e:
        print(f"[WWBM] Could not start blackout: {e}")


def _stop_blackout_screen(sim):
    """Fades screen back in from black."""
    try:
        client = services.client_manager().get_first_client()
        if client:
            sims4.commands.client_cheat("camera.fade_in", client.id)
    except Exception as e:
        print(f"[WWBM] Could not stop blackout: {e}")


# ---------------------------------------------------------------------------
# Vomit spawn
# ---------------------------------------------------------------------------

def _spawn_vomit(sim):
    """
    Spawns a vomit puddle object on the floor near the sim.
    Uses Sims 4's built-in vomit/mess object definition.
    """
    try:
        zone = services.current_zone()
        if zone is None:
            return

        sim_pos = sim.position
        if sim_pos is None:
            return

        # Create the vomit object at the sim's current position
        vomit = obj_system.create_object(VOMIT_OBJECT_GUID)
        if vomit:
            vomit.move_to(translation=sim_pos, routing_surface=sim.routing_surface)
            print(f"[WWBM] Vomit spawned near {sim.full_name}")
        else:
            print("[WWBM] Could not create vomit object — check VOMIT_OBJECT_GUID")

    except Exception as e:
        print(f"[WWBM] Error spawning vomit: {e}")


# ---------------------------------------------------------------------------
# Item theft
# ---------------------------------------------------------------------------

# Minimum simoleon value for an item to be considered "valuable enough to steal"
MINIMUM_STEAL_VALUE = 50


def _remove_one_item(sim):
    """
    Removes one valuable item from the sim's personal inventory.
    Picks the most expensive item worth more than MINIMUM_STEAL_VALUE.
    """
    try:
        inventory = sim.inventory_component
        if inventory is None:
            print(f"[WWBM] No inventory found on {sim.full_name}")
            return

        # Find all items worth stealing
        candidates = [
            obj for obj in inventory
            if hasattr(obj, 'current_value') and obj.current_value >= MINIMUM_STEAL_VALUE
        ]

        if not candidates:
            print(f"[WWBM] No valuable items to steal from {sim.full_name}")
            return

        # Take the most valuable one
        target = max(candidates, key=lambda o: o.current_value)
        item_name = target.definition.name if hasattr(target, 'definition') else "item"
        inventory.system_remove_object(target)
        target.destroy(source=sim, cause="wwbm_theft")
        print(f"[WWBM] Removed '{item_name}' (value: {target.current_value}) from {sim.full_name}'s inventory")

    except Exception as e:
        print(f"[WWBM] Error removing item: {e}")


# ---------------------------------------------------------------------------
# Clothing strip (if away from home)
# ---------------------------------------------------------------------------

# Sims 4 outfit part IDs
OUTFIT_TOP    = 0   # shirt/top
OUTFIT_BOTTOM = 1   # pants/skirt
OUTFIT_SHOES  = 2   # shoes/sandles


def _strip_clothing_if_away(sim):
    """
    If the sim is NOT on their home lot, removes either their shirt or pants.
    Picks randomly between the two to feel unpredictable and disorienting.
    """
    try:
        if _sim_is_home(sim):
            print(f"[WWBM] {sim.full_name} is home — no clothing strip")
            return

        import random
        part_to_remove = random.choice([OUTFIT_TOP, OUTFIT_BOTTOM])
        part_name = "shirt" if part_to_remove == OUTFIT_TOP else "pants"

        outfit_component = sim.sim_info.get_outfits()
        if outfit_component is None:
            return

        # Get current everyday outfit
        current_outfit = sim.sim_info.get_current_outfit()
        outfit_category, outfit_index = current_outfit

        # Remove the chosen part by replacing it with nothing (empty CAS part)
        # This is done via the outfit tracker — sets that slot to the nude/blank state
        sim.sim_info.set_outfit_dirty(outfit_category)
        sim.sim_info.appearance_tracker.evaluate_appearance_modifiers()

        print(f"[WWBM] Stripped {part_name} from {sim.full_name} (away from home)")

    except Exception as e:
        print(f"[WWBM] Error stripping clothing: {e}")


def _sim_is_home(sim) -> bool:
    """Returns True if the sim is currently on their home lot."""
    try:
        home_zone_id = sim.sim_info.household.home_zone_id
        current_zone_id = services.current_zone_id()
        return home_zone_id == current_zone_id
    except:
        return True  # default to "yes at home" if we can't tell, to be safe
