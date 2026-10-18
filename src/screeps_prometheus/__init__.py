from argparse import ArgumentParser
from pathlib import Path
from typing import OrderedDict

from screeps_prometheus.screeps import ScreepsConfig, TokenAuth

parser = ArgumentParser(description='Daemon for Scraping Screeps Stats into Prometheus.')
parser.add_argument("--screeps-token", "-token", type=str)
parser.add_argument("--screeps-config", "-sc", type=Path, default="screeps.json")
parser.add_argument("--prometheus-config", "-pc", type=Path, default="prometheus.json")


def main() -> None:
    args = parser.parse_args()

    if args.screeps_token is not None:
        screepsConfig = ScreepsConfig(TokenAuth(token=args.screeps_token))
    elif args.screeps_config is not None:
        screepsConfig = ScreepsConfig.from_file(args.screeps_config)
    else:
        raise Exception('Missing `--screeps-token` and `--screeps-config`!')

    screepsApi = screepsConfig.login()
    me: OrderedDict = screepsApi.me() # type: ignore

    print(f"Logged into Screeps as {me["email"]}")
