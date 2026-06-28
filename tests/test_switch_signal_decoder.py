from itc_data_frame_decoder import parse_switches_and_signals


def _bin_to_hex(binary_str: str) -> str:
    hex_len = (len(binary_str) + 3) // 4
    return hex(int(binary_str, 2))[2:].zfill(hex_len)


def test_bnsf_intermediate_no_switches():
    result = parse_switches_and_signals("076", _bin_to_hex("0111011000000000"))

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "0", "signals": "2"}


def test_bnsf_control_point_one_switch_three_signals():
    result = parse_switches_and_signals("076", _bin_to_hex("011100011110111100000000"))

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "1", "signals": "3"}


def test_bnsf_707645511005():
    result = parse_switches_and_signals(
        "076", _bin_to_hex("101001011110111100000000")
    )

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "1", "signals": "3"}


def test_up_ambiguous():
    result = parse_switches_and_signals("802", _bin_to_hex("0101111100000000"))

    assert result["success"] == "ambiguous"


def test_unknown_railroad():
    result = parse_switches_and_signals("999", "7600")

    assert result["success"] == "no"
    assert result["results"] == []


def test_hex_string_input():
    result = parse_switches_and_signals("076", "7600")

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "0", "signals": "2"}
