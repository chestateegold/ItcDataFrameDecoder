import tempfile
from pathlib import Path

from itc_data_frame_decoder.wiu_resolver import (
    _apply_hierarchy,
    resolve_wius,
)


class TestApplyHierarchy:
    def test_success_beats_ambiguous(self):
        final = _apply_hierarchy([
            {"success": "no", "results": []},
            {"success": "ambiguous", "results": []},
            {"success": "yes", "results": {"switches": "1", "signals": "3"}},
        ])

        assert final == {"success": "yes", "switches": "1", "signals": "3"}

    def test_ambiguous_beats_failed(self):
        final = _apply_hierarchy([
            {"success": "no", "results": []},
            {"success": "ambiguous", "results": []},
        ])

        assert final == {"success": "ambiguous", "switches": "", "signals": ""}

    def test_all_failed(self):
        final = _apply_hierarchy([
            {"success": "no", "results": []},
        ])

        assert final == {"success": "no", "switches": "", "signals": ""}


class TestResolveWius:
    def test_single_bnsf_packet(self):
        result = resolve_wius([
            {"wiu_id": "707660905005", "rr": "076", "data_hex": "80"},
        ])

        assert result["707660905005"] == {
            "rr": "076", "success": "yes", "switches": "1", "signals": "0",
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

        assert result["707645511005"]["success"] == "yes"
        assert result["707645511005"]["switches"] == "1"
        assert result["707645511005"]["signals"] == "3"


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
            assert lines[0] == "wiu_id,rr,success,switches,signals"
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
            assert lines[0] == "wiu_id,rr,success,switches,signals"
        finally:
            temp_input.unlink(missing_ok=True)
            temp_output.unlink(missing_ok=True)
