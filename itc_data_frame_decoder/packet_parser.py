import re
from typing import Optional


_MIN_HEX_LENGTH = 26


def extract_hex_candidates(line: str) -> list[str]:
    return [
        m.upper()
        for m in re.findall(r"[0-9A-Fa-f]{26,}", line)
        if len(m) % 2 == 0
    ]


def parse_packet(packet_hex: str) -> Optional[dict]:
    if len(packet_hex) < _MIN_HEX_LENGTH:
        return None

    hex_str = packet_hex.upper()
    return {
        "declared_length_bytes": int(hex_str[2:6], 16),
        "packet_type": hex_str[6:8],
        "flags_reserved": hex_str[8:10],
        "address_hex": hex_str[10:20],
        "metadata_hex": hex_str[20:26],
        "data_hex": hex_str[26:],
        "actual_length_bytes": len(hex_str) // 2,
    }


def address_to_decimal_id(address_hex: str) -> str:
    return str(int(address_hex, 16))


def extract_rr_code(decimal_id: str) -> str:
    if len(decimal_id) < 5:
        return ""
    return decimal_id[1:4]
