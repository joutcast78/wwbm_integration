# =============================================================================
# __init__.py
# Main entry point. Sims 4 loads this first when the mod folder is found.
# Checks that WickedfulWhims and Basemental are installed, then wires
# every system together in the correct order.
# =============================================================================

def initialize():
    print("[WWBM] ==========================================")
    print("[WWBM]  WW + Basemental Integration Mod Loading ")
    print("[WWBM] ==========================================")

    # --- Check WickedfulWhims is installed ---
    ww_present = _check_import("wickedwhims", "WickedWhims")
    if not ww_present:
        # Still works with vanilla WooHoo events if WW is missing,
        # but warn the user so they know WW features won't be active
        print("[WWBM] WARNING: WickedWhims not found.")
        print("[WWBM] Mod will still work using vanilla Sims 4 WooHoo events.")
        print("[WWBM] Install WickedWhims for the best experience.")

    # --- Check Basemental is installed ---
    bm_present = _check_import("basementaldrugssystem", "Basemental Drugs")
    if not bm_present:
        print("[WWBM] ERROR: Basemental Drugs not found.")
        print("[WWBM] Drug tracking will not work. Install Basemental Drugs and restart.")
        return

    # --- Register the G drug with Basemental ---
    from wwbm_integration import g_drug
    g_drug.register_with_basemental()

    # --- Hook into Basemental drug intake events ---
    from wwbm_integration import basemental_hooks
    basemental_hooks.register_hooks()

    # --- Hook into WooHoo events (vanilla + WickedfulWhims) ---
    from wwbm_integration import ww_hooks
    ww_hooks.register_hooks()

    # --- Hook into date completion events (for Repair Date detection) ---
    ww_hooks.register_date_hook()

    print("[WWBM] ==========================================")
    print("[WWBM]  All systems loaded successfully.")
    print("[WWBM] ==========================================")


def _check_import(module_name: str, display_name: str) -> bool:
    """Tries to import a module. Returns True if found."""
    try:
        __import__(module_name)
        print(f"[WWBM] ✓ {display_name} detected")
        return True
    except ImportError:
        print(f"[WWBM] ✗ {display_name} NOT detected")
        return False


# Run immediately when Sims 4 loads this mod
initialize()
