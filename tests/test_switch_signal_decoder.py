import pytest

from itc_data_frame_decoder import (
    decode_all_switch_signal_combinations,
    parse_switches_and_signals,
)


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

    assert result["success"] == "ambiguous"


def test_up_ambiguous():
    result = parse_switches_and_signals("802", _bin_to_hex("0101111100000000"))

    assert result["success"] == "ambiguous"


def test_unknown_railroad():
    result = parse_switches_and_signals("999", "7600")

    assert result["success"] == "no"
    assert result["results"] == []
    assert result["possible_results"] == []


def test_hex_string_input():
    result = parse_switches_and_signals("076", "7600")

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "0", "signals": "2"}


def test_up_80_is_ambiguous():
    result = parse_switches_and_signals("802", "80")

    assert result["success"] == "ambiguous"


def test_ns_one_switch_two_signals():
    result = parse_switches_and_signals("550", "10A0")

    assert result["success"] == "ambiguous"


def test_hex_string_input():
    result = parse_switches_and_signals("550", "F7BDE8")

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "1", "signals": "4"}


def test_non_string_input_rejected():
    with pytest.raises(TypeError, match="data_hex must be a hex string"):
        parse_switches_and_signals("076", 0x7600)


def test_conflict_result_1():
    result = parse_switches_and_signals("076", "67CF7F9E")

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "3", "signals": "5"}
    assert result["possible_results"] == [{"switches": "3", "signals": "5"}]


def test_conflict_result_2():
    result = parse_switches_and_signals("076", "23DEF7BC")

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "0", "signals": "6"}
    assert result["possible_results"] == [{"switches": "0", "signals": "6"}]


def test_conflict_result_3():
    result = parse_switches_and_signals("076", "03DEF7BC")

    assert result["success"] == "yes"
    assert result["results"] == {"switches": "0", "signals": "5"}
    assert result["possible_results"] == [{"switches": "0", "signals": "5"}]


def test_decode_all_returns_single_strict_candidate():
    result = decode_all_switch_signal_combinations("076", "67CF7F9E")

    assert result == [{"switches": "3", "signals": "5"}]


def test_decode_all_returns_multiple_candidates_for_ambiguous_packet():
    result = decode_all_switch_signal_combinations("802", "80")

    assert result == [
        {"switches": "0", "signals": "1"},
        {"switches": "1", "signals": "0"},
    ]


def test_decode_all_returns_no_candidates_for_invalid_packet():
    result = decode_all_switch_signal_combinations("999", "7600")

    assert result == []


def test_decode_all_bnsf_relaxed_adds_expected_candidates():
    strict_result = decode_all_switch_signal_combinations("076", "23DEF7BC")
    relaxed_result = decode_all_switch_signal_combinations("076", "23DEF7BC", allow_in_motion=True)

    assert strict_result == [{"switches": "0", "signals": "6"}]
    assert relaxed_result == [
        {"switches": "0", "signals": "6"},
        {"switches": "3", "signals": "5"},
    ]


def test_decode_all_bnsf_relaxed_adds_expected_candidates_for_leading_zeros():
    strict_result = decode_all_switch_signal_combinations("076", "03DEF7BC")
    relaxed_result = decode_all_switch_signal_combinations("076", "03DEF7BC", allow_in_motion=True)

    assert strict_result == [{"switches": "0", "signals": "5"}]
    assert relaxed_result == [
        {"switches": "0", "signals": "5"},
        {"switches": "3", "signals": "5"},
    ]


def test_decode_all_ns_relaxed_uses_trailing_switch_in_motion_bits():
    strict_result = decode_all_switch_signal_combinations("550", "F7BDE8")
    relaxed_result = decode_all_switch_signal_combinations("550", "F7BDE8", allow_in_motion=True)

    assert strict_result == [{"switches": "1", "signals": "4"}]
    assert relaxed_result == [
        {"switches": "1", "signals": "4"},
        {"switches": "3", "signals": "3"},
        {"switches": "6", "signals": "2"},
        {"switches": "8", "signals": "1"},
        {"switches": "11", "signals": "0"},
    ]
