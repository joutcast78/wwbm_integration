# =============================================================================
# relationship_damage.py
# After a session affected by the ED condition ends, this tanks the relationship
# between the two sims and sets a special flag that means it can ONLY be
# repaired by the affected sim taking the other on a Repair Date.
# =============================================================================

import services
import relationships.relationship_track as rel_track

# The relationship score we drop both sims down to after the session.
# Sims 4 friendship tracks typically run from -100 to 100.
# -80 is "Enemies" territory.
RELATIONSHIP_SCORE_AFTER = -80

# We store the repair flag in a simple dict so we can check it later.
# Format: { (sim_id_A, sim_id_B): True }
_needs_repair_date = {}


def _pair_key(sim_a, sim_b):
    """Always returns the same key regardless of which sim is A or B."""
    ids = sorted([sim_a.sim_id, sim_b.sim_id])
    return (ids[0], ids[1])


def apply_post_session_damage(affected_sim, partner_sim):
    """
    Call this right after the session ends.
    Tanks both sims' relationship scores and locks repair behind a date.
    """
    print(f"[WWBM] Applying relationship damage between {affected_sim.full_name} and {partner_sim.full_name}")

    _tank_relationship(affected_sim, partner_sim)
    _set_repair_flag(affected_sim, partner_sim)


def _tank_relationship(sim_a, sim_b):
    """Drops the friendship/romance track between two sims to a very negative value."""
    try:
        rel_service = services.relationship_service()
        if rel_service is None:
            return

        # Get the relationship object between these two sims
        relationship = rel_service.get(sim_a.sim_id, sim_b.sim_id, create=False)
        if relationship is None:
            return

        # Find the friendship track and set it to the damage value
        for track in relationship.relationship_tracks:
            track_name = str(track.stat_type).lower()
            if "friendship" in track_name or "sentiment" in track_name:
                track.set_value(RELATIONSHIP_SCORE_AFTER)

        print(f"[WWBM] Relationship between {sim_a.full_name} and {sim_b.full_name} tanked to {RELATIONSHIP_SCORE_AFTER}")

    except Exception as e:
        print(f"[WWBM] Error tanking relationship: {e}")


def _set_repair_flag(sim_a, sim_b):
    """Sets the flag that means this relationship needs a Repair Date to fix."""
    key = _pair_key(sim_a, sim_b)
    _needs_repair_date[key] = True
    print(f"[WWBM] Repair date flag set for {sim_a.full_name} + {sim_b.full_name}")


def requires_repair_date(sim_a, sim_b) -> bool:
    """Returns True if this pair needs a Repair Date before relationship can improve."""
    return _needs_repair_date.get(_pair_key(sim_a, sim_b), False)


def clear_repair_flag(sim_a, sim_b):
    """
    Call this when the Repair Date has been completed successfully.
    After this, the relationship can improve normally again.
    """
    key = _pair_key(sim_a, sim_b)
    _needs_repair_date.pop(key, None)
    print(f"[WWBM] Repair date completed — {sim_a.full_name} and {sim_b.full_name} can rebuild")
