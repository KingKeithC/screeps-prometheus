from argparse import ArgumentParser
from pathlib import Path

from screeps_prometheus.screeps import ScreepsConfig

parser = ArgumentParser(description='Daemon for Scraping Screeps Stats into Prometheus.')
parser.add_argument("--screeps-config", "-c", type=Path, default="screeps.json")


def main() -> None:
    args = parser.parse_args()
    screepsConfig = ScreepsConfig.from_file(args.screeps_config)

    print("Hello from screeps-prometheus!")
