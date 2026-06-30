# ItcDataFrameDecoder

Decodes ITC (Interoperable Train Control) packets to determine switch and signal counts from the data payload.

## Algorithm

The decoder performs an exhaustive sweep to discover how many switches and signals are encoded in a variable-length binary payload. Switches occupy 2 bits each; by default the valid switch states are `01` (normal) and `10` (reversed). Signals occupy 5 bits each (railroad-specific aspect codes). The boundary between them is not explicitly marked; the algorithm finds it by validating both sides simultaneously.

1. **Collect candidates** - Given a candidate switch count `s`, verify the switch side and signal side together.
   - For railroads with `switchBytesFirst = true`, validate the first `s * 2` bits as switch pairs, then parse the remainder as 5-bit signal groups.
   - For railroads with `switchBytesFirst = false`, try placing the `s * 2` switch bits at each boundary between complete 5-bit signal groups, and only accept placements whose remaining suffix bits are all `0` byte-padding.
   - Every non-zero signal value must match the railroad's known aspect codes.
2. **Exhaustive sweep** - Try every possible switch count from `0` to `max_s` (total bits / 2). Collect all valid `(switches, signals)` pairs and de-duplicate them by semantic result.
3. **Strict vs relaxed mode** - The low-level decoder can optionally allow a railroad-configured transient switch state (`switchInMotionBits`) in addition to `01` and `10`. This is opt-in and intended for packet-level analysis/debugging.
4. **Compatibility wrapper** - `parse_switches_and_signals(...)` collapses the candidate set into the legacy API shape: exactly 1 candidate -> `"yes"`, 0 -> `"no"`, more than 1 -> `"ambiguous"`.

## Install

```sh
git clone <repo-url>
cd ItcDataFrameDecoder
pip install -e ".[dev]"
```

## Architecture

The project has three distinct layers:

| Layer | Module | Concern |
|---|---|---|
| Decoder | `switch_signal_decoder.py` | Pure algorithm - given a payload hex string and railroad, returns possible switch/signal decodes |
| Trial process | `wiu_resolver.py` | Groups packets by WIU, evaluates packet-level decoder results, applies success hierarchy |
| I/O shell | `cli.py` | Reads hex file, parses frames, delegates to resolver, writes CSV |

## CLI

### Decode packets

Reads plain hex ITC packets (one per line, min 26 hex chars) and outputs a CSV with switch/signal results grouped by WIU address. Packets are assumed to already be in the expected ITC frame format; this PoC does not perform frame validation beyond extracting the fixed fields it needs. Packets for railroads not in the config are skipped.

```sh
python -m itc_data_frame_decoder.cli packets.hex output.csv
```

Input example (`packets.hex`):
```
4900103300A4C3E07A2D8207F580
4900123300B5A8D9673B020C469F7BCF
4900163300B5A8D9667302031255F7BDEF78
```

Output CSV columns: `wiu_id, rr, success, switches, signals, has_conflict`

| wiu_id | rr | success | switches | signals | has_conflict |
|---|---|---|---|---|---|
| 707660905005 | 076 | yes | 1 | 0 | no |
| 780221900403 | 802 | yes | 4 | 6 | no |
| 780221900603 | 802 | yes | 2 | 4 | no |

**Result hierarchy per WIU:** Compare all packet-level strict `"yes"` decodes for the WIU. If there is exactly one unique successful `(switches, signals)` result, record it as `"yes"`. If there are multiple different successful decodes, re-run those packets in relaxed mode with the railroad-configured in-motion switch bits enabled and look for exactly one common candidate across the relaxed candidate sets. If that shared candidate exists, record it as `"yes"`. Otherwise record `"no"` and set `has_conflict` to `yes`. If there are no successful decodes but at least one packet is `"ambiguous"`, record `"ambiguous"`. Otherwise record `"no"`.

**Known edge case:** If a WIU is represented by only a single packet and that packet was captured while a switch was actively being thrown, the resolver has no second packet to compare against when applying the relaxed reconciliation step. In that rare case the output may remain ambiguous or resolve to a less useful strict-only interpretation. This implementation intentionally does not try to solve that one-packet transitional-switch scenario.

## Python API

### Packet parsing

```python
from itc_data_frame_decoder.packet_parser import (
    parse_packet,
    extract_hex_candidates,
    address_to_decimal_id,
    extract_rr_code,
)

packet = parse_packet("4900123300B5A8D9673B020C469F7BCF")
assert packet["address_hex"] == "B5A8D9673B"
assert packet["data_hex"] == "9F7BCF"

wiu_id = address_to_decimal_id(packet["address_hex"])
assert wiu_id == "780221900603"

rr = extract_rr_code(wiu_id)
assert rr == "802"

candidates = extract_hex_candidates("prefix 4900123300B5A8D9673B020C469F7BCF suffix")
assert len(candidates) == 1
```

### Switch/signal decoding

```python
from itc_data_frame_decoder import (
    decode_all_switch_signal_combinations,
    parse_switches_and_signals,
)

candidates = decode_all_switch_signal_combinations("076", "23DEF7BC")
# [{"switches": "0", "signals": "6"}]

relaxed_candidates = decode_all_switch_signal_combinations(
    "076", "23DEF7BC", allow_in_motion=True
)
# [{"switches": "0", "signals": "6"}, {"switches": "3", "signals": "5"}]

# Relaxed mode uses the railroad-configured in-motion switch state
# in addition to the normal switch states. This is used by the WIU
# resolver as a reconciliation fallback when strict packet decodes conflict.

result = parse_switches_and_signals("076", "7600")
# {
#   "success": "yes",
#   "results": {"switches": "0", "signals": "2"},
#   "possible_results": [{"switches": "0", "signals": "2"}],
# }

result = parse_switches_and_signals("802", "5F80")
# {
#   "success": "ambiguous",
#   "results": [],
#   "possible_results": [{"switches": "0", "signals": "2"}, {"switches": "1", "signals": "3"}],
# }

result = parse_switches_and_signals("802", "80")
# {
#   "success": "ambiguous",
#   "results": [],
#   "possible_results": [{"switches": "0", "signals": "1"}, {"switches": "1", "signals": "0"}],
# }

# Hex string input is required.
# parse_switches_and_signals("076", 0x7600) -> TypeError
```

### WIU resolver

```python
from itc_data_frame_decoder.wiu_resolver import resolve_wius

results = resolve_wius([
    {"wiu_id": "707645500005", "rr": "076", "data_hex": "67CF7F9E"},
    {"wiu_id": "707645500005", "rr": "076", "data_hex": "23DEF7BC"},
    {"wiu_id": "707645500005", "rr": "076", "data_hex": "03DEF7BC"},
])
# {
#   "707645500005": {
#       "rr": "076", "success": "yes", "switches": "3", "signals": "5", "has_conflict": "no"
#   },
# }
```

## Tests

```sh
python -m pytest tests -v
```

## Project structure

```text
itc_data_frame_decoder/
|-- __init__.py                  # package entry point
|-- cli.py                       # I/O shell: reads hex, writes CSV
|-- packet_parser.py             # ITC frame field extraction
|-- railroad_config.json         # railroad signal config + optional in-motion switch bits
|-- switch_signal_decoder.py     # exhaustive sweep: hex -> possible switch/signal decodes
`-- wiu_resolver.py              # trial process: groups packets, applies hierarchy
tests/
|-- test_packet_parser.py        # frame parser tests
|-- test_switch_signal_decoder.py # decoder algorithm tests
`-- test_wiu_resolver.py         # resolver, hierarchy, and CLI integration tests
packets.hex                      # example packet data
```
