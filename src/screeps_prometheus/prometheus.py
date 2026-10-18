from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from prometheus_client.metrics_core import CounterMetricFamily, GaugeMetricFamily, Metric
from prometheus_client.registry import Collector


type ScreepsStats = dict[str, Any]
type StatScraper = Callable[[], ScreepsStats | None]

@dataclass
class PrometheusConfig:
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


class ScreepsCollector(Collector):
    def __init__(self, statGetter: StatScraper) -> None:
        self._statGetter = statGetter

    def collect(self) -> Iterable[Metric]:
        print("Collecting stats...")
        stats: ScreepsStats | None = self._statGetter()

        if stats is None or len(stats) == 1:
            print(f"No stats exist")
            return
        elif not stats["ok"]:
            raise Exception(f'Fetching Memory was not OK: {stats["ok"]}')

        for name, value in stats["data"].items():
            yield GaugeMetricFamily(name, f'Auto gauge for {name}', value=value)
