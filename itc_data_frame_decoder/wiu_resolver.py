import json
from collections import defaultdict
from pathlib import Path

from .switch_signal_decoder import (
    decode_all_switch_signal_combinations,
    parse_switches_and_signals,
)


def _load_configured_rrs() -> set[str]:
    config_path = Path(__file__).parent / "railroad_config.json"
    config = json.loads(config_path.read_text())
    return {c["rr"] for c in config}


def _candidate_tuples(candidates: list[dict]) -> set[tuple[str, str]]:
    return {(candidate["switches"], candidate["signals"]) for candidate in candidates}


def _apply_hierarchy(results: list[dict], rr: str) -> dict:
    successful_decodes = {
        (r["results"]["switches"], r["results"]["signals"])
        for r in results
        if r["success"] == "yes"
    }

    if len(successful_decodes) == 1:
        switches, signals = next(iter(successful_decodes))
        return {
            "success": "yes",
            "switches": switches,
            "signals": signals,
            "has_conflict": "no",
        }

    if len(successful_decodes) > 1:
        relaxed_candidate_sets = []
        for result in results:
            relaxed_candidates = decode_all_switch_signal_combinations(
                rr,
                result["data_hex"],
                allow_in_motion=True,
            )
            relaxed_set = _candidate_tuples(relaxed_candidates)
            if relaxed_set:
                relaxed_candidate_sets.append(relaxed_set)

        if relaxed_candidate_sets:
            common_candidates = set.intersection(*relaxed_candidate_sets)
            if len(common_candidates) == 1:
                switches, signals = next(iter(common_candidates))
                return {
                    "success": "yes",
                    "switches": switches,
                    "signals": signals,
                    "has_conflict": "no",
                }

        return {"success": "no", "switches": "", "signals": "", "has_conflict": "yes"}

    if any(r["success"] == "ambiguous" for r in results):
        return {"success": "ambiguous", "switches": "", "signals": "", "has_conflict": "no"}

    return {"success": "no", "switches": "", "signals": "", "has_conflict": "no"}


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
        result["data_hex"] = data_hex
        entry["results"].append(result)

    resolved = {}
    for wiu_id, entry in wiu_data.items():
        resolved[wiu_id] = {
            "rr": entry["rr"],
            **_apply_hierarchy(entry["results"], entry["rr"]),
        }
    return resolved
