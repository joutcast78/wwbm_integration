# =============================================================================
# g_drug.py
# Adds "G" (GHB) as a new drug to Basemental's drug database.
# Basemental uses a registration system — we inject our drug into it at load time.
# =============================================================================

from wwbm_integration import ghb_effects

# ---------------------------------------------------------------------------
# Drug definition dictionary — matches the format Basemental uses internally
# for its own drugs. Check Basemental's source for the latest required fields.
# ---------------------------------------------------------------------------

G_DRUG_DEFINITION = {
    "name": "G",
    "display_name": "G",                         # shown in UI
    "description": "A small vial of clear liquid. Hard to dose. Easy to regret.",
    "category": "depressant",
    "item_guid": None,                            # set below after object is created
    "addiction_chance": 0.6,                     # 60% chance to become addicted per use
    "overdose_threshold": 2,                     # 2 uses in short period = overdose risk
    "effects": {
        "energy":    -30,                         # makes sim tired/sluggish
        "fun":        20,                         # brief euphoria
        "social":     15,                         # feel sociable briefly
        "hygiene":   -10,
    },
    "moodlets_on_take": [],                      # we handle moodlets ourselves in ghb_effects.py
    "on_consume_callback": _on_g_consumed,       # our custom callback (defined below)
    "duration_game_minutes": 90,                 # how long the drug "lasts" in game
    "withdrawal_moodlet": "wwbm_g_withdrawal",
    "street_value": 80,                          # simoleons
}


def _on_g_consumed(sim, drug_data):
    """
    Basemental calls this function when a Sim consumes G.
    We hand off to our GHB effects system from here.
    """
    print(f"[WWBM] {sim.full_name} consumed G — handing off to GHB effects")
    ghb_effects.on_sim_takes_g(sim)


def register_with_basemental():
    """
    Called at mod load time.
    Injects G into Basemental's drug registry so it appears in-game.
    """
    try:
        # Basemental exposes a drug registry object — the exact import path may
        # vary slightly between Basemental versions. Check their latest source.
        import basementaldrugssystem.drugs.drug_registry as bm_registry

        if hasattr(bm_registry, "register_drug"):
            bm_registry.register_drug("g", G_DRUG_DEFINITION)
            print("[WWBM] G drug registered with Basemental successfully")
        else:
            print("[WWBM] WARNING: Basemental drug registry API not found — G may not appear in game")
            print("[WWBM] Check Basemental version and update the import path in g_drug.py")

    except ImportError:
        print("[WWBM] Basemental not found — G drug not registered. Is Basemental installed?")
    except Exception as e:
        print(f"[WWBM] Error registering G drug: {e}")
