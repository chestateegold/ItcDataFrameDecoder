# ItcDataFrameDecoder

Decodes ITC (Interoperable Train Control) packets to determine switch and signal counts from the data payload.

## Algorithm

The decoder performs an exhaustive sweep to discover how many switches and signals are encoded in a variable-length binary payload. Switches occupy 2 bits each (`01` = normal, `10` = reversed); signals occupy 5 bits each (railroad-specific aspect codes). The boundary between them is not explicitly marked; the algorithm finds it by validating both sides simultaneously.

1. **Validate(s)** - Given a candidate switch count `s`, verify the switch side and signal side together. For railroads with `switchBytesFirst = true`, the decoder validates the first `s * 2` bits as switches, then parses the remainder as 5-bit signal groups. For railroads with `switchBytesFirst = false`, the decoder tries placing the `s * 2` switch bits at each boundary between complete 5-bit signal groups, and only accepts placements whose remaining suffix bits are all `0` byte-padding. Every non-zero signal value must match the railroad's known aspect codes. Returns the signal count, or `None` if either side fails.
2. **Exhaustive sweep** - Try every possible switch count from `0` to `max_s` (total bits / 2). Collect all valid `(switches, signals)` pairs.
3. **Result** - Exactly 1 valid pair -> `"yes"` with the counts. Zero pairs -> `"no"`. Multiple pairs -> `"ambiguous"`.

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
| Decoder | `switch_signal_decoder.py` | Pure algorithm - given a payload hex string and railroad, returns switch/signal counts |
| Trial process | `wiu_resolver.py` | Groups packets by WIU, deduplicates, tries each unique data payload, applies success hierarchy |
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

Output CSV columns: `wiu_id, rr, success, switches, signals`

| wiu_id | rr | success | switches | signals |
|---|---|---|---|---|
| 707660905005 | 076 | yes | 1 | 0 |
| 780221900403 | 802 | yes | 4 | 6 |
| 780221900603 | 802 | yes | 2 | 4 |

**Result hierarchy per WIU:** If any packet returns `"yes"` -> record as success. Otherwise if any returns `"ambiguous"` -> record as ambiguous. Otherwise -> `"no"`.

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
from itc_data_frame_decoder import parse_switches_and_signals

result = parse_switches_and_signals("076", "7600")
# {"success": "yes", "results": {"switches": "0", "signals": "2"}}

result = parse_switches_and_signals("802", "5F80")
# {"success": "ambiguous", "results": []}

result = parse_switches_and_signals("802", "80")
# {"success": "ambiguous", "results": []}

# Hex string input is required.
# parse_switches_and_signals("076", 0x7600) -> TypeError
```

### WIU resolver

```python
from itc_data_frame_decoder.wiu_resolver import resolve_wius

results = resolve_wius([
    {"wiu_id": "707660905005", "rr": "076", "data_hex": "80"},
    {"wiu_id": "707660905005", "rr": "076", "data_hex": "80"},
    {"wiu_id": "780221900403", "rr": "802", "data_hex": "55F7BDEF78"},
])
# {
#   "707660905005": {"rr": "076", "success": "yes", "switches": "1", "signals": "0"},
#   "780221900403": {"rr": "802", "success": "yes", "switches": "4", "signals": "6"},
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
|-- railroad_config.json         # BNSF (076) and UP (802) signal config
|-- switch_signal_decoder.py     # exhaustive sweep: hex -> switch/signal counts
`-- wiu_resolver.py              # trial process: groups packets, applies hierarchy
tests/
|-- test_packet_parser.py        # frame parser tests
|-- test_switch_signal_decoder.py # decoder algorithm tests
`-- test_wiu_resolver.py         # resolver, hierarchy, and CLI integration tests
packets.hex                      # example deduplicated packet data
```
