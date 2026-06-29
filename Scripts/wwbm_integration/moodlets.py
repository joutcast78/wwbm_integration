# =============================================================================
# moodlets.py
# Defines all the custom moodlets this mod adds.
# Moodlets are the little status icons/feelings that appear on a Sim's panel.
# We use buff_EffectModifier to hook into the game's existing buff system.
# =============================================================================

import services
import sims4.resources
from buffs.buff import Buff
from sims4.tuning.tunable import TunableReference

# ---------------------------------------------------------------------------
# We define moodlet IDs as simple string constants so every file uses the
# same names. The actual XML tuning files (in the Tuning/ folder) match these.
# ---------------------------------------------------------------------------

BUFF_AMPH_AGGRESSION_1  = "wwbm_amph_aggression_1"   # mild irritability
BUFF_AMPH_AGGRESSION_2  = "wwbm_amph_aggression_2"   # anger rising
BUFF_AMPH_AGGRESSION_3  = "wwbm_amph_aggression_3"   # furious
BUFF_AMPH_FRUSTRATED    = "wwbm_amph_frustrated"      # post-session rage
BUFF_PARTNER_BORED_1    = "wwbm_partner_bored_1"      # partner getting bored
BUFF_PARTNER_BORED_2    = "wwbm_partner_bored_2"      # partner annoyed
BUFF_PARTNER_AGGRAVATED = "wwbm_partner_aggravated"   # partner done with this
BUFF_RELATIONSHIP_RUINED= "wwbm_relationship_ruined"  # lingering negative moodlet
BUFF_GHB_WAVY           = "wwbm_ghb_wavy"            # G is hitting
BUFF_GHB_BLACKOUT       = "wwbm_ghb_blackout"         # blacked out


def add_buff(sim, buff_name: str, duration_game_minutes: int = 120):
    """
    Adds a moodlet buff to a Sim.
    duration_game_minutes: how long the moodlet lasts in game time.
    120 game minutes = 2 game hours (a medium-length moodlet).
    """
    try:
        buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
        buff_type = buff_manager.get(buff_name)
        if buff_type and sim.buffs:
            sim.buffs.add_buff_from_op(
                buff_type,
                buff_reason=None,
                source=None,
                duration_override=duration_game_minutes
            )
    except Exception as e:
        print(f"[WWBM] Could not add buff {buff_name} to {sim}: {e}")


def remove_buff(sim, buff_name: str):
    """Removes a moodlet buff from a Sim if they have it."""
    try:
        buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
        buff_type = buff_manager.get(buff_name)
        if buff_type and sim.buffs and sim.buffs.has_buff(buff_type):
            sim.buffs.remove_buff_by_type(buff_type)
    except Exception as e:
        print(f"[WWBM] Could not remove buff {buff_name}: {e}")


def has_buff(sim, buff_name: str) -> bool:
    """Returns True if the Sim currently has this moodlet."""
    try:
        buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
        buff_type = buff_manager.get(buff_name)
        return bool(buff_type and sim.buffs and sim.buffs.has_buff(buff_type))
    except:
        return False
