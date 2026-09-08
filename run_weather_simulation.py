# run_weather_simulation.py  (project root)
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  -- compatibility wrapper
#
# The real implementation lives in scripts/run_weather_simulation.py.
# This file re-exports run_from_csv so that any code that previously
# imported from the root module continues to work unchanged.
#
#   from run_weather_simulation import run_from_csv  # still works
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.run_weather_simulation import run_from_csv  # noqa: F401
