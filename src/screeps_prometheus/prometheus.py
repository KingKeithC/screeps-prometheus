from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, NoReturn

from prometheus_client import CollectorRegistry, start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

from screeps_prometheus import ScreepsStats, StatScraper


@dataclass
class PrometheusConfig:
    addr: str = "0.0.0.0"
    port: int = 8585
    jobName: str = "screeps-prometheus"
    metricsNamespace: str = "screeps"

    @staticmethod
    def from_file(path: Path) -> PrometheusConfig:
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open('rb') as fh:
            vals = json.load(fh)
            return PrometheusConfig(**vals)

    def serve_forever(self, scraper: StatScraper) -> NoReturn:
        # Create the registry with our custom collector.
        reg = CollectorRegistry()
        reg.register(ScreepsCollector(self, scraper))

        print(f'Serving Metrics on {self.addr}:{self.port}')
        server, t = start_http_server(addr=self.addr, port=self.port, registry=reg)
        server.serve_forever()

        print(f'Shutting down...')
        server.server_close()
        t.join()
        print(f'Bye :)')
        exit(0)


type ReportValue = int | float | dict

class ScreepsCollector(Collector):
    def __init__(self, config: PrometheusConfig, statGetter: StatScraper) -> None:
        self._config = config
        self._statGetter = statGetter

    def collect(self) -> Iterable[Metric]:
        print("Collecting stats...")
        latest: ScreepsStats | None = self._statGetter()
        if latest is None:
            print("Stats fetch was null.")
            return

        # Parse each item in the stat dictionary into a gauge and return the gauge
        for name, value in latest["data"].items():
            key = PrometheusConfig.metricsNamespace + '_' + name

            if isinstance(value, int | float):
                # Single scaler values get their own gauge, with no extra labels.
                yield GaugeMetricFamily(key, f'Auto gauge for {name}', value=value)


            elif isinstance(value, dict): # pyright: ignore[reportUnnecessaryIsInstance]
                # Dicts are treated as a set of labelled values under the same key.
                value: dict[str, int | float | dict[str, int | float]]
                gauge = GaugeMetricFamily(key, f'Auto gauge for {name} family')

                # If the dict contains another dict, add the metrics from the second level under both keys.
                for entry in value.items():
                    if isinstance(entry[1], dict):
                        for [mmName, mmValue] in entry[1].items():
                            gauge.add_metric([entry[0], mmName], mmValue)
                    else:
                        gauge.add_metric([entry[0]], entry[1])

                yield gauge
