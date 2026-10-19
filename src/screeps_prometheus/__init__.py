from argparse import ArgumentParser
from pathlib import Path

from prometheus_client import CollectorRegistry, start_http_server

from screeps_prometheus.prometheus import PrometheusConfig, ScreepsCollector, StatScraper
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

    screepsApi = screepsConfig.login()
    statGetter: StatScraper = lambda: screepsApi.memory(path="stats", shard=screepsConfig.shard)

    me: OrderedDict = screepsApi.me() # type: ignore

    print(f"Logged into Screeps as {me["email"]}")

    registry = CollectorRegistry()
    registry.register(ScreepsCollector(prometheusConfig, statGetter))

    print(f'Exposing Metric on localhost:{prometheusConfig.port}')
    server, t = start_http_server(port=prometheusConfig.port, registry=registry)
    server.serve_forever()

    print(f'Shutting down...')
    server.server_close()
    t.join()
    print(f'Bye :)')
