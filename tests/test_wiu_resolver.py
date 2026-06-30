import tempfile
from pathlib import Path

from itc_data_frame_decoder.wiu_resolver import (
    _apply_hierarchy,
    resolve_wius,
)


class TestApplyHierarchy:
    def test_matching_successes_return_yes(self):
        final = _apply_hierarchy([
            {"success": "ambiguous", "results": [], "data_hex": "5F80"},
            {"success": "yes", "results": {"switches": "1", "signals": "3"}, "data_hex": "7DEF00"},
            {"success": "yes", "results": {"switches": "1", "signals": "3"}, "data_hex": "7DEF00"},
        ], "802")

        assert final == {
            "success": "yes",
            "switches": "1",
            "signals": "3",
            "has_conflict": "no",
        }

    def test_conflicting_successes_return_no(self):
        final = _apply_hierarchy([
            {"success": "no", "results": [], "data_hex": "7601"},
            {"success": "yes", "results": {"switches": "1", "signals": "0"}, "data_hex": "80"},
            {"success": "yes", "results": {"switches": "3", "signals": "5"}, "data_hex": "67DEF7BC"},
        ], "076")

        assert final == {"success": "no", "switches": "", "signals": "", "has_conflict": "yes"}

    def test_ambiguous_without_successes(self):
        final = _apply_hierarchy([
            {"success": "ambiguous", "results": [], "data_hex": "80"},
            {"success": "no", "results": [], "data_hex": "7601"},
        ], "802")

        assert final == {"success": "ambiguous", "switches": "", "signals": "", "has_conflict": "no"}

    def test_all_failed(self):
        final = _apply_hierarchy([
            {"success": "no", "results": [], "data_hex": "7601"},
        ], "076")

        assert final == {"success": "no", "switches": "", "signals": "", "has_conflict": "no"}

    def test_success_ignores_failed_packets_if_successes_agree(self):
        final = _apply_hierarchy([
            {"success": "no", "results": [], "data_hex": "7601"},
            {"success": "yes", "results": {"switches": "1", "signals": "3"}, "data_hex": "7DEF00"},
        ], "802")

        assert final == {"success": "yes", "switches": "1", "signals": "3", "has_conflict": "no"}

    def test_conflicting_successes_can_reconcile_in_relaxed_mode(self):
        final = _apply_hierarchy([
            {"success": "yes", "results": {"switches": "3", "signals": "5"}, "data_hex": "67CF7F9E"},
            {"success": "yes", "results": {"switches": "0", "signals": "6"}, "data_hex": "23DEF7BC"},
            {"success": "yes", "results": {"switches": "0", "signals": "5"}, "data_hex": "03DEF7BC"},
        ], "076")

        assert final == {"success": "yes", "switches": "3", "signals": "5", "has_conflict": "no"}


class TestResolveWius:
    def test_single_bnsf_packet(self):
        result = resolve_wius([
            {"wiu_id": "707660905005", "rr": "076", "data_hex": "80"},
        ])

        assert result["707660905005"] == {
            "rr": "076", "success": "yes", "switches": "1", "signals": "0", "has_conflict": "no",
        }

    def test_unknown_railroad_skipped(self):
        result = resolve_wius([
            {"wiu_id": "000000000000", "rr": "999", "data_hex": "C380"},
        ])

        assert result == {}

    def test_hierarchy_across_packets(self):
        result = resolve_wius([
            {"wiu_id": "707645511005", "rr": "076", "data_hex": "A5EF00"},
        ])

        assert result["707645511005"] == {
            "rr": "076", "success": "ambiguous", "switches": "", "signals": "", "has_conflict": "no",
        }

    def test_packet_failures_do_not_block_matching_success(self):
        result = resolve_wius([
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "67DEF7BC"},
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "67CF7F9E"},
        ])

        assert result["707645500005"] == {
            "rr": "076", "success": "yes", "switches": "3", "signals": "5", "has_conflict": "no",
        }

    def test_conflicting_successes_mark_conflict(self):
        result = resolve_wius([
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "80"},
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "67DEF7BC"},
        ])

        assert result["707645500005"] == {
            "rr": "076", "success": "no", "switches": "", "signals": "", "has_conflict": "yes",
        }

    def test_conflicting_successes_can_reconcile_for_wiu(self):
        result = resolve_wius([
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "67CF7F9E"},
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "23DEF7BC"},
            {"wiu_id": "707645500005", "rr": "076", "data_hex": "03DEF7BC"},
        ])

        assert result["707645500005"] == {
            "rr": "076", "success": "yes", "switches": "3", "signals": "5", "has_conflict": "no",
        }


class TestCli:
    def test_single_bnsf_packet(self):
        from itc_data_frame_decoder.cli import main

        temp_input = Path(tempfile.mktemp(suffix=".txt"))
        temp_output = Path(tempfile.mktemp(suffix=".csv"))
        try:
            temp_input.write_text("0000103300A4C3E07A2D8207F580")
            sys_args = ["cli.py", str(temp_input), str(temp_output)]

            import sys
            original_argv = sys.argv
            try:
                sys.argv = sys_args
                main()
            finally:
                sys.argv = original_argv

            lines = temp_output.read_text().strip().split("\n")
            assert len(lines) == 2
            assert lines[0] == "wiu_id,rr,success,switches,signals,has_conflict"
            assert lines[1].startswith("707660905005,076")
        finally:
            temp_input.unlink(missing_ok=True)
            temp_output.unlink(missing_ok=True)

    def test_unknown_railroad_skipped(self):
        from itc_data_frame_decoder.cli import main

        temp_input = Path(tempfile.mktemp(suffix=".txt"))
        temp_output = Path(tempfile.mktemp(suffix=".csv"))
        try:
            temp_input.write_text("000011330000000000000000000000000000")
            sys_args = ["cli.py", str(temp_input), str(temp_output)]

            import sys
            original_argv = sys.argv
            try:
                sys.argv = sys_args
                main()
            finally:
                sys.argv = original_argv

            lines = temp_output.read_text().strip().split("\n")
            assert len(lines) == 1
            assert lines[0] == "wiu_id,rr,success,switches,signals,has_conflict"
        finally:
            temp_input.unlink(missing_ok=True)
            temp_output.unlink(missing_ok=True)
