from itc_data_frame_decoder.packet_parser import (
    address_to_decimal_id,
    extract_hex_candidates,
    extract_rr_code,
    parse_packet,
)


class TestPacketParser:
    def test_parse_packet_valid(self):
        packet = parse_packet("0000123300B5A8D9673B020C469F7BCF")

        assert packet is not None
        assert packet["declared_length_bytes"] == 0x0012
        assert packet["packet_type"] == "33"
        assert packet["flags_reserved"] == "00"
        assert packet["address_hex"] == "B5A8D9673B"
        assert packet["metadata_hex"] == "020C46"
        assert packet["data_hex"] == "9F7BCF"
        assert packet["actual_length_bytes"] == 16

    def test_parse_packet_too_short(self):
        packet = parse_packet("0000113300")

        assert packet is None

    def test_parse_packet_exact_min_length(self):
        packet = parse_packet("AA" * 13)

        assert packet is not None
        assert packet["data_hex"] == ""

    def test_extract_hex_candidates_single(self):
        candidates = extract_hex_candidates("prefix 0000113300B5A8D9673B020C469F7BCF suffix")

        assert candidates == ["0000113300B5A8D9673B020C469F7BCF"]

    def test_extract_hex_candidates_odd_length_filtered(self):
        candidates = extract_hex_candidates("0000113300B5A8D9673B020C469F7BCF0")

        assert candidates == []

    def test_extract_hex_candidates_multiple(self):
        candidates = extract_hex_candidates(
            "0000113300B5A8D9673B020C469F7BCF 0000133300B5A8D9667302031255F7BDEF78"
        )

        assert len(candidates) == 2

    def test_address_to_decimal_id(self):
        result = address_to_decimal_id("B5A8D9673B")

        assert result == "780221900603"

    def test_extract_rr_code(self):
        rr = extract_rr_code("780221900603")

        assert rr == "802"

    def test_extract_rr_code_short_id(self):
        rr = extract_rr_code("1234")

        assert rr == ""

    def test_extract_rr_code_bnsf(self):
        rr = extract_rr_code("707660905005")

        assert rr == "076"
