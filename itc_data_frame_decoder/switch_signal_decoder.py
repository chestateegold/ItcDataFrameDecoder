import json
from pathlib import Path
from typing import Optional

_config_path = Path(__file__).parent / "railroad_config.json"
with open(_config_path) as _f:
    _RAILROAD_CONFIGS = json.load(_f)


def _get_rr_config(rr: str) -> Optional[dict]:
    return next((c for c in _RAILROAD_CONFIGS if c["rr"] == rr), None)


def decode_all_switch_signal_combinations(
    rr: str, data_hex: str, allow_in_motion: bool = False
) -> list[dict[str, str]]:
    if not isinstance(data_hex, str):
        raise TypeError("data_hex must be a hex string")

    rr_config = _get_rr_config(rr)
    if rr_config is None:
        return []

    switch_bytes_first = rr_config["switchBytesFirst"]
    valid_signal_set = {int(k) for k in rr_config["signals"].keys()}
    allowed_switch_pairs = {"01", "10"}
    if allow_in_motion:
        switch_in_motion_bits = rr_config.get("switchInMotionBits")
        if switch_in_motion_bits:
            allowed_switch_pairs.add(switch_in_motion_bits)

    hex_str = data_hex.upper()
    bit_str = "".join(
        bin(int(ch, 16))[2:].zfill(4) for ch in hex_str
    )
    bit_len = len(bit_str)

    def validate_signals(signal_bits: str) -> Optional[int]:
        signal_count = 0
        for i in range(0, len(signal_bits), 5):
            chunk = signal_bits[i:i + 5]
            if len(chunk) < 5:
                break
            chunk = chunk[::-1]
            val = int(chunk, 2)
            if val == 0:
                continue
            if val not in valid_signal_set:
                return None
            signal_count += 1
        return signal_count

    def validate(s: int) -> set[int]:
        if switch_bytes_first:
            switch_bits = s * 2
            if switch_bits > bit_len:
                return set()
            for i in range(0, switch_bits, 2):
                chunk = bit_str[i:i + 2]
                if chunk not in allowed_switch_pairs:
                    return set()
            signal_bits = bit_str[switch_bits:]
            signal_count = validate_signals(signal_bits)
            return {signal_count} if signal_count is not None else set()

        switch_bit_count = s * 2
        valid_signal_counts = set()

        for signal_chunk_count in range(bit_len // 5 + 1):
            switch_start = signal_chunk_count * 5
            switch_end = switch_start + switch_bit_count
            if switch_end > bit_len:
                break

            signal_bits = bit_str[:switch_start]
            signal_count = validate_signals(signal_bits)
            if signal_count is None:
                continue

            switch_bits_str = bit_str[switch_start:switch_end]
            for i in range(0, len(switch_bits_str), 2):
                chunk = switch_bits_str[i:i + 2]
                if chunk not in allowed_switch_pairs:
                    break
            else:
                padding_bits = bit_str[switch_end:]
                if all(bit == "0" for bit in padding_bits):
                    valid_signal_counts.add(signal_count)

        return valid_signal_counts

    max_s = bit_len // 2

    valid_results = set()

    for s in range(max_s + 1):
        for signal_count in validate(s):
            valid_results.add((s, signal_count))

    return [
        {"switches": str(switches), "signals": str(signals)}
        for switches, signals in sorted(valid_results)
    ]


def parse_switches_and_signals(rr: str, data_hex: str) -> dict:
    possible_results = decode_all_switch_signal_combinations(rr, data_hex)

    if len(possible_results) == 1:
        return {
            "success": "yes",
            "results": possible_results[0],
            "possible_results": possible_results,
        }
    if len(possible_results) == 0:
        return {"success": "no", "results": [], "possible_results": []}
    return {"success": "ambiguous", "results": [], "possible_results": possible_results}
