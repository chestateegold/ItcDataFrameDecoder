from argparse import ArgumentParser

from .packet_parser import (
    address_to_decimal_id,
    extract_hex_candidates,
    extract_rr_code,
    parse_packet,
)
from .wiu_resolver import resolve_wius


def main():
    parser = ArgumentParser(description="Decode ITC packets and record switch/signal results per WIU.")
    parser.add_argument("input", help="Input file with plain hex packets (one per line)")
    parser.add_argument("output", help="Output CSV file")
    args = parser.parse_args()

    packets = []

    with open(args.input) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            for candidate in extract_hex_candidates(line):
                packet = parse_packet(candidate)
                if packet is None:
                    continue
                wiu_id = address_to_decimal_id(packet["address_hex"])
                rr = extract_rr_code(wiu_id)
                packets.append({"wiu_id": wiu_id, "rr": rr, "data_hex": packet["data_hex"]})

    resolved = resolve_wius(packets)

    with open(args.output, "w", newline="") as f:
        f.write("wiu_id,rr,success,switches,signals,has_conflict\n")
        for wiu_id, entry in sorted(resolved.items()):
            f.write(
                f"{wiu_id},{entry['rr']},{entry['success']},"
                f"{entry['switches']},{entry['signals']},{entry['has_conflict']}\n"
            )


if __name__ == "__main__":
    main()
