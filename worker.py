from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="PinMazon publisher worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.parse_args()
    print("Publisher worker is disabled in Milestone B. No Pinterest action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
