# src/resilience/__init__.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Resilience & Offline Integration package
#
# Public API re-exports — import from here instead of individual sub-modules.
# ─────────────────────────────────────────────────────────────────────────────

from .connectivity    import (ONLINE, OFFLINE, OFFLINE_AUTONOMOUS,
                              get_connectivity_status, is_record_offline,
                              probe_uplink)
from .cache           import save_snapshot, load_snapshot, clear_cache
from .fallback        import (safe_dispatch, fallback_dispatch,
                              MODE_OPTIMIZED, MODE_FALLBACK)
from .scenario_runner import run_resilience_scenario, build_scenario_records
