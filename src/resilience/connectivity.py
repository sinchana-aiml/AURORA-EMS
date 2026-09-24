# src/resilience/connectivity.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Connectivity Monitor
# Member: Resilience & Offline Integration
#
# Determines whether the station has a live uplink and exposes a single
# status string the dashboard can render directly.
#
# Builds on the Digital Twin's existing communication-outage scenario:
# records tagged communication_status == "offline" by
# scenarios.apply_communication_outage_scenario() are treated as offline.
# ─────────────────────────────────────────────────────────────────────────────

import socket

# ── Dashboard-facing status strings ───────────────────────────────────────────
ONLINE             = "ONLINE"
OFFLINE            = "OFFLINE"
OFFLINE_AUTONOMOUS = "OFFLINE - AUTONOMOUS CONTROL ACTIVE"

# Consecutive offline hours after which the station is considered to be
# running itself without operator confirmation.
AUTONOMOUS_AFTER_HOURS = 3

# Uplink reachability probe target. In a real deployment this becomes the
# station's satellite gateway rather than a public DNS server.
_PROBE_HOST    = "8.8.8.8"
_PROBE_PORT    = 53
_PROBE_TIMEOUT = 2.0


def probe_uplink(host=_PROBE_HOST, port=_PROBE_PORT, timeout=_PROBE_TIMEOUT):
    """
    Returns True if the uplink is reachable.

    Kept separate from get_connectivity_status() so tests and the scenario
    runner never depend on a real socket — a network probe inside a test
    would be slow and non-deterministic.
    """
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def is_record_offline(weather_record):
    """
    True when a weather record has been tagged offline by the Digital Twin's
    apply_communication_outage_scenario().
    """
    return weather_record.get("communication_status") == "offline"


def get_connectivity_status(offline, consecutive_offline_hours=0):
    """
    Maps an offline flag plus the outage duration to a dashboard status string.

    offline                   : bool — True when the uplink is down
    consecutive_offline_hours : how many hours the outage has already lasted

    Returns ONLINE, OFFLINE, or OFFLINE_AUTONOMOUS.
    """
    if not offline:
        return ONLINE
    if consecutive_offline_hours >= AUTONOMOUS_AFTER_HOURS:
        return OFFLINE_AUTONOMOUS
    return OFFLINE
