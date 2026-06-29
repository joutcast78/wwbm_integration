# =============================================================================
# ww_hooks.py
# Hooks into the Sims 4 WooHoo interaction system, enhanced by WickedfulWhims.
#
# How it works:
#   Sims 4 fires a zone event when any WooHoo interaction completes.
#   WickedfulWhims adds its own post-WooHoo callback on top of that.
#   We listen to BOTH so the mod works whether WickedfulWhims is present or not.
#
# What we do with those events:
#   BEFORE/AT START : check ED conditions, start consequence systems
#   AFTER           : apply post-session damage, relationship tank, moodlets
# =============================================================================

import services
import sims4.commands
import interactions.utils.satisfy_motive_primitive as motives
from sims4.resources import Types
from event_testing import test_events

from wwbm_integration import (
    ed_system,
    aggression_escalator,
    partner_reactions,
    relationship_damage,
    moodlets,
    drug_tracker,
    ghb_effects,
)

# Tracks active affected sessions so we know who to apply consequences to on end
# { male_sim_id: { "trigger": str, "partner": sim_object } }
_active_ed_sessions = {}


# =============================================================================
# REGISTRATION — called once at mod load by __init__.py
# =============================================================================

def register_hooks():
    """
    Registers our listeners with both the vanilla Sims 4 event system
    and WickedWhims' post-WooHoo callback if WickedWhims is present.
    """

    # --- Vanilla Sims 4 hook ---
    # The game's EventManager fires events for interactions completing.
    # We listen for the WooHoo interaction finishing.
    try:
        services.get_event_manager().register_with_custom_key(
            test_events.TestEvent.InteractionComplete,
            "wwbm_woohoo_complete",
            _on_woohoo_interaction_complete
        )
        print("[WWBM] ✓ Hooked into Sims 4 WooHoo interaction events")
    except Exception as e:
        print(f"[WWBM] Could not register vanilla WooHoo hook: {e}")

    # --- WickedWhims hook (bonus layer if WW is installed) ---
    # WickedWhims fires its own post-WooHoo event with richer context.
    # If WickedWhims isn't installed this block is silently skipped.
    try:
        import wickedwhims.core.woohoo.woohoo_handlers as ww_woohoo
        if hasattr(ww_woohoo, "on_woohoo_completed"):
            ww_woohoo.on_woohoo_completed.append(_on_wickedwhims_woohoo_complete)
            print("[WWBM] ✓ Hooked into WickedWhims post-WooHoo event")
        else:
            print("[WWBM] WickedWhims found but post-WooHoo hook not available — using vanilla hook only")
    except ImportError:
        print("[WWBM] WickedWhims not detected — using vanilla Sims 4 WooHoo hook only")
    except Exception as e:
        print(f"[WWBM] WickedWhims hook error: {e}")


# =============================================================================
# VANILLA SIMS 4 HOOK
# Fires when any interaction tagged as WooHoo completes in the game.
# =============================================================================

# The Sims 4 internal affordance names for WooHoo interactions.
# These cover beds, hot tubs, rocket ships, closets, etc.
WOOHOO_AFFORDANCE_NAMES = [
    "woohoo",
    "woohoo_bed",
    "woohoo_hottub",
    "woohoo_rocket",
    "woohoo_closet",
    "woohoo_bush",
    "woohoo_tent",
    "woohoo_observatory",
    "tryforababy",
    "try_for_baby",
]


def _on_woohoo_interaction_complete(event, resolver):
    """
    Fires when the game's EventManager detects any interaction completing.
    We filter for WooHoo interactions by checking the affordance name.
    """
    try:
        interaction = resolver.interaction if hasattr(resolver, 'interaction') else None
        if interaction is None:
            return

        # Check if this interaction is a WooHoo interaction
        affordance_name = str(interaction.affordance).lower()
        if not any(name in affordance_name for name in WOOHOO_AFFORDANCE_NAMES):
            return

        # Get the two sims involved
        actor = interaction.sim
        target = interaction.target if hasattr(interaction, 'target') else None

        if actor is None:
            return

        # Route to our shared handler
        _handle_woohoo_event(actor, target)

    except Exception as e:
        print(f"[WWBM] Error in vanilla WooHoo hook: {e}")


# =============================================================================
# WICKEDWHIMS HOOK
# Fires after WickedWhims processes a WooHoo interaction.
# Has richer context — gives us both sims directly.
# =============================================================================

def _on_wickedwhims_woohoo_complete(woohoo_context):
    """
    Fires when WickedWhims completes processing a WooHoo.
    woohoo_context is WickedWhims' own context object containing both sims.
    """
    try:
        # WickedWhims context gives us the initiator and the partner directly
        actor   = woohoo_context.get_actor()   if hasattr(woohoo_context, 'get_actor')   else None
        partner = woohoo_context.get_partner() if hasattr(woohoo_context, 'get_partner') else None

        if actor is None:
            return

        _handle_woohoo_event(actor, partner)

    except Exception as e:
        print(f"[WWBM] Error in WickedWhims WooHoo hook: {e}")


# =============================================================================
# SHARED HANDLER
# Both hooks route here. This is where we check conditions and fire consequences.
# =============================================================================

def _handle_woohoo_event(sim_a, sim_b):
    """
    Core logic. Called when a WooHoo completes involving sim_a and sim_b.
    Checks which sim (if any) has an ED condition active, then:
      - Applies the appropriate moodlets and consequence systems
      - Records post-session relationship damage
    """

    # Check each sim for ED conditions (only fires for male sims internally)
    for sim, partner in [(sim_a, sim_b), (sim_b, sim_a)]:
        if sim is None:
            continue

        trigger = ed_system.check_ed_condition(sim)

        if trigger == ed_system.TRIGGER_NONE:
            continue

        print(f"[WWBM] ED condition detected for {sim.full_name} — trigger: {trigger}")

        # --- Consequence chain ---

        # 1. Start the aggression escalator for amphetamine trigger
        if trigger == ed_system.TRIGGER_AMPH:
            aggression_escalator.start_escalator(sim)

        # 2. Ramp the partner's boredom/frustration
        if partner:
            partner_reactions.start_partner_reaction(partner)

        # 3. Apply the post-session moodlets immediately (session already ended)
        #    The escalator adds moodlets during the session — here we apply the
        #    POST-session ones that linger after they part ways.
        _apply_post_session_moodlets(sim, partner, trigger)

        # 4. Tank the relationship and lock it behind a Repair Date
        if partner:
            relationship_damage.apply_post_session_damage(sim, partner)

        # 5. Clean up the running systems (session is over)
        aggression_escalator.stop_escalator(sim)
        if partner:
            partner_reactions.stop_partner_reaction(partner)


def _apply_post_session_moodlets(sim, partner, trigger: str):
    """
    Applies the moodlets that both sims carry AFTER the session ends.
    These are the feelings they walk away with.
    """

    # The sim under the influence: furious and humiliated
    moodlets.add_buff(sim, moodlets.BUFF_AMPH_FRUSTRATED, duration_game_minutes=240)

    # The partner: aggravated and done
    if partner:
        moodlets.add_buff(partner, moodlets.BUFF_PARTNER_AGGRAVATED, duration_game_minutes=360)

    # Both sims get the lingering "relationship ruined" moodlet — lasts 24 game hours
    moodlets.add_buff(sim, moodlets.BUFF_RELATIONSHIP_RUINED, duration_game_minutes=1440)
    if partner:
        moodlets.add_buff(partner, moodlets.BUFF_RELATIONSHIP_RUINED, duration_game_minutes=1440)


# =============================================================================
# G DRUG CONNECTION POINT
# Called from ghb_effects.py when a sim under G initiates WooHoo.
# Checks the 60-second window and fires the blackout if still active.
# =============================================================================

def notify_g_woohoo_attempt(sim):
    """
    Called when a Sim who has taken G initiates a WooHoo interaction.
    If we are still within the 60-second real-world window, triggers the blackout.
    If the window has passed, the WooHoo proceeds normally (but still very risky).
    """
    seconds_since = drug_tracker.real_seconds_since(sim, "g")

    if seconds_since <= ghb_effects.WINDOW_SECONDS:
        print(f"[WWBM] G window active ({seconds_since:.1f}s elapsed) — triggering blackout for {sim.full_name}")
        ghb_effects.trigger_blackout(sim)
    else:
        print(f"[WWBM] G window closed ({seconds_since:.1f}s elapsed) — no blackout, WooHoo proceeds")


# =============================================================================
# REPAIR DATE DETECTION
# Hooks into the Sims 4 date/outing system to detect when the repair date
# is completed. After a successful date, the relationship lock is lifted.
# =============================================================================

def register_date_hook():
    """
    Listens for date completion events so we can check if it was a Repair Date.
    Called at mod load alongside register_hooks().
    """
    try:
        services.get_event_manager().register_with_custom_key(
            test_events.TestEvent.DateEnded,
            "wwbm_date_ended",
            _on_date_ended
        )
        print("[WWBM] ✓ Hooked into date completion events for Repair Date detection")
    except Exception as e:
        print(f"[WWBM] Could not register date hook: {e}")


def _on_date_ended(event, resolver):
    """
    Fires when a date/outing ends.
    We check if the two sims on the date have a pending repair flag between them.
    If they do, and the date was scored positively, we clear the repair flag.
    """
    try:
        situation = resolver.situation if hasattr(resolver, 'situation') else None
        if situation is None:
            return

        # Get the sims involved in this date
        date_sims = list(situation.all_sims_in_situation_gen())
        if len(date_sims) < 2:
            return

        sim_a, sim_b = date_sims[0], date_sims[1]

        # Check if these two have a repair flag between them
        if not relationship_damage.requires_repair_date(sim_a, sim_b):
            return

        # Check if the date ended well (score above neutral)
        date_score = situation.score if hasattr(situation, 'score') else 0
        if date_score > 0:
            relationship_damage.clear_repair_flag(sim_a, sim_b)
            print(f"[WWBM] Repair Date completed — {sim_a.full_name} and {sim_b.full_name} can begin to rebuild")

            # Give both sims a small "cautiously hopeful" moodlet
            _apply_repair_moodlet(sim_a)
            _apply_repair_moodlet(sim_b)
        else:
            print(f"[WWBM] Date ended poorly — repair flag stays for {sim_a.full_name} and {sim_b.full_name}")

    except Exception as e:
        print(f"[WWBM] Error in date end hook: {e}")


def _apply_repair_moodlet(sim):
    """Small positive moodlet after a successful Repair Date."""
    # Uses the game's built-in "Good Date" buff as a placeholder.
    # You can replace with a custom "Cautiously Hopeful" buff defined in wwbm_buffs.xml
    try:
        buff_manager = services.get_instance_manager(Types.BUFF)
        good_date_buff = buff_manager.get("buff_date_good")
        if good_date_buff and sim.buffs:
            sim.buffs.add_buff_from_op(good_date_buff, duration_override=180)
    except Exception as e:
        print(f"[WWBM] Could not apply repair moodlet: {e}")
