import json
from pathlib import Path
from typing import Optional

_config_path = Path(__file__).parent / "railroad_config.json"
with open(_config_path) as _f:
    _RAILROAD_CONFIGS = json.load(_f)


def parse_switches_and_signals(rr: str, data_hex: str) -> dict:
    if not isinstance(data_hex, str):
        raise TypeError("data_hex must be a hex string")

    rr_config = next((c for c in _RAILROAD_CONFIGS if c["rr"] == rr), None)
    if rr_config is None:
        return {"success": "no", "results": []}

    switch_bytes_first = rr_config["switchBytesFirst"]
    reverse_signal_bits = rr_config["reverseSignalBits"]
    valid_signal_set = {int(k) for k in rr_config["signals"].keys()}

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
            if reverse_signal_bits:
                chunk = chunk[::-1]
            val = int(chunk, 2)
            if val == 0:
                continue
            if val not in valid_signal_set:
                return None
            signal_count += 1
        return signal_count

    def validate(s: int) -> Optional[int]:
        if switch_bytes_first:
            switch_bits = s * 2
            if switch_bits > bit_len:
                return None
            for i in range(0, switch_bits, 2):
                chunk = bit_str[i:i + 2]
                if chunk not in ("01", "10"):
                    return None
            signal_bits = bit_str[switch_bits:]
            return validate_signals(signal_bits)
        else:
            signal_bits = bit_str[:bit_len - s * 2]
            signal_count = validate_signals(signal_bits)
            if signal_count is None:
                return None
            switch_bits_str = bit_str[bit_len - s * 2:]
            for i in range(0, len(switch_bits_str), 2):
                chunk = switch_bits_str[i:i + 2]
                if chunk not in ("01", "10"):
                    return None
            return signal_count

    max_s = bit_len // 2

    valid_results = []

    for s in range(max_s + 1):
        s_val = validate(s)
        if s_val is not None:
            valid_results.append({"switches": str(s), "signals": str(s_val)})

    if len(valid_results) == 1:
        return {"success": "yes", "results": valid_results[0]}
    elif len(valid_results) == 0:
        return {"success": "no", "results": []}
    else:
        return {"success": "ambiguous", "results": []}
