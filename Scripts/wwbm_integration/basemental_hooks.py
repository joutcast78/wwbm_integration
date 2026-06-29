# =============================================================================
# basemental_hooks.py
# Listens for Basemental's drug consumption events and logs them to drug_tracker.
# This is what connects "Sim took a drug in Basemental" to our ED/consequence systems.
# =============================================================================

from wwbm_integration import drug_tracker

# Map Basemental's internal drug names to our tracker's substance keys
BASEMENTAL_DRUG_MAP = {
    "cocaine":         "cocaine",
    "amphetamine":     "amphetamine",
    "speed":           "amphetamine",   # Basemental sometimes calls it speed
    "meth":            "amphetamine",   # meth triggers same condition
    "alcohol":         "alcohol",
    "beer":            "alcohol",
    "wine":            "alcohol",
    "spirits":         "alcohol",
    "g":               "g",
    "ghb":             "g",
}


def register_hooks():
    """
    Called at mod load. Hooks into Basemental's drug consumption events.
    Basemental uses a callback/listener system for drug intake events.
    """
    try:
        import basementaldrugssystem.events.drug_events as bm_events

        if hasattr(bm_events, "on_drug_consumed"):
            bm_events.on_drug_consumed.append(_on_drug_consumed)
            print("[WWBM] Hooked into Basemental drug consumption events")
        else:
            print("[WWBM] WARNING: Basemental event API not found — drug tracking may not work")
            print("[WWBM] Check Basemental version and update basemental_hooks.py")

    except ImportError:
        print("[WWBM] Basemental not found — drug hooks not registered")
    except Exception as e:
        print(f"[WWBM] Error registering Basemental hooks: {e}")


def _on_drug_consumed(sim, drug_name: str, amount: int = 1):
    """
    Fires every time a Sim takes a drug or drinks alcohol in Basemental.
    We translate the drug name and log it to our tracker.
    amount = number of lines/drinks/doses taken at once (usually 1)
    """
    substance = BASEMENTAL_DRUG_MAP.get(drug_name.lower())

    if substance is None:
        return  # drug we don't track, ignore it

    # Log once per dose/line/drink
    for _ in range(amount):
        drug_tracker.record_intake(sim, substance)

    print(f"[WWBM] Logged: {sim.full_name} took {amount}x {substance} (from Basemental: '{drug_name}')")
