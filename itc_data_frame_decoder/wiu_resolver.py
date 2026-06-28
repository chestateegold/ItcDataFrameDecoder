import json
from collections import defaultdict
from pathlib import Path

from .switch_signal_decoder import parse_switches_and_signals


def _load_configured_rrs() -> set[str]:
    config_path = Path(__file__).parent / "railroad_config.json"
    config = json.loads(config_path.read_text())
    return {c["rr"] for c in config}


def _apply_hierarchy(results: list[dict]) -> dict:
    successes = [r for r in results if r["success"] == "yes"]
    if successes:
        first = successes[0]
        return {"success": "yes", "switches": first["results"]["switches"], "signals": first["results"]["signals"]}

    ambiguous = [r for r in results if r["success"] == "ambiguous"]
    if ambiguous:
        return {"success": "ambiguous", "switches": "", "signals": ""}

    return {"success": "no", "switches": "", "signals": ""}


def resolve_wius(packets: list[dict]) -> dict[str, dict]:
    configured_rrs = _load_configured_rrs()

    wiu_data: dict[str, dict] = defaultdict(lambda: {"rr": "", "results": []})

    for pkt in packets:
        wiu_id = pkt["wiu_id"]
        rr = pkt["rr"]
        data_hex = pkt["data_hex"]
        if rr not in configured_rrs:
            continue
        entry = wiu_data[wiu_id]
        entry["rr"] = rr
        result = parse_switches_and_signals(rr, data_hex)
        entry["results"].append(result)

    resolved = {}
    for wiu_id, entry in wiu_data.items():
        resolved[wiu_id] = {
            "rr": entry["rr"],
            **_apply_hierarchy(entry["results"]),
        }
    return resolved
