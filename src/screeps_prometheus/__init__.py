
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Callable

type ScreepsStats = dict[str, Any]
type StatScraper = Callable[[], ScreepsStats | None]

from screeps_prometheus.prometheus import PrometheusConfig
from screeps_prometheus.screeps import ScreepsConfig, TokenAuth


parser = ArgumentParser(description='Daemon for Scraping Screeps Stats into Prometheus.')
parser.add_argument("--screeps-token", "-token", type=str, help='Simple way of connecting to main MMO.')
parser.add_argument("--screeps-config", "-sc", type=Path, default="screeps.json", help='Use to connect to worlds other than MMO.')

parser.add_argument("--prometheus-config", "-pc", type=Path, help="Path to a json file containing settings for the Prometheus Exporter")



def main() -> None:
    args = parser.parse_args()

    if args.screeps_token is not None:
        screepsConfig = ScreepsConfig(TokenAuth(token=args.screeps_token))
    elif args.screeps_config is not None:
        screepsConfig = ScreepsConfig.from_file(args.screeps_config)
    else:
        raise Exception('Missing `--screeps-token` and `--screeps-config`!')

    if args.prometheus_config is not None:
        prometheusConfig = PrometheusConfig.from_file(args.prometheus_config)
    else:
        prometheusConfig = PrometheusConfig()

    api = screepsConfig.login()
    scraper = screepsConfig.get_stat_scraper(api)
    prometheusConfig.serve_forever(scraper)
